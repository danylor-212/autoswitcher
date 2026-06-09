# core.py — V2 facade. The implementation lives in pipeline.py; this module
# keeps the import surface (`from core import LayoutSwitcherCore, VERSION`)
# stable for settings.py / tray.py / main.py.

from pipeline import LayoutSwitcherCore, VERSION

__all__ = ['LayoutSwitcherCore', 'VERSION']
