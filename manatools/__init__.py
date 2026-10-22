# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:

import os
import sys

# gettext picks the message language from LANGUAGE/LC_ALL/LC_MESSAGES/LANG,
# which Windows never sets, so every translation would fall back to English.
# Seed LANGUAGE from the user's UI language (e.g. "it_IT"), unless the user
# already chose one.
if sys.platform == 'win32' and not any(
        os.environ.get(v) for v in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG')):
    try:
        import ctypes
        import locale
        _lang = locale.windows_locale.get(
            ctypes.windll.kernel32.GetUserDefaultUILanguage())
        if _lang:
            os.environ['LANGUAGE'] = _lang
    except Exception:
        pass
