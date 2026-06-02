/**
 * Spatium Computationis — SSE Client
 * Handles Server-Sent Events for real-time dashboard updates
 */

class SSEClient {
    constructor(url = '/sse/events') {
        this.url = url;
        this.source = null;
        this.handlers = {};
        this.reconnectDelay = 3000;
        this.maxReconnectDelay = 30000;
    }

    connect() {
        this.source = new EventSource(this.url);

        this.source.addEventListener('connected', (e) => {
            const data = JSON.parse(e.data);
            this._updateStatus('online');
            this._emit('connected', data);
        });

        this.source.addEventListener('task_submitted', (e) => {
            const data = JSON.parse(e.data);
            this._addFeedItem('task_submitted', data);
            this._emit('task_submitted', data);
        });

        this.source.addEventListener('task_completed', (e) => {
            const data = JSON.parse(e.data);
            this._addFeedItem('task_completed', data);
            this._emit('task_completed', data);
        });

        this.source.addEventListener('agent_status', (e) => {
            const data = JSON.parse(e.data);
            this._emit('agent_status', data);
        });

        this.source.addEventListener('pipeline_update', (e) => {
            const data = JSON.parse(e.data);
            this._addFeedItem('pipeline_update', data);
            this._emit('pipeline_update', data);
        });

        this.source.addEventListener('field_update', (e) => {
            const data = JSON.parse(e.data);
            this._addFeedItem('field_update', data);
            this._emit('field_update', data);
        });

        this.source.onerror = () => {
            this._updateStatus('offline');
            this.source.close();
            setTimeout(() => this.connect(), this.reconnectDelay);
            this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxReconnectDelay);
        };

        this.source.onopen = () => {
            this.reconnectDelay = 3000;
            this._updateStatus('online');
        };
    }

    on(event, handler) {
        if (!this.handlers[event]) this.handlers[event] = [];
        this.handlers[event].push(handler);
    }

    _emit(event, data) {
        (this.handlers[event] || []).forEach(h => h(data));
    }

    _updateStatus(status) {
        const dot = document.getElementById('connection-status');
        if (dot) {
            dot.className = `status-dot ${status}`;
        }
    }

    _addFeedItem(type, data) {
        const feed = document.getElementById('live-feed');
        if (!feed) return;

        // Remove placeholder
        const placeholder = feed.querySelector('.feed-placeholder');
        if (placeholder) placeholder.remove();

        const item = document.createElement('div');
        item.className = 'feed-item';
        item.innerHTML = `
            <strong>${type}</strong>: ${data.data?.task_type || data.data?.message || JSON.stringify(data.data).slice(0, 80)}
            <br><small>${SC.shortTime()}</small>
        `;

        feed.insertBefore(item, feed.firstChild);

        // Keep max 50 items
        while (feed.children.length > 50) {
            feed.removeChild(feed.lastChild);
        }
    }

    disconnect() {
        if (this.source) {
            this.source.close();
            this.source = null;
        }
    }
}

// Auto-connect on dashboard page
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('live-feed')) {
        const sse = new SSEClient();
        sse.connect();
        window._sseClient = sse;
    }
});
