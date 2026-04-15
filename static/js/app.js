/* OMNIBOT TITAN v2.7.2 - Main JavaScript */

// Touch Keyboard Injection
const KEYBOARD_HTML = `
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
`;

// Initialize touch keyboard
document.addEventListener('DOMContentLoaded', function() {
    // Inject keyboard HTML
    const div = document.createElement('div');
    div.innerHTML = KEYBOARD_HTML;
    document.body.appendChild(div);
    
    // Initialize keyboard functionality
    initTouchKeyboard();
});

function initTouchKeyboard() {
    const kb = document.getElementById('omni-keyboard');
    if (!kb) return;
    
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
    
    // Attach to all inputs
    document.querySelectorAll('input, textarea').forEach(el => {
        el.addEventListener('focus', () => showKeyboard(el));
    });
    
    document.addEventListener('click', e => {
        if (e.target.matches('input, textarea')) return;
        if (e.target.closest('#omni-keyboard')) return;
        hideKeyboard();
    });
}

// API Helper Functions
async function apiGet(endpoint) {
    const res = await fetch('/api' + endpoint);
    return res.json();
}

async function apiPost(endpoint, data) {
    const res = await fetch('/api' + endpoint, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    return res.json();
}
