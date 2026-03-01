# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
"""
GTK backend for YTable using Gtk4.

Renders a header row via Gtk.Grid and rows via Gtk.ListBox. Supports:
- Column headers from `YTableHeader.header()`
- Column alignment from `YTableHeader.alignment()`
- Checkbox columns declared via `YTableHeader.isCheckboxColumn()`
- Selection driven by `YTableItem.selected()`; emits SelectionChanged on change
- Checkbox toggles emit ValueChanged and update `YTableCell.checked()`
- Resizable columns with drag handles between headers
- Column alignment between header and rows

Sorting UI is not implemented; if needed we can add clickable headers.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, GLib, Gdk, Pango
import logging
from ...yui_common import *


class YTableGtk(YSelectionWidget):
    """
    GTK4 implementation of YTable with resizable columns and proper alignment.
    
    Features:
    - Column resizing via draggable header separators (all columns, including last)
    - Uniform column widths across header and all rows
    - Checkbox column support with proper alignment
    - Single/Multi selection modes
    - Horizontal + vertical scrolling via a single ScrolledWindow
    """

    # CSS provider is registered once per process/display to avoid accumulation.
    _css_provider_installed: bool = False
    
    def __init__(self, parent=None, header: YTableHeader = None, multiSelection=False):
        super().__init__(parent)
        if header is None:
            raise ValueError("YTableGtk requires a YTableHeader")
        self._header = header
        self._multi = bool(multiSelection)
        
        # Force single-selection if any checkbox columns present
        try:
            for c_idx in range(self._header.columns()):
                if self._header.isCheckboxColumn(c_idx):
                    self._multi = False
                    break
        except Exception:
            pass
        
        self._backend_widget = None
        self._header_box = None
        self._listbox = None
        self._row_to_item = {}
        self._item_to_row = {}
        self._rows = []
        self._suppress_selection_handler = False
        self._suppress_item_change = False
        self._logger = logging.getLogger(f"manatools.aui.gtk.{self.__class__.__name__}")
        self._old_selected_items = []
        self._changed_item = None
        
        # Column width management
        self._column_widths = []
        self._min_column_width = 50
        self._default_column_width = 100
        self._drag_data = None
        self._header_cells = []
        self._header_labels = []  # Store header labels separately

        # stretched by default; can be overridden by setStretchable
        self.setStretchable(YUIDimension.YD_HORIZ, True)
        self.setStretchable(YUIDimension.YD_VERT, True)

        # Saved horizontal scroll position used to block GTK's
        # automatic "scroll selected row into view" behaviour.
        self._saved_hscroll: float = 0.0

        # Initialize column widths
        self._init_column_widths()

    def widgetClass(self):
        return "YTable"

    def _create_backend_widget(self):
        """
        Create the GTK widget hierarchy for the table.
        
        Structure:
        - Main vertical box (vbox)
          - Header box with column labels and resize handles
          - Separator
          - ScrolledWindow with ListBox for rows
        """
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        # Create header with resizable columns
        self._create_header()
        
        # Horizontal separator between header and content
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        
        # ListBox inside ScrolledWindow for rows
        self._create_listbox()
        
        # Inner content vbox: header + separator + rows — all inside ONE ScrolledWindow
        # so both scroll together horizontally.
        # hexpand=True: content fills the SW's allocated width.  The horizontal scrollbar
        # appears automatically when the sum of fixed column set_size_request values
        # (which set the child's natural minimum width) exceeds the SW's allocation.
        inner_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner_vbox.set_hexpand(True)
        inner_vbox.set_vexpand(True)
        try:
            inner_vbox.append(self._header_box)
            inner_vbox.append(separator)
            inner_vbox.append(self._listbox)
        except Exception:
            try:
                inner_vbox.add(self._header_box)
                inner_vbox.add(separator)
                inner_vbox.add(self._listbox)
            except Exception:
                pass

        # Single ScrolledWindow: horizontal scrollbar covers header + rows together.
        self._sw = Gtk.ScrolledWindow()
        self._sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        # Propagate natural height so the SW requests enough vertical space for the
        # content (otherwise the viewport defaults to ~0 px and the table is invisible).
        # Do NOT propagate width: that would eliminate the horizontal scrollbar.
        try:
            self._sw.set_propagate_natural_height(True)
        except Exception:
            pass
        try:
            self._sw.set_child(inner_vbox)
        except Exception:
            try:
                self._sw.add(inner_vbox)
            except Exception:
                pass

        # Set expansion properties.
        # Both stretchable flags are True by default (set in __init__), so the table
        # grows to fill available space in any container.  The stretchable() calls
        # here reflect that default and allow callers to override via setStretchable().
        try:
            vbox.set_hexpand(self.stretchable(YUIDimension.YD_HORIZ))
            vbox.set_vexpand(self.stretchable(YUIDimension.YD_VERT))
            vbox.set_valign(Gtk.Align.FILL)
            self._listbox.set_hexpand(True)
            self._listbox.set_vexpand(True)
            self._listbox.set_valign(Gtk.Align.FILL)
            self._sw.set_hexpand(True)
            self._sw.set_vexpand(True)
            self._sw.set_valign(Gtk.Align.FILL)
        except Exception:
            pass

        self._backend_widget = vbox

        # Assemble: outer vbox wraps only the single ScrolledWindow
        try:
            vbox.append(self._sw)
        except Exception:
            try:
                vbox.add(self._sw)
            except Exception:
                pass

        # Apply initial state
        self._apply_initial_state()
        
        # Connect selection handlers
        self._connect_selection_handlers()
        
        self._logger.debug("_create_backend_widget: <%s>", self.debugLabel())

        # Populate if items exist
        try:
            if getattr(self, "_items", None):
                self.rebuildTable()
        except Exception:
            self._logger.exception("rebuildTable failed during _create_backend_widget")

    def _init_column_widths(self):
        """Initialize column widths based on header content."""
        try:
            cols = self._header.columns()
            self._column_widths = [self._default_column_width] * cols
            
            # Adjust based on header text length
            for col in range(cols):
                try:
                    header_text = self._header.header(col)
                    if header_text:
                        # Estimate width based on text length
                        text_width = len(header_text) * 8 + 20  # Rough estimate
                        self._column_widths[col] = max(text_width, self._min_column_width)
                except Exception:
                    pass
        except Exception:
            self._column_widths = []

    def _create_header(self):
        """
        Create header with column labels and resizable separators.
        
        Each column has:
        - Label with proper alignment
        - Resizable separator (except last column)
        """
        self._header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._header_cells = []
        self._header_labels = []
        
        try:
            cols = self._header.columns()
        except Exception:
            cols = 0
            
        for col in range(cols):
            # Create container for this column header.
            # The last column expands to fill remaining space so its content is
            # never clipped when the window is wider than the sum of column widths.
            # All other columns are given a fixed minimum width.
            col_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            col_box.set_hexpand(col == cols - 1)
            
            # Apply column width (used as minimum; last column may grow further)
            width = self._get_column_width(col)
            col_box.set_size_request(width, -1)
            
            # Create label with proper alignment
            try:
                txt = self._header.header(col)
            except Exception:
                txt = ""
                
            lbl = Gtk.Label(label=txt)
            lbl.set_halign(Gtk.Align.START)
            lbl.set_margin_start(5)
            lbl.set_margin_end(5)
            lbl.set_hexpand(True)
            
            # Apply alignment to header label
            try:
                align = self._header.alignment(col)
                if align == YAlignmentType.YAlignCenter:
                    lbl.set_xalign(0.5)
                elif align == YAlignmentType.YAlignEnd:
                    lbl.set_xalign(1.0)
                else:
                    lbl.set_xalign(0.0)
            except Exception:
                lbl.set_xalign(0.0)
            
            self._header_labels.append(lbl)
            
            # Add separator for resizing (except last column)
            if col < cols - 1:
                # Create separator container
                sep_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                
                # Create draggable handle
                sep_handle = Gtk.Box()
                sep_handle.set_size_request(8, -1)
                sep_handle.get_style_context().add_class("col-sep-handle")
                
                # Add event controllers for dragging
                motion_ctrl = Gtk.EventControllerMotion.new()
                drag_ctrl = Gtk.GestureDrag.new()
                
                # Store column index
                sep_handle.column_index = col
                sep_container.column_index = col
                
                # Connect signals
                motion_ctrl.connect("enter", self._on_separator_enter)
                motion_ctrl.connect("leave", self._on_separator_leave)
                drag_ctrl.connect("drag-begin", self._on_drag_begin)
                drag_ctrl.connect("drag-update", self._on_drag_update)
                drag_ctrl.connect("drag-end", self._on_drag_end)
                
                sep_handle.add_controller(motion_ctrl)
                sep_handle.add_controller(drag_ctrl)
                
                # Create visual separator
                sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
                sep.set_margin_end(5)
                
                sep_container.append(sep_handle)
                sep_container.append(sep)
                
                col_box.append(lbl)
                col_box.append(sep_container)
            else:
                # Last column: add a right-edge drag handle so it is also resizable.
                sep_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                sep_handle = Gtk.Box()
                sep_handle.set_size_request(8, -1)
                sep_handle.get_style_context().add_class("col-sep-handle")

                motion_ctrl = Gtk.EventControllerMotion.new()
                drag_ctrl = Gtk.GestureDrag.new()
                sep_handle.column_index = col
                sep_container.column_index = col

                motion_ctrl.connect("enter", self._on_separator_enter)
                motion_ctrl.connect("leave", self._on_separator_leave)
                drag_ctrl.connect("drag-begin", self._on_drag_begin)
                drag_ctrl.connect("drag-update", self._on_drag_update)
                drag_ctrl.connect("drag-end", self._on_drag_end)

                sep_handle.add_controller(motion_ctrl)
                sep_handle.add_controller(drag_ctrl)
                sep_container.append(sep_handle)

                col_box.append(lbl)
                col_box.append(sep_container)

            self._header_box.append(col_box)
            self._header_cells.append(col_box)
            
        # Setup CSS for styling
        self._setup_header_css()

    def _setup_header_css(self):
        """Setup CSS for header styling — CSS provider is registered once per process."""
        # Always tag the current header box, regardless of whether CSS was already loaded.
        try:
            self._header_box.get_style_context().add_class("y-table-header")
        except Exception:
            pass
        if YTableGtk._css_provider_installed:
            return
        css_provider = Gtk.CssProvider()
        css = """
        /* Style for column separator handles */
        .col-sep-handle {
            background-color: transparent;
            min-width: 8px;
        }
        
        .col-sep-handle:hover {
            background-color: alpha(@theme_fg_color, 0.2);
        }
        
        /* Style for header */
        .y-table-header {
            padding: 4px 0px;
            background-color: @theme_bg_color;
            border-bottom: 1px solid @borders;
        }
        
        .y-table-header label {
            padding: 4px 8px;
            font-weight: bold;
        }
        
        /* Style for table rows */
        .y-table-row {
            border-bottom: 1px solid alpha(@theme_fg_color, 0.1);
        }
        
        .y-table-row:hover {
            background-color: alpha(@theme_selected_bg_color, 0.1);
        }
        """
        
        try:
            try:
                css_provider.load_from_data(css, -1)
            except TypeError:
                css_provider.load_from_data(css.encode())

            # Apply provider globally; class is already set above.
            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
                YTableGtk._css_provider_installed = True
        except Exception as e:
            self._logger.debug("CSS setup failed: %s", str(e))

    def _create_listbox(self):
        """Create the ListBox for table rows."""
        self._listbox = Gtk.ListBox()
        try:
            mode = Gtk.SelectionMode.MULTIPLE if self._multi else Gtk.SelectionMode.SINGLE
            self._listbox.set_selection_mode(mode)
        except Exception:
            self._logger.exception("Failed to set selection mode on ListBox")

    def _apply_initial_state(self):
        """Apply initial widget state (enabled, tooltip, visibility)."""
        # Enabled state
        try:
            if hasattr(self._backend_widget, "set_sensitive"):
                self._backend_widget.set_sensitive(bool(getattr(self, "_enabled", True)))
            if hasattr(self._listbox, "set_sensitive"):
                self._listbox.set_sensitive(bool(getattr(self, "_enabled", True)))
        except Exception:
            pass
        
        # Help text (tooltip)
        try:
            if getattr(self, "_help_text", None):
                try:
                    self._backend_widget.set_tooltip_text(self._help_text)
                except Exception:
                    pass
        except Exception:
            pass
        
        # Visibility
        try:
            if hasattr(self._backend_widget, "set_visible"):
                self._backend_widget.set_visible(self.visible())
        except Exception:
            pass

    def _connect_selection_handlers(self):
        """Connect selection event handlers."""
        # GestureClick on the listbox: save horizontal scroll offset BEFORE GTK
        # internally selects the row and auto-scrolls it into view.  The saved
        # value is then restored via idle_add in each selection signal handler.
        try:
            click_ctrl = Gtk.GestureClick.new()
            click_ctrl.connect("pressed", self._on_listbox_press)
            self._listbox.add_controller(click_ctrl)
        except Exception:
            self._logger.debug("Could not attach GestureClick to listbox")

        if self._multi:
            try:
                self._listbox.connect("selected-rows-changed", 
                                    lambda lb: self._on_selected_rows_changed(lb))
                self._listbox.connect("row-activated", 
                                    lambda lb, row: self._on_row_selected_for_multi(lb, row))
            except Exception:
                self._logger.exception("Failed to connect multi-selection handlers")
        else:
            try:
                self._listbox.connect("row-selected", 
                                    lambda lb, row: self._on_row_selected(lb, row))
            except Exception:
                self._logger.exception("Failed to connect single-selection handler")

    def _on_listbox_press(self, gesture, n_press, x, y):
        """Save horizontal scroll offset before the click triggers row selection."""
        try:
            hadj = self._sw.get_hadjustment()
            if hadj:
                self._saved_hscroll = hadj.get_value()
        except Exception:
            pass

    def _schedule_hscroll_restore(self, saved: float):
        """Restore the horizontal scroll position after GTK has finished processing
        the selection event (scheduled via idle_add so it runs after the frame)."""
        sw = getattr(self, '_sw', None)
        if sw is None:
            return
        def _restore():
            try:
                hadj = sw.get_hadjustment()
                if hadj:
                    hadj.set_value(saved)
            except Exception:
                pass
            return False  # don't repeat
        try:
            GLib.idle_add(_restore)
        except Exception:
            pass

    def _get_column_width(self, col):
        """Get width for specified column."""
        if col < len(self._column_widths):
            width = self._column_widths[col]
            return max(width, self._min_column_width) if width > 0 else self._default_column_width
        return self._default_column_width

    def _header_is_checkbox(self, col):
        """Check if column is a checkbox column."""
        try:
            return bool(self._header.isCheckboxColumn(col))
        except Exception:
            return False

    def rebuildTable(self):
        """
        Rebuild the entire table from scratch.
        
        This ensures column alignment between header and all rows.
        """
        self._logger.debug("rebuildTable: %d items", len(self._items) if self._items else 0)
        if self._backend_widget is None or self._listbox is None:
            self._create_backend_widget()

        # Clear existing rows
        self._clear_rows()

        # Build new rows
        try:
            cols = self._header.columns()
        except Exception:
            cols = 0
        if cols <= 0:
            cols = 1

        for row_idx, it in enumerate(list(getattr(self, '_items', []) or [])):
            try:
                row = self._create_row(it, cols)
                if row:
                    self._listbox.append(row)
                    self._row_to_item[row] = it
                    self._item_to_row[it] = row
                    self._rows.append(row)
            except Exception:
                self._logger.exception("Failed to create row %d", row_idx)

        # Apply selection from model
        self._apply_model_selection()

    def _clear_rows(self):
        """Clear all rows from the table."""
        try:
            self._row_to_item.clear()
            self._item_to_row.clear()
        except Exception:
            self._logger.exception("Failed to clear row-item mappings")
        
        try:
            for row in self._rows:
                try:
                    self._listbox.remove(row)
                except Exception:
                    self._logger.exception("Failed to remove row during clear_rows")
            self._rows = []
        except Exception:
            self._logger.exception("Failed to clear rows")

    def _create_row(self, item, cols):
        """
        Create a single table row with proper column alignment.
        
        Args:
            item: YTableItem for this row
            cols: Number of columns
            
        Returns:
            Gtk.ListBoxRow or None on error
        """
        try:
            row = Gtk.ListBoxRow()
            ctx = row.get_style_context()
            ctx.add_class("y-table-row")
            
            # Use Grid instead of Box for better column control
            grid = Gtk.Grid()
            grid.set_column_spacing(0)
            grid.set_row_spacing(0)
            grid.set_hexpand(True)
            
            # Create cells for each column with exact widths
            for col in range(cols):
                cell_widget = self._create_cell_widget(item, col)
                if cell_widget:
                    # Attach cell to grid at column position
                    grid.attach(cell_widget, col, 0, 1, 1)
            
            row.set_child(grid)
            return row
        except Exception:
            self._logger.exception("Failed to create row")
            return None

    def _create_cell_widget(self, item, col):
        """
        Create widget for a single cell with proper width and alignment.
        
        Args:
            item: YTableItem containing cell data
            col: Column index
            
        Returns:
            Gtk.Widget for the cell
        """
        try:
            # Get cell data
            cell = item.cell(col) if hasattr(item, 'cell') else None
            is_cb = self._header_is_checkbox(col)
            
            # Get alignment for this column
            try:
                align_t = self._header.alignment(col)
            except Exception:
                align_t = YAlignmentType.YAlignBegin
            
            # Create container for this cell.
            # The last column is allowed to fill the remaining row width so that
            # it stays aligned with its header and content is never clipped.
            cell_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            try:
                total_cols = self._header.columns()
            except Exception:
                total_cols = -1
            cell_container.set_hexpand(col == total_cols - 1)
            
            # Apply column width (minimum; last column may grow further)
            width = self._get_column_width(col)
            cell_container.set_size_request(width, -1)
            
            # Create cell content based on type
            if is_cb:
                content = self._create_checkbox_content(cell, align_t, item, col)
            else:
                content = self._create_label_content(cell, align_t)
            
            if content:
                cell_container.append(content)
            
            return cell_container
        except Exception:
            self._logger.exception("Failed to create cell widget for column %d", col)
            # Return empty container with correct width
            empty = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            empty.set_size_request(self._get_column_width(col), -1)
            return empty

    def _create_checkbox_content(self, cell, align_t, item, col):
        """
        Create checkbox cell content with proper alignment.
        
        Args:
            cell: YTableCell or None
            align_t: Alignment type
            item: Parent YTableItem
            col: Column index
            
        Returns:
            Gtk.Widget for checkbox cell
        """
        try:
            # Create checkbox
            chk = Gtk.CheckButton()
            try:
                chk.set_active(cell.checked() if cell is not None else False)
            except Exception:
                chk.set_active(False)

            # Build an explicit fill wrapper and place checkbox according to
            # column alignment. This is more reliable than relying on halign
            # on Gtk.CheckButton alone in fixed-width table cells.
            wrapper = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            wrapper.set_hexpand(True)
            wrapper.set_halign(Gtk.Align.FILL)

            def _hspacer():
                spacer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
                spacer.set_hexpand(True)
                return spacer

            if align_t == YAlignmentType.YAlignCenter:
                wrapper.append(_hspacer())
                chk.set_margin_start(0)
                chk.set_margin_end(0)
                wrapper.append(chk)
                wrapper.append(_hspacer())
            elif align_t == YAlignmentType.YAlignEnd:
                wrapper.append(_hspacer())
                chk.set_margin_start(0)
                chk.set_margin_end(6)
                wrapper.append(chk)
            else:
                chk.set_margin_start(6)
                chk.set_margin_end(0)
                wrapper.append(chk)
                wrapper.append(_hspacer())

            chk.set_valign(Gtk.Align.CENTER)
            
            # Connect toggle handler
            def _on_toggled(btn, item=item, cindex=col):
                try:
                    c = item.cell(cindex)
                    if c is not None:
                        c.setChecked(bool(btn.get_active()))
                    # Track changed item
                    self._changed_item = item
                    # Emit value changed
                    dlg = self.findDialog()
                    if dlg is not None and self.notify():
                        dlg._post_event(YWidgetEvent(self, YEventReason.ValueChanged))
                except Exception:
                    self._logger.exception("Checkbox toggle failed")
            
            chk.connect("toggled", _on_toggled)

            return wrapper
        except Exception:
            self._logger.exception("Failed to create checkbox content")
            return Gtk.Label(label="")

    def _create_label_content(self, cell, align_t):
        """
        Create label cell content with proper alignment.
        
        Args:
            cell: YTableCell or None
            align_t: Alignment type
            
        Returns:
            Gtk.Label widget
        """
        try:
            # Get text
            txt = cell.label() if cell is not None else ""
            lbl = Gtk.Label(label=txt)
            lbl.set_halign(Gtk.Align.FILL)
            lbl.set_margin_start(5)
            lbl.set_margin_end(5)
            lbl.set_hexpand(True)
            lbl.set_ellipsize(Pango.EllipsizeMode.END)
            
            # Apply alignment
            if align_t == YAlignmentType.YAlignCenter:
                lbl.set_xalign(0.5)
            elif align_t == YAlignmentType.YAlignEnd:
                lbl.set_xalign(1.0)
            else:
                lbl.set_xalign(0.0)
            
            return lbl
        except Exception:
            self._logger.exception("Failed to create label content")
            lbl = Gtk.Label(label="")
            lbl.set_xalign(0.0)
            return lbl

    def _apply_model_selection(self):
        """Apply selection state from model to UI."""
        # Save horizontal scroll so programmatic select_row calls don't move the viewport.
        try:
            hadj = self._sw.get_hadjustment() if getattr(self, '_sw', None) else None
            saved_h = hadj.get_value() if hadj else 0.0
        except Exception:
            saved_h = 0.0
        try:
            self._suppress_selection_handler = True
            
            # Clear all selections first
            try:
                self._listbox.unselect_all()
            except Exception:
                pass
            
            # Apply selection from model
            selected_items = []
            for it in list(getattr(self, '_items', []) or []):
                if hasattr(it, 'selected') and it.selected():
                    selected_items.append(it)
            
            # Select items in UI
            for it in selected_items:
                try:
                    row = self._item_to_row.get(it)
                    if row is not None:
                        self._listbox.select_row(row)
                except Exception:
                    pass
            
            # For single selection, ensure only one is selected in both UI and model
            if not self._multi and len(selected_items) > 1:
                for it in selected_items[1:]:
                    try:
                        row = self._item_to_row.get(it)
                        if row is not None:
                            self._listbox.unselect_row(row)
                    except Exception:
                        pass
                selected_items = selected_items[:1]

            # Sync the cached list so it matches what was just set in the UI.
            # This is critical: callers that query selectedItems() immediately
            # after rebuildTable() / addItems() must see the correct selection.
            self._selected_items = list(selected_items)

        finally:
            self._suppress_selection_handler = False
            self._schedule_hscroll_restore(saved_h)

    # Column resizing handlers
    def _on_separator_enter(self, controller, x, y):
        """Change cursor to col-resize when hovering over separator."""
        try:
            widget = controller.get_widget()
            display = widget.get_display()
            cursor = Gdk.Cursor.new_from_name(display, "col-resize")
            if cursor:
                widget.get_root().set_cursor(cursor)
        except Exception:
            pass

    def _on_separator_leave(self, controller):
        """Reset cursor when leaving separator."""
        try:
            widget = controller.get_widget()
            widget.get_root().set_cursor(None)
        except Exception:
            pass

    def _on_drag_begin(self, gesture, start_x, start_y):
        """Begin column resize drag operation."""
        try:
            widget = gesture.get_widget()
            col_index = widget.column_index
            
            if col_index < len(self._column_widths):
                # Use the actual allocated width as the drag baseline rather than
                # the stored value.  This matters for the last column which has
                # hexpand=True: GTK may have allocated it more space than the
                # stored minimum, so the drag must start from what the user sees.
                if col_index < len(self._header_cells):
                    allocated = self._header_cells[col_index].get_allocated_width()
                    current_width = allocated if allocated > 0 else self._column_widths[col_index]
                else:
                    current_width = self._column_widths[col_index]
                self._drag_data = {
                    'column_index': col_index,
                    'start_width': current_width,
                    'start_x': start_x
                }
        except Exception:
            self._drag_data = None

    def _on_drag_update(self, gesture, offset_x, offset_y):
        """Update column width during drag."""
        if not self._drag_data:
            return
            
        try:
            col_index = self._drag_data['column_index']
            new_width = max(self._min_column_width, 
                          self._drag_data['start_width'] + offset_x)
            
            # Update column width
            self._update_column_width(col_index, new_width)
            
            self._drag_data['current_width'] = new_width
        except Exception:
            self._logger.exception("Drag update failed")

    def _on_drag_end(self, gesture, offset_x, offset_y):
        """End column resize drag operation."""
        self._drag_data = None

    def _update_column_width(self, col_index, new_width):
        """
        Update width for a specific column in header and all rows.
        """
        if col_index >= len(self._column_widths):
            return
            
        # Update stored width
        self._column_widths[col_index] = new_width
        
        # Update header cell
        if col_index < len(self._header_cells):
            try:
                self._header_cells[col_index].set_size_request(new_width, -1)
            except Exception:
                pass
        
        # Update all rows
        for row in self._rows:
            try:
                grid = row.get_child()
                if grid and isinstance(grid, Gtk.Grid):
                    # Get the cell container at this column index
                    cell_widget = grid.get_child_at(col_index, 0)
                    if cell_widget:
                        cell_widget.set_size_request(new_width, -1)
            except Exception:
                pass

    # Selection handlers
    def _on_row_selected(self, listbox, row):
        if self._suppress_selection_handler:
            return
        # Restore horizontal scroll: GTK scrolled the row into view before this
        # signal fired; undo that via idle_add using the value saved at click time.
        self._schedule_hscroll_restore(self._saved_hscroll)
        try:
            # Update selected flags
            for it in list(getattr(self, '_items', []) or []):
                try:
                    it.setSelected(False)
                except Exception:
                    pass
            if row is not None:
                it = self._row_to_item.get(row)
                if it is not None:
                    try:
                        it.setSelected(True)
                    except Exception:
                        pass
                    self._old_selected_items = self._selected_items
                    self._selected_items = [it]
            else:
                self._old_selected_items = self._selected_items
                self._selected_items = []
            # notify
            try:
                if self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
            except Exception:
                pass
        except Exception:
            pass

    def _on_selected_rows_changed(self, listbox):
        if self._suppress_selection_handler:
            return
        self._schedule_hscroll_restore(self._saved_hscroll)
        try:
            selected_rows = listbox.get_selected_rows() or []
            new_selected = []
            for row in selected_rows:
                it = self._row_to_item.get(row)
                if it is not None:
                    new_selected.append(it)
            # Truncate to a single item for single-selection BEFORE updating model flags
            # so the .selected() state on discarded items is not set True.
            if not self._multi and len(new_selected) > 1:
                new_selected = [new_selected[-1]]
            # set flags
            try:
                for it in list(getattr(self, '_items', []) or []):
                    it.setSelected(False)
                for it in new_selected:
                    it.setSelected(True)
            except Exception:
                pass

            self._old_selected_items = self._selected_items
            self._selected_items = new_selected
            # notify
            try:
                if self.notify():
                    dlg = self.findDialog()
                    if dlg is not None:
                        dlg._post_event(YWidgetEvent(self, YEventReason.SelectionChanged))
            except Exception:
                pass
        except Exception:
            pass

    def _on_row_selected_for_multi(self, listbox, row):
        """
        Handler for row selection in multi-selection mode: for de-selection.
        """
        if self._suppress_selection_handler:
            return
        self._schedule_hscroll_restore(self._saved_hscroll)
        self._logger.debug("_on_row_selected_for_multi called")
        sel_rows = listbox.get_selected_rows()
        it = self._row_to_item.get(row, None)
        if it is not None:
            if it in self._old_selected_items:
                self._listbox.unselect_row(row)
                it.setSelected(False)
                self._on_selected_rows_changed(listbox)
            else:
                self._old_selected_items = self._selected_items

    # API methods
    def addItem(self, item):
        """Add a single item to the table."""
        if isinstance(item, str):
            item = YTableItem(item)
        if not isinstance(item, YTableItem):
            raise TypeError("YTableGtk.addItem expects a YTableItem or string label")
        super().addItem(item)
        item.setIndex(len(self._items) - 1)
        if getattr(self, '_listbox', None) is not None:
            self.rebuildTable()

    def addItems(self, items):
        """Add multiple items to the table efficiently."""
        for item in items:
            if isinstance(item, str):
                item = YTableItem(item)
                super().addItem(item)
            elif isinstance(item, YTableItem):
                super().addItem(item)
            else:
                self._logger.error("YTable.addItem: invalid item type %s", type(item))
                raise TypeError("YTableGtk.addItem expects a YTableItem or string label")
            item.setIndex(len(self._items) - 1)
        if getattr(self, '_listbox', None) is not None:
            self.rebuildTable()

    def selectItem(self, item, selected=True):
        """Select or deselect an item."""
        try:
            item.setSelected(bool(selected))
        except Exception:
            pass
        
        if getattr(self, '_listbox', None) is None:
            if selected:
                if item not in self._selected_items:
                    self._selected_items.append(item)
            else:
                try:
                    if item in self._selected_items:
                        self._selected_items.remove(item)
                except Exception:
                    pass
            return
        
        saved_h: float = 0.0
        try:
            row = self._item_to_row.get(item)
            if row is None:
                self.rebuildTable()
                row = self._item_to_row.get(item)
            if row is None:
                return

            # Save horizontal scroll before programmatic select_row.
            try:
                hadj = self._sw.get_hadjustment() if getattr(self, '_sw', None) else None
                saved_h = hadj.get_value() if hadj else 0.0
            except Exception:
                saved_h = 0.0

            self._suppress_selection_handler = True
            if selected:
                if not self._multi:
                    # Deselect previously selected items in both UI and model.
                    for prev_it in list(self._selected_items):
                        try:
                            prev_it.setSelected(False)
                        except Exception:
                            pass
                    try:
                        for r in list(self._listbox.get_selected_rows() or []):
                            self._listbox.unselect_row(r)
                    except Exception:
                        pass
                self._listbox.select_row(row)
            else:
                try:
                    self._listbox.unselect_row(row)
                except Exception:
                    pass
            # Manually sync _selected_items: the handler is suppressed so it won't fire.
            if selected:
                if not self._multi:
                    self._selected_items = [item]
                elif item not in self._selected_items:
                    self._selected_items.append(item)
            else:
                self._selected_items = [i for i in self._selected_items if i is not item]
        finally:
            self._suppress_selection_handler = False
            self._schedule_hscroll_restore(saved_h)

    def deleteAllItems(self):
        """Delete all items from the table."""
        try:
            super().deleteAllItems()
        except Exception:
            self._items = []
        # Always clear local state regardless of what the base class did.
        self._selected_items = []
        self._old_selected_items = []
        self._changed_item = None
        self._clear_rows()

    def changedItem(self):
        """Get the item that was most recently changed."""
        return getattr(self, "_changed_item", None)

    def _set_backend_enabled(self, enabled):
        """Enable/disable the GTK table at runtime."""
        try:
            if getattr(self, "_backend_widget", None) is not None and hasattr(self._backend_widget, "set_sensitive"):
                self._backend_widget.set_sensitive(bool(enabled))
        except Exception:
            pass
        try:
            if getattr(self, "_listbox", None) is not None and hasattr(self._listbox, "set_sensitive"):
                self._listbox.set_sensitive(bool(enabled))
        except Exception:
            pass

    def setVisible(self, visible: bool = True):
        """Set widget visibility."""
        super().setVisible(visible)
        try:
            if getattr(self, "_backend_widget", None) is not None and hasattr(self._backend_widget, "set_visible"):
                self._backend_widget.set_visible(bool(visible))
        except Exception:
            self._logger.exception("setVisible failed")

    def setHelpText(self, help_text: str):
        """Set help text (tooltip) for the widget."""
        super().setHelpText(help_text)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                try:
                    self._backend_widget.set_tooltip_text(help_text)
                except Exception:
                    pass
        except Exception:
            self._logger.exception("setHelpText failed")
