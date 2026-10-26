/**
 * ManaTools Web Backend JavaScript
 * 
 * Author: Matteo Pasotti <xquiet@coriolite.com>
 * 
 * License: LGPLv2+
 *
 * Handles user interaction events and WebSocket communication with the Python backend.
 */

(function () {
    'use strict';

    // WebSocket connection
    let ws = null;
    let wsReconnectAttempts = 0;
    let wsShutdown = false;          // set on clean app exit; suppresses reconnect
    const MAX_RECONNECT_ATTEMPTS = 10;
    const RECONNECT_DELAY = 1000;

    // ============================================
    // Connection status badge
    // ============================================

    function setBadge(state) {
        const badge = document.getElementById('mana-conn-badge');
        if (!badge) return;
        const states = {
            connecting: { text: 'connecting…', cls: 'text-bg-secondary' },
            connected: { text: 'connected', cls: 'text-bg-success' },
            disconnected: { text: 'disconnected', cls: 'text-bg-danger' },
            reconnecting: { text: 'reconnecting…', cls: 'text-bg-warning' },
        };
        const s = states[state] || states.connecting;
        badge.textContent = s.text;
        badge.className = `badge ms-auto ${s.cls}`;
    }

    // ============================================
    // Initialisation
    // ============================================

    function init() {
        console.log('ManaTools Web Client initializing...');
        connectWebSocket();
        attachEventListeners();
        initContextMenuListeners();
        const reloadBtn = document.getElementById('mana-reload-btn');
        if (reloadBtn) reloadBtn.addEventListener('click', function () { window.location.reload(); });
    }

    // ============================================
    // WebSocket
    // ============================================

    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        setBadge('connecting');

        try {
            ws = new WebSocket(wsUrl);

            ws.onopen = function () {
                console.log('WebSocket connected');
                wsReconnectAttempts = 0;
                setBadge('connected');
                // Signal server to push deferred content (e.g. table rows).
                sendEvent({ type: 'ready' });
            };

            ws.onmessage = function (event) {
                handleServerMessage(JSON.parse(event.data));
            };

            ws.onclose = function () {
                console.log('WebSocket disconnected');
                setBadge('disconnected');
                // The server cancels the open menu itself once we reconnect.
                discardContextMenu();
                attemptReconnect();
            };

            ws.onerror = function (error) {
                console.error('WebSocket error:', error);
                setBadge('disconnected');
            };
        } catch (e) {
            console.error('Failed to create WebSocket:', e);
            setBadge('disconnected');
            setupFallbackCommunication();
        }
    }

    function attemptReconnect() {
        if (wsShutdown) return;
        if (wsReconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            wsReconnectAttempts++;
            setBadge('reconnecting');
            console.log(`Reconnecting (attempt ${wsReconnectAttempts})...`);
            setTimeout(connectWebSocket, RECONNECT_DELAY * wsReconnectAttempts);
        } else {
            console.error('Max reconnection attempts reached');
            setBadge('disconnected');
            setupFallbackCommunication();
        }
    }

    function setupFallbackCommunication() {
        console.log('Using fallback POST communication');
        // Events will be sent via POST to /event endpoint
    }

    function sendEvent(eventData) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(eventData));
        } else {
            fetch('/event', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(eventData)
            }).catch(err => console.error('Failed to send event:', err));
        }
    }

    // ============================================
    // Server → client messages
    // ============================================

    function handleServerMessage(message) {
        switch (message.type) {
            case 'update':
                applyUpdates(message.updates);
                break;
            case 'refresh':
                document.getElementById('mana-app').innerHTML = message.html;
                attachEventListeners();
                initMenuBehavior();
                break;
            case 'show_modal':
                // A popup over an open menu: dismiss it so its dialog gets
                // the cancellation instead of keeping stale menu state.
                if (ctxMenu) closeContextMenu(true);
                hideIdle();
                showModal(message.dialog_id, message.html, message.element_id);
                break;
            case 'hide_modal':
                if (ctxMenu && message.dialog_id && ctxMenu.dialogId === message.dialog_id) {
                    closeContextMenu(true);
                }
                hideModal(message.dialog_id, message.element_id);
                break;
            case 'busy':
                setBusy(message.state);
                break;
            case 'reload':
                // A new root dialog: it brings its own title, menu bar and
                // widget ids, so fetch the page again rather than patching it.
                window.location.reload();
                break;
            case 'show_context_menu':
                showContextMenu(message);
                break;
            case 'idle':
                discardContextMenu();
                showIdle(message.reason || 'Waiting for the application…');
                break;
            case 'shutdown':
                discardContextMenu();
                showShutdown(message.reason || 'The application has closed.');
                break;
            default:
                console.log('Unknown message type:', message.type);
        }
    }

    function setBusy(state) {
        const overlay = document.getElementById('mana-busy-overlay');
        if (!overlay) return;
        overlay.hidden = !state;
    }

    function showOverlay(reason, idle) {
        // Hide busy overlay in case it was up when the dialog went away.
        setBusy(false);
        const overlay = document.getElementById('mana-shutdown-overlay');
        if (!overlay) return;
        const msg = overlay.querySelector('.mana-shutdown-msg');
        if (msg) msg.textContent = reason;
        const reloadBtn = document.getElementById('mana-reload-btn');
        if (reloadBtn) reloadBtn.hidden = idle;
        overlay.dataset.idle = idle ? 'true' : '';
        overlay.hidden = false;
    }

    function showShutdown(reason) {
        wsShutdown = true;
        setBadge('disconnected');
        showOverlay(reason, false);
    }

    function showIdle(reason) {
        // The application is between dialogs: the process and the server are
        // still alive, so keep the connection (no wsShutdown) and wait for the
        // next "reload" or "show_modal".  The last dialog's widgets are gone
        // on the Python side, so drop them here too.
        const app = document.getElementById('mana-app');
        if (app) app.innerHTML = '';
        showOverlay(reason, true);
    }

    function hideIdle() {
        const overlay = document.getElementById('mana-shutdown-overlay');
        if (overlay && overlay.dataset.idle === 'true') {
            overlay.hidden = true;
            overlay.dataset.idle = '';
        }
    }

    function findModal(dialogId, elementId) {
        if (elementId) {
            const byId = document.getElementById(elementId);
            if (byId) return byId;
        }
        if (dialogId) {
            return document.querySelector(
                '.mana-popup-overlay[data-dialog-id="' + CSS.escape(dialogId) + '"]');
        }
        return null;
    }

    function showModal(dialogId, html, elementId) {
        // Modals stack: a dialog opened from a popup (e.g. a file chooser) must
        // not evict the popup that opened it. Only replace this dialog's own
        // overlay, which is how a replay after reconnect refreshes the stack.
        const existing = findModal(dialogId, elementId);
        if (existing) existing.remove();

        document.body.insertAdjacentHTML('beforeend', html);

        const modal = findModal(dialogId, elementId);
        if (!modal) return;

        attachEventListenersToElement(modal);

        // Close modal on backdrop click (click outside the container).
        // Only the topmost overlay is clickable, so this always targets it.
        modal.addEventListener('click', function (e) {
            if (e.target === modal) {
                sendEvent({ type: 'close', data: {} });
            }
        });
    }

    function hideModal(dialogId, elementId) {
        const modal = findModal(dialogId, elementId);
        if (modal) modal.remove();
    }

    function applyUpdates(updates) {
        if (!Array.isArray(updates)) return;

        updates.forEach(function (update) {
            const target = document.querySelector(update.target);
            if (!target) {
                console.warn('Update target not found:', update.target);
                return;
            }

            switch (update.action) {
                case 'replace': {
                    const temp = document.createElement('div');
                    temp.innerHTML = update.html;
                    const newElement = temp.firstElementChild;
                    if (newElement) {
                        target.replaceWith(newElement);
                        attachEventListenersToElement(newElement);
                    }
                    break;
                }
                case 'attr':
                    if (update.value === null || update.value === false) {
                        target.removeAttribute(update.attr);
                    } else if (update.value === true) {
                        target.setAttribute(update.attr, '');
                    } else {
                        target.setAttribute(update.attr, update.value);
                    }
                    if (update.attr === 'data-notify-context-menu') ctxMarkRows(target);
                    break;
                case 'html':
                    target.innerHTML = update.html;
                    attachEventListenersToElement(target);
                    break;
                case 'rows': {
                    // Deferred table row injection: replace the skeleton tbody with
                    // real data rows, then re-initialise pagination/search.
                    const tbody = target.querySelector('.mana-table-inner tbody');
                    if (tbody) tbody.innerHTML = update.html;
                    attachEventListenersToElement(target);
                    break;
                }
                case 'text':
                    target.textContent = update.text;
                    break;
            }
        });
    }

    // ============================================
    // Event listener attachment
    // ============================================

    function attachEventListeners() {
        const app = document.getElementById('mana-app');
        if (app) attachEventListenersToElement(app);
    }

    // Widgets rendered with data-autoscroll (YRichText.setAutoScrollDown) stay
    // scrolled to the bottom whenever they are rendered or updated.
    function scrollAutoScrollViews(root) {
        const views = Array.from(root.querySelectorAll('[data-autoscroll]'));
        if (root.matches && root.matches('[data-autoscroll]')) views.unshift(root);
        views.forEach(el => { el.scrollTop = el.scrollHeight; });
    }

    function attachEventListenersToElement(root) {
        // Include root itself when it matches the selector (e.g. when a button
        // or input is the element that was just replaced in the DOM — it is not
        // a descendant of itself, so querySelectorAll alone would miss it).
        const on = (sel, evt, fn) => {
            const elements = Array.from(root.querySelectorAll(sel));
            if (root.matches && root.matches(sel)) elements.unshift(root);
            elements.forEach(el => {
                el.removeEventListener(evt, fn);
                el.addEventListener(evt, fn);
            });
        };

        scrollAutoScrollViews(root);

        on('.mana-ypushbutton', 'click', handleButtonClick);

        on('.mana-yinputfield, .mana-yintfield, .mana-ydatefield, .mana-ytimefield',
            'change', handleInputChange);

        on('.mana-ycheckbox', 'change', handleCheckboxChange);
        on('.mana-yradiobutton', 'change', handleRadioChange);
        on('.mana-ycombobox', 'change', handleSelectChange);
        on('.mana-yselectionbox', 'change', handleSelectionChange);
        on('.mana-ymultilineedit', 'change', handleTextareaChange);

        on('.mana-yslider', 'input', handleSliderInput);
        on('.mana-yslider', 'change', handleSliderChange);

        on('.mana-ytable .mana-table-inner tbody tr', 'click', handleTableRowClick);
        on('.mana-ytable .mana-table-inner tbody td input[type="checkbox"]', 'change', handleTableCellCheckboxChange);
        on('.mana-yrichtext a', 'click', handleRichTextLinkClick);

        initAllTables(root);
        initSplitters(root);
        on('.mana-tree-item', 'click', handleTreeItemClick);
        on('.mana-tab', 'click', handleTabClick);
        on('.mana-menu-item', 'click', handleMenuItemClick);
        on('.mana-checkboxframe-toggle', 'change', handleCheckboxFrameToggle);

        initMenuBehavior(root);

        // Close open menus when clicking outside any menubar
        document.removeEventListener('click', closeMenusOnOutsideClick);
        document.addEventListener('click', closeMenusOnOutsideClick);

        document.removeEventListener('keydown', handleKeyDown);
        document.addEventListener('keydown', handleKeyDown);

        ctxMarkRows(root);
        initContextMenuListeners();
    }

    // ============================================
    // Helpers
    // ============================================

    function getWidgetId(element) {
        if (element.dataset.widgetId) return element.dataset.widgetId;
        if (element.id) return element.id;
        const container = element.closest('[data-widget-class]');
        return container ? container.id : null;
    }

    // ============================================
    // Event handlers
    // ============================================

    function handleButtonClick(event) {
        const btn = event.currentTarget;
        if (btn.disabled) return;
        sendEvent({ type: 'event', widget_id: getWidgetId(btn), reason: 'Activated', data: {} });
    }

    function handleInputChange(event) {
        const input = event.target;
        sendEvent({ type: 'event', widget_id: getWidgetId(input), reason: 'ValueChanged', data: { value: input.value } });
    }

    function handleCheckboxChange(event) {
        const cb = event.target;
        sendEvent({ type: 'event', widget_id: getWidgetId(cb), reason: 'ValueChanged', data: { checked: cb.checked } });
    }

    function handleRadioChange(event) {
        const rb = event.target;
        sendEvent({ type: 'event', widget_id: getWidgetId(rb), reason: 'ValueChanged', data: { checked: rb.checked } });
    }

    function handleSelectChange(event) {
        const select = event.target;
        // selectedValue carries the raw (DOM-decoded) option label so the server
        // can match by item.label() directly, regardless of HTML-escaping.
        sendEvent({ type: 'event', widget_id: getWidgetId(select), reason: 'SelectionChanged', data: { selectedIndex: select.selectedIndex, selectedValue: select.value } });
    }

    function handleSelectionChange(event) {
        const select = event.target;
        const selectedIndices = Array.from(select.selectedOptions).map(opt => parseInt(opt.value));
        sendEvent({ type: 'event', widget_id: getWidgetId(select), reason: 'SelectionChanged', data: { selectedIndex: selectedIndices } });
    }

    function handleTextareaChange(event) {
        const textarea = event.target;
        sendEvent({ type: 'event', widget_id: getWidgetId(textarea), reason: 'ValueChanged', data: { value: textarea.value } });
    }

    function handleSliderInput(event) {
        const slider = event.target;
        const container = slider.closest('.mana-slider-container');
        if (container) {
            const display = container.querySelector('.mana-slider-value');
            if (display) display.textContent = slider.value;
        }
    }

    function handleSliderChange(event) {
        const slider = event.target;
        sendEvent({ type: 'event', widget_id: getWidgetId(slider), reason: 'ValueChanged', data: { value: parseInt(slider.value) } });
    }

    function handleTableRowClick(event) {
        // Checkbox cells have their own handler — skip row-selection for them.
        if (event.target.matches('input[type="checkbox"]')) return;
        const row = event.currentTarget;
        const tableEl = row.closest('.mana-ytable');
        // Use the absolute position among ALL tbody children (including hidden rows)
        // so the index matches the server-side _rows[] list regardless of pagination.
        const rowIndex = Array.from(row.parentElement.children).indexOf(row);
        row.classList.toggle('selected');
        sendEvent({ type: 'event', widget_id: getWidgetId(tableEl), reason: 'SelectionChanged', data: { selectedIndex: rowIndex } });
    }

    function handleTableCellCheckboxChange(event) {
        const cb = event.currentTarget;
        const td = cb.closest('td');
        const tr = cb.closest('tr');
        const tableEl = cb.closest('.mana-ytable');
        if (!tr || !tableEl) return;
        const rowIndex = Array.from(tr.parentElement.children).indexOf(tr);
        const colIndex = td ? td.cellIndex : parseInt(cb.dataset.col || '0', 10);
        sendEvent({ type: 'table_checkbox', widget_id: getWidgetId(tableEl),
                    row: rowIndex, col: colIndex, checked: cb.checked });
    }

    function handleRichTextLinkClick(event) {
        event.preventDefault();
        const anchor = event.currentTarget;
        const url = anchor.getAttribute('href') || '';
        const richTextEl = anchor.closest('.mana-yrichtext');
        if (!richTextEl) return;
        sendEvent({ type: 'link_activated', widget_id: getWidgetId(richTextEl), url: url });
    }

    function handleTreeItemClick(event) {
        // Stop bubbling so only the innermost .mana-tree-item fires,
        // not every ancestor item up the tree.
        event.stopPropagation();

        const item = event.currentTarget;
        const treeId = item.dataset.treeId;
        const itemId = item.dataset.itemId;

        if (!treeId || !itemId) return;

        // Update visual selection: clear siblings, mark this one.
        const tree = document.getElementById(treeId);
        if (tree) {
            tree.querySelectorAll('.mana-tree-item').forEach(el => {
                el.classList.remove('selected');
            });
        }
        item.classList.add('selected');

        // Toggle open/collapsed on items that have children.
        if (item.querySelector('.mana-tree-children')) {
            item.classList.toggle('open');
            item.classList.toggle('collapsed');
        }

        sendEvent({
            type: 'event',
            widget_id: treeId,
            reason: 'SelectionChanged',
            data: { itemId: itemId }
        });
    }

    function handleTabClick(event) {
        const tab = event.currentTarget;
        const tabIndex = parseInt(tab.dataset.tabIndex, 10);
        const tabWidget = tab.closest('.mana-ydumbtab');
        if (!tabWidget) return;
        tabWidget.querySelectorAll('.mana-tab').forEach(function (t) {
            t.classList.remove('active');
            t.setAttribute('aria-selected', 'false');
        });
        tab.classList.add('active');
        tab.setAttribute('aria-selected', 'true');
        sendEvent({ type: 'event', widget_id: getWidgetId(tabWidget), reason: 'SelectionChanged', data: { selectedIndex: tabIndex } });
    }

    function handleMenuItemClick(event) {
        event.stopPropagation();
        event.preventDefault();
        const item = event.currentTarget;
        if (item.classList.contains('disabled')) return;
        // Close all open menus
        document.querySelectorAll('.mana-menu.open').forEach(m => m.classList.remove('open'));
        const menubar = item.closest('.mana-ymenubar');
        if (!menubar) return;
        sendEvent({
            type: 'event',
            widget_id: getWidgetId(menubar),
            reason: 'Activated',
            data: {
                menuItem: item.textContent.trim(),
                itemId: item.dataset.itemId || null
            }
        });
    }

    function initMenuBehavior(root) {
        // Click on a menu label: toggle open, close siblings
        (root || document).querySelectorAll('.mana-menu-label').forEach(function (label) {
            label.removeEventListener('click', onMenuLabelClick);
            label.addEventListener('click', onMenuLabelClick);
        });
    }

    function onMenuLabelClick(event) {
        event.stopPropagation();
        const menu = event.currentTarget.closest('.mana-menu');
        const isOpen = menu.classList.contains('open');
        // Close all open menus in this menubar
        const menubar = menu.closest('.mana-ymenubar');
        if (menubar) {
            menubar.querySelectorAll('.mana-menu.open').forEach(m => m.classList.remove('open'));
        }
        if (!isOpen) {
            menu.classList.add('open');
        }
    }

    function handleCheckboxFrameToggle(event) {
        const cb = event.target;
        const frame = cb.closest('.mana-ycheckboxframe');
        const content = frame.querySelector('.mana-checkboxframe-content');
        if (content) content.classList.toggle('mana-disabled', !cb.checked);
        sendEvent({ type: 'event', widget_id: getWidgetId(frame), reason: 'ValueChanged', data: { checked: cb.checked } });
    }

    function closeMenusOnOutsideClick(event) {
        if (!event.target.closest('.mana-ymenubar')) {
            document.querySelectorAll('.mana-menu.open').forEach(m => m.classList.remove('open'));
        }
    }

    function handleKeyDown(event) {
        if (event.altKey && event.key.length === 1) {
            const widget = document.querySelector(`[data-shortcut="${event.key.toLowerCase()}"]`);
            if (widget && !widget.disabled) {
                event.preventDefault();
                widget.click();
            }
        }

        if (event.key === 'Enter') {
            const defaultBtn = document.querySelector('.mana-ypushbutton.mana-default');
            const active = document.activeElement;
            if (active.tagName !== 'INPUT' && active.tagName !== 'TEXTAREA') {
                if (defaultBtn && !defaultBtn.disabled) defaultBtn.click();
            }
        }

        if (event.key === 'Escape') {
            sendEvent({ type: 'close', data: {} });
        }
    }

    // ============================================
    // Context menus
    // ============================================
    //
    // A widget whose root carries data-notify-context-menu="1" asks the server
    // for a menu (ContextMenuActivated); the server answers with
    // show_context_menu and gets back a context_menu pick or cancellation.
    // Selection is never changed here: the server selects the row and pushes it.

    const CTX_LONG_PRESS_MS = 500;
    const CTX_LONG_PRESS_SLOP = 10;
    const CTX_MARGIN = 4;
    const CTX_MAX_DEPTH = 16;
    const CTX_TABLE_ROWS = '.mana-ytable[data-notify-context-menu="1"] .mana-table-inner tbody > tr:not(.mana-table-loading)';

    let ctxSeq = 0;                 // bumped on every request and on outside pointerdowns
    let ctxPending = null;          // last request: { seq, widgetId, rowIndex, invoker, x, y }
    let ctxMenu = null;             // the open menu, see showContextMenu()
    let ctxLongPress = null;        // touch long-press in progress
    let ctxLongPressAt = -Infinity; // when the last long-press fired
    let ctxSuppressClickUntil = 0;  // swallow the click that ends a long-press
    let ctxKeyboardAt = -Infinity;  // when the last keyboard request was sent

    function initContextMenuListeners() {
        document.removeEventListener('contextmenu', handleCtxContextMenu);
        document.addEventListener('contextmenu', handleCtxContextMenu);
        document.removeEventListener('pointerdown', handleCtxPointerDown, true);
        document.addEventListener('pointerdown', handleCtxPointerDown, true);
        document.removeEventListener('pointermove', handleCtxPointerMove, true);
        document.addEventListener('pointermove', handleCtxPointerMove, { capture: true, passive: true });
        document.removeEventListener('pointerup', handleCtxPointerUp, true);
        document.addEventListener('pointerup', handleCtxPointerUp, true);
        document.removeEventListener('pointercancel', handleCtxPointerUp, true);
        document.addEventListener('pointercancel', handleCtxPointerUp, true);
        document.removeEventListener('mousedown', handleCtxMouseDown, true);
        document.addEventListener('mousedown', handleCtxMouseDown, true);
        window.removeEventListener('click', handleCtxClickCapture, true);
        window.addEventListener('click', handleCtxClickCapture, true);
        window.removeEventListener('keydown', handleCtxKeyDown, true);
        window.addEventListener('keydown', handleCtxKeyDown, true);
    }

    // Rows of context-menu tables are made focusable (not tabbable) so a
    // clicked row keeps focus for Shift+F10 and gets it back on close.
    function ctxMarkRows(root) {
        const rows = Array.from(root.querySelectorAll(CTX_TABLE_ROWS));
        if (root.matches && root.matches(CTX_TABLE_ROWS)) rows.unshift(root);
        rows.forEach(function (tr) {
            if (!tr.hasAttribute('tabindex')) tr.tabIndex = -1;
        });
    }

    function ctxWidgetRoot(el) {
        const root = (el && el.closest) ? el.closest('[data-widget-class]') : null;
        if (!root || root.dataset.notifyContextMenu !== '1') return null;
        if (root.disabled || root.hasAttribute('disabled') || root.closest('.mana-disabled')) return null;
        return root;
    }

    function ctxVisibleRect(el) {
        if (!el || !el.getBoundingClientRect) return null;
        const r = el.getBoundingClientRect();
        return (r.width > 0 || r.height > 0) ? r : null;
    }

    function ctxInTableChrome(root, el) {
        const chrome = el.closest('.mana-table-controls, .mana-table-footer');
        return !!chrome && root.contains(chrome);
    }

    function ctxTreeItem(root, el) {
        const item = (el && el.closest) ? el.closest('.mana-tree-item') : null;
        return (item && root.contains(item) && item.dataset.itemId) ? item : null;
    }

    function ctxTableRow(root, el) {
        const tr = (el && el.closest) ? el.closest('tr') : null;
        if (!tr || !root.contains(tr) || tr.classList.contains('mana-table-loading')) return null;
        const body = tr.parentElement;
        if (!body || body.tagName !== 'TBODY' || !body.closest('.mana-table-inner')) return null;
        return tr;
    }

    function ctxRowIndex(tr) {
        return Array.from(tr.parentElement.children).indexOf(tr);
    }

    function ctxOptionHeight(select) {
        const n = select.options.length;
        return n ? select.scrollHeight / n : 0;
    }

    // Listbox options may have no layout box of their own (engine-dependent),
    // so fall back to evenly sized rows inside the <select>.
    function ctxOptionRect(select, option) {
        const r = ctxVisibleRect(option);
        if (r) return r;
        const box = select.getBoundingClientRect();
        const h = ctxOptionHeight(select);
        const top = box.top + select.clientTop + option.index * h - select.scrollTop;
        return { left: box.left + select.clientLeft, top: top, bottom: top + h };
    }

    function ctxOptionAt(select, x, y) {
        const opts = Array.from(select.options);
        if (!opts.length) return null;
        if (ctxVisibleRect(opts[0])) {
            return opts.find(function (o) {
                const r = o.getBoundingClientRect();
                return y >= r.top && y < r.bottom && x >= r.left && x < r.right;
            }) || null;
        }
        const box = select.getBoundingClientRect();
        const h = ctxOptionHeight(select);
        if (h <= 0) return null;
        const idx = Math.floor((y - box.top - select.clientTop + select.scrollTop) / h);
        return (idx >= 0 && idx < opts.length) ? opts[idx] : null;
    }

    function ctxKeyboardOption(select) {
        const sel = Array.from(select.selectedOptions || []);
        if (select.multiple && sel.length) return sel[sel.length - 1];
        if (select.selectedIndex >= 0) return select.options[select.selectedIndex];
        return null;
    }

    function ctxAssignOption(ref, option) {
        if (!option) return;
        const v = parseInt(option.value, 10);
        if (Number.isFinite(v)) ref.rowIndex = v;
    }

    function ctxTableKeyboardRow(root, active) {
        const own = ctxTableRow(root, active);
        if (own) return own;
        const rows = Array.from(root.querySelectorAll('.mana-table-inner tbody > tr:not(.mana-table-loading)'));
        const visible = rows.filter(function (r) { return r.style.display !== 'none'; });
        return visible.find(function (r) { return r.classList.contains('selected'); }) ||
            rows.find(function (r) { return r.classList.contains('selected'); }) ||
            visible[0] || null;
    }

    // Widget and row under a pointer; null when the native menu should show.
    function ctxPointerTarget(el, x, y) {
        const root = ctxWidgetRoot(el);
        if (!root) return null;
        const ref = {};
        if (root.tagName === 'SELECT') {
            const own = el.closest('option');
            ctxAssignOption(ref, (own && root.contains(own)) ? own : ctxOptionAt(root, x, y));
            return { root: root, ref: ref };
        }
        if (root.classList.contains('mana-ytable') && ctxInTableChrome(root, el)) return null;
        const item = root.dataset.widgetClass === 'YTree' ? ctxTreeItem(root, el) : null;
        if (item) {
            ref.itemId = item.dataset.itemId;
        } else if (root.classList.contains('mana-ytable')) {
            const tr = ctxTableRow(root, el);
            if (tr) ref.rowIndex = ctxRowIndex(tr);
        }
        return { root: root, ref: ref };
    }

    // Widget, row and anchor point for Shift+F10 / the ContextMenu key.
    function ctxKeyboardTarget() {
        const active = document.activeElement;
        if (!active || active === document.body || active === document.documentElement) return null;
        const root = ctxWidgetRoot(active);
        if (!root) return null;
        const ref = {};
        let anchor = null;
        if (root.tagName === 'SELECT') {
            const opt = ctxKeyboardOption(root);
            ctxAssignOption(ref, opt);
            const box = root.getBoundingClientRect();
            if (opt) {
                const r = ctxOptionRect(root, opt);
                anchor = { x: r.left, y: Math.min(Math.max(r.bottom, box.top), box.bottom) };
            } else {
                anchor = { x: box.left, y: box.bottom };
            }
            return { root: root, ref: ref, x: anchor.x, y: anchor.y };
        }
        if (root.classList.contains('mana-ytable') && ctxInTableChrome(root, active)) return null;
        let rowEl = null;
        if (root.dataset.widgetClass === 'YTree') {
            rowEl = ctxTreeItem(root, active) || root.querySelector('.mana-tree-item.selected');
            if (rowEl) ref.itemId = rowEl.dataset.itemId;
        }
        if (!rowEl && root.classList.contains('mana-ytable')) {
            rowEl = ctxTableKeyboardRow(root, active);
            if (rowEl) ref.rowIndex = ctxRowIndex(rowEl);
        }
        const r = ctxVisibleRect(rowEl) ||
            ctxVisibleRect(root.querySelector('.mana-table-scroll')) ||
            ctxVisibleRect(active) || root.getBoundingClientRect();
        return { root: root, ref: ref, x: r.left, y: r.bottom };
    }

    function ctxRequest(root, ref, x, y, source, invoker) {
        ctxSeq++;
        const widgetId = getWidgetId(root);
        const cx = Math.max(0, Math.round(x));
        const cy = Math.max(0, Math.round(y));
        ctxPending = {
            seq: ctxSeq, widgetId: widgetId,
            rowIndex: Number.isInteger(ref.rowIndex) ? ref.rowIndex : null,
            invoker: invoker || null, x: cx, y: cy,
        };
        const data = Object.assign({}, ref, { clientX: cx, clientY: cy, source: source, seq: ctxSeq });
        sendEvent({ type: 'event', widget_id: widgetId, reason: 'ContextMenuActivated', data: data });
    }

    function handleCtxContextMenu(event) {
        if (ctxMenu && ctxMenu.root.contains(event.target)) {
            event.preventDefault();
            return;
        }
        const now = performance.now();
        // The keyboard request already went out from keydown; swallow the
        // contextmenu event some engines fire for the same key press.
        if (event.isTrusted && now - ctxKeyboardAt < 600) {
            ctxKeyboardAt = -Infinity;
            event.preventDefault();
            return;
        }
        if (ctxLongPress) {
            // Engines that fire contextmenu on a touch hold: let the
            // long-press path own it so only one request goes out.
            event.preventDefault();
            if (!ctxLongPress.fired) {
                clearTimeout(ctxLongPress.timer);
                ctxFireLongPress();
            }
            return;
        }
        if (event.isTrusted && now - ctxLongPressAt < 1000) {
            if (ctxWidgetRoot(event.target)) event.preventDefault();
            return;
        }
        const t = ctxPointerTarget(event.target, event.clientX, event.clientY);
        if (!t) return;
        event.preventDefault();
        const source = event.pointerType === 'touch' ? 'touch' : 'pointer';
        ctxRequest(t.root, t.ref, event.clientX, event.clientY, source, document.activeElement);
    }

    function handleCtxPointerDown(event) {
        if (ctxMenu && ctxMenu.root.contains(event.target)) return;
        ctxSeq++;
        ctxCancelLongPress();
        ctxSuppressClickUntil = 0;
        if (ctxMenu || event.pointerType !== 'touch' || !event.isPrimary) return;
        const t = ctxPointerTarget(event.target, event.clientX, event.clientY);
        if (!t) return;
        ctxLongPress = {
            id: event.pointerId, x: event.clientX, y: event.clientY,
            target: t, fired: false,
            timer: setTimeout(ctxFireLongPress, CTX_LONG_PRESS_MS),
        };
    }

    function handleCtxPointerMove(event) {
        const lp = ctxLongPress;
        if (!lp || lp.fired || event.pointerId !== lp.id) return;
        if (Math.hypot(event.clientX - lp.x, event.clientY - lp.y) > CTX_LONG_PRESS_SLOP) {
            ctxCancelLongPress();
        }
    }

    function handleCtxPointerUp(event) {
        const lp = ctxLongPress;
        if (!lp || event.pointerId !== lp.id) return;
        if (lp.fired) ctxSuppressClickUntil = performance.now() + 600;
        ctxCancelLongPress();
    }

    function ctxCancelLongPress() {
        if (ctxLongPress && ctxLongPress.timer) clearTimeout(ctxLongPress.timer);
        ctxLongPress = null;
    }

    function ctxFireLongPress() {
        const lp = ctxLongPress;
        if (!lp || lp.fired) return;
        lp.fired = true;
        lp.timer = null;
        ctxLongPressAt = performance.now();
        // Until the finger lifts; pointerup narrows this to the trailing click.
        ctxSuppressClickUntil = ctxLongPressAt + 60000;
        if (!lp.target.root.isConnected) return;
        ctxRequest(lp.target.root, lp.target.ref, lp.x, lp.y, 'touch', document.activeElement);
    }

    function handleCtxClickCapture(event) {
        if (ctxSuppressClickUntil && performance.now() < ctxSuppressClickUntil) {
            ctxSuppressClickUntil = 0;
            event.preventDefault();
            event.stopPropagation();
        }
    }

    // A right button press on a listbox may select the option natively;
    // the server owns the selection, so keep the browser out of it.
    function handleCtxMouseDown(event) {
        if (event.button !== 2) return;
        const root = ctxWidgetRoot(event.target);
        if (root && root.tagName === 'SELECT') event.preventDefault();
    }

    function handleCtxKeyDown(event) {
        if (ctxMenu) {
            ctxMenuKeyDown(event);
            return;
        }
        const isCtxKey = event.key === 'ContextMenu' || (event.key === 'F10' && event.shiftKey);
        if (!isCtxKey || event.ctrlKey || event.altKey || event.metaKey) return;
        const t = ctxKeyboardTarget();
        if (!t) return;
        event.preventDefault();
        event.stopPropagation();
        ctxKeyboardAt = performance.now();
        ctxRequest(t.root, t.ref, t.x, t.y, 'keyboard', document.activeElement);
    }

    // ---- Menu construction -------------------------------------------

    // '&X' marks the mnemonic X (first one only), '&&' is a literal '&'.
    function ctxParseLabel(raw) {
        const chars = Array.from(raw);
        const nodes = [];
        let buf = '';
        let text = '';
        let mnemonic = '';
        for (let i = 0; i < chars.length; i++) {
            const ch = chars[i];
            if (ch === '&' && i + 1 < chars.length) {
                const next = chars[++i];
                if (next !== '&' && !mnemonic && next.trim()) {
                    if (buf) nodes.push(document.createTextNode(buf));
                    buf = '';
                    const u = document.createElement('u');
                    u.textContent = next;
                    nodes.push(u);
                    mnemonic = next.toLowerCase();
                } else {
                    buf += next;
                }
                text += next;
                continue;
            }
            buf += ch;
            text += ch;
        }
        if (buf) nodes.push(document.createTextNode(buf));
        return { nodes: nodes, text: text, mnemonic: mnemonic };
    }

    // Only same-origin, path-relative icon URLs (the server's /icon/ route).
    function ctxIconUrl(icon) {
        if (typeof icon !== 'string' || icon.charAt(0) !== '/') return '';
        const second = icon.charAt(1);
        if (second === '/' || second === '\\') return '';
        try {
            return new URL(icon, window.location.href).origin === window.location.origin ? icon : '';
        } catch (e) {
            return '';
        }
    }

    function ctxBuildMenu(items, ariaLabel, depth) {
        const menu = document.createElement('div');
        menu.className = 'mana-ctxmenu';
        menu.setAttribute('role', 'menu');
        menu.setAttribute('aria-label', ariaLabel);
        menu.tabIndex = -1;
        const list = (Array.isArray(items) ? items : []).filter(function (it) {
            return it && typeof it === 'object';
        });
        const hasIcons = list.some(function (it) { return !it.separator && ctxIconUrl(it.icon); });
        if (hasIcons) menu.classList.add('mana-ctxmenu-has-icons');

        list.forEach(function (it) {
            if (it.separator) {
                const sep = document.createElement('div');
                sep.className = 'mana-ctxmenu-separator';
                sep.setAttribute('role', 'separator');
                menu.appendChild(sep);
                return;
            }
            const el = document.createElement('div');
            el.className = 'mana-ctxmenu-item';
            el.setAttribute('role', 'menuitem');
            el.tabIndex = -1;
            el.dataset.itemId = String(it.id);
            const parsed = ctxParseLabel(typeof it.label === 'string' ? it.label : '');
            el.dataset.label = parsed.text;
            if (parsed.mnemonic) el.dataset.mnemonic = parsed.mnemonic;
            if (it.enabled === false) el.setAttribute('aria-disabled', 'true');

            if (hasIcons) {
                const url = ctxIconUrl(it.icon);
                let icon;
                if (url) {
                    icon = document.createElement('img');
                    icon.src = url;
                    icon.alt = '';
                    icon.addEventListener('error', function () { icon.style.visibility = 'hidden'; });
                } else {
                    icon = document.createElement('span');
                    icon.setAttribute('aria-hidden', 'true');
                }
                icon.className = 'mana-ctxmenu-icon';
                el.appendChild(icon);
            }

            const label = document.createElement('span');
            label.className = 'mana-ctxmenu-label';
            parsed.nodes.forEach(function (n) { label.appendChild(n); });
            el.appendChild(label);

            if (it.submenu && depth < CTX_MAX_DEPTH) {
                el.setAttribute('aria-haspopup', 'menu');
                el.setAttribute('aria-expanded', 'false');
                // The flyout is nested in the item: keep its text out of the name.
                el.setAttribute('aria-label', parsed.text);
                const sub = ctxBuildMenu(it.items, parsed.text, depth + 1);
                sub.classList.add('mana-ctxmenu-sub');
                sub.hidden = true;
                el.appendChild(sub);
            }
            menu.appendChild(el);
        });
        return menu;
    }

    // ---- Positioning ---------------------------------------------------

    function ctxViewport() {
        const de = document.documentElement;
        return { w: de.clientWidth || window.innerWidth, h: de.clientHeight || window.innerHeight };
    }

    function ctxClamp(v, size, limit) {
        return Math.max(CTX_MARGIN, Math.min(v, limit - size - CTX_MARGIN));
    }

    function ctxPlaceRoot(menu, x, y) {
        const vp = ctxViewport();
        const r = menu.getBoundingClientRect();
        let left = x;
        let top = y;
        if (left + r.width > vp.w - CTX_MARGIN) left = x - r.width;
        if (top + r.height > vp.h - CTX_MARGIN) top = y - r.height;
        menu.style.left = ctxClamp(left, r.width, vp.w) + 'px';
        menu.style.top = ctxClamp(top, r.height, vp.h) + 'px';
    }

    function ctxPlaceFlyout(item, sub) {
        sub.style.visibility = 'hidden';
        sub.style.left = '0px';
        sub.style.top = '0px';
        const vp = ctxViewport();
        const pr = item.getBoundingClientRect();
        const r = sub.getBoundingClientRect();
        const pad = parseFloat(window.getComputedStyle(sub).paddingTop) || 0;
        let left = pr.right;
        if (left + r.width > vp.w - CTX_MARGIN) left = pr.left - r.width;
        sub.style.left = ctxClamp(left, r.width, vp.w) + 'px';
        sub.style.top = ctxClamp(pr.top - pad, r.height, vp.h) + 'px';
        sub.style.visibility = '';
    }

    // ---- Levels, focus, activation ------------------------------------

    function ctxLevelItems(level) {
        return Array.from(level.children).filter(function (el) {
            return el.getAttribute('role') === 'menuitem';
        });
    }

    function ctxIsDisabled(item) {
        return item.getAttribute('aria-disabled') === 'true';
    }

    function ctxSubmenuOf(item) {
        return item.getAttribute('aria-haspopup') === 'menu'
            ? item.querySelector(':scope > .mana-ctxmenu') : null;
    }

    // Scroll only the item's own level (never the page, which would dismiss).
    function ctxFocus(el) {
        if (!el) return;
        el.focus({ preventScroll: true });
        const level = el.parentElement;
        if (el.getAttribute('role') !== 'menuitem' || !level) return;
        if (el.offsetTop < level.scrollTop) {
            level.scrollTop = el.offsetTop;
        } else if (el.offsetTop + el.offsetHeight > level.scrollTop + level.clientHeight) {
            level.scrollTop = el.offsetTop + el.offsetHeight - level.clientHeight;
        }
    }

    function ctxFocusFirst(level) {
        const items = ctxLevelItems(level);
        ctxFocus(items.find(function (it) { return !ctxIsDisabled(it); }) || items[0] || level);
    }

    function ctxTrimLevels(count) {
        const m = ctxMenu;
        while (m.levels.length > Math.max(1, count)) {
            const sub = m.levels.pop();
            sub.hidden = true;
            if (sub.parentElement) sub.parentElement.setAttribute('aria-expanded', 'false');
        }
    }

    function ctxOpenSubmenu(item, focusFirst) {
        const m = ctxMenu;
        if (!m || ctxIsDisabled(item)) return;
        const sub = ctxSubmenuOf(item);
        if (!sub || !ctxLevelItems(sub).length) return;
        const idx = m.levels.indexOf(item.parentElement);
        if (idx < 0) return;
        if (m.levels[idx + 1] !== sub) {
            ctxTrimLevels(idx + 1);
            sub.hidden = false;
            item.setAttribute('aria-expanded', 'true');
            ctxPlaceFlyout(item, sub);
            m.levels.push(sub);
        }
        if (focusFirst) ctxFocusFirst(sub);
    }

    function ctxCloseLevel() {
        const m = ctxMenu;
        if (!m || m.levels.length < 2) return;
        const sub = m.levels[m.levels.length - 1];
        ctxTrimLevels(m.levels.length - 1);
        ctxFocus(sub.parentElement);
    }

    function ctxActivateItem(item) {
        const m = ctxMenu;
        if (!m || ctxIsDisabled(item)) return;
        if (ctxSubmenuOf(item)) {
            ctxOpenSubmenu(item, true);
            return;
        }
        const id = parseInt(item.dataset.itemId, 10);
        if (!Number.isFinite(id)) return;
        sendEvent({ type: 'context_menu', menu_id: m.menuId, item_id: id });
        closeContextMenu(false);
    }

    function ctxTypeAhead(items, cur, ch) {
        const c = ch.toLowerCase();
        const byMnemonic = items.filter(function (it) { return it.dataset.mnemonic === c; });
        if (byMnemonic.length === 1) {
            ctxFocus(byMnemonic[0]);
            ctxActivateItem(byMnemonic[0]);
            return;
        }
        const pool = byMnemonic.length ? byMnemonic : items.filter(function (it) {
            return (it.dataset.label || '').trim().toLowerCase().startsWith(c);
        });
        if (!pool.length) return;
        const next = pool.find(function (it) { return items.indexOf(it) > cur; }) || pool[0];
        ctxFocus(next);
    }

    function ctxMenuKeyDown(event) {
        // Nothing behind the menu (Esc -> close, Enter -> default button,
        // Alt+letter shortcuts) may see keys while it is open.
        event.stopPropagation();
        const m = ctxMenu;
        const items = ctxLevelItems(m.levels[m.levels.length - 1]);
        const cur = items.indexOf(document.activeElement);
        const n = items.length;
        let handled = true;
        switch (event.key) {
            case 'ArrowDown':
                if (n) ctxFocus(items[cur < 0 ? 0 : (cur + 1) % n]);
                break;
            case 'ArrowUp':
                if (n) ctxFocus(items[cur < 0 ? n - 1 : (cur - 1 + n) % n]);
                break;
            case 'Home':
                if (n) ctxFocus(items[0]);
                break;
            case 'End':
                if (n) ctxFocus(items[n - 1]);
                break;
            case 'ArrowRight':
                if (cur >= 0) ctxOpenSubmenu(items[cur], true);
                break;
            case 'ArrowLeft':
                ctxCloseLevel();
                break;
            case 'Escape':
                if (m.levels.length > 1) ctxCloseLevel();
                else closeContextMenu(true);
                break;
            case 'Tab':
                closeContextMenu(true);
                break;
            case 'Enter':
            case ' ':
                if (cur >= 0) ctxActivateItem(items[cur]);
                break;
            default:
                if (event.key.length === 1 && !event.ctrlKey && !event.metaKey) {
                    ctxTypeAhead(items, cur, event.key);
                } else {
                    handled = false;
                }
        }
        if (handled) event.preventDefault();
    }

    function ctxEventItem(event) {
        // The innermost item whose own level contains the target: a pointer
        // over a flyout's padding must not count as its parent item.
        const item = event.target.closest('[role="menuitem"]');
        if (!item || !ctxMenu || !ctxMenu.root.contains(item)) return null;
        return event.target.closest('.mana-ctxmenu') === item.parentElement ? item : null;
    }

    function ctxOnMenuOver(event) {
        const item = ctxEventItem(event);
        if (!item) return;
        const idx = ctxMenu.levels.indexOf(item.parentElement);
        if (idx < 0) return;
        const sub = ctxSubmenuOf(item);
        if (!sub || ctxMenu.levels[idx + 1] !== sub) ctxTrimLevels(idx + 1);
        if (document.activeElement !== item) ctxFocus(item);
        if (sub) ctxOpenSubmenu(item, false);
    }

    function ctxOnMenuClick(event) {
        event.stopPropagation();
        const item = ctxEventItem(event);
        if (item) ctxActivateItem(item);
    }

    // ---- Open / close --------------------------------------------------

    function showContextMenu(msg) {
        const seq = Number(msg.seq);
        if (seq !== ctxSeq || !Array.isArray(msg.items) || !msg.items.length) {
            sendEvent({ type: 'context_menu', menu_id: msg.menu_id, cancelled: true });
            return;
        }
        const pending = (ctxPending && ctxPending.seq === seq) ? ctxPending : null;
        let invoker = pending ? pending.invoker : null;
        if (ctxMenu) {
            // Replaced by the server: no cancel for the old one.
            if (!invoker) invoker = ctxMenu.invoker;
            closeContextMenu(false, false);
        }
        document.querySelectorAll('.mana-menu.open').forEach(function (mm) { mm.classList.remove('open'); });

        const catcher = document.createElement('div');
        catcher.className = 'mana-ctxmenu-catcher';
        catcher.setAttribute('aria-hidden', 'true');
        const root = ctxBuildMenu(msg.items, 'Context menu', 0);
        root.style.visibility = 'hidden';
        root.style.left = '0px';
        root.style.top = '0px';
        document.body.appendChild(catcher);
        document.body.appendChild(root);

        ctxMenu = {
            menuId: msg.menu_id,
            dialogId: typeof msg.dialog_id === 'string' ? msg.dialog_id : '',
            seq: seq,
            catcher: catcher,
            root: root,
            levels: [root],
            invoker: invoker,
            widgetId: pending ? pending.widgetId : null,
            rowIndex: pending ? pending.rowIndex : null,
        };

        const num = function (v, dflt) { return (typeof v === 'number' && Number.isFinite(v)) ? v : dflt; };
        ctxPlaceRoot(root, num(msg.x, pending ? pending.x : 0), num(msg.y, pending ? pending.y : 0));
        root.style.visibility = '';

        catcher.addEventListener('click', ctxOnCatcherClick);
        catcher.addEventListener('auxclick', ctxOnCatcherAuxClick);
        catcher.addEventListener('contextmenu', ctxOnCatcherContextMenu);
        root.addEventListener('mouseover', ctxOnMenuOver);
        root.addEventListener('click', ctxOnMenuClick);
        ctxAttachDismissListeners();

        ctxFocusFirst(root);
    }

    function closeContextMenu(sendCancel, restoreFocus) {
        const m = ctxMenu;
        if (!m) return;
        ctxMenu = null;
        ctxDetachDismissListeners();
        m.catcher.remove();
        m.root.remove();
        if (sendCancel) sendEvent({ type: 'context_menu', menu_id: m.menuId, cancelled: true });
        if (restoreFocus !== false) ctxRestoreFocus(m);
    }

    // Drop the menu without telling the server (connection lost, dialog gone).
    function discardContextMenu() {
        ctxCancelLongPress();
        ctxPending = null;
        closeContextMenu(false, false);
    }

    function ctxRestoreFocus(m) {
        let el = m.invoker;
        if (!el || !el.isConnected || el === document.body || el === document.documentElement) {
            el = null;
            const root = m.widgetId ? document.getElementById(m.widgetId) : null;
            if (root && root.tagName === 'SELECT') {
                el = root;
            } else if (root && m.rowIndex !== null) {
                const tbody = root.querySelector('.mana-table-inner tbody');
                const tr = tbody ? tbody.children[m.rowIndex] : null;
                if (tr && tr.hasAttribute('tabindex')) el = tr;
            }
        }
        if (el && typeof el.focus === 'function') el.focus({ preventScroll: true });
    }

    function ctxOnCatcherClick(event) {
        event.stopPropagation();
        closeContextMenu(true);
    }

    function ctxOnCatcherAuxClick(event) {
        if (event.button !== 1) return;
        event.stopPropagation();
        closeContextMenu(true);
    }

    // Right-click outside: cancel, then hand the click to whatever is under
    // the pointer so a new context request can start there.
    function ctxOnCatcherContextMenu(event) {
        event.preventDefault();
        event.stopPropagation();
        const x = event.clientX;
        const y = event.clientY;
        closeContextMenu(true);
        const under = document.elementFromPoint(x, y);
        if (under) {
            under.dispatchEvent(new MouseEvent('contextmenu', {
                bubbles: true, cancelable: true, view: window,
                clientX: x, clientY: y, screenX: event.screenX, screenY: event.screenY,
                button: 2, buttons: 0,
                shiftKey: event.shiftKey, ctrlKey: event.ctrlKey,
                altKey: event.altKey, metaKey: event.metaKey,
            }));
        }
    }

    function ctxDismiss() {
        closeContextMenu(true);
    }

    function ctxOnVisibility() {
        if (document.visibilityState === 'hidden') closeContextMenu(true);
    }

    function ctxOnWheel(event) {
        if (ctxMenu && !ctxMenu.root.contains(event.target)) closeContextMenu(true);
    }

    function ctxOnScroll(event) {
        if (!ctxMenu) return;
        const t = event.target;
        if (t instanceof Element) {
            // The menu's own overflow, and views the app scrolls programmatically.
            if (ctxMenu.root.contains(t) || t.closest('[data-autoscroll]')) return;
        }
        closeContextMenu(true);
    }

    function ctxAttachDismissListeners() {
        window.addEventListener('resize', ctxDismiss);
        window.addEventListener('blur', ctxDismiss);
        document.addEventListener('visibilitychange', ctxOnVisibility);
        window.addEventListener('wheel', ctxOnWheel, { capture: true, passive: true });
        document.addEventListener('scroll', ctxOnScroll, { capture: true, passive: true });
    }

    function ctxDetachDismissListeners() {
        window.removeEventListener('resize', ctxDismiss);
        window.removeEventListener('blur', ctxDismiss);
        document.removeEventListener('visibilitychange', ctxOnVisibility);
        window.removeEventListener('wheel', ctxOnWheel, true);
        document.removeEventListener('scroll', ctxOnScroll, true);
    }

    // ============================================
    // Table pagination
    // ============================================

    function initAllTables(root) {
        const elements = Array.from((root || document).querySelectorAll('.mana-ytable'));
        if (root && root.matches && root.matches('.mana-ytable')) elements.unshift(root);
        elements.forEach(initManaTable);
    }

    function initManaTable(tableEl) {
        // Preserve page/filter state when the element is re-initialised after a
        // DOM replacement so the user's position is not lost on minor updates.
        const prev = tableEl._manaTable || {};
        tableEl._manaTable = {
            page:     prev.page     || 0,
            pageSize: prev.pageSize || 10,
            filter:   prev.filter   || '',
        };

        const pageSizeEl = tableEl.querySelector('.mana-table-pagesize');
        const searchEl   = tableEl.querySelector('.mana-table-search');

        // Named handlers + remove/add: initManaTable re-runs on every rows
        // update while these controls survive, so listeners must not stack.
        if (pageSizeEl) {
            // Restore previous page-size selection in the <select>
            pageSizeEl.value = String(tableEl._manaTable.pageSize);
            pageSizeEl.removeEventListener('change', handleTablePageSizeChange);
            pageSizeEl.addEventListener('change', handleTablePageSizeChange);
        }

        if (searchEl) {
            searchEl.value = tableEl._manaTable.filter;
            searchEl.removeEventListener('input', handleTableSearchInput);
            searchEl.addEventListener('input', handleTableSearchInput);
        }

        renderManaTable(tableEl);
    }

    function handleTablePageSizeChange(event) {
        const tableEl = event.currentTarget.closest('.mana-ytable');
        if (!tableEl || !tableEl._manaTable) return;
        tableEl._manaTable.pageSize = parseInt(event.currentTarget.value, 10);
        tableEl._manaTable.page = 0;
        renderManaTable(tableEl);
    }

    function handleTableSearchInput(event) {
        const tableEl = event.currentTarget.closest('.mana-ytable');
        if (!tableEl || !tableEl._manaTable) return;
        tableEl._manaTable.filter = event.currentTarget.value.toLowerCase();
        tableEl._manaTable.page = 0;
        renderManaTable(tableEl);
    }

    function renderManaTable(tableEl) {
        const state  = tableEl._manaTable;
        const tbody  = tableEl.querySelector('.mana-table-inner tbody');
        if (!tbody) return;

        const allRows  = Array.from(tbody.querySelectorAll('tr'));
        const filtered = state.filter
            ? allRows.filter(r => r.textContent.toLowerCase().includes(state.filter))
            : allRows;

        const total     = filtered.length;
        const pageSize  = (state.pageSize === -1) ? total : state.pageSize;
        const totalPages = (pageSize > 0) ? Math.ceil(total / pageSize) : 1;

        // Clamp current page
        if (state.page >= totalPages) state.page = Math.max(0, totalPages - 1);

        const start = state.page * (pageSize === -1 ? 0 : pageSize);
        const end   = (pageSize === -1) ? total : Math.min(start + pageSize, total);

        // Show only the rows belonging to the current page; hide the rest.
        // All rows stay in the DOM so absolute rowIndex remains correct.
        const visibleSet = new Set(filtered.slice(start, end));
        allRows.forEach(r => { r.style.display = visibleSet.has(r) ? '' : 'none'; });

        // Info text
        const infoEl = tableEl.querySelector('.mana-table-info');
        if (infoEl) {
            if (total === 0) {
                infoEl.textContent = state.filter ? 'No matching entries' : 'No entries';
            } else {
                const s = start + 1, e = Math.min(end, total);
                infoEl.textContent = state.filter
                    ? `Showing ${s}\u2013${e} of ${total} filtered entries`
                    : `Showing ${s}\u2013${e} of ${total} entries`;
            }
        }

        // Pagination controls
        const paginationEl = tableEl.querySelector('.mana-table-pagination');
        if (!paginationEl) return;
        paginationEl.innerHTML = '';

        if (totalPages <= 1) return;

        function makeLi(label, page, disabled, active) {
            const li  = document.createElement('li');
            li.className = 'page-item' + (disabled ? ' disabled' : '') + (active ? ' active' : '');
            const btn = document.createElement('button');
            btn.className   = 'page-link';
            btn.innerHTML   = label;
            btn.setAttribute('aria-label', label.replace(/&[^;]+;/g, ''));
            if (!disabled) {
                btn.addEventListener('click', function () {
                    state.page = page;
                    renderManaTable(tableEl);
                });
            }
            li.appendChild(btn);
            return li;
        }

        paginationEl.appendChild(
            makeLi('&laquo;', state.page - 1, state.page === 0, false)
        );

        tablePageNumbers(state.page, totalPages).forEach(function (p) {
            if (p === '…') {
                const li = document.createElement('li');
                li.className = 'page-item disabled';
                li.innerHTML = '<span class="page-link">\u2026</span>';
                paginationEl.appendChild(li);
            } else {
                paginationEl.appendChild(makeLi(String(p + 1), p, false, p === state.page));
            }
        });

        paginationEl.appendChild(
            makeLi('&raquo;', state.page + 1, state.page >= totalPages - 1, false)
        );
    }

    function tablePageNumbers(current, total) {
        if (total <= 7) {
            return Array.from({ length: total }, function (_, i) { return i; });
        }
        if (current <= 3) {
            return [0, 1, 2, 3, 4, '…', total - 1];
        }
        if (current >= total - 4) {
            return [0, '…', total - 5, total - 4, total - 3, total - 2, total - 1];
        }
        return [0, '…', current - 1, current, current + 1, '…', total - 1];
    }

    // ============================================
    // Paned splitter drag
    // ============================================

    let _splitter = null;

    function initSplitters(root) {
        const elements = Array.from((root || document).querySelectorAll('.mana-paned-divider'));
        if (root && root.matches && root.matches('.mana-paned-divider')) elements.unshift(root);
        elements.forEach(function (el) {
            el.removeEventListener('mousedown', handleSplitterMouseDown);
            el.addEventListener('mousedown', handleSplitterMouseDown);
            el.removeEventListener('touchstart', handleSplitterTouchStart);
            el.addEventListener('touchstart', handleSplitterTouchStart, { passive: false });
        });
    }

    function handleSplitterMouseDown(e) {
        e.preventDefault();
        _startSplitter(e.currentTarget, e.clientX, e.clientY);
        document.addEventListener('mousemove', handleSplitterMouseMove);
        document.addEventListener('mouseup', handleSplitterMouseUp);
    }

    function handleSplitterTouchStart(e) {
        if (e.touches.length !== 1) return;
        e.preventDefault();
        const t = e.touches[0];
        _startSplitter(e.currentTarget, t.clientX, t.clientY);
        document.addEventListener('touchmove', handleSplitterTouchMove, { passive: false });
        document.addEventListener('touchend', handleSplitterTouchEnd);
    }

    function _startSplitter(divider, clientX, clientY) {
        const paned = divider.closest('.mana-ypaned');
        if (!paned) return;

        // Use the actual computed flex-direction so the drag axis is correct
        // even when a media query flips a horizontal paned to column layout.
        const isRow = window.getComputedStyle(paned).flexDirection === 'row';

        const prev = divider.previousElementSibling;
        const next = divider.nextElementSibling;
        if (!prev || !next) return;

        _splitter = {
            paned, isRow, prev, next,
            startPos:      isRow ? clientX : clientY,
            startPrevSize: isRow ? prev.offsetWidth : prev.offsetHeight,
            startNextSize: isRow ? next.offsetWidth : next.offsetHeight,
        };

        document.body.classList.add(isRow ? 'mana-dragging-col' : 'mana-dragging-row');
    }

    function handleSplitterMouseMove(e) {
        _moveSplitter(e.clientX, e.clientY);
    }

    function handleSplitterTouchMove(e) {
        if (!_splitter || e.touches.length !== 1) return;
        e.preventDefault();
        _moveSplitter(e.touches[0].clientX, e.touches[0].clientY);
    }

    function _moveSplitter(clientX, clientY) {
        if (!_splitter) return;
        const { isRow, prev, next, startPos, startPrevSize, startNextSize } = _splitter;

        const delta    = (isRow ? clientX : clientY) - startPos;
        const total    = startPrevSize + startNextSize;
        const minSize  = 80;
        const newPrev  = Math.max(minSize, Math.min(total - minSize, startPrevSize + delta));
        const newNext  = total - newPrev;

        prev.style.flex = '0 0 ' + newPrev + 'px';
        next.style.flex = '0 0 ' + newNext + 'px';
    }

    function handleSplitterMouseUp() {
        document.removeEventListener('mousemove', handleSplitterMouseMove);
        document.removeEventListener('mouseup', handleSplitterMouseUp);
        _endSplitter();
    }

    function handleSplitterTouchEnd() {
        document.removeEventListener('touchmove', handleSplitterTouchMove);
        document.removeEventListener('touchend', handleSplitterTouchEnd);
        _endSplitter();
    }

    function _endSplitter() {
        if (!_splitter) return;
        document.body.classList.remove('mana-dragging-col', 'mana-dragging-row');
        _splitter = null;
    }

    // ============================================
    // Bootstrap
    // ============================================

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();