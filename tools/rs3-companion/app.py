"""
RS3 Companion — bar builder, tick-paced practice/autopress overlay, and
keybind/update settings in one app.

Practice tab has two modes, same distinction as the old standalone tool:
  - Prompt mode (default): shows/beeps the next ability. Sends nothing.
  - Autopress mode (armed explicitly): also sends the mapped key on cue,
    to whichever window has focus. Built for a self-hosted/private
    server — on Jagex's live game this is macroing under their rules and
    risks the account; that risk doesn't apply to your own server.

Global hotkeys (work even while another window, e.g. the game, has
focus): F8 autopress, F9 start/pause, F10 reset, F11 cycle style,
F12 sound. Everything is also reachable from the Practice tab's buttons.
"""

import sys
import webbrowser

import customtkinter as ctk

try:
    import keyboard
except ImportError:
    print("Missing dependency. Run: pip install -r requirements.txt")
    sys.exit(1)

try:
    import winsound
    def beep():
        winsound.Beep(880, 90)
except ImportError:
    def beep():
        pass  # non-Windows dev fallback

from data import STYLES, STYLE_ORDER, BOSSES, BOSS_ORDER
from config import AppConfig
import updater

TICK_MS = 600  # 1 RS3 game tick

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

BG = "#141219"
SURFACE = "#1c1a24"
MUTED = "#a39dbb"
TEXT = "#ece9f5"
TAG_COLORS = {
    "ultimate": "#a780f2",
    "threshold": "#6ea3ff",
    "basic": "#5c5968",
}


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        # CustomTkinter has a known Windows quirk where the window can
        # render without an OS title bar (no visible close button) until
        # it's hidden and re-shown once. Withdraw now, deiconify once
        # everything below is built, so there's always a way to close it.
        self.withdraw()
        self.title("RS3 Companion")
        self.geometry("860x620")
        self.configure(fg_color=BG)

        self.config_store = AppConfig()
        self.style_key = self.config_store.data["last_style"]
        self.boss_key = self.config_store.data["last_boss"]
        self.mode = self.config_store.data["last_mode"]

        # practice engine state
        self.running = False
        self.autopress = False
        self.sound_on = self.config_store.data["sound_on"]
        self.tick = 0
        self.step_idx = -1
        self.in_loop = False
        self.loop_pos = 0
        self.next_due_tick = 0
        self.current_name = ""
        self.overlay = None
        self.overlay_widgets = {}

        self._build_tabs()
        self._bind_hotkeys()
        self._reset_practice()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(TICK_MS, self._tick_loop)
        self.after(150, self.deiconify)

    # ---------------------------------------------------------------
    # Layout
    # ---------------------------------------------------------------

    def _build_tabs(self):
        self.tabs = ctk.CTkTabview(self, fg_color=SURFACE)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)
        self.tabs.add("Bar Builder")
        self.tabs.add("Practice")
        self.tabs.add("Settings")

        self._build_bar_builder(self.tabs.tab("Bar Builder"))
        self._build_practice(self.tabs.tab("Practice"))
        self._build_settings(self.tabs.tab("Settings"))

    # ---------- Bar Builder tab ----------

    def _build_bar_builder(self, parent):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(top, text="Style").grid(row=0, column=0, padx=(0, 6), sticky="w")
        self.style_menu = ctk.CTkOptionMenu(
            top, values=[STYLES[k]["label"] for k in STYLE_ORDER],
            command=self._on_style_change, width=160)
        self.style_menu.set(STYLES[self.style_key]["label"])
        self.style_menu.grid(row=0, column=1, padx=(0, 16))

        ctk.CTkLabel(top, text="Boss").grid(row=0, column=2, padx=(0, 6), sticky="w")
        self.boss_menu = ctk.CTkOptionMenu(
            top, values=[BOSSES[k]["label"] for k in BOSS_ORDER],
            command=self._on_boss_change, width=220)
        self.boss_menu.set(BOSSES[self.boss_key]["label"])
        self.boss_menu.grid(row=0, column=3, padx=(0, 16))

        ctk.CTkLabel(top, text="Mode").grid(row=0, column=4, padx=(0, 6), sticky="w")
        self.mode_menu = ctk.CTkOptionMenu(
            top, values=["Revo Basics + Manual", "Revo++ (Full Auto)"],
            command=self._on_mode_change, width=190)
        self.mode_menu.set("Revo Basics + Manual" if self.mode == "revo_basics"
                            else "Revo++ (Full Auto)")
        self.mode_menu.grid(row=0, column=5)

        self.bar_scroll = ctk.CTkScrollableFrame(parent, fg_color=SURFACE)
        self.bar_scroll.pack(fill="both", expand=True, padx=8, pady=8)

        self._render_bar_builder()

    def _render_bar_builder(self):
        for w in self.bar_scroll.winfo_children():
            w.destroy()

        style = STYLES[self.style_key]
        boss = BOSSES[self.boss_key]
        accent = style["color"]
        revopp = self.mode == "revo_pp"

        head = ctk.CTkFrame(self.bar_scroll, fg_color="transparent")
        head.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(head, text=f"{style['label']} — {boss['label']}",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=accent).pack(anchor="w")
        ctk.CTkLabel(head, text=f"{style['weapon']}   •   {style['resource']}",
                     text_color=MUTED).pack(anchor="w")

        if self.boss_key != "general":
            bframe = ctk.CTkFrame(self.bar_scroll, fg_color=BG, corner_radius=8)
            bframe.pack(fill="x", pady=(0, 12))
            ctk.CTkLabel(bframe, text=boss["summary"], wraplength=740,
                         justify="left", text_color=TEXT).pack(
                anchor="w", padx=12, pady=(10, 6))
            if boss["bar_notes"]:
                ctk.CTkLabel(bframe, text="Bar adjustments for this fight:",
                             font=ctk.CTkFont(weight="bold"),
                             text_color=accent).pack(anchor="w", padx=12)
                for note in boss["bar_notes"]:
                    ctk.CTkLabel(bframe, text=f"• {note}", wraplength=740,
                                 justify="left", text_color=TEXT).pack(
                        anchor="w", padx=20, pady=(2, 0))
            ctk.CTkFrame(bframe, height=6, fg_color="transparent").pack()

        ctk.CTkLabel(self.bar_scroll, text="REVOLUTION BAR",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=MUTED).pack(anchor="w", pady=(4, 4))

        for i, entry in enumerate(style["bar"], start=1):
            row = ctk.CTkFrame(self.bar_scroll, fg_color=BG, corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=str(i), width=24, text_color=MUTED,
                         font=ctk.CTkFont(family="Consolas")).pack(
                side="left", padx=(10, 6), pady=8)
            ctk.CTkLabel(row, text=entry["ability"], width=220, anchor="w",
                         font=ctk.CTkFont(family="Consolas", weight="bold"),
                         text_color=TEXT).pack(side="left", pady=8)
            tag = ctk.CTkLabel(
                row, text=entry["type"].upper(), width=90,
                fg_color=TAG_COLORS[entry["type"]], corner_radius=4,
                text_color="#141219" if entry["type"] != "basic" else TEXT,
                font=ctk.CTkFont(size=10, weight="bold"))
            tag.pack(side="left", padx=8, pady=8)
            role_text = entry["revopp"] if revopp else entry["basics"]
            ctk.CTkLabel(row, text=role_text, anchor="w", justify="left",
                         wraplength=380, text_color=MUTED).pack(
                side="left", padx=(4, 10), pady=8, fill="x", expand=True)

        if boss["mechanics"]:
            ctk.CTkLabel(self.bar_scroll, text="BOSS MECHANICS",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=MUTED).pack(anchor="w", pady=(16, 4))
            for m in boss["mechanics"]:
                mrow = ctk.CTkFrame(self.bar_scroll, fg_color=BG, corner_radius=6)
                mrow.pack(fill="x", pady=2)
                ctk.CTkLabel(mrow, text=m["name"], width=220, anchor="w",
                             font=ctk.CTkFont(weight="bold"),
                             text_color=accent).pack(side="left", padx=10, pady=8)
                ctk.CTkLabel(mrow, text=m["counter"], anchor="w", justify="left",
                             wraplength=480, text_color=TEXT).pack(
                    side="left", padx=(4, 10), pady=8, fill="x", expand=True)

        ctk.CTkLabel(self.bar_scroll, text="DEFENSIVE & UTILITY",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=MUTED).pack(anchor="w", pady=(16, 4))
        for d in style["defensive"]:
            drow = ctk.CTkFrame(self.bar_scroll, fg_color=BG, corner_radius=6)
            drow.pack(fill="x", pady=2)
            ctk.CTkLabel(drow, text=d["mechanic"], width=220, anchor="w",
                         font=ctk.CTkFont(weight="bold"),
                         text_color=accent).pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(drow, text=d["counter"], anchor="w", justify="left",
                         wraplength=480, text_color=TEXT).pack(
                side="left", padx=(4, 10), pady=8, fill="x", expand=True)

        ctk.CTkLabel(self.bar_scroll, text="GEAR & RELIC TUNING",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=MUTED).pack(anchor="w", pady=(16, 4))
        gear = style["gear"]
        gframe = ctk.CTkFrame(self.bar_scroll, fg_color=BG, corner_radius=6)
        gframe.pack(fill="x", pady=2)
        for label, value in (("Aura", gear["aura"]), ("Pocket", gear["pocket"]),
                              ("Relics/Perks", gear["relics"])):
            grow = ctk.CTkFrame(gframe, fg_color="transparent")
            grow.pack(fill="x", padx=10, pady=6)
            ctk.CTkLabel(grow, text=label, width=110, anchor="w",
                         font=ctk.CTkFont(weight="bold"),
                         text_color=accent).pack(side="left")
            ctk.CTkLabel(grow, text=value, anchor="w", justify="left",
                         wraplength=560, text_color=TEXT).pack(
                side="left", fill="x", expand=True)

    def _on_style_change(self, label):
        self.style_key = next(k for k in STYLE_ORDER if STYLES[k]["label"] == label)
        self.config_store.data["last_style"] = self.style_key
        self._render_bar_builder()
        self._reset_practice()

    def _on_boss_change(self, label):
        self.boss_key = next(k for k in BOSS_ORDER if BOSSES[k]["label"] == label)
        self.config_store.data["last_boss"] = self.boss_key
        self._render_bar_builder()

    def _on_mode_change(self, label):
        self.mode = "revo_pp" if label.startswith("Revo++") else "revo_basics"
        self.config_store.data["last_mode"] = self.mode
        self._render_bar_builder()

    # ---------- Practice tab ----------

    def _build_practice(self, parent):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=20, pady=20)

        self.p_style_label = ctk.CTkLabel(
            wrap, text=STYLES[self.style_key]["label"].upper(),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=STYLES[self.style_key]["color"])
        self.p_style_label.pack(anchor="w")

        self.p_now_label = ctk.CTkLabel(
            wrap, text="Press Start", font=ctk.CTkFont(size=30, weight="bold"),
            text_color=TEXT)
        self.p_now_label.pack(anchor="w", pady=(6, 2))

        self.p_next_label = ctk.CTkLabel(
            wrap, text="", font=ctk.CTkFont(size=15), text_color=MUTED)
        self.p_next_label.pack(anchor="w")

        self.p_tick_label = ctk.CTkLabel(
            wrap, text="tick 0", font=ctk.CTkFont(family="Consolas"),
            text_color=MUTED)
        self.p_tick_label.pack(anchor="w", pady=(10, 20))

        controls = ctk.CTkFrame(wrap, fg_color="transparent")
        controls.pack(fill="x")

        self.start_btn = ctk.CTkButton(controls, text="Start (F9)", width=140,
                                        command=self._toggle_running)
        self.start_btn.grid(row=0, column=0, padx=(0, 8), pady=4)
        ctk.CTkButton(controls, text="Reset (F10)", width=120,
                      command=lambda: self._reset_practice()).grid(
            row=0, column=1, padx=8, pady=4)
        ctk.CTkButton(controls, text="Pop-out overlay", width=140,
                      command=self._toggle_overlay).grid(
            row=0, column=2, padx=8, pady=4)

        switches = ctk.CTkFrame(wrap, fg_color="transparent")
        switches.pack(fill="x", pady=(12, 0))

        self.sound_switch = ctk.CTkSwitch(switches, text="Sound cue (F12)",
                                           command=self._toggle_sound)
        if self.sound_on:
            self.sound_switch.select()
        self.sound_switch.grid(row=0, column=0, padx=(0, 24), sticky="w")

        self.autopress_switch = ctk.CTkSwitch(
            switches, text="Autopress armed (F8)", progress_color="#c9382f",
            command=self._toggle_autopress)
        self.autopress_switch.grid(row=0, column=1, sticky="w")

        self.mode_indicator = ctk.CTkLabel(
            wrap, text="PROMPT ONLY", text_color=MUTED,
            font=ctk.CTkFont(size=11, weight="bold"))
        self.mode_indicator.pack(anchor="w", pady=(16, 0))

        warn = ("Autopress sends real keystrokes to whichever window has focus. "
                "Built for a self-hosted/private server — on Jagex's live game "
                "this is macroing under their rules and risks the account.")
        ctk.CTkLabel(wrap, text=warn, text_color=MUTED, wraplength=760,
                     justify="left", font=ctk.CTkFont(size=11)).pack(
            anchor="w", pady=(4, 0))

    def _close_overlay(self):
        if self.overlay and self.overlay.winfo_exists():
            self.overlay.destroy()
        self.overlay = None

    def _toggle_overlay(self):
        if self.overlay and self.overlay.winfo_exists():
            self._close_overlay()
            return
        self.overlay = ctk.CTkToplevel(self)
        # CustomTkinter has a known Windows quirk where a freshly-created
        # Toplevel can render with no OS title bar (and so no visible
        # close button) until it's hidden and re-shown once. Do that
        # before anything else so there's always a way to close this
        # window even if that glitch happens.
        self.overlay.withdraw()
        self.overlay.title("RS3 Companion — Practice")
        self.overlay.geometry("340x160+60+60")
        self.overlay.attributes("-topmost", True)
        self.overlay.configure(fg_color=BG)
        self.overlay.protocol("WM_DELETE_WINDOW", self._close_overlay)
        self.overlay.bind("<Escape>", lambda e: self._close_overlay())

        accent = ctk.CTkFrame(self.overlay, height=4,
                               fg_color=STYLES[self.style_key]["color"])
        accent.pack(fill="x")

        header = ctk.CTkFrame(self.overlay, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(8, 0))
        ctk.CTkLabel(header, text="Practice overlay", text_color=MUTED,
                     font=ctk.CTkFont(size=11)).pack(side="left")
        ctk.CTkButton(header, text="×", width=24, height=24, fg_color="transparent",
                      hover_color="#3a1f1e", text_color=MUTED,
                      command=self._close_overlay).pack(side="right")

        now = ctk.CTkLabel(self.overlay, text=self.current_name or "—",
                            font=ctk.CTkFont(size=20, weight="bold"),
                            text_color=TEXT)
        now.pack(anchor="w", padx=14, pady=(6, 2))
        nxt = ctk.CTkLabel(self.overlay, text="", text_color=MUTED)
        nxt.pack(anchor="w", padx=14)
        tickl = ctk.CTkLabel(self.overlay, text=f"tick {self.tick}",
                              text_color=MUTED, font=ctk.CTkFont(family="Consolas", size=10))
        tickl.pack(anchor="w", padx=14, pady=(10, 0))
        self.overlay_widgets = {"now": now, "next": nxt, "tick": tickl, "accent": accent}

        # Drag-to-move by the header, since the OS title bar can't
        # always be relied on to render (see the withdraw() note above).
        for widget in (header, self.overlay):
            widget.bind("<ButtonPress-1>", self._overlay_drag_start)
            widget.bind("<B1-Motion>", self._overlay_drag_move)

        self.overlay.after(150, self.overlay.deiconify)

    def _overlay_drag_start(self, event):
        self._overlay_drag_x = event.x_root - self.overlay.winfo_x()
        self._overlay_drag_y = event.y_root - self.overlay.winfo_y()

    def _overlay_drag_move(self, event):
        x = event.x_root - self._overlay_drag_x
        y = event.y_root - self._overlay_drag_y
        self.overlay.geometry(f"+{x}+{y}")

    # ---------- Settings tab ----------

    def _build_settings(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=SURFACE)
        scroll.pack(fill="both", expand=True, padx=8, pady=8)

        ctk.CTkLabel(scroll, text="KEY BINDINGS", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=MUTED).pack(anchor="w", pady=(4, 8))

        kb_top = ctk.CTkFrame(scroll, fg_color="transparent")
        kb_top.pack(fill="x")
        ctk.CTkLabel(kb_top, text="Editing bindings for:").pack(side="left", padx=(0, 8))
        self.settings_style_menu = ctk.CTkOptionMenu(
            kb_top, values=[STYLES[k]["label"] for k in STYLE_ORDER],
            command=self._render_keybind_editor, width=160)
        self.settings_style_menu.set(STYLES[self.style_key]["label"])
        self.settings_style_menu.pack(side="left")

        self.keybind_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.keybind_frame.pack(fill="x", pady=8)
        self.key_entries = {}
        self._render_keybind_editor(self.settings_style_menu.get())

        kb_buttons = ctk.CTkFrame(scroll, fg_color="transparent")
        kb_buttons.pack(fill="x", pady=(0, 20))
        ctk.CTkButton(kb_buttons, text="Save bindings",
                      command=self._save_keybinds).pack(side="left", padx=(0, 8))
        ctk.CTkButton(kb_buttons, text="Reset to defaults", fg_color="#443f56",
                      command=self._reset_keybinds).pack(side="left")

        ctk.CTkLabel(scroll, text="UPDATES", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=MUTED).pack(anchor="w", pady=(12, 8))
        self.version_label = ctk.CTkLabel(
            scroll, text=f"Installed version: {updater.local_version()}", text_color=TEXT)
        self.version_label.pack(anchor="w")
        self.update_status = ctk.CTkLabel(scroll, text="", text_color=MUTED,
                                           wraplength=700, justify="left")
        self.update_status.pack(anchor="w", pady=(4, 8))

        upd_buttons = ctk.CTkFrame(scroll, fg_color="transparent")
        upd_buttons.pack(fill="x")
        ctk.CTkButton(upd_buttons, text="Check for updates",
                      command=self._check_updates).pack(side="left", padx=(0, 8))
        self.update_now_btn = ctk.CTkButton(
            upd_buttons, text="Update now", state="disabled",
            command=self._apply_update)
        self.update_now_btn.pack(side="left")
        self._pending_release_url = None

    def _render_keybind_editor(self, style_label):
        style_key = next(k for k in STYLE_ORDER if STYLES[k]["label"] == style_label)
        for w in self.keybind_frame.winfo_children():
            w.destroy()
        self.key_entries = {}
        keys = self.config_store.keys_for(style_key)
        for ability in STYLES[style_key]["keys_default"]:
            row = ctk.CTkFrame(self.keybind_frame, fg_color=BG, corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=ability, anchor="w", width=280,
                         text_color=TEXT).pack(side="left", padx=10, pady=6)
            entry = ctk.CTkEntry(row, width=60)
            entry.insert(0, keys.get(ability, ""))
            entry.pack(side="left", padx=10, pady=6)
            self.key_entries[ability] = entry
        self._keybind_editor_style = style_key

    def _save_keybinds(self):
        style_key = self._keybind_editor_style
        for ability, entry in self.key_entries.items():
            self.config_store.set_key(style_key, ability, entry.get().strip())
        self.config_store.save()

    def _reset_keybinds(self):
        style_key = self._keybind_editor_style
        self.config_store.reset_keys(style_key)
        self.config_store.save()
        self._render_keybind_editor(STYLES[style_key]["label"])

    def _check_updates(self):
        self.update_status.configure(text="Checking...")
        self.update()  # flush UI before the (blocking) network call
        tag, url, notes = updater.latest_release()
        local = updater.local_version()
        if tag is None:
            self.update_status.configure(text=notes)
            self.update_now_btn.configure(state="disabled")
            self._pending_release_url = None
            return
        if tag.lstrip("v") == local.lstrip("v"):
            self.update_status.configure(text=f"Already up to date ({local}).")
            self.update_now_btn.configure(state="disabled")
            self._pending_release_url = None
        else:
            self.update_status.configure(
                text=f"Update available: {local} → {tag}\n{notes[:300]}")
            self._pending_release_url = url
            if updater.is_git_checkout():
                self.update_now_btn.configure(state="normal", text="Update now (git pull)")
            else:
                self.update_now_btn.configure(state="normal", text="Open release page")

    def _apply_update(self):
        if updater.is_git_checkout():
            ok, msg = updater.apply_git_update()
            self.update_status.configure(text=msg)
            if ok:
                self.update_now_btn.configure(state="disabled")
        elif self._pending_release_url:
            webbrowser.open(self._pending_release_url)

    # ---------------------------------------------------------------
    # Global hotkeys
    # ---------------------------------------------------------------

    def _bind_hotkeys(self):
        # keyboard's hotkey callbacks run on its own listener thread, not
        # Tkinter's main loop -- self.after(0, ...) marshals the actual
        # work back onto the main thread before touching any widget.
        keyboard.add_hotkey("f8", lambda: self.after(0, self._toggle_autopress))
        keyboard.add_hotkey("f9", lambda: self.after(0, self._toggle_running))
        keyboard.add_hotkey("f10", lambda: self.after(0, self._reset_practice))
        keyboard.add_hotkey("f11", lambda: self.after(0, self._cycle_style))
        keyboard.add_hotkey("f12", lambda: self.after(0, self._toggle_sound))

    def _toggle_autopress(self):
        self.autopress = not self.autopress
        state = "AUTOPRESS ARMED" if self.autopress else "PROMPT ONLY"
        color = "#ff7a70" if self.autopress else MUTED
        self.mode_indicator.configure(text=state, text_color=color)
        if self.autopress:
            self.autopress_switch.select()
        else:
            self.autopress_switch.deselect()

    def _toggle_running(self):
        self.running = not self.running
        self.start_btn.configure(text="Pause (F9)" if self.running else "Start (F9)")
        if self.running and self.step_idx == -1:
            self._reset_practice(keep_running=True)

    def _toggle_sound(self):
        self.sound_on = not self.sound_on
        self.config_store.data["sound_on"] = self.sound_on
        if self.sound_on:
            self.sound_switch.select()
        else:
            self.sound_switch.deselect()

    def _cycle_style(self):
        idx = STYLE_ORDER.index(self.style_key)
        next_key = STYLE_ORDER[(idx + 1) % len(STYLE_ORDER)]
        self.style_menu.set(STYLES[next_key]["label"])
        self._on_style_change(STYLES[next_key]["label"])

    # ---------------------------------------------------------------
    # Tick engine
    # ---------------------------------------------------------------

    def _reset_practice(self, keep_running=False):
        self.tick = 0
        self.step_idx = 0
        self.in_loop = False
        self.loop_pos = 0
        if not keep_running:
            self.running = False
            if hasattr(self, "start_btn"):
                self.start_btn.configure(text="Start (F9)")
        opener = STYLES[self.style_key]["opener"]
        self.next_due_tick = opener[0][1]
        self.p_style_label.configure(text=STYLES[self.style_key]["label"].upper(),
                                      text_color=STYLES[self.style_key]["color"])
        self._render_current(opener[0][0])

    def _tick_loop(self):
        if self.running:
            self.tick += 1
            self._maybe_advance()
        self.p_tick_label.configure(text=f"tick {self.tick}")
        if self.overlay and self.overlay.winfo_exists():
            self.overlay_widgets["tick"].configure(text=f"tick {self.tick}")
        self.after(TICK_MS, self._tick_loop)

    def _maybe_advance(self):
        if self.tick < self.next_due_tick:
            return
        style = STYLES[self.style_key]
        opener, loop, interval = style["opener"], style["loop"], style["loop_interval_ticks"]

        if not self.in_loop:
            self.step_idx += 1
            if self.step_idx >= len(opener):
                self.in_loop = True
                self.loop_pos = 0
                self.next_due_tick = self.tick + interval
                self._render_current(loop[0])
                self._cue()
                return
            name, _ = opener[self.step_idx]
            self._render_current(name)
            if self.step_idx + 1 < len(opener):
                self.next_due_tick = self.tick + opener[self.step_idx + 1][1]
            else:
                self.next_due_tick = self.tick + interval
            self._cue()
        else:
            self.loop_pos = (self.loop_pos + 1) % len(loop)
            self.next_due_tick = self.tick + interval
            self._render_current(loop[self.loop_pos])
            self._cue()

    def _render_current(self, name):
        self.current_name = name
        upcoming = self._peek_next()
        self.p_now_label.configure(text=name)
        self.p_next_label.configure(text=f"next: {upcoming}" if upcoming else "")
        if self.overlay and self.overlay.winfo_exists():
            self.overlay_widgets["now"].configure(text=name)
            self.overlay_widgets["next"].configure(
                text=f"next: {upcoming}" if upcoming else "")
            self.overlay_widgets["accent"].configure(
                fg_color=STYLES[self.style_key]["color"])

    def _peek_next(self):
        style = STYLES[self.style_key]
        opener, loop = style["opener"], style["loop"]
        if not self.in_loop:
            nxt_idx = self.step_idx + 1
            if nxt_idx < len(opener):
                return opener[nxt_idx][0]
            return loop[0]
        return loop[(self.loop_pos + 1) % len(loop)]

    def _cue(self):
        if self.sound_on:
            beep()
        if self.autopress:
            key = self.config_store.keys_for(self.style_key).get(self.current_name)
            if key:
                keyboard.send(key)

    # ---------------------------------------------------------------

    def _on_close(self):
        self.config_store.save()
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        self.destroy()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
