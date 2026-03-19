"""
OMNIBOT v2.6 Sentinel - Sentiment Analyzer
Free sentiment analysis using Reddit and RSS feeds
"""

import logging
import re
from typing import Dict, List
from collections import defaultdict
from datetime import datetime, timedelta

from config.settings import SENTIMENT

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analyzes market sentiment from free sources"""

    def __init__(self):
        self.config = SENTIMENT
        self.cache = {}
        self.last_update = None

        # Initialize sources
        self.sources = {}
        if "reddit" in self.config.get("sources", []):
            self.sources["reddit"] = RedditSource(self.config)
        if "rss" in self.config.get("sources", []):
            self.sources["rss"] = RSSSource(self.config)

        logger.info(f"Sentiment Analyzer initialized with {len(self.sources)} sources")

    def analyze(self, symbols: List[str] = None) -> Dict:
        """Analyze sentiment for given symbols"""
        results = {
            "overall": 0.0,
            "trend": "neutral",
            "sources": {},
            "symbols": {},
            "timestamp": datetime.now().isoformat()
        }

        try:
            # Collect sentiment from all sources
            all_mentions = defaultdict(list)

            for source_name, source in self.sources.items():
                try:
                    mentions = source.fetch_mentions(symbols)
                    all_mentions[source_name].extend(mentions)

                    # Calculate source-specific sentiment
                    source_sentiment = self._calculate_sentiment(mentions)
                    results["sources"][source_name] = {
                        "score": source_sentiment,
                        "volume": len(mentions)
                    }

                except Exception as e:
                    logger.error(f"Error fetching from {source_name}: {e}")

            # Calculate per-symbol sentiment
            if symbols:
                for symbol in symbols:
                    symbol_mentions = []
                    for source_mentions in all_mentions.values():
                        symbol_mentions.extend([m for m in source_mentions if symbol.upper() in m.get("text", "").upper()])

                    results["symbols"][symbol] = self._calculate_sentiment(symbol_mentions)

            # Calculate overall sentiment
            if results["sources"]:
                overall = sum(s["score"] for s in results["sources"].values()) / len(results["sources"])
                results["overall"] = overall
                results["trend"] = "positive" if overall > 0.2 else "negative" if overall < -0.2 else "neutral"

        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")

        return results

    def _calculate_sentiment(self, mentions: List[Dict]) -> float:
        """Calculate average sentiment score"""
        if not mentions:
            return 0.0

        scores = [m.get("sentiment", 0) for m in mentions]
        return sum(scores) / len(scores)


class RedditSource:
    """Reddit sentiment source"""

    def __init__(self, config):
        self.config = config
        self.subreddits = config.get("reddit_subreddits", ["wallstreetbets", "stocks", "investing"])

    def fetch_mentions(self, symbols: List[str] = None) -> List[Dict]:
        """Fetch mentions from Reddit (mock implementation)"""
        # In production, use PRAW library with Reddit API
        # This is a simplified mock for demonstration
        mentions = []

        # Mock data for testing
        mock_posts = [
            {"text": "AAPL looking bullish today! 🚀", "sentiment": 0.8},
            {"text": "TSLA is overvalued imo", "sentiment": -0.3},
            {"text": "NVDA crushing earnings!", "sentiment": 0.9},
            {"text": "Market is crashing help", "sentiment": -0.7},
            {"text": "MSFT stable growth", "sentiment": 0.4}
        ]

        for post in mock_posts:
            mentions.append({
                "source": "reddit",
                "text": post["text"],
                "sentiment": post["sentiment"],
                "timestamp": datetime.now().isoformat()
            })

        return mentions


class RSSSource:
    """RSS feed sentiment source"""

    def __init__(self, config):
        self.config = config
        self.feeds = config.get("rss_feeds", [])

    def fetch_mentions(self, symbols: List[str] = None) -> List[Dict]:
        """Fetch mentions from RSS feeds (mock implementation)"""
        # In production, use feedparser library
        mentions = []

        # Mock data
        mock_headlines = [
            {"text": "Tech stocks rally on strong earnings", "sentiment": 0.6},
            {"text": "Market volatility increases amid uncertainty", "sentiment": -0.4},
            {"text": "Analysts upgrade semiconductor sector", "sentiment": 0.5}
        ]

        for headline in mock_headlines:
            mentions.append({
                "source": "rss",
                "text": headline["text"],
                "sentiment": headline["sentiment"],
                "timestamp": datetime.now().isoformat()
            })

        return mentions
