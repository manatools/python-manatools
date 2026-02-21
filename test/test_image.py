#!/usr/bin/env python3

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import logging

# Configure file logger for this test: write DEBUG logs to '<testname>.log' in cwd
try:
  log_name = os.path.splitext(os.path.basename(__file__))[0] + '.log'
  fh = logging.FileHandler(log_name, mode='w')
  fh.setLevel(logging.DEBUG)
  fh.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s'))
  root_logger = logging.getLogger()
  root_logger.setLevel(logging.DEBUG)
  existing = False
  for h in list(root_logger.handlers):
    try:
      if isinstance(h, logging.FileHandler) and os.path.abspath(getattr(h, 'baseFilename', '')) == os.path.abspath(log_name):
        existing = True
        break
    except Exception:
      pass
  if not existing:
    root_logger.addHandler(fh)
  print(f"Logging test output to: {os.path.abspath(log_name)}")
except Exception as _e:
  print(f"Failed to configure file logger: {_e}")

def test_image(backend_name=None):
    if backend_name:
        print(f"Setting backend to: {backend_name}")
        os.environ['YUI_BACKEND'] = backend_name
    else:
        print("Using auto-detection")

    try:
        from manatools.aui.yui import YUI, YUI_ui
        import manatools.aui.yui_common as yui

        # Force re-detection
        YUI._instance = None
        YUI._backend = None

        backend = YUI.backend()
        print(f"Using backend: {backend.value}")

        ui = YUI_ui()
        factory = ui.widgetFactory()
        dlg = factory.createPopupDialog()
        vbox = factory.createVBox(dlg)
        factory.createHeading(vbox, "Image widget demo")

        # Use an example image path if available (relative to project), otherwise empty
        example = os.path.join(os.path.dirname(__file__), '..', 'share/images', 'manatools.png')
        example = os.path.abspath(example)
        if not os.path.exists(example):
            example = ""

        images = [example, "system-software-install"]

        # Create a MinSize wrapper so we can enforce a minimum visible size:
        # start with a conservative minimum (width x height in chars)
        min_w = 40
        min_h = 6
        min_container = factory.createMinSize(vbox, min_w, min_h)
        img = factory.createImage(min_container, "/usr/share/isodumper/header.png")
        # Keep references for interactive toggles
        current_mode = {"auto_scale": True, "vert_stretch": True, "min_h": min_h}

        # helper to inspect backend widget (best-effort multi-backend)
        def inspect_backend_widget(w):
            info = {}
            try:
                info['type'] = type(w).__name__
            except Exception:
                info['type'] = str(w)
            # try Qt style
            try:
                if hasattr(w, 'size') and callable(getattr(w, 'size')):
                    s = w.size()
                    try:
                        info['w'] = s.width()
                        info['h'] = s.height()
                    except Exception:
                        try:
                            info['w'] = s.width
                            info['h'] = s.height
                        except Exception:
                            pass
            except Exception:
                pass
            # try Gtk style
            try:
                if hasattr(w, 'get_allocated_width'):
                    info['w'] = w.get_allocated_width()
                if hasattr(w, 'get_allocated_height'):
                    info['h'] = w.get_allocated_height()
            except Exception:
                pass
            # try curses placeholder
            try:
                if hasattr(w, 'widgetClass') and w.widgetClass() == 'YImageCurses':
                    info['curses'] = True
            except Exception:
                pass
            return info

        def log_image_state(prefix=""):
            try:
                root_logger.debug("%s Image api: imageFileName=%r", prefix, (img.imageFileName() if hasattr(img, "imageFileName") else None))
            except Exception:
                root_logger.debug("%s Image api: imageFileName=<?>", prefix)
            try:
                root_logger.debug("%s Image api: autoScale=%r", prefix, (img.autoScale() if hasattr(img, "autoScale") else "<no-api>"))
            except Exception:
                root_logger.debug("%s Image api: autoScale=<no-api>", prefix)
            try:
                root_logger.debug("%s Image api: stretchable_vert=%r", prefix, bool(img.stretchable(yui.YUIDimension.YD_VERT)))
            except Exception:
                root_logger.debug("%s Image api: stretchable_vert=<no-api>", prefix)
            try:
                # Min container introspection
                mw = getattr(min_container, 'minHeight', None)
                if callable(mw):
                    root_logger.debug("%s Min container minHeight()=%r", prefix, mw())
                else:
                    # sometimes stored as attribute
                    root_logger.debug("%s Min container min_h attr=%r", prefix, getattr(min_container, '_minHeight', '<unknown>'))
            except Exception:
                root_logger.debug("%s Min container: <inspect failed>", prefix)
            # backend widget inspection
            try:
                be = None
                try:
                    be = img.get_backend_widget()
                except Exception:
                    try:
                        be = img._backend_widget
                    except Exception:
                        be = None
                if be is not None:
                    info = inspect_backend_widget(be)
                    root_logger.debug("%s Backend widget info: %s", prefix, info)
                else:
                    root_logger.debug("%s Backend widget: None", prefix)
            except Exception:
                root_logger.debug("%s Backend inspection failed", prefix)

        # mode application routine
        def apply_mode(name, autoscale, vert_stretch, min_h):
            try:
                # autoscale
                try:
                    if hasattr(img, "setAutoScale"):
                        img.setAutoScale(bool(autoscale))
                except Exception:
                    pass
                # vertical stretch
                try:
                    img.setStretchable(yui.YUIDimension.YD_VERT, bool(vert_stretch))
                except Exception:
                    # fallback: setStretchable with older naming
                    try:
                        img.setStretchable(yui.YUIDimension.YD_VERT, vert_stretch)
                    except Exception:
                        pass
                # set minimum height on the container
                try:
                    if hasattr(min_container, "setMinHeight"):
                        min_container.setMinHeight(int(min_h))
                    else:
                        # try setMinSize if available
                        if hasattr(min_container, "setMinSize"):
                            min_container.setMinSize(getattr(min_container, "minWidth", min_w), int(min_h))
                except Exception:
                    pass

                current_mode.update({"auto_scale": autoscale, "vert_stretch": vert_stretch, "min_h": min_h})
                log_image_state(prefix=f"APPLY_MODE {name}:")
            except Exception as e:
                root_logger.exception("Failed applying mode %s: %s", name, e)

        # Prepare three typical modes to reproduce behaviour:
        modes = [
            ("autoscale=ON, vert_stretch=ON, min_h=6", True, True, 6),
            ("autoscale=ON, vert_stretch=OFF, min_h=6", True, False, 6),
            ("autoscale=OFF, vert_stretch=OFF, min_h=6", False, False, 6),
        ]

        # Controls: AutoScale + Stretch flags + MinHeight presets
        ctrl = factory.createFrame(vbox, "Controls")
        ctrl_v = factory.createVBox(ctrl)
        desc = factory.createLabel(ctrl_v, "Autoscale keeps aspect. Stretch H/V lets the widget expand in width/height. With AutoScale=ON, expansion preserves ratio.")
        toggles = factory.createHBox(ctrl_v)
        chk_auto = factory.createCheckBox(toggles, "AutoScale", True)
        chk_h = factory.createCheckBox(toggles, "Stretch H", True)
        chk_v = factory.createCheckBox(toggles, "Stretch V", True)
        mhbox = factory.createHBox(ctrl_v)
        btn_min6 = factory.createPushButton(factory.createLeft(mhbox), "MinHeight: 6")
        btn_min10 = factory.createPushButton(factory.createLeft(mhbox), "MinHeight: 10")

        status = factory.createLabel(vbox, "Status: size=?, pix=?, mode=?")

        # Apply initial state
        try:
            img.setAutoScale(True)
        except Exception:
            pass
        try:
            img.setStretchable(yui.YUIDimension.YD_HORIZ, True)
            img.setStretchable(yui.YUIDimension.YD_VERT, True)
        except Exception:
            pass
        try:
            min_container.setMinHeight(min_h)
        except Exception:
            pass

        def backend_sizes():
            # best-effort introspection
            try:
                be = img.get_backend_widget()
            except Exception:
                be = None
            w = h = pw = ph = None
            if be is not None:
                try:
                    s = be.size()
                    w = getattr(s, "width")() if callable(getattr(s, "width", None)) else getattr(s, "width", None)
                    h = getattr(s, "height")() if callable(getattr(s, "height", None)) else getattr(s, "height", None)
                except Exception:
                    pass
            # image API might not expose pix size; rely on backend size as proxy
            return w, h, pw, ph

        def update_status(prefix=""):
            try:
                w, h, pw, ph = backend_sizes()
                mode = f"auto={getattr(img, 'autoScale', lambda: None)()} H={img.stretchable(yui.YUIDimension.YD_HORIZ)} V={img.stretchable(yui.YUIDimension.YD_VERT)}"
                status.setText(f"{prefix} Status: widget=({w}x{h}) pix=({pw}x{ph}) {mode}")
            except Exception:
                pass

        update_status("Init:")

        # Existing buttons: toggle image and close
        hbox = factory.createHBox(vbox)
        toggle = factory.createPushButton(factory.createLeft(hbox), "Toggle Image")
        close = factory.createPushButton(factory.createRight(hbox), "Close")

        dlg.open()
        while True:
          event = dlg.waitForEvent()
          if not event:
            continue
          typ = event.eventType()
          if typ == yui.YEventType.CancelEvent:
                dlg.destroy()
                break
          elif typ == yui.YEventType.WidgetEvent:
              wdg = event.widget()
              reason = event.reason()
              if wdg == close:
                  dlg.destroy()
                  break
              elif wdg == toggle:
                  img.setImage(images[1] if img.imageFileName() == images[0] else images[0])
                  update_status("Toggle:")
              elif wdg == chk_auto and reason == yui.YEventReason.ValueChanged:
                  try:
                      img.setAutoScale(chk_auto.value())
                  except Exception:
                      pass
                  update_status("Auto:")
              elif wdg == chk_h and reason == yui.YEventReason.ValueChanged:
                  try:
                      img.setStretchable(yui.YUIDimension.YD_HORIZ, chk_h.value())
                  except Exception:
                      pass
                  update_status("StretchH:")
              elif wdg == chk_v and reason == yui.YEventReason.ValueChanged:
                  try:
                      img.setStretchable(yui.YUIDimension.YD_VERT, chk_v.value())
                  except Exception:
                      pass
                  update_status("StretchV:")
              elif wdg == btn_min6 and reason == yui.YEventReason.Activated:
                  try:
                      min_container.setMinHeight(6)
                  except Exception:
                      pass
                  update_status("MinH=6:")
              elif wdg == btn_min10 and reason == yui.YEventReason.Activated:
                  try:
                      min_container.setMinHeight(10)
                  except Exception:
                      pass
                  update_status("MinH=10:")
              # manual log trigger: if clicking image (some backends may send event)
              if wdg == img:
                  log_image_state(prefix="IMAGE_CLICK:")

        root_logger.info("Dialog closed")
    except Exception as e:
        print(f"Error testing Image with backend {backend_name}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_image(sys.argv[1])
    else:
        test_image()
