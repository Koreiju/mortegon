/**
 * cp/ui_utils.js — Theme injection, loading bar, pipeline stats/log overlays,
 * rainbow animation, and small string-utility methods.
 *
 * All methods become ChunkProjector instance methods via prototype mixin.
 * THREE is a CDN global loaded before this module runs.
 */

export const UiUtilsMixin = {

    initMaroniteTheme() {
        const style = document.createElement('style');
        style.innerHTML = `
            @font-face { font-family: 'VHS'; src: url('/static/vhs.ttf') format('truetype'); }
            @keyframes rainbow-text { 0% { color: #ff5555; } 16% { color: #ffff55; } 33% { color: #55ff55; } 50% { color: #55ffff; } 66% { color: #5555ff; } 83% { color: #ff55ff; } 100% { color: #ff5555; } }
            @keyframes rainbow-bg { 0% { background-color: #ff5555; } 16% { background-color: #ffff55; } 33% { background-color: #55ff55; } 50% { background-color: #55ffff; } 66% { background-color: #5555ff; } 83% { background-color: #ff55ff; } 100% { background-color: #ff5555; } }
            :root {
                --surface-base: #000000; --surface-elevated: #0c0e10; --surface-hover: #15181b;
                --border-light: #b8c0c8; --text-primary: #d7dde2; --text-secondary: #9aa3ab;
                --text-muted: #7c858d; --accent-pastel: #b8c0c8; --accent-pastel-green: #9aa3ab;
                --radius-md: 0px; --radius-sm: 0px; --shadow-soft: none;
            }
            body, input, button, .sidebar, .panel, #history-container, #results-container, #billboard, #wfh-loader-box, .empty-state, .bucket-heading {
                font-family: 'VHS', 'VCR OSD Mono', 'Courier New', monospace !important;
                text-transform: uppercase !important; letter-spacing: 1px !important;
                text-shadow: none !important; -webkit-text-stroke: 0 !important;
            }
            *, body, input, button, a, .instance-score, .page-score, .url-bucket-count, .instance-xpath, .ft-url-label, .instance-text, .billboard-header, #billboard-title, #billboard pre, #billboard code {
                animation: none !important; /* de-rainbowed → silver text (black/silver design) */
            }
            #wfh-loader-bar { animation: none !important; }
            .sidebar, .panel, .panel-left, .panel-right, #left-panel, #right-panel, .side-panel, #history-container, #results-container, #billboard, #wfh-loader-box, #rs-latch, #ft-latch {
                background: var(--surface-base) !important; border: 3px ridge var(--border-light) !important;
                border-radius: var(--radius-md) !important; box-shadow: var(--shadow-soft) !important; box-sizing: border-box !important;
            }
            .sidebar #history-container, .sidebar #results-container { border: none !important; box-shadow: none !important; animation: none !important; }
            #rs-latch { border-right: none !important; border-top-right-radius: 0 !important; border-bottom-right-radius: 0 !important; }
            #ft-latch { border-left: none !important; border-top-left-radius: 0 !important; border-bottom-left-radius: 0 !important; }
            .sidebar::after, #billboard::after, #wfh-loader-box::after, body::after, .sidebar::before, #billboard::before, #wfh-loader-box::before, body::before { display: none !important; content: none !important; animation: none !important; background: none !important; }
            .result-card, .instance-row, .page-card, .url-bucket, .bucket-heading, .ft-item, .ft-items, .ft-folder-title, .ft-header-main { background: transparent !important; border-color: var(--border-light) !important; }
            input { background: #000000 !important; border: 2px inset #ffffff !important; border-radius: var(--radius-sm) !important; padding: 6px 10px; box-sizing: border-box; font-family: 'VHS', 'VCR OSD Mono', 'Courier New', monospace !important; }
            input:focus { border-color: var(--accent-pastel) !important; outline: none; }
            button { background: #000000 !important; border: 2px outset #ffffff !important; border-radius: var(--radius-sm) !important; cursor: pointer; font-family: 'VHS', 'VCR OSD Mono', 'Courier New', monospace !important; font-weight: bold; padding: 2px 6px; }
            button:active { border: 2px inset #ffffff !important; }
            #ft-latch, #rs-latch { animation: none !important; }
            .instance-row:hover, .page-card.clickable-card:hover, .url-bucket:hover, .ft-item:hover, .ft-folder-title:hover, button:hover { border-color: var(--border-light) !important; transform: none !important; filter: none !important; animation: none !important; }
            #rs-latch:hover, #ft-latch:hover { border-color: var(--border-light) !important; animation: none !important; }
            .instance-row:hover *, .page-card.clickable-card:hover *, .url-bucket:hover *, .ft-item:hover *, .ft-folder-title:hover *, button:hover *, #rs-latch:hover *, #ft-latch:hover * { color: #ffffff !important; text-shadow: none !important; animation: none !important; }
            a { text-decoration: underline; }
            .instance-score, .page-score, .url-bucket-count { font-weight: normal; }
            #billboard { padding: 0 !important; overflow: hidden; z-index: 10005 !important; }
            .billboard-header { background: #000000 !important; border-bottom: 2px ridge var(--border-light) !important; padding: 4px 8px; font-family: 'VHS', 'VCR OSD Mono', 'Courier New', monospace !important; font-weight: bold; }
            #billboard-title { font-weight: bold; font-size: 14px; }
            .billboard-content { padding: 15px; }
            #billboard pre, #billboard code { background: #000000 !important; border: 2px inset #888 !important; border-radius: 0 !important; padding: 8px; font-family: 'VHS', 'VCR OSD Mono', 'Courier New', monospace !important; }
        `;
        document.head.appendChild(style);
    },

    initLoadingBar() {
        const barHtml = `
            <div id="wfh-loader-box" style="position: fixed; bottom: 20px; right: 320px; width: 280px; background: var(--surface-base, #242933); border: 1px solid var(--border-light, #434c5e); border-radius: 8px; padding: 12px 15px; z-index: 10000; display: flex; flex-direction: column; transition: opacity 0.3s ease, transform 0.3s ease; opacity: 0; transform: translateY(10px); pointer-events: none; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                <div style="margin-bottom: 8px; font-size: 11px; color: var(--text-primary, #eceff4); font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; display: flex; justify-content: space-between; align-items: center;">
                    <span>System Activity</span>
                    <button onclick="app.hideLoadingProgress()" style="background: none; border: none; color: var(--text-muted, #aeb5c0); cursor: pointer; padding: 0; margin: 0; font-size: 16px; line-height: 1;">&times;</button>
                </div>
                <div style="width: 100%; background: var(--surface-elevated, #2e3440); border-radius: 4px; overflow: hidden; height: 4px; margin-bottom: 8px;">
                    <div id="wfh-loader-bar" style="width: 0%; height: 100%; background: var(--accent-pastel, #88c0d0); transition: width 0.2s ease;"></div>
                </div>
                <div id="wfh-loader-text" style="color: var(--text-secondary, #d8dee9); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%;">Initializing...</div>
            </div>

            <div id="wfh-stats-box" style="position: fixed; bottom: 20px; right: 612px; width: 260px; background: var(--surface-base, #242933); border: 1px solid var(--border-light, #434c5e); border-radius: 8px; padding: 12px 15px; z-index: 10000; display: none; flex-direction: column; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-family: 'JetBrains Mono', 'Consolas', monospace;">
                <div style="margin-bottom: 8px; font-size: 11px; color: var(--text-primary, #eceff4); font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; display: flex; justify-content: space-between; align-items: center;">
                    <span><i class="fas fa-microchip"></i> Pipeline</span>
                    <button onclick="document.getElementById('wfh-stats-box').style.display='none'" style="background: none; border: none; color: var(--text-muted, #aeb5c0); cursor: pointer; padding: 0; margin: 0; font-size: 16px; line-height: 1;">&times;</button>
                </div>
                <div id="wfh-stats-rows" style="display: grid; grid-template-columns: 1fr auto; gap: 4px 12px; font-size: 11px; color: var(--text-secondary, #d8dee9);">
                    <span>elapsed</span><span id="wfh-stat-elapsed">0.0s</span>
                    <span>iters / nodes</span><span id="wfh-stat-iters">0 / 0</span>
                    <span>verified deltas</span><span id="wfh-stat-verified">0</span>
                    <span>chunks → tfidf</span><span id="wfh-stat-vec">0 / 0</span>
                    <span>db rows committed</span><span id="wfh-stat-db">0</span>
                    <span>vocab</span><span id="wfh-stat-vocab">0</span>
                    <span>global docs</span><span id="wfh-stat-docs">0</span>
                </div>
            </div>

            <!-- Log panel: header is the drag handle. Minimise collapses
                 the body so the panel shrinks to a tiny bar that re-
                 expands on click. Resizable via CSS native resize handle. -->
            <div id="wfh-log-box" style="position: fixed; bottom: 20px; right: 884px; width: 320px; max-height: 200px; background: var(--surface-base, #242933); border: 1px solid var(--border-light, #434c5e); border-radius: 8px; padding: 0; z-index: 10000; display: none; flex-direction: column; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-family: 'JetBrains Mono', 'Consolas', monospace; resize: both; overflow: hidden;">
                <div id="wfh-log-header" style="font-size: 11px; color: var(--text-primary, #eceff4); font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; display: flex; justify-content: space-between; align-items: center; cursor: move; padding: 8px 12px; user-select: none; border-bottom: 1px solid var(--border-light, #434c5e); background: rgba(0,0,0,0.15);">
                    <span><i class="fas fa-stream"></i> Pipeline Log <span id="wfh-log-count" style="opacity:.55; font-weight:400; margin-left:6px;"></span></span>
                    <span style="display: flex; gap: 4px;">
                        <button id="wfh-log-min-btn" title="Minimize" style="background: none; border: none; color: var(--text-muted, #aeb5c0); cursor: pointer; padding: 0 4px; margin: 0; font-size: 14px; line-height: 1;"><i class="fas fa-window-minimize"></i></button>
                        <button id="wfh-log-close-btn" title="Close" style="background: none; border: none; color: var(--text-muted, #aeb5c0); cursor: pointer; padding: 0 4px; margin: 0; font-size: 16px; line-height: 1;">&times;</button>
                    </span>
                </div>
                <div id="wfh-log-rows" style="overflow-y: auto; flex: 1; padding: 8px 12px; font-size: 10px; color: var(--text-secondary, #d8dee9); line-height: 1.4;"></div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', barHtml);
        // Wire up drag + minimize + close after the elements exist.
        this._wireLogPanel();
    },

    /**
     * Make the log panel draggable by its header and minimizable to a
     * bar. The minimize state collapses #wfh-log-rows so the panel
     * becomes a thin titlebar showing only "Pipeline Log (N)"; clicking
     * the header again (when minimized) or the minimize button toggles
     * back to the full panel. Drag uses raw pointer events with a fixed
     * top/left coordinate so the panel detaches from the bottom-right
     * anchor as soon as the user grabs it.
     */
    _wireLogPanel() {
        const box    = document.getElementById('wfh-log-box');
        const header = document.getElementById('wfh-log-header');
        const minBtn = document.getElementById('wfh-log-min-btn');
        const close  = document.getElementById('wfh-log-close-btn');
        const rows   = document.getElementById('wfh-log-rows');
        if (!box || !header) return;

        // Drag — header is the handle. We flip to top/left positioning
        // on first mousedown so subsequent moves are absolute deltas.
        //
        // We also track the cumulative travel of the cursor between
        // mousedown and the *next* click (browsers fire `click` after
        // `mouseup` even if the mouse moved during the gesture, as long
        // as down and up land on the same element). If the user moved
        // more than DRAG_THRESHOLD_PX, the click that follows is a
        // drag-end — not an intent to restore the minimized panel —
        // and `_lastWasDrag` flips on to suppress the click handler
        // below.
        const DRAG_THRESHOLD_PX = 4;
        let dragging = false, dx = 0, dy = 0, anchored = false;
        let downX = 0, downY = 0, maxTravel = 0;
        let lastWasDrag = false;
        const onDown = (ev) => {
            // Don't initiate drag from the buttons (they get their own clicks).
            if (ev.target.closest('button')) return;
            const r = box.getBoundingClientRect();
            if (!anchored) {
                box.style.right  = 'auto';
                box.style.bottom = 'auto';
                box.style.top    = r.top + 'px';
                box.style.left   = r.left + 'px';
                anchored = true;
            }
            dx = ev.clientX - r.left;
            dy = ev.clientY - r.top;
            downX = ev.clientX; downY = ev.clientY;
            maxTravel = 0;
            dragging = true;
            ev.preventDefault();
        };
        const onMove = (ev) => {
            if (!dragging) return;
            const travel = Math.hypot(ev.clientX - downX, ev.clientY - downY);
            if (travel > maxTravel) maxTravel = travel;
            const w = box.offsetWidth;
            const maxX = window.innerWidth  - 40;
            const maxY = window.innerHeight - 24;
            const nx = Math.max(-w + 40, Math.min(maxX, ev.clientX - dx));
            const ny = Math.max(0,         Math.min(maxY, ev.clientY - dy));
            box.style.left = nx + 'px';
            box.style.top  = ny + 'px';
        };
        const onUp = () => {
            // Latch the drag flag so the next `click` (which fires on
            // the header right after this mouseup) knows to ignore the
            // restore-on-click behaviour. Cleared once the click is
            // consumed (or unconsumed) by the click handler below.
            lastWasDrag = dragging && maxTravel > DRAG_THRESHOLD_PX;
            dragging = false;
        };
        header.addEventListener('mousedown', onDown);
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup',   onUp);

        // Minimize — collapse the rows body. Re-expand by clicking the
        // header (anywhere except buttons) OR the minimize button again.
        const setMinimized = (m) => {
            if (m) {
                rows.style.display = 'none';
                box.style.maxHeight = 'unset';
                box.style.height    = 'auto';
                box.style.resize    = 'none';
                if (minBtn) minBtn.innerHTML = '<i class="fas fa-window-maximize"></i>';
                box.dataset.minimized = '1';
            } else {
                rows.style.display = '';
                box.style.maxHeight = '200px';
                box.style.resize    = 'both';
                if (minBtn) minBtn.innerHTML = '<i class="fas fa-window-minimize"></i>';
                box.dataset.minimized = '';
            }
        };
        if (minBtn) {
            minBtn.addEventListener('click', (ev) => {
                ev.stopPropagation();
                setMinimized(box.dataset.minimized !== '1');
            });
        }
        // Click anywhere on the header (except buttons) restores when
        // minimized — common UX for tray-style panels.
        //
        // Drag-vs-click debounce: if the preceding mouseup ended a
        // real drag (cursor moved > DRAG_THRESHOLD_PX), suppress this
        // click. Without this guard, releasing the mouse after dragging
        // the minimized panel would also restore it, because browsers
        // fire `click` for any down→up pair on the same element.
        header.addEventListener('click', (ev) => {
            if (ev.target.closest('button')) return;
            if (lastWasDrag) { lastWasDrag = false; return; }
            if (box.dataset.minimized === '1') setMinimized(false);
        });
        if (close) {
            close.addEventListener('click', (ev) => {
                ev.stopPropagation();
                box.style.display = 'none';
            });
        }
    },

    _appendLogLine(frame) {
        const box  = document.getElementById('wfh-log-box');
        const rows = document.getElementById('wfh-log-rows');
        if (!box || !rows) return;
        if (box.style.display === 'none') box.style.display = 'flex';
        const stageColors = { tfidf: '#eef0f2', stream: '#b8c0c8', scan: '#b8c0c8' };
        const color = stageColors[frame.stage] || '#9ca3af';
        const stage = (frame.stage || '?').toUpperCase().padEnd(6, ' ');
        const msg   = (frame.message || '').replace(/[<>]/g, '');
        const ts    = frame.ts ? new Date(frame.ts * 1000) : new Date();
        const hh    = String(ts.getHours()).padStart(2, '0');
        const mm    = String(ts.getMinutes()).padStart(2, '0');
        const ss    = String(ts.getSeconds()).padStart(2, '0');
        const row   = document.createElement('div');
        row.style.cssText = 'white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 1px 0;';
        row.innerHTML = `<span style="color:#6b7280">${hh}:${mm}:${ss}</span> `
            + `<span style="color:${color}">${stage}</span> ${msg}`;
        rows.appendChild(row);
        while (rows.children.length > 100) rows.removeChild(rows.firstChild);
        rows.scrollTop = rows.scrollHeight;
        // Live count in the header so the minimised bar still tells the
        // user how many log entries are buffered.
        const countEl = document.getElementById('wfh-log-count');
        if (countEl) countEl.textContent = `(${rows.children.length})`;
    },

    _updateStatsOverlay(frame) {
        const box = document.getElementById('wfh-stats-box');
        if (!box) return;
        if (box.style.display === 'none') box.style.display = 'flex';
        const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        set('wfh-stat-elapsed',  `${frame.elapsed_s ?? 0}s`);
        set('wfh-stat-iters',    `${frame.iter_count || 0} / ${frame.nodes_streamed || 0}`);
        set('wfh-stat-verified', String(frame.deltas_verified || 0));
        set('wfh-stat-vec',      `${frame.chunks_built || 0} / ${frame.chunks_vectorized || 0}`);
        set('wfh-stat-db',       String(frame.instances_persisted || 0));
        set('wfh-stat-vocab',    String(frame.vocab_size || 0));
        set('wfh-stat-docs',     String(frame.doc_count || 0));
        if (frame.complete) {
            box.style.borderColor = '#b8c0c8';
            const title = box.querySelector('span');
            if (title) title.innerHTML = '<i class="fas fa-check-circle" style="color:#b8c0c8"></i> Pipeline Complete';
            if (this._statsHideTimer) clearTimeout(this._statsHideTimer);
            this._statsHideTimer = setTimeout(() => {
                box.style.display = 'none';
                box.style.borderColor = '';
                if (title) title.innerHTML = '<i class="fas fa-microchip"></i> Pipeline';
            }, 4000);
        }
    },

    setLoadingProgress(text, pct) {
        const box    = document.getElementById('wfh-loader-box');
        const bar    = document.getElementById('wfh-loader-bar');
        const textEl = document.getElementById('wfh-loader-text');
        if (box && bar && textEl) {
            box.style.opacity = '1';
            box.style.transform = 'translateY(0)';
            box.style.pointerEvents = 'all';
            bar.style.width = pct + '%';
            textEl.textContent = text;
            textEl.title = text;
        }
    },

    hideLoadingProgress() {
        const box = document.getElementById('wfh-loader-box');
        if (box) {
            box.style.opacity = '0';
            box.style.transform = 'translateY(10px)';
            box.style.pointerEvents = 'none';
        }
    },

    initBillboardArrow() {
        let svg = document.getElementById('billboard-arrow-svg');
        if (!svg) {
            svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.id = 'billboard-arrow-svg';
            svg.style.cssText = 'position:fixed; top:0; left:0; width:100%; height:100%; pointer-events:none; z-index:10004; display:none;';
            const defs   = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
            const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
            marker.setAttribute('id', 'arrowhead');
            marker.setAttribute('markerWidth',  '10');
            marker.setAttribute('markerHeight', '7');
            marker.setAttribute('refX', '9');
            marker.setAttribute('refY', '3.5');
            marker.setAttribute('orient', 'auto');
            const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
            polygon.setAttribute('points', '0 0, 10 3.5, 0 7');
            polygon.setAttribute('fill', 'var(--border-light, #c0c0c0)');
            marker.appendChild(polygon);
            defs.appendChild(marker);
            svg.appendChild(defs);
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.id = 'billboard-arrow-line';
            line.setAttribute('stroke', 'var(--border-light, #c0c0c0)');
            line.setAttribute('stroke-width', '2');
            // Solid line — no dasharray (Mortegon §6.3)
            line.setAttribute('marker-end', 'url(#arrowhead)');
            svg.appendChild(line);
            document.body.appendChild(svg);
        }
    },

    hideBillboardArrow() {
        const svg = document.getElementById('billboard-arrow-svg');
        if (svg) svg.style.display = 'none';
    },

    initRainbowObserver() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach(m => {
                m.addedNodes.forEach(node => {
                    if (node.nodeType === Node.ELEMENT_NODE) this.applyRainbowDelays(node);
                });
                if (m.type === 'characterData' && m.target.parentElement) {
                    this._applyDelay(m.target.parentElement, true);
                }
            });
        });
        observer.observe(document.body, { childList: true, subtree: true, characterData: true });
        this.applyRainbowDelays(document.body);
    },

    applyRainbowDelays(container) {
        if (!container || !container.querySelectorAll) return;
        this._applyDelay(container);
        container.querySelectorAll('*').forEach(el => this._applyDelay(el));
    },

    _applyDelay(el, force = false) {
        if (!el || el.nodeType !== Node.ELEMENT_NODE) return;
        if (!force && el.dataset && el.dataset.rainbowDelayed) return;
        let hasText = false;
        if (el.childNodes) {
            el.childNodes.forEach(child => {
                if (child.nodeType === Node.TEXT_NODE && child.textContent.trim().length > 0) hasText = true;
            });
        }
        if (['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(el.tagName)) hasText = true;
        if (hasText) {
            let delay = el.dataset.rainbowDelayVal;
            if (!delay) { delay = (Math.random() * 4).toFixed(2); el.dataset.rainbowDelayVal = delay; }
            el.style.setProperty('animation-delay', `-${delay}s`, 'important');
            if (el.dataset) el.dataset.rainbowDelayed = 'true';
        }
    },

    getContrastYIQ(threeColor) {
        const yiq = (threeColor.r * 255 * 299 + threeColor.g * 255 * 587 + threeColor.b * 255 * 114) / 1000;
        return yiq >= 128 ? '#000000' : '#ffffff';
    },

    shortenUrl(url) {
        try {
            const u    = new URL(url);
            const path = u.pathname.length > 32 ? u.pathname.slice(0, 32) + '...' : u.pathname;
            return `${u.host}${path}${u.search ? '?...' : ''}`;
        } catch {
            return (url || '').slice(0, 64);
        }
    },

    shortenXpath(xpath) {
        if (!xpath) return '';
        const parts = xpath.split('/').filter(Boolean);
        if (parts.length <= 4) return xpath;
        return '/' + parts.slice(0, 2).join('/') + '/.../' + parts.slice(-2).join('/');
    },

    escape(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    },
};
