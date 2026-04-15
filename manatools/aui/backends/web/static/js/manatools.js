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
                showModal(message.dialog_id, message.html);
                break;
            case 'hide_modal':
                hideModal(message.dialog_id);
                break;
            case 'busy':
                setBusy(message.state);
                break;
            case 'shutdown':
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

    function showShutdown(reason) {
        wsShutdown = true;
        setBadge('disconnected');
        // Hide busy overlay in case it was up when the app exited.
        setBusy(false);
        const overlay = document.getElementById('mana-shutdown-overlay');
        if (!overlay) return;
        const msg = overlay.querySelector('.mana-shutdown-msg');
        if (msg) msg.textContent = reason;
        overlay.hidden = false;
    }

    function showModal(dialogId, html) {
        // Remove any existing popup modal first.
        const existing = document.getElementById('mana-popup-modal');
        if (existing) existing.remove();

        document.body.insertAdjacentHTML('beforeend', html);

        const modal = document.getElementById('mana-popup-modal');
        if (!modal) return;

        attachEventListenersToElement(modal);

        // Close modal on backdrop click (click outside the container).
        modal.addEventListener('click', function (e) {
            if (e.target === modal) {
                sendEvent({ type: 'close', data: {} });
            }
        });
    }

    function hideModal(dialogId) {
        const modal = document.getElementById('mana-popup-modal');
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

        if (pageSizeEl) {
            // Restore previous page-size selection in the <select>
            pageSizeEl.value = String(tableEl._manaTable.pageSize);
            pageSizeEl.addEventListener('change', function () {
                tableEl._manaTable.pageSize = parseInt(this.value, 10);
                tableEl._manaTable.page = 0;
                renderManaTable(tableEl);
            });
        }

        if (searchEl) {
            searchEl.value = tableEl._manaTable.filter;
            searchEl.addEventListener('input', function () {
                tableEl._manaTable.filter = this.value.toLowerCase();
                tableEl._manaTable.page = 0;
                renderManaTable(tableEl);
            });
        }

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
    // Bootstrap
    // ============================================

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();