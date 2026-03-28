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
            default:
                console.log('Unknown message type:', message.type);
        }
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

        on('.mana-ytable tbody tr', 'click', handleTableRowClick);
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
        sendEvent({ type: 'event', widget_id: getWidgetId(select), reason: 'SelectionChanged', data: { selectedIndex: select.selectedIndex } });
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
        const row = event.currentTarget;
        const table = row.closest('.mana-ytable');
        const rowIndex = Array.from(row.parentElement.children).indexOf(row);
        row.classList.toggle('selected');
        sendEvent({ type: 'event', widget_id: getWidgetId(table), reason: 'SelectionChanged', data: { selectedIndex: rowIndex } });
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
        const tabIndex = parseInt(tab.dataset.tabIndex);
        const tabWidget = tab.closest('.mana-ydumbtab');
        tabWidget.querySelectorAll('.mana-tab').forEach(t => t.classList.remove('selected'));
        tab.classList.add('selected');
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
    // Bootstrap
    // ============================================

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();