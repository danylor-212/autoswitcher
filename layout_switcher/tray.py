
# tray.py
import pystray
from PIL import Image, ImageDraw
import os


class TrayIcon:
    def __init__(self, core_engine, settings_callback=None, quit_callback=None):
        self.core = core_engine
        self.settings_callback = settings_callback
        # quit_callback lets main.py shut down the Tk root cleanly
        self.quit_callback = quit_callback
        self.icon = None

    def create_image(self):
        """Brand icon: violet [ ] brackets on dark background."""
        size = 64
        bg = "#0A1628"
        violet = "#A78BFA"

        image = Image.new('RGB', (size, size), bg)
        dc = ImageDraw.Draw(image)

        # Rounded background (draw filled rounded rect)
        r = 12  # corner radius
        dc.rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=bg)

        # Left bracket [
        bw = 4  # stroke width
        x1, y1, y2 = 14, 10, 54
        arm = 7
        # vertical bar
        dc.rectangle((x1, y1, x1 + bw, y2), fill=violet)
        # top arm
        dc.rectangle((x1, y1, x1 + arm, y1 + bw), fill=violet)
        # bottom arm
        dc.rectangle((x1, y2 - bw, x1 + arm, y2), fill=violet)

        # Right bracket ]
        x2 = size - 14 - bw
        # vertical bar
        dc.rectangle((x2, y1, x2 + bw, y2), fill=violet)
        # top arm
        dc.rectangle((x2 - arm + bw, y1, x2 + bw, y1 + bw), fill=violet)
        # bottom arm
        dc.rectangle((x2 - arm + bw, y2 - bw, x2 + bw, y2), fill=violet)

        return image

    def _toggle_enabled(self, icon, item):
        """Toggle master on/off directly from the tray menu."""
        self.core.enabled = not self.core.enabled
        self.core.save_config()
        icon.update_menu()

    def on_settings(self, icon, item):
        if self.settings_callback:
            self.settings_callback()

    def on_exit(self, icon, item):
        self.core.stop()
        icon.stop()
        # Ask Tk to shut down gracefully instead of os._exit() which
        # skips all cleanup and can leave the app lingering in Task Manager.
        if self.quit_callback:
            self.quit_callback()
        else:
            os._exit(0)

    def notify(self, msg: str, title: str = "AutoSwitcher"):
        """Show a tray balloon notification. Safe to call from any thread."""
        if self.icon is not None:
            try:
                self.icon.notify(msg, title)
            except Exception:
                pass

    def run(self):
        image = self.create_image()

        menu = pystray.Menu(
            pystray.MenuItem(
                'Enabled',
                self._toggle_enabled,
                checked=lambda item: self.core.enabled,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Settings', self.on_settings),
            pystray.MenuItem('Exit', self.on_exit),
        )

        self.icon = pystray.Icon(
            "AutoSwitcher",
            image,
            "AutoSwitcher",
            menu,
        )

        print("Tray Icon Running.")
        self.icon.run()
