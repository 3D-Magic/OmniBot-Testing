"""
OMNIBOT v2.6 Sentinel - Free Sentiment Analysis
Uses Reddit API and RSS feeds (zero cost)
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import feedparser
import aiohttp
import asyncpraw
from textblob import TextBlob

from config.settings import SENTIMENT

logger = logging.getLogger(__name__)

@dataclass
class SentimentScore:
    """Sentiment analysis result"""
    source: str
    symbol: str
    score: float  # -1.0 to 1.0
    volume: int   # Number of mentions
    timestamp: datetime
    sample_texts: List[str]

class SentimentAnalyzer:
    """Analyzes market sentiment from free sources"""

    def __init__(self):
        self.config = SENTIMENT
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
        self.reddit = None
        self.session = None

    async def initialize(self):
        """Initialize API connections"""
        if self.config["sources"]["reddit"]["enabled"]:
            await self._init_reddit()
        self.session = aiohttp.ClientSession()

    async def _init_reddit(self):
        """Initialize Reddit API (free, no auth required for read-only)"""
        try:
            # Using read-only mode (no API key needed for public data)
            self.reddit = asyncpraw.Reddit(
                client_id="OMNIBOT_READ_ONLY",
                client_secret=None,
                user_agent="OMNIBOTv2.6-SentimentAnalyzer"
            )
            logger.info("Reddit API initialized (read-only)")
        except Exception as e:
            logger.warning(f"Could not initialize Reddit: {e}")
            self.reddit = None

    async def analyze_symbol(self, symbol: str) -> Optional[SentimentScore]:
        """Analyze sentiment for a stock symbol"""
        if not self.config["enabled"]:
            return None

        # Check cache
        cache_key = f"sentiment_{symbol}"
        if cache_key in self.cache:
            cached_time, cached_result = self.cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=self.cache_timeout):
                return cached_result

        scores = []
        volumes = []
        sample_texts = []

        # Reddit sentiment
        if self.config["sources"]["reddit"]["enabled"] and self.reddit:
            reddit_sentiment = await self._analyze_reddit(symbol)
            if reddit_sentiment:
                scores.append(reddit_sentiment["score"] * 0.4)  # 40% weight
                volumes.append(reddit_sentiment["volume"])
                sample_texts.extend(reddit_sentiment["samples"])

        # RSS sentiment
        if self.config["sources"]["rss"]["enabled"]:
            rss_sentiment = await self._analyze_rss(symbol)
            if rss_sentiment:
                scores.append(rss_sentiment["score"] * 0.6)  # 60% weight
                volumes.append(rss_sentiment["volume"])
                sample_texts.extend(rss_sentiment["samples"])

        if not scores:
            return None

        # Calculate weighted average
        total_volume = sum(volumes)
        if total_volume == 0:
            return None

        weighted_score = sum(
            score * (volume / total_volume)
            for score, volume in zip(scores, volumes)
        )

        result = SentimentScore(
            source="combined",
            symbol=symbol,
            score=weighted_score,
            volume=total_volume,
            timestamp=datetime.now(),
            sample_texts=sample_texts[:5]  # Keep top 5 samples
        )

        # Update cache
        self.cache[cache_key] = (datetime.now(), result)

        return result

    async def _analyze_reddit(self, symbol: str) -> Optional[Dict]:
        """Analyze Reddit sentiment for symbol"""
        if not self.reddit:
            return None

        try:
            subreddits = self.config["sources"]["reddit"]["subreddits"]
            mentions = []
            texts = []

            # Search each subreddit
            for subreddit_name in subreddits:
                try:
                    subreddit = await self.reddit.subreddit(subreddit_name)

                    # Search for symbol (case insensitive)
                    async for submission in subreddit.search(
                        f"{symbol} OR ${symbol}",
                        sort="new",
                        time_filter="day",
                        limit=25
                    ):
                        text = f"{submission.title} {submission.selftext}"
                        mentions.append(text)

                    # Check comments in hot posts
                    async for submission in subreddit.hot(limit=10):
                        submission.comments.replace_more(limit=0)
                        async for comment in submission.comments:
                            if symbol.upper() in comment.body.upper():
                                mentions.append(comment.body)
                                if len(mentions) >= 50:  # Limit for performance
                                    break

                except Exception as e:
                    logger.debug(f"Reddit search error in {subreddit_name}: {e}")
                    continue

            if not mentions:
                return None

            # Analyze sentiment
            sentiments = []
            for text in mentions[:50]:  # Limit to 50 mentions
                blob = TextBlob(text)
                sentiments.append(blob.sentiment.polarity)
                if len(texts) < 3:  # Keep sample texts
                    texts.append(text[:200])

            avg_sentiment = sum(sentiments) / len(sentiments)

            return {
                "score": avg_sentiment,
                "volume": len(mentions),
                "samples": texts
            }

        except Exception as e:
            logger.error(f"Reddit analysis error: {e}")
            return None

    async def _analyze_rss(self, symbol: str) -> Optional[Dict]:
        """Analyze RSS feed sentiment for symbol"""
        try:
            feeds = self.config["sources"]["rss"]["feeds"]
            mentions = []
            texts = []

            for feed_url in feeds:
                try:
                    feed = feedparser.parse(feed_url)

                    for entry in feed.entries[:20]:  # Last 20 entries
                        title = entry.get("title", "")
                        summary = entry.get("summary", "")
                        content = f"{title} {summary}"

                        # Check if symbol mentioned
                        if symbol.upper() in content.upper():
                            mentions.append(content)
                            if len(texts) < 3:
                                texts.append(content[:200])

                except Exception as e:
                    logger.debug(f"RSS parse error for {feed_url}: {e}")
                    continue

            if not mentions:
                return None

            # Analyze sentiment
            sentiments = []
            for text in mentions:
                blob = TextBlob(text)
                sentiments.append(blob.sentiment.polarity)

            avg_sentiment = sum(sentiments) / len(sentiments)

            return {
                "score": avg_sentiment,
                "volume": len(mentions),
                "samples": texts
            }

        except Exception as e:
            logger.error(f"RSS analysis error: {e}")
            return None

    def get_sentiment_trend(self, symbol: str, hours: int = 24) -> Dict:
        """Get sentiment trend over time"""
        # This would require historical storage
        # For now, return current sentiment with trend estimate
        current = self.cache.get(f"sentiment_{symbol}")

        if not current:
            return {"trend": "unknown", "current": 0, "change": 0}

        return {
            "trend": "positive" if current[1].score > 0.2 else "negative" if current[1].score < -0.2 else "neutral",
            "current": current[1].score,
            "change": 0,  # Would calculate from historical
            "volume": current[1].volume
        }

    async def get_market_sentiment(self) -> Dict[str, float]:
        """Get overall market sentiment (SPY, QQQ, etc.)"""
        market_etfs = ["SPY", "QQQ", "IWM", "VIX"]
        sentiments = {}

        for etf in market_etfs:
            result = await self.analyze_symbol(etf)
            if result:
                sentiments[etf] = result.score

        return sentiments

    async def close(self):
        """Close connections"""
        if self.reddit:
            await self.reddit.close()
        if self.session:
            await self.session.close()
