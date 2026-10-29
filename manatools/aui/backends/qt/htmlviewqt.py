# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
Qt backend YHtmlView.

Engine: QtWebEngine when PySide6.QtWebEngineWidgets is importable, hardened:
- JavaScript, plugins, WebGL, local storage, file/remote access from local
  content, DNS prefetch and hyperlink auditing are off;
- an off-the-record profile (no cache, no cookies on disk) whose request
  interceptor refuses every network load except images when the application
  allowed remote content;
- a page that refuses every navigation but loading our own document; link
  clicks are reported as activations instead, and no new window can open.
Chromium itself runs the page in its sandboxed renderer process.

Fallback: QTextBrowser, when QtWebEngine is missing or fails.  It only ever
receives the sanitized document and loads nothing but inline data: images.

Content always goes through YHtmlViewBase sanitizing first.

License: LGPLv2+

@package manatools.aui.backends.qt
'''
import base64
import logging
import re
import weakref

from PySide6 import QtWidgets, QtCore, QtGui
from ...yui_common import *

# QWebEngineView.setHtml() goes through a data: URL capped at 2 MB.
_SETHTML_LIMIT = 2 * 1024 * 1024 - 4096
_DATA_IMAGE_RE = re.compile(r"^data:(image/[a-z0-9.+-]+);base64,(.*)$", re.IGNORECASE | re.DOTALL)

_webengine_classes = None


def _webengine():
    """Lazily build the QtWebEngine helper classes; False if unavailable."""
    global _webengine_classes
    if _webengine_classes is not None:
        return _webengine_classes
    try:
        from PySide6 import QtWebEngineCore, QtWebEngineWidgets
    except Exception:
        _webengine_classes = False
        return False

    Info = QtWebEngineCore.QWebEngineUrlRequestInfo
    image_type = getattr(Info.ResourceType, "ResourceTypeImage", None)

    class _Interceptor(QtWebEngineCore.QWebEngineUrlRequestInterceptor):
        """Blocks every request except our own document and, when allowed,
        remote images."""

        def __init__(self, owner, parent=None):
            super().__init__(parent)
            self._owner = weakref.ref(owner)

        def interceptRequest(self, info):
            scheme = info.requestUrl().scheme().lower()
            if scheme in ("data", "about"):
                return
            owner = self._owner()
            if (scheme in ("http", "https") and owner is not None and owner.allowRemote()
                    and info.resourceType() == image_type):
                return
            info.block(True)

    class _Page(QtWebEngineCore.QWebEnginePage):
        """Never navigates: link clicks become activations."""

        def __init__(self, profile, owner, parent=None):
            super().__init__(profile, parent)
            self._owner = weakref.ref(owner)

        def acceptNavigationRequest(self, url, nav_type, is_main_frame):
            if nav_type == QtWebEngineCore.QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
                owner = self._owner()
                if owner is not None:
                    owner._on_link(url.toString())
                return False
            # Only our own setHtml() load (a data: URL) may proceed.
            return url.scheme().lower() in ("data", "about")

        def createWindow(self, _type):
            return None

        def javaScriptConsoleMessage(self, *_args):
            pass

    _webengine_classes = (QtWebEngineCore, QtWebEngineWidgets, _Interceptor, _Page)
    return _webengine_classes


class _HtmlTextBrowser(QtWidgets.QTextBrowser):
    """QTextBrowser that loads inline data: images only (never files or
    network) and keeps a compact minimum size, like YRichText's browser."""

    def minimumSizeHint(self):
        return QtCore.QSize(0, 0)

    def loadResource(self, res_type, url):
        try:
            if res_type == QtGui.QTextDocument.ResourceType.ImageResource.value or \
                    res_type == QtGui.QTextDocument.ResourceType.ImageResource:
                m = _DATA_IMAGE_RE.match(url.toString())
                if m:
                    image = QtGui.QImage()
                    if image.loadFromData(base64.b64decode(m.group(2))):
                        return image
        except Exception:
            pass
        return None


class YHtmlViewQt(YHtmlViewBase):
    """Read-only, hardened HTML view (QtWebEngine, QTextBrowser fallback)."""

    def __init__(self, parent=None, html: str = ""):
        # Attributes first: addChild() on the parent may build us immediately.
        self._engine = None          # "webengine" or "textbrowser"
        self._profile = None
        self._interceptor = None
        self._logger = logging.getLogger(f"manatools.aui.qt.{self.__class__.__name__}")
        super().__init__(parent, html)

    # -- backend construction -----------------------------------------------

    def _create_webengine_view(self, classes):
        QtWebEngineCore, QtWebEngineWidgets, Interceptor, Page = classes
        Settings = QtWebEngineCore.QWebEngineSettings
        Profile = QtWebEngineCore.QWebEngineProfile

        view = QtWebEngineWidgets.QWebEngineView()
        profile = Profile()  # no storage name: off-the-record
        for name, value in (("setHttpCacheType", getattr(Profile.HttpCacheType, "NoCache", None)),
                            ("setPersistentCookiesPolicy",
                             getattr(Profile.PersistentCookiesPolicy, "NoPersistentCookies", None))):
            try:
                if value is not None:
                    getattr(profile, name)(value)
            except Exception:
                self._logger.debug("profile %s failed", name, exc_info=True)
        interceptor = Interceptor(self, profile)
        profile.setUrlRequestInterceptor(interceptor)

        page = Page(profile, self, view)
        # Qt deletes children in insertion order and a profile must outlive
        # its pages: parent the profile only now, after the page.
        profile.setParent(view)
        settings = page.settings()
        for attr, on in (("JavascriptEnabled", False),
                         ("JavascriptCanOpenWindows", False),
                         ("JavascriptCanAccessClipboard", False),
                         ("LocalContentCanAccessRemoteUrls", False),
                         ("LocalContentCanAccessFileUrls", False),
                         ("PluginsEnabled", False),
                         ("PdfViewerEnabled", False),
                         ("WebGLEnabled", False),
                         ("Accelerated2dCanvasEnabled", False),
                         ("LocalStorageEnabled", False),
                         ("HyperlinkAuditingEnabled", False),
                         ("DnsPrefetchEnabled", False),
                         ("ErrorPageEnabled", False),
                         ("NavigateOnDropEnabled", False),
                         ("AutoLoadImages", True)):
            flag = getattr(Settings.WebAttribute, attr, None)
            if flag is not None:
                try:
                    settings.setAttribute(flag, on)
                except Exception:
                    self._logger.debug("setting %s failed", attr, exc_info=True)
        view.setPage(page)
        try:
            view.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        except Exception:
            pass
        self._profile, self._interceptor = profile, interceptor
        return view

    def _create_text_browser(self):
        tb = _HtmlTextBrowser()
        tb.setOpenExternalLinks(False)
        tb.setOpenLinks(False)
        tb.setReadOnly(True)
        tb.anchorClicked.connect(lambda url: self._on_link(url.toString()))
        return tb

    def _create_backend_widget(self):
        view = None
        classes = _webengine()
        if classes:
            try:
                view = self._create_webengine_view(classes)
                self._engine = "webengine"
            except Exception:
                self._logger.exception("QtWebEngine view failed; using QTextBrowser")
                view = None
        if view is None:
            view = self._create_text_browser()
            self._engine = "textbrowser"

        try:
            sp = view.sizePolicy()
            expand = QtWidgets.QSizePolicy.Policy.Expanding
            fixed = QtWidgets.QSizePolicy.Policy.Preferred
            sp.setHorizontalPolicy(expand if (self.stretchable(YUIDimension.YD_HORIZ)
                                              or self.weight(YUIDimension.YD_HORIZ)) else fixed)
            sp.setVerticalPolicy(expand if (self.stretchable(YUIDimension.YD_VERT)
                                            or self.weight(YUIDimension.YD_VERT)) else fixed)
            view.setSizePolicy(sp)
        except Exception:
            self._logger.exception("Error setting size policy")

        self._backend_widget = view
        try:
            view.setEnabled(bool(self._enabled))
            if self._help_text:
                view.setToolTip(self._help_text)
            view.setVisible(self.visible())
        except Exception:
            self._logger.exception("Failed to apply initial widget state")
        self._push_content()
        self._logger.debug("_create_backend_widget: <%s> engine=%s", self.debugLabel(), self._engine)

    # -- content ------------------------------------------------------------

    def _push_content(self):
        view = getattr(self, "_backend_widget", None)
        if view is None:
            return
        try:
            document = self._sanitized().document
            if self._engine == "webengine" and len(document.encode("utf-8")) > _SETHTML_LIMIT:
                self._logger.warning("HTML too large for QtWebEngine setHtml(); showing text rendering")
                document = ("<!DOCTYPE html><html><head><meta charset=\"utf-8\"></head>"
                            f"<body>{self._text_simple_html()}</body></html>")
            view.setHtml(document)
        except Exception:
            self._logger.exception("Failed to show HTML content")

    def _apply_content(self):
        self._push_content()

    def _on_link(self, url: str):
        index = self._link_index(url)
        if index is not None:
            self._activate_link(index)

    # -- common widget API --------------------------------------------------

    def _set_backend_enabled(self, enabled):
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.setEnabled(bool(enabled))
        except Exception:
            self._logger.exception("Failed to set enabled state")

    def setVisible(self, visible=True):
        super().setVisible(visible)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.setVisible(visible)
        except Exception:
            self._logger.exception("setVisible failed")

    def setHelpText(self, help_text: str):
        super().setHelpText(help_text)
        try:
            if getattr(self, "_backend_widget", None) is not None:
                self._backend_widget.setToolTip(help_text)
        except Exception:
            self._logger.exception("setHelpText failed")
