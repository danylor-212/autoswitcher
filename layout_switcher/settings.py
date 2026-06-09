
# settings.py — Dark UI with customtkinter, matching AutoSwitch landing page brand.

import tkinter as tk
import customtkinter as ctk

from core import VERSION
from shortcut import parse_shortcut, format_shortcut

# ── Design tokens (from landing page) ────────────────────────────────────────
_BG          = "#0A1628"
_BG_ELEVATED = "#0F1D32"
_BG_CARD     = "#122240"
_BG_HOVER    = "#162A4E"
_VIOLET      = "#A78BFA"
_VIOLET_LT   = "#C4B5FD"
_VIOLET_DK   = "#7C3AED"
_TEXT         = "#FFFFFF"
_TEXT_SEC     = "#8B8FA3"
_TEXT_MUTED   = "#4D5166"
_BORDER       = "#2A2550"
_SUCCESS      = "#34D399"
_ERROR        = "#F87171"

_FONT_BODY   = ("Segoe UI", 13)
_FONT_SMALL  = ("Segoe UI", 11)
_FONT_TITLE  = ("Segoe UI", 18, "bold")
_FONT_HEAD   = ("Segoe UI", 13, "bold")
_FONT_MONO   = ("Consolas", 13)
_FONT_MONO_S = ("Consolas", 11)


class SettingsWindow:
    """Dark-themed settings window using customtkinter."""

    def __init__(self, root: ctk.CTk, core):
        self.root = root
        self.core = core

        self.root.title("AutoSwitcher")
        self.root.geometry("480x600")
        self.root.resizable(False, False)
        self.root.configure(fg_color=_BG)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        # Shortcut capture state
        self._capturing = False

        self._build_ui()
        self.refresh_data()

    # ══════════════════════════════════════════════════════════════════════
    # UI Construction
    # ══════════════════════════════════════════════════════════════════════
    def _build_ui(self):
        self.tabs = ctk.CTkTabview(
            self.root,
            fg_color=_BG_ELEVATED,
            segmented_button_fg_color=_BG_CARD,
            segmented_button_selected_color=_VIOLET,
            segmented_button_selected_hover_color=_VIOLET_LT,
            segmented_button_unselected_color=_BG_CARD,
            segmented_button_unselected_hover_color=_BG_HOVER,
            text_color=_TEXT,
            corner_radius=12,
        )
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(12, 12))

        self.tabs.add("General")
        self.tabs.add("Whitelist")
        self.tabs.add("Apps")
        self.tabs.add("About")

        self._build_general_tab(self.tabs.tab("General"))
        self._build_whitelist_tab(self.tabs.tab("Whitelist"))
        self._build_apps_tab(self.tabs.tab("Apps"))
        self._build_about_tab(self.tabs.tab("About"))

    # ── General tab ──────────────────────────────────────────────────────
    def _build_general_tab(self, parent):
        parent.configure(fg_color=_BG_ELEVATED)

        # Master toggle
        self.var_enabled = ctk.BooleanVar()
        self._switch(parent, "Enable Auto-Switching", self.var_enabled,
                     lambda: self._on_toggle('enabled', self.var_enabled),
                     pady=(0, 12))

        self._separator(parent)

        # Direction
        self._label(parent, "Switching direction", font=_FONT_HEAD)
        self.var_en_uk = ctk.BooleanVar()
        self._switch(parent, "English  \u2192  Ukrainian", self.var_en_uk,
                     lambda: self._on_toggle('switch_en_to_uk', self.var_en_uk),
                     indent=True)
        self.var_uk_en = ctk.BooleanVar()
        self._switch(parent, "Ukrainian  \u2192  English", self.var_uk_en,
                     lambda: self._on_toggle('switch_uk_to_en', self.var_uk_en),
                     indent=True, pady=(0, 12))

        self._separator(parent)

        # T9
        self._label(parent, "T9 Autocorrect", font=_FONT_HEAD)
        self.var_t9_en = ctk.BooleanVar()
        self._switch(parent, "English T9", self.var_t9_en,
                     lambda: self._on_toggle('t9_eng', self.var_t9_en),
                     indent=True)
        self.var_t9_uk = ctk.BooleanVar()
        self._switch(parent, "Ukrainian T9", self.var_t9_uk,
                     lambda: self._on_toggle('t9_ukr', self.var_t9_uk),
                     indent=True, pady=(0, 12))

        self._separator(parent)

        # Notifications
        self.var_notifications = ctk.BooleanVar()
        self._switch(parent, "Tray notifications", self.var_notifications,
                     lambda: self._on_toggle('notifications_enabled',
                                             self.var_notifications),
                     pady=(0, 12))

        self._separator(parent)

        # Revert shortcut
        self._label(parent, "Revert shortcut", font=_FONT_HEAD)
        shortcut_frame = ctk.CTkFrame(parent, fg_color=_BG_CARD,
                                       corner_radius=8, border_width=1,
                                       border_color=_BORDER)
        shortcut_frame.pack(fill="x", pady=(4, 12))
        shortcut_inner = ctk.CTkFrame(shortcut_frame, fg_color="transparent")
        shortcut_inner.pack(fill="x", padx=12, pady=10)

        self.lbl_shortcut = ctk.CTkLabel(
            shortcut_inner, text="Alt + 2", font=_FONT_MONO,
            text_color=_VIOLET, anchor="w",
        )
        self.lbl_shortcut.pack(side="left", fill="x", expand=True)

        self.btn_shortcut = ctk.CTkButton(
            shortcut_inner, text="Change", width=80, height=28,
            font=_FONT_SMALL, corner_radius=6,
            fg_color=_VIOLET_DK, hover_color=_VIOLET,
            text_color=_TEXT, command=self._start_capture,
        )
        self.btn_shortcut.pack(side="right")

        self._separator(parent)

        # Layout variant
        self._label(parent, "Keyboard layout", font=_FONT_HEAD)
        self.var_layout_variant = ctk.StringVar(value="standard")
        ctk.CTkRadioButton(
            parent, text="Standard  (ЙЦУКЕН)", font=_FONT_SMALL,
            variable=self.var_layout_variant, value="standard",
            fg_color=_VIOLET, hover_color=_VIOLET_LT,
            border_color=_BORDER, text_color=_TEXT_SEC,
            command=self._on_variant_change,
        ).pack(anchor="w", padx=(16, 0), pady=(2, 0))
        ctk.CTkRadioButton(
            parent, text="Enhanced  (with Ґ)", font=_FONT_SMALL,
            variable=self.var_layout_variant, value="enhanced",
            fg_color=_VIOLET, hover_color=_VIOLET_LT,
            border_color=_BORDER, text_color=_TEXT_SEC,
            command=self._on_variant_change,
        ).pack(anchor="w", padx=(16, 0), pady=(2, 0))

        # Status bar
        self.status_general = ctk.CTkLabel(
            parent, text="", font=_FONT_SMALL, text_color=_TEXT_MUTED,
        )
        self.status_general.pack(side="bottom", anchor="w", pady=(8, 0))

    # ── Whitelist tab ────────────────────────────────────────────────────
    def _build_whitelist_tab(self, parent):
        parent.configure(fg_color=_BG_ELEVATED)
        self._label(parent, "Words that are never auto-corrected:",
                     font=_FONT_SMALL, color=_TEXT_SEC)

        # Scrollable list
        self.wl_scroll = ctk.CTkScrollableFrame(
            parent, fg_color=_BG_CARD, corner_radius=8,
            border_width=1, border_color=_BORDER, height=260,
        )
        self.wl_scroll.pack(fill="both", expand=True, pady=(4, 8))

        # Entry + Add
        ctrl = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl.pack(fill="x")
        self.entry_word = ctk.CTkEntry(
            ctrl, font=_FONT_SMALL, height=34,
            fg_color=_BG_CARD, border_color=_BORDER,
            text_color=_TEXT, placeholder_text="Add word...",
            placeholder_text_color=_TEXT_MUTED,
        )
        self.entry_word.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_word.bind("<Return>", lambda _: self._add_word())

        ctk.CTkButton(
            ctrl, text="Add", width=60, height=34, font=_FONT_SMALL,
            fg_color=_VIOLET, hover_color=_VIOLET_LT, text_color=_BG,
            corner_radius=6, command=self._add_word,
        ).pack(side="right")

        self.status_whitelist = ctk.CTkLabel(
            parent, text="", font=_FONT_SMALL, text_color=_TEXT_MUTED,
        )
        self.status_whitelist.pack(anchor="w", pady=(4, 0))

    # ── Apps tab ─────────────────────────────────────────────────────────
    def _build_apps_tab(self, parent):
        parent.configure(fg_color=_BG_ELEVATED)
        self._label(parent, "Disable auto-correction in these apps:",
                     font=_FONT_SMALL, color=_TEXT_SEC)
        self._label(parent, "Enter the .exe name, e.g. keepass.exe",
                     font=("Segoe UI", 10), color=_TEXT_MUTED)

        self.apps_scroll = ctk.CTkScrollableFrame(
            parent, fg_color=_BG_CARD, corner_radius=8,
            border_width=1, border_color=_BORDER, height=260,
        )
        self.apps_scroll.pack(fill="both", expand=True, pady=(4, 8))

        ctrl = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl.pack(fill="x")
        self.entry_app = ctk.CTkEntry(
            ctrl, font=_FONT_SMALL, height=34,
            fg_color=_BG_CARD, border_color=_BORDER,
            text_color=_TEXT, placeholder_text="app.exe",
            placeholder_text_color=_TEXT_MUTED,
        )
        self.entry_app.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_app.bind("<Return>", lambda _: self._add_app())

        ctk.CTkButton(
            ctrl, text="Add", width=60, height=34, font=_FONT_SMALL,
            fg_color=_VIOLET, hover_color=_VIOLET_LT, text_color=_BG,
            corner_radius=6, command=self._add_app,
        ).pack(side="right")

        self.status_apps = ctk.CTkLabel(
            parent, text="", font=_FONT_SMALL, text_color=_TEXT_MUTED,
        )
        self.status_apps.pack(anchor="w", pady=(4, 0))

    # ── About tab ────────────────────────────────────────────────────────
    def _build_about_tab(self, parent):
        parent.configure(fg_color=_BG_ELEVATED)

        ctk.CTkLabel(
            parent, text="AutoSwitcher", font=_FONT_TITLE,
            text_color=_TEXT,
        ).pack(anchor="w", pady=(12, 0))

        ctk.CTkLabel(
            parent, text=f"v{VERSION}", font=_FONT_MONO_S,
            text_color=_TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 12))

        self._separator(parent)

        # Correction counter
        counter_frame = ctk.CTkFrame(parent, fg_color="transparent")
        counter_frame.pack(anchor="w", pady=(0, 12))
        ctk.CTkLabel(
            counter_frame, text="Corrections today:", font=_FONT_BODY,
            text_color=_TEXT_SEC,
        ).pack(side="left")
        self.lbl_counter = ctk.CTkLabel(
            counter_frame, text="0", font=("Segoe UI", 16, "bold"),
            text_color=_VIOLET,
        )
        self.lbl_counter.pack(side="left", padx=(8, 0))

        self._separator(parent)

        # Shortcut help
        shortcut_text = format_shortcut(self.core._revert_shortcut)
        self.lbl_help = ctk.CTkLabel(
            parent,
            text=f"{shortcut_text}  \u2014  undo / force-swap / whitelist\n"
                 f"Works within 5 seconds of correction",
            font=_FONT_MONO_S,
            text_color=_TEXT_MUTED,
            justify="left",
        )
        self.lbl_help.pack(anchor="w", pady=(0, 12))

        self._separator(parent)

        ctk.CTkLabel(
            parent,
            text="Keyboard layout auto-switcher EN \u2194 UK\n"
                 "by Antigravity",
            font=_FONT_SMALL, text_color=_TEXT_MUTED, justify="left",
        ).pack(anchor="w", pady=(0, 0))

    # ══════════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════════
    def _switch(self, parent, text, var, command, indent=False, pady=(0, 4)):
        """Create a CTkSwitch toggle."""
        sw = ctk.CTkSwitch(
            parent, text=text, variable=var, command=command,
            font=_FONT_BODY, text_color=_TEXT_SEC,
            fg_color=_BG_CARD, progress_color=_VIOLET,
            button_color=_TEXT, button_hover_color=_VIOLET_LT,
        )
        padx = (20, 0) if indent else (0, 0)
        sw.pack(anchor="w", padx=padx, pady=pady)

    def _label(self, parent, text, font=_FONT_BODY, color=_TEXT):
        ctk.CTkLabel(parent, text=text, font=font,
                     text_color=color).pack(anchor="w", pady=(0, 4))

    def _separator(self, parent):
        ctk.CTkFrame(parent, height=1, fg_color=_BORDER).pack(
            fill="x", pady=(0, 10))

    def _row_item(self, scroll_frame, text, remove_cb):
        """A single row in a scrollable list: label + X button."""
        row = ctk.CTkFrame(scroll_frame, fg_color=_BG_HOVER,
                           corner_radius=6, height=32)
        row.pack(fill="x", pady=(0, 3), padx=2)
        row.pack_propagate(False)
        ctk.CTkLabel(
            row, text=text, font=_FONT_SMALL, text_color=_TEXT,
            anchor="w",
        ).pack(side="left", padx=(10, 0), fill="x", expand=True)
        ctk.CTkButton(
            row, text="\u00d7", width=28, height=24, font=("Consolas", 14),
            fg_color="transparent", hover_color=_ERROR,
            text_color=_TEXT_MUTED, corner_radius=4,
            command=lambda: remove_cb(text),
        ).pack(side="right", padx=(0, 4))

    # ══════════════════════════════════════════════════════════════════════
    # Window management
    # ══════════════════════════════════════════════════════════════════════
    def show(self):
        self.refresh_data()
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(100, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()

    def hide(self):
        self._stop_capture()
        self.root.withdraw()

    # ══════════════════════════════════════════════════════════════════════
    # Data sync
    # ══════════════════════════════════════════════════════════════════════
    def refresh_data(self):
        self.var_enabled.set(self.core.enabled)
        self.var_en_uk.set(self.core.switch_en_to_uk)
        self.var_uk_en.set(self.core.switch_uk_to_en)
        self.var_t9_en.set(self.core.t9_eng)
        self.var_t9_uk.set(self.core.t9_ukr)
        self.var_notifications.set(self.core.notifications_enabled)
        self.var_layout_variant.set(self.core.layout_variant)
        self.lbl_shortcut.configure(
            text=format_shortcut(self.core._revert_shortcut))
        self.lbl_counter.configure(text=str(self.core.correction_count))

        # Rebuild whitelist rows
        for w in self.wl_scroll.winfo_children():
            w.destroy()
        for word in sorted(self.core.whitelist):
            self._row_item(self.wl_scroll, word, self._remove_word)

        # Rebuild apps rows
        for w in self.apps_scroll.winfo_children():
            w.destroy()
        for app in sorted(self.core.disabled_apps):
            self._row_item(self.apps_scroll, app, self._remove_app)

        # Update help text
        shortcut_text = format_shortcut(self.core._revert_shortcut)
        self.lbl_help.configure(
            text=f"{shortcut_text}  \u2014  undo / force-swap / whitelist\n"
                 f"Works within 5 seconds of correction")

    # ══════════════════════════════════════════════════════════════════════
    # Event handlers
    # ══════════════════════════════════════════════════════════════════════
    def _on_toggle(self, field, var):
        # Write ONLY the toggled field: writing all of them here used to
        # clobber changes made via the tray menu while this window was open.
        setattr(self.core, field, var.get())
        self.core.save_config()
        self.status_general.configure(text="Settings saved.")

    def _on_variant_change(self):
        v = self.var_layout_variant.get()
        self.core.layout_variant = v
        self.core.mapper.set_variant(v)
        self.core.save_config()
        self.status_general.configure(text=f"Layout: {v}. Saved.")

    # ── Shortcut capture ─────────────────────────────────────────────────
    def _start_capture(self):
        if self._capturing:
            return
        self._capturing = True
        self.core.shortcut_capture_active = True
        self._capture_mods = set()
        self.lbl_shortcut.configure(text="Press shortcut...", text_color=_ERROR)
        self.btn_shortcut.configure(text="Cancel", fg_color=_ERROR,
                                     command=self._stop_capture)
        self._bind_kp = self.root.bind("<KeyPress>", self._on_capture_key, add="+")
        self._bind_kr = self.root.bind("<KeyRelease>", self._on_capture_release, add="+")
        # Timeout after 5 seconds
        self._capture_timer = self.root.after(5000, self._stop_capture)

    def _stop_capture(self):
        if not self._capturing:
            return
        self._capturing = False
        self.core.shortcut_capture_active = False
        try:
            self.root.unbind("<KeyPress>", self._bind_kp)
        except Exception:
            pass
        try:
            self.root.unbind("<KeyRelease>", self._bind_kr)
        except Exception:
            pass
        try:
            self.root.after_cancel(self._capture_timer)
        except Exception:
            pass
        self.lbl_shortcut.configure(
            text=format_shortcut(self.core._revert_shortcut),
            text_color=_VIOLET,
        )
        self.btn_shortcut.configure(text="Change", fg_color=_VIOLET_DK,
                                     command=self._start_capture)

    _TK_MODIFIER_MAP = {
        'Alt_L': 'alt', 'Alt_R': 'alt',
        'Control_L': 'ctrl', 'Control_R': 'ctrl',
        'Shift_L': 'shift', 'Shift_R': 'shift',
    }

    def _on_capture_key(self, event):
        """Tkinter <KeyPress> handler during shortcut capture."""
        keysym = event.keysym
        # Track modifier
        mod = self._TK_MODIFIER_MAP.get(keysym)
        if mod:
            self._capture_mods.add(mod)
            display = ' + '.join(m.capitalize() for m in sorted(self._capture_mods))
            self.lbl_shortcut.configure(text=f"{display} + ...")
            return "break"

        # Non-modifier key completes the capture
        if not self._capture_mods:
            return "break"  # need at least one modifier

        # Resolve key name
        key_name = keysym.lower()
        # Normalize common keysyms
        if key_name.startswith('kp_'):
            key_name = key_name[3:]  # keypad keys
        if len(key_name) == 1 and key_name.isalnum():
            pass  # single char like '2', 'a'
        elif key_name.startswith('f') and key_name[1:].isdigit():
            pass  # function key like f5
        else:
            return "break"  # unsupported key

        shortcut_str = '+'.join(sorted(self._capture_mods)) + '+' + key_name
        try:
            sd = parse_shortcut(shortcut_str)
            self.core._revert_shortcut = sd
            self.core.save_config()
            self._stop_capture()
            self.status_general.configure(
                text=f"Shortcut set to {format_shortcut(sd)}. Saved.")
        except ValueError:
            self._stop_capture()
        return "break"

    def _on_capture_release(self, event):
        keysym = event.keysym
        mod = self._TK_MODIFIER_MAP.get(keysym)
        if mod:
            self._capture_mods.discard(mod)
        return "break"

    # ── Whitelist ────────────────────────────────────────────────────────
    def _add_word(self):
        word = self.entry_word.get().strip()
        if not word:
            return
        before = len(self.core.whitelist)
        self.core.whitelist_add(word)
        if len(self.core.whitelist) > before:
            self.core.save_config()
            self.entry_word.delete(0, "end")
            self.refresh_data()
            self.status_whitelist.configure(text=f"Added '{word}'")
        else:
            self.status_whitelist.configure(text=f"'{word}' already in list")

    def _remove_word(self, word):
        self.core.whitelist_remove(word)
        self.core.save_config()
        self.refresh_data()
        self.status_whitelist.configure(text=f"Removed '{word}'")

    # ── Apps ─────────────────────────────────────────────────────────────
    def _add_app(self):
        app = self.entry_app.get().strip().lower()
        if not app:
            return
        if app not in {a.lower() for a in self.core.disabled_apps}:
            self.core.disabled_apps.append(app)
            self.core.save_config()
            self.entry_app.delete(0, "end")
            self.refresh_data()
            self.status_apps.configure(text=f"Added '{app}'")
        else:
            self.status_apps.configure(text=f"'{app}' already in list")

    def _remove_app(self, app):
        self.core.disabled_apps = [
            a for a in self.core.disabled_apps if a.lower() != app.lower()
        ]
        self.core.save_config()
        self.refresh_data()
        self.status_apps.configure(text=f"Removed '{app}'")
