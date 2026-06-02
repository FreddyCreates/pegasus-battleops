/**
 * Spatium Computationis — Interactive App
 * WebSocket-powered real-time console application
 */

class InteractiveApp {
    constructor() {
        this.ws = null;
        this.url = `ws://${window.location.host}/ws/app`;
        this.consoleEl = document.getElementById('console-output');
        this.eventLogEl = document.getElementById('event-log');
        this.reconnectAttempts = 0;
        this.maxReconnect = 10;
    }

    connect() {
        this._log('system', 'Connecting to WebSocket...');
        this._updateStatus('connecting');

        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            this.reconnectAttempts = 0;
            this._updateStatus('online');
            this._log('system', 'WebSocket connected ✓');
        };

        this.ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            this._handleMessage(msg);
        };

        this.ws.onerror = () => {
            this._log('error', 'WebSocket error');
        };

        this.ws.onclose = () => {
            this._updateStatus('offline');
            this._log('system', 'WebSocket disconnected');
            this._scheduleReconnect();
        };
    }

    send(action, data = {}) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            this._log('error', 'Not connected');
            return;
        }
        const msg = { action, ...data };
        this.ws.send(JSON.stringify(msg));
        this._log('system', `Sent: ${action}`);
    }

    _handleMessage(msg) {
        switch (msg.type) {
            case 'welcome':
                this._log('event', `⌬ ${msg.message} (${msg.connections} connections)`);
                break;
            case 'pong':
                this._log('response', `Pong — ${msg.timestamp}`);
                break;
            case 'status':
                this._log('response', `Status: ${JSON.stringify(msg.data)}`);
                this._updateStats(msg.data);
                break;
            case 'task_submitted':
                this._log('event', `Task submitted: ${msg.data.task_type} [${msg.data.task_id}]`);
                this._addEvent(msg);
                break;
            case 'subscribed':
                this._log('event', `Subscribed to: ${msg.channels.join(', ')}`);
                break;
            case 'error':
                this._log('error', msg.message);
                break;
            default:
                this._log('event', `${msg.type}: ${JSON.stringify(msg.data || msg).slice(0, 120)}`);
                this._addEvent(msg);
        }
    }

    _log(type, message) {
        const line = document.createElement('div');
        line.className = `console-line ${type}`;
        line.innerHTML = `
            <span class="line-time">${SC.shortTime()}</span>
            <span class="line-type">${type.slice(0, 4)}</span>
            <span class="line-msg">${message}</span>
        `;
        this.consoleEl.appendChild(line);
        this.consoleEl.scrollTop = this.consoleEl.scrollHeight;
    }

    _addEvent(msg) {
        if (!this.eventLogEl) return;

        // Remove placeholder
        const placeholder = this.eventLogEl.querySelector('.feed-placeholder');
        if (placeholder) placeholder.remove();

        const entry = document.createElement('div');
        entry.className = 'event-entry';
        entry.innerHTML = `
            <div class="event-type">${msg.type}</div>
            <div class="event-data">${JSON.stringify(msg.data || {}).slice(0, 100)}</div>
            <div class="event-time">${SC.shortTime()}</div>
        `;
        this.eventLogEl.insertBefore(entry, this.eventLogEl.firstChild);

        while (this.eventLogEl.children.length > 30) {
            this.eventLogEl.removeChild(this.eventLogEl.lastChild);
        }
    }

    _updateStatus(status) {
        const dot = document.getElementById('ws-status');
        const text = document.getElementById('ws-status-text');
        if (dot) dot.className = `status-dot ${status}`;
        if (text) text.textContent = status === 'online' ? 'Connected' : status === 'connecting' ? 'Connecting...' : 'Disconnected';
    }

    _updateStats(data) {
        const el = (id, val) => {
            const e = document.getElementById(id);
            if (e) e.textContent = val;
        };
        el('stat-connections', data.connections);
        el('stat-sse', data.sse_subscribers);
        el('stat-system', data.system);
    }

    _scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnect) {
            this._log('error', 'Max reconnection attempts reached');
            return;
        }
        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 30000);
        this._log('system', `Reconnecting in ${(delay / 1000).toFixed(1)}s...`);
        setTimeout(() => this.connect(), delay);
    }

    clear() {
        this.consoleEl.innerHTML = '';
        this._log('system', 'Console cleared');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const app = new InteractiveApp();
    app.connect();
    window._app = app;

    // Button handlers
    document.getElementById('btn-clear')?.addEventListener('click', () => app.clear());
    document.getElementById('btn-reconnect')?.addEventListener('click', () => app.connect());
    document.getElementById('btn-ping')?.addEventListener('click', () => app.send('ping'));

    // Send button
    document.getElementById('btn-send')?.addEventListener('click', () => {
        const action = document.getElementById('input-action').value;
        const payloadStr = document.getElementById('input-payload').value;

        let extra = {};
        if (payloadStr) {
            try {
                extra = JSON.parse(payloadStr);
            } catch (e) {
                extra = { payload: payloadStr };
            }
        }
        app.send(action, extra);
    });

    // Enter to send
    document.getElementById('input-payload')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') document.getElementById('btn-send').click();
    });

    // Quick action buttons
    document.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.action;
            const type = btn.dataset.type;
            app.send(action, { task_type: type, payload: {} });
        });
    });
});
