# main.py — wiring: core pipeline, tray icon, settings window.
import sys
import os
import threading

# Ensure sibling modules are importable both when running as a script
# and when frozen by PyInstaller (sys._MEIPASS is already on sys.path).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk

from core import LayoutSwitcherCore, VERSION
from tray import TrayIcon
from settings import SettingsWindow


def main():
    print(f"Initializing AutoSwitcher v{VERSION}...")

    core = LayoutSwitcherCore()
    core.start()

    # Tkinter root — must be created on the main thread.
    # Start hidden; the user opens Settings via the tray menu.
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()

    settings_window = SettingsWindow(root, core)

    def show_settings_safe():
        root.after(0, settings_window.show)

    def quit_safe():
        root.after(0, root.quit)

    tray = TrayIcon(
        core,
        settings_callback=show_settings_safe,
        quit_callback=quit_safe,
    )
    core.notify_callback = tray.notify

    tray_thread = threading.Thread(target=tray.run, daemon=True, name="TrayThread")
    tray_thread.start()

    print("Running. Right-click the tray icon to open Settings or Exit.")
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        print("Shutting down...")
        core.stop()


if __name__ == "__main__":
    main()
