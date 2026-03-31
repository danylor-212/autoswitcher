
# main.py
import sys
import os
import threading
import customtkinter as ctk

# Ensure sibling modules are importable both when running as a script
# and when frozen by PyInstaller (sys._MEIPASS is already on sys.path).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mapper import LayoutMapper
from core import LayoutSwitcherCore
from tray import TrayIcon
from settings import SettingsWindow


def main():
    print("Initializing AutoSwitcher...")

    # 1. Core logic
    mapper = LayoutMapper()
    core = LayoutSwitcherCore(mapper)
    core.start()

    # 2. Tkinter root — must be created on the main thread.
    #    Start hidden; the user opens Settings via the tray menu.
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()  # Hide on startup — live in the tray

    settings_window = SettingsWindow(root, core)

    # Safe cross-thread callback: schedule show() on the Tk event loop
    def show_settings_safe():
        root.after(0, settings_window.show)

    # Safe cross-thread callback: ask Tk to quit from any thread
    def quit_safe():
        root.after(0, root.quit)

    # 3. Tray icon (runs in its own daemon thread)
    tray = TrayIcon(
        core,
        settings_callback=show_settings_safe,
        quit_callback=quit_safe,
    )

    # Wire tray notification callback so core can fire balloon notifications.
    # tray.icon is set inside tray.run() so notify() guards against None.
    core.notify_callback = tray.notify

    tray_thread = threading.Thread(target=tray.run, daemon=True, name="TrayThread")
    tray_thread.start()

    print("Running. Right-click the tray icon to open Settings or Exit.")

    # 4. Tk event loop — blocks until root.quit() or root.destroy()
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        print("Shutting down...")
        core.stop()


if __name__ == "__main__":
    main()
