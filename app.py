#!/usr/bin/env python3
"""
OMNIBOT v2.7.2 Titan - FULLY FUNCTIONAL TRADING BOT
Main application entry point
"""
import os
import sys
import logging
from flask import Flask, session
from flask_socketio import SocketIO
from flask_session import Session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Import our modules
from config import Settings
from brokers import AlpacaConfig, BinanceConfig, PayPalWallet, BalanceAggregator
from engine import TradingEngine



# ============ TOUCH KEYBOARD HTML ============

KEYBOARD_HTML = """
<style>
#omni-keyboard {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  background: linear-gradient(180deg, #1a1a2e 0%, #0a0a0f 100%);
  border-top: 2px solid #333;
  padding: 8px;
  z-index: 99999;
  display: none;
  user-select: none;
  box-shadow: 0 -4px 20px rgba(0,0,0,0.5);
}
.omni-kb-row { display: flex; justify-content: center; gap: 4px; margin-bottom: 4px; }
.omni-kb-btn {
  flex: 1; max-width: 70px; height: 48px;
  background: linear-gradient(180deg, #444 0%, #333 100%);
  color: #fff; border: 1px solid #555;
  border-radius: 6px; font-size: 18px; font-weight: bold;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all 0.1s;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
}
.omni-kb-btn:hover { background: linear-gradient(180deg, #555 0%, #444 100%); }
.omni-kb-btn:active { background: #00d4ff; color: #000; transform: scale(0.95); }
.omni-kb-btn.wide { flex: 2; max-width: 110px; }
.omni-kb-btn.space { flex: 4; max-width: 280px; }
.omni-kb-btn.special { background: linear-gradient(180deg, #6366f1 0%, #4f46e5 100%); }
</style>
<div id="omni-keyboard">
  <div class="omni-kb-row">
    <div class="omni-kb-btn" data-k="1">1</div><div class="omni-kb-btn" data-k="2">2</div><div class="omni-kb-btn" data-k="3">3</div>
    <div class="omni-kb-btn" data-k="4">4</div><div class="omni-kb-btn" data-k="5">5</div><div class="omni-kb-btn" data-k="6">6</div>
    <div class="omni-kb-btn" data-k="7">7</div><div class="omni-kb-btn" data-k="8">8</div><div class="omni-kb-btn" data-k="9">9</div>
    <div class="omni-kb-btn" data-k="0">0</div>
  </div>
  <div class="omni-kb-row">
    <div class="omni-kb-btn" data-k="q">q</div><div class="omni-kb-btn" data-k="w">w</div><div class="omni-kb-btn" data-k="e">e</div>
    <div class="omni-kb-btn" data-k="r">r</div><div class="omni-kb-btn" data-k="t">t</div><div class="omni-kb-btn" data-k="y">y</div>
    <div class="omni-kb-btn" data-k="u">u</div><div class="omni-kb-btn" data-k="i">i</div><div class="omni-kb-btn" data-k="o">o</div>
    <div class="omni-kb-btn" data-k="p">p</div>
  </div>
  <div class="omni-kb-row">
    <div class="omni-kb-btn" data-k="a">a</div><div class="omni-kb-btn" data-k="s">s</div><div class="omni-kb-btn" data-k="d">d</div>
    <div class="omni-kb-btn" data-k="f">f</div><div class="omni-kb-btn" data-k="g">g</div><div class="omni-kb-btn" data-k="h">h</div>
    <div class="omni-kb-btn" data-k="j">j</div><div class="omni-kb-btn" data-k="k">k</div><div class="omni-kb-btn" data-k="l">l</div>
  </div>
  <div class="omni-kb-row">
    <div class="omni-kb-btn wide special" data-k="shift">&#8679;</div>
    <div class="omni-kb-btn" data-k="z">z</div><div class="omni-kb-btn" data-k="x">x</div>
    <div class="omni-kb-btn" data-k="c">c</div><div class="omni-kb-btn" data-k="v">v</div>
    <div class="omni-kb-btn" data-k="b">b</div><div class="omni-kb-btn" data-k="n">n</div>
    <div class="omni-kb-btn" data-k="m">m</div>
    <div class="omni-kb-btn wide special" data-k="bksp">&#9003;</div>
  </div>
  <div class="omni-kb-row">
    <div class="omni-kb-btn wide special" data-k="toggle">123</div>
    <div class="omni-kb-btn space" data-k=" ">Space</div>
    <div class="omni-kb-btn wide special" data-k="enter">&#9166;</div>
  </div>
</div>
<script>
(function() {
  let kb = document.getElementById('omni-keyboard');
  let activeInput = null;
  let shifted = false;
  let symMode = false;
  const letters = "abcdefghijklmnopqrstuvwxyz";
  const syms1 = "1234567890";
  const syms2 = "!@#$%^&*()";
  
  function updateLabels() {
    document.querySelectorAll('.omni-kb-btn[data-k]').forEach(btn => {
      let k = btn.getAttribute('data-k');
      if (k.length === 1 && letters.includes(k)) {
        btn.textContent = shifted ? k.toUpperCase() : k.toLowerCase();
      }
    });
  }
  
  function insertChar(ch) {
    if (!activeInput) return;
    let start = activeInput.selectionStart;
    let end = activeInput.selectionEnd;
    let val = activeInput.value;
    activeInput.value = val.substring(0, start) + ch + val.substring(end);
    activeInput.selectionStart = activeInput.selectionEnd = start + ch.length;
    activeInput.dispatchEvent(new Event('input', {bubbles:true}));
  }
  
  kb.addEventListener('click', function(e) {
    let btn = e.target.closest('.omni-kb-btn');
    if (!btn) return;
    let k = btn.getAttribute('data-k');
    if (!k) return;
    
    if (k === 'shift') { shifted = !shifted; updateLabels(); return; }
    if (k === 'bksp') {
      if (activeInput) {
        let start = activeInput.selectionStart;
        let end = activeInput.selectionEnd;
        let val = activeInput.value;
        if (start === end && start > 0) {
          activeInput.value = val.substring(0, start-1) + val.substring(end);
          activeInput.selectionStart = activeInput.selectionEnd = start - 1;
        } else {
          activeInput.value = val.substring(0, start) + val.substring(end);
          activeInput.selectionStart = activeInput.selectionEnd = start;
        }
        activeInput.dispatchEvent(new Event('input', {bubbles:true}));
      }
      return;
    }
    if (k === 'enter') {
      kb.style.display = 'none';
      if (activeInput) activeInput.blur();
      return;
    }
    if (k === 'toggle') {
      symMode = !symMode;
      document.querySelectorAll('.omni-kb-row:first-child .omni-kb-btn').forEach((btn, i) => {
        if (syms1[i]) {
          btn.setAttribute('data-k', symMode ? syms2[i] : syms1[i]);
          btn.textContent = symMode ? syms2[i] : syms1[i];
        }
      });
      btn.textContent = symMode ? "abc" : "123";
      return;
    }
    
    let ch = k;
    if (k.length === 1 && letters.includes(k)) {
      ch = shifted ? k.toUpperCase() : k.toLowerCase();
    }
    insertChar(ch);
    if (shifted) { shifted = false; updateLabels(); }
  });
  
  function showKeyboard(el) {
    activeInput = el;
    kb.style.display = 'block';
    el.scrollIntoView({behavior: 'smooth', block: 'center'});
  }
  
  function hideKeyboard() {
    kb.style.display = 'none';
    activeInput = null;
  }
  
  document.querySelectorAll('input, textarea').forEach(el => {
    el.addEventListener('focus', () => showKeyboard(el));
  });
  
  document.addEventListener('click', e => {
    if (e.target.matches('input, textarea')) return;
    if (e.target.closest('#omni-keyboard')) return;
    hideKeyboard();
  });
})();
</script>
"""




# ============ TOUCH SCROLL + KEYBOARD INJECTION ============
SCROLL_CSS = """
<style>
html,body,.main-content,.sidebar,.content,.nav-menu{-webkit-overflow-scrolling:touch !important}
html::-webkit-scrollbar,body::-webkit-scrollbar,.main-content::-webkit-scrollbar,.sidebar::-webkit-scrollbar,.content::-webkit-scrollbar,.nav-menu::-webkit-scrollbar{width:6px}
html::-webkit-scrollbar-track{background:rgba(0,0,0,0.2)}
html::-webkit-scrollbar-thumb{background:#333;border-radius:3px}
html::-webkit-scrollbar-thumb:hover{background:#555}
html{scrollbar-width:thin;-ms-overflow-style:auto}
body{overflow-x:hidden}
</style>
"""

KEYBOARD_JS = """
<script>
(function(){
  if(document.getElementById('osk')) return;
  var kbd = document.createElement('div');
  kbd.id = 'osk';
  kbd.innerHTML = '<style>#osk{position:fixed;bottom:0;left:0;right:0;background:#0f0f1a;border-top:2px solid #333;padding:6px;z-index:99999;display:none}.osk-row{display:flex;justify-content:center;gap:3px;margin-bottom:3px}.osk-key{min-width:28px;height:42px;padding:0 8px;background:#2a2a3a;color:#fff;border:1px solid #444;border-radius:5px;font-size:15px;font-weight:600;display:flex;align-items:center;justify-content:center;cursor:pointer;-webkit-tap-highlight-color:transparent;touch-action:manipulation;user-select:none}.osk-key:active{background:#00d4ff;color:#000;border-color:#00d4ff}.osk-key.w2{min-width:56px}.osk-key.w3{min-width:84px;flex:1;max-width:200px}.osk-key.sp{background:#3b3b5a}</style>'+
  '<div class="osk-row"><div class="osk-key" data-c="1">1</div><div class="osk-key" data-c="2">2</div><div class="osk-key" data-c="3">3</div><div class="osk-key" data-c="4">4</div><div class="osk-key" data-c="5">5</div><div class="osk-key" data-c="6">6</div><div class="osk-key" data-c="7">7</div><div class="osk-key" data-c="8">8</div><div class="osk-key" data-c="9">9</div><div class="osk-key" data-c="0">0</div></div>'+
  '<div class="osk-row"><div class="osk-key" data-c="q">q</div><div class="osk-key" data-c="w">w</div><div class="osk-key" data-c="e">e</div><div class="osk-key" data-c="r">r</div><div class="osk-key" data-c="t">t</div><div class="osk-key" data-c="y">y</div><div class="osk-key" data-c="u">u</div><div class="osk-key" data-c="i">i</div><div class="osk-key" data-c="o">o</div><div class="osk-key" data-c="p">p</div></div>'+
  '<div class="osk-row"><div class="osk-key" data-c="a">a</div><div class="osk-key" data-c="s">s</div><div class="osk-key" data-c="d">d</div><div class="osk-key" data-c="f">f</div><div class="osk-key" data-c="g">g</div><div class="osk-key" data-c="h">h</div><div class="osk-key" data-c="j">j</div><div class="osk-key" data-c="k">k</div><div class="osk-key" data-c="l">l</div></div>'+
  '<div class="osk-row"><div class="osk-key w2 sp" data-c="SHIFT">&#8679;</div><div class="osk-key" data-c="z">z</div><div class="osk-key" data-c="x">x</div><div class="osk-key" data-c="c">c</div><div class="osk-key" data-c="v">v</div><div class="osk-key" data-c="b">b</div><div class="osk-key" data-c="n">n</div><div class="osk-key" data-c="m">m</div><div class="osk-key w2 sp" data-c="DEL">&#9003;</div></div>'+
  '<div class="osk-row"><div class="osk-key w2 sp" data-c=".">.</div><div class="osk-key w3" data-c=" ">Space</div><div class="osk-key w2 sp" data-c="ENTER">Done</div></div>';
  document.body.appendChild(kbd);
  var target=null, shift=false, lowers='qwertyuiopasdfghjklzxcvbnm';
  function type(ch){ if(!target)return; var s=target.selectionStart,e=target.selectionEnd,v=target.value; target.value=v.slice(0,s)+ch+v.slice(e); target.selectionStart=target.selectionEnd=s+ch.length; target.dispatchEvent(new Event('input',{bubbles:true})); }
  function del(){ if(!target)return; var s=target.selectionStart,e=target.selectionEnd,v=target.value; if(s===e&&s>0){target.value=v.slice(0,s-1)+v.slice(e);target.selectionStart=target.selectionEnd=s-1;}else{target.value=v.slice(0,s)+v.slice(e);target.selectionStart=target.selectionEnd=s;} target.dispatchEvent(new Event('input',{bubbles:true})); }
  function update(){ document.querySelectorAll('.osk-key[data-c]').forEach(function(b){ var c=b.getAttribute('data-c'); if(c.length===1&&lowers.indexOf(c)!==-1) b.textContent=shift?c.toUpperCase():c; }); }
  kbd.addEventListener('touchstart',function(ev){ ev.preventDefault(); ev.stopPropagation(); var btn=ev.target.closest('.osk-key'); if(!btn)return; var c=btn.getAttribute('data-c'); if(c==='SHIFT'){shift=!shift;update();return;} if(c==='DEL'){del();return;} if(c==='ENTER'){kbd.style.display='none';if(target)target.blur();return;} var out=c; if(c.length===1&&lowers.indexOf(c)!==-1) out=shift?c.toUpperCase():c; type(out); if(shift){shift=false;update();} },{passive:false}); kbd.addEventListener('mousedown',function(ev){ ev.preventDefault(); ev.stopPropagation(); var btn=ev.target.closest('.osk-key'); if(!btn)return; var c=btn.getAttribute('data-c'); if(c==='SHIFT'){shift=!shift;update();return;} if(c==='DEL'){del();return;} if(c==='ENTER'){kbd.style.display='none';if(target)target.blur();return;} var out=c; if(c.length===1&&lowers.indexOf(c)!==-1) out=shift?c.toUpperCase():c; type(out); if(shift){shift=false;update();} }); kbd.addEventListener('click',function(ev){ ev.preventDefault(); ev.stopPropagation(); var btn=ev.target.closest('.osk-key'); if(!btn)return; var c=btn.getAttribute('data-c'); if(c==='SHIFT'){shift=!shift;update();return;} if(c==='DEL'){del();return;} if(c==='ENTER'){kbd.style.display='none';if(target)target.blur();return;} var out=c; if(c.length===1&&lowers.indexOf(c)!==-1) out=shift?c.toUpperCase():c; type(out); if(shift){shift=false;update();} });
  function show(el){ target=el; kbd.style.display='block'; el.scrollIntoView({behavior:'smooth',block:'center'}); }
  function hide(){ kbd.style.display='none'; target=null; }
  document.querySelectorAll('input,textarea').forEach(function(el){ el.addEventListener('focus',function(){show(el);}); });
  document.addEventListener('click',function(e){ if(e.target.matches('input,textarea'))return; if(e.target.closest('#osk'))return; hide(); });
})();
</script>
"""

def inject_touch_keyboard(response):
    ct = response.content_type or ''
    if 'text/html' in ct:
        try:
            text = response.get_data(as_text=True)
            if text:
                # Inject scroll CSS in <head> on all pages
                if 'html{scrollbar-width' not in text:
                    if '</head>' in text:
                        text = text.replace('</head>', SCROLL_CSS + '</head>')
                    elif '<html' in text:
                        text = text.replace('<html', SCROLL_CSS + '<html')
                    else:
                        text = SCROLL_CSS + text
                # Inject keyboard before </body> (skip if page already has inline keyboard)
                if 'id="osk"' not in text and 'id="omni-keyboard"' not in text:
                    kb = KEYBOARD_JS if 'KEYBOARD_JS' in globals() else KEYBOARD_HTML
                    if '</body>' in text:
                        text = text.replace('</body>', kb + '</body>')
                    else:
                        text = text + kb
                response.set_data(text)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"inject_touch_keyboard error: {e}")
    return response

def create_app():
    """Application factory - creates and configures the Flask app"""
    
    # Create Flask app
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.after_request(inject_touch_keyboard)
    app.secret_key = os.environ.get('SECRET_KEY', 'omnibot-secret-key-change-in-production')
    
    # Session configuration
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
    Session(app)
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # Initialize settings
    settings = Settings()
    logger.info(f"[APP] Loaded settings from {settings.filepath}")
    
    # Initialize balance aggregator
    balance_aggregator = BalanceAggregator()
    
    # Initialize brokers from settings
    if settings.is_configured('alpaca'):
        alpaca_config = settings.get_broker_config('alpaca')
        if alpaca_config.get('enabled', True):
            alpaca = AlpacaConfig(
                api_key=alpaca_config.get('api_key'),
                secret_key=alpaca_config.get('secret_key'),
                paper=alpaca_config.get('paper', True)
            )
            balance_aggregator.add_broker('alpaca', alpaca)
            alpaca.connect()
    
    if settings.is_configured('binance'):
        binance_config = settings.get_broker_config('binance')
        if binance_config.get('enabled', True):
            binance = BinanceConfig(
                api_key=binance_config.get('api_key'),
                secret_key=binance_config.get('secret_key'),
                testnet=binance_config.get('testnet', True)
            )
            balance_aggregator.add_broker('binance', binance)
            binance.connect()
    
    # Initialize PayPal wallet
    if settings.is_configured('paypal'):
        paypal_config = settings.get_broker_config('paypal')
        paypal = PayPalWallet(
            client_id=paypal_config.get('client_id'),
            client_secret=paypal_config.get('client_secret'),
            sandbox=paypal_config.get('sandbox', True)
        )
        balance_aggregator.add_broker('paypal', paypal)
        if paypal_config.get('enabled', False):
            paypal.connect()
    
    # Connect all configured brokers
    try:
        balance_aggregator.connect_all()
    except Exception as e:
        logger.warning(f"[APP] Some brokers failed to connect at startup: {e}")
    
    # Initialize Interactive Brokers (if configured)
    if settings.is_configured('interactive_brokers'):
        try:
            from brokers.ib_gateway_config import IBGatewayConfig
            ib_config = settings.get_broker_config('interactive_brokers')
            ib = IBGatewayConfig(
                host=ib_config.get('host', '127.0.0.1'),
                port=ib_config.get('port', 7497),
                client_id=ib_config.get('client_id', 1)
            )
            balance_aggregator.add_broker('interactive_brokers', ib)
            if ib_config.get('enabled', False):
                ib.connect()
        except Exception as e:
            logger.warning(f"[APP] Could not initialize Interactive Brokers: {e}")
    
    # Initialize screen manager (for Raspberry Pi)
    try:
        from src.system.screen_manager import ScreenManager
        screen_manager = ScreenManager(settings.get_all())
        app.screen_manager = screen_manager
        logger.info("[APP] Screen manager initialized")
    except Exception as e:
        logger.warning(f"[APP] Screen manager not available: {e}")
        app.screen_manager = None
    
    # Initialize trading engine
    trading_engine = TradingEngine(balance_aggregator, settings)
    
    # Store in app context
    app.settings = settings
    app.balance_aggregator = balance_aggregator
    app.trading_engine = trading_engine
    app.socketio = socketio
    
    # Import and register dashboard blueprint
    from src.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)
    
    # Start trading engine if enabled
    if settings.get('trading_enabled', False):
        trading_engine.start()
    
    logger.info("[APP] Application initialized successfully")
    
    return app, socketio


def main():
    """Main entry point"""
    app, socketio = create_app()
    
    # Get host and port from settings
    host = app.settings.get('dashboard_host', '0.0.0.0')
    port = app.settings.get('dashboard_port', 8081)
    
    logger.info(f"[APP] Starting OMNIBOT v2.7.2 Titan on {host}:{port}")
    logger.info(f"[APP] Dashboard: http://{host}:{port}")
    
    # Run with SocketIO
    socketio.run(app, host=host, port=port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
