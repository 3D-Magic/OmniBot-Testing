/* OMNIBOT TITAN v2.7.2 - Main JavaScript */

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
