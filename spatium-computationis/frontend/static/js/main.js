/**
 * Spatium Computationis — Main JS
 * Core utilities and API client
 */

const SC = {
    api: {
        base: '',

        async get(path) {
            const resp = await fetch(`${this.base}${path}`);
            if (!resp.ok) throw new Error(`API error: ${resp.status}`);
            return resp.json();
        },

        async post(path, data) {
            const resp = await fetch(`${this.base}${path}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (!resp.ok) throw new Error(`API error: ${resp.status}`);
            return resp.json();
        },
    },

    // Format timestamp
    formatTime(isoString) {
        const d = new Date(isoString);
        return d.toLocaleTimeString('en-US', { hour12: false });
    },

    // Short time for console
    shortTime() {
        return new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    },
};

// Load platform status on page load
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const status = await SC.api.get('/api/platform/status');
        const el = document.getElementById('system-status');
        if (el) el.textContent = 'Active';

        const agentEl = document.getElementById('agent-count');
        if (agentEl && status.total_agents !== undefined) {
            agentEl.textContent = status.total_agents;
        }
    } catch (e) {
        const el = document.getElementById('system-status');
        if (el) el.textContent = 'Connecting...';
    }
});
