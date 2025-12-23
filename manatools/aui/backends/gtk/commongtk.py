# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Python manatools.aui.backends.gtk contains all GTK backend classes

License: LGPLv2+

Author:  Angelo Naselli <anaselli@linux.it>

@package manatools.aui.backends.gtk
'''

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, GObject, GdkPixbuf, GLib
import cairo
import threading
import os
import logging
from ...yui_common import *


__all__ = ["_resolve_icon"]


def _resolve_icon(icon_name, size=16):
        """Return a `Gtk.Image` for the given icon_name or None.

        Resolution policy:
        - If `icon_name` looks like a filesystem path (absolute or contains path
        separator) or the file exists, load from file. If no extension, also
        try the same path with `.png` appended.
        - Otherwise, strip any extension and try to load from the system
        icon theme. If that fails, try creating an image from the original
        name (some engines accept full names).
        """        
        if not icon_name:
            return None
        
        # Helper function to load from file
        def load_from_file(filename):
            if os.path.exists(filename):
                try:
                    # Try as a file path
                    picture = Gtk.Picture.new_for_filename(filename)
                    if picture.get_paintable():
                        image = Gtk.Image.new_from_paintable(picture.get_paintable())
                        if image.get_paintable():
                            return image
                except Exception:
                    pass
                
                # Alternative: try GdkPixbuf
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
                    if pixbuf:
                        return Gtk.Image.new_from_pixbuf(pixbuf)
                except Exception:
                    pass
            return None
        
        # Step 1: Try as file path
        try:
            if (os.path.isabs(icon_name) or 
                os.path.sep in icon_name or 
                os.path.exists(icon_name)):
                
                result = load_from_file(icon_name)
                if result:
                    return result
                
                # If no extension, try with .png
                base, ext = os.path.splitext(icon_name)
                if not ext:
                    result = load_from_file(icon_name + '.png')
                    if result:
                        return result
        except Exception:
            pass
        
        # Step 2: Try icon theme
        try:
            # Strip extension for icon name
            base_name = os.path.splitext(icon_name)[0] if '.' in icon_name else icon_name
            
            # Get default display and theme
            display = Gdk.Display.get_default()
            if display:
                theme = Gtk.IconTheme.get_for_display(display)
                
                # Try to lookup the icon
                paint = theme.lookup_icon(
                    base_name,
                    fallbacks=None,
                    size=size,
                    scale=1,
                    direction=Gtk.TextDirection.LTR,
                    flags=Gtk.IconLookupFlags.FORCE_REGULAR
                )
                
                if paint:
                    return Gtk.Image.new_from_paintable(paint)
            
            # Fallback: simple icon name creation
            image = Gtk.Image.new_from_icon_name(base_name)
            if image.get_icon_name():  # Check if icon was actually set
                return image
                
        except Exception:
            pass
        
        # Step 3: Final attempt with original name
        try:
            image = Gtk.Image.new_from_icon_name(icon_name)
            if image.get_icon_name():
                return image
        except Exception:
            pass
        
        return None