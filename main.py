import customtkinter as ctk
import threading
import requests
import re
import os
import sys
from PIL import Image
from io import BytesIO
from tkinter import messagebox
from core.engine import SyntioxEngine
from core.config import config
from core.history import history
from core.updater import check_for_updates

ctk.set_appearance_mode(config.get("theme", "Dark"))
ctk.set_default_color_theme("blue")

ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

APP_NAME = "Syntiox DL"
APP_VERSION = "1.0.0"


def get_asset_path(filename):
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'assets', filename)


class SyntioxDLApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Syntiox DL - Pro Downloader")
        self.geometry("900x680")
        self.resizable(False, False)
        self._center_window(900, 680)

        # Window icon
        icon_ico = get_asset_path('icon.ico')
        icon_png = get_asset_path('icon.png')
        if os.path.exists(icon_ico):
            self.after(200, lambda: self.iconbitmap(icon_ico))
        if os.path.exists(icon_png):
            try:
                self._icon_img = Image.open(icon_png)
                self.iconphoto(False, ctk.CTkImage(
                    light_image=self._icon_img,
                    dark_image=self._icon_img,
                    size=(32, 32)
                )._light_image)
            except Exception:
                pass

        # App state
        self.engine = SyntioxEngine()
        self.current_video_info = None
        self._download_thread = None
        self._progress_target = 0.0
        self._progress_current = 0.0
        self._progress_animating = False

        # Start invisible for fade-in
        self.attributes('-alpha', 0.0)

        self.setup_ui()
        self.check_system_requirements()
        self.after(60, self._fade_in)
        self.after(2000, self._check_for_updates)  # Check after UI is loaded

    # --- Window Helpers ---

    def _center_window(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _fade_in(self, alpha=0.0):
        alpha = min(alpha + 0.06, 1.0)
        self.attributes('-alpha', alpha)
        if alpha < 1.0:
            self.after(14, lambda: self._fade_in(alpha))

    # --- Progress Animation ---

    def _animate_progress(self):
        if not self._progress_animating:
            return
        diff = self._progress_target - self._progress_current
        if abs(diff) < 0.003:
            self._progress_current = self._progress_target
            self.progress_bar.set(self._progress_current)
            self._progress_animating = False
        else:
            self._progress_current += diff * 0.14
            self.progress_bar.set(self._progress_current)
            self.after(14, self._animate_progress)

    def _set_progress(self, value):
        self._progress_target = value
        if not self._progress_animating:
            self._progress_animating = True
            self._animate_progress()

    # --- UI Setup ---

    def setup_ui(self):
        # Header bar — buttons use pack(side=right) to avoid overlap/clip
        self.header_frame = ctk.CTkFrame(self, fg_color=("gray88", "gray14"), corner_radius=0, height=68)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        # Right-side buttons packed first so they anchor correctly
        header_right = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        header_right.pack(side="right", padx=12, pady=10)

        self.settings_btn = ctk.CTkButton(
            header_right, text="⚙️  Settings", width=118,
            fg_color="transparent", border_width=1,
            command=self.open_settings
        )
        self.settings_btn.pack(side="right", padx=(6, 0))

        self.history_btn = ctk.CTkButton(
            header_right, text="🕒  History", width=118,
            fg_color="transparent", border_width=1,
            command=self.open_history
        )
        self.history_btn.pack(side="right")

        # Title label fills remaining space (centered visually)
        self.header_label = ctk.CTkLabel(
            self.header_frame,
            text="⚡  SYNTIOX DL",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        self.header_label.pack(side="left", expand=True)

        # Thin separator line under header
        ctk.CTkFrame(self, height=2, fg_color=("gray70", "gray28")).pack(fill="x")

        # Main content container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=14)

        # URL Input card
        url_card = ctk.CTkFrame(self.main_container, corner_radius=12)
        url_card.pack(fill="x", pady=(0, 10))
        url_inner = ctk.CTkFrame(url_card, fg_color="transparent")
        url_inner.pack(fill="x", padx=14, pady=12)

        self.url_entry = ctk.CTkEntry(
            url_inner,
            placeholder_text="🔗   Paste YouTube or Playlist URL here...",
            height=42, font=ctk.CTkFont(size=13)
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.url_entry.bind("<Return>", lambda e: self.start_analyze())

        self.paste_btn = ctk.CTkButton(
            url_inner, text="📋", width=42, height=42,
            command=self._paste_url,
            fg_color=("gray78", "gray28"), hover_color=("gray68", "gray38")
        )
        self.paste_btn.pack(side="left", padx=(0, 8))

        self.analyze_btn = ctk.CTkButton(
            url_inner, text="Analyze", width=130, height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.start_analyze
        )
        self.analyze_btn.pack(side="left")

        # Video info card
        info_card = ctk.CTkFrame(self.main_container, corner_radius=12, height=155)
        info_card.pack(fill="x", pady=(0, 10))
        info_card.pack_propagate(False)

        self.thumb_label = ctk.CTkLabel(
            info_card, text="No Video\nLoaded",
            width=215, height=120,
            fg_color=("gray80", "gray22"),
            corner_radius=8,
            font=ctk.CTkFont(size=12)
        )
        self.thumb_label.place(x=14, rely=0.5, anchor="w")

        details_frame = ctk.CTkFrame(info_card, fg_color="transparent")
        details_frame.place(x=244, y=12, relwidth=0.72, relheight=0.85)

        self.title_label = ctk.CTkLabel(
            details_frame, text="Title: N/A",
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=570, justify="left", anchor="w"
        )
        self.title_label.pack(anchor="w", pady=(0, 10))

        self.status_label = ctk.CTkLabel(
            details_frame,
            text="●  Status: Waiting",
            text_color="gray55",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.status_label.pack(anchor="w")

        # Options card
        opts_card = ctk.CTkFrame(self.main_container, corner_radius=12)
        opts_card.pack(fill="x", pady=(0, 10))
        opts_inner = ctk.CTkFrame(opts_card, fg_color="transparent")
        opts_inner.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(opts_inner, text="Quality:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 6))
        self.format_var = ctk.StringVar(value="best")
        self.quality_dropdown = ctk.CTkOptionMenu(opts_inner, variable=self.format_var, values=["Wait for analyze..."], width=195)
        self.quality_dropdown.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(opts_inner, text="Format:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 6))
        self.ext_var = ctk.StringVar(value="mp4")
        self.ext_dropdown = ctk.CTkOptionMenu(opts_inner, variable=self.ext_var, values=["mp4", "mkv"], width=95)
        self.ext_dropdown.pack(side="left", padx=(0, 22))

        self.audio_only_var = ctk.BooleanVar(value=False)
        self.audio_checkbox = ctk.CTkCheckBox(
            opts_inner, text="🎵  Audio Only",
            variable=self.audio_only_var,
            command=self.toggle_audio_mode
        )
        self.audio_checkbox.pack(side="left")

        # Path card
        path_card = ctk.CTkFrame(self.main_container, corner_radius=12)
        path_card.pack(fill="x", pady=(0, 10))
        path_inner = ctk.CTkFrame(path_card, fg_color="transparent")
        path_inner.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(path_inner, text="📁", font=ctk.CTkFont(size=16)).pack(side="left", padx=(0, 8))
        self.path_var = ctk.StringVar(value=config.get("default_video_path"))
        self.path_entry = ctk.CTkEntry(path_inner, textvariable=self.path_var, height=38)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.browse_btn = ctk.CTkButton(path_inner, text="Browse", width=90, height=38, command=self.browse_folder)
        self.browse_btn.pack(side="left")

        # Progress card
        prog_card = ctk.CTkFrame(self.main_container, corner_radius=12)
        prog_card.pack(fill="x", pady=(0, 10))
        prog_inner = ctk.CTkFrame(prog_card, fg_color="transparent")
        prog_inner.pack(fill="x", padx=14, pady=12)

        self.progress_bar = ctk.CTkProgressBar(prog_inner, height=14, corner_radius=7)
        self.progress_bar.pack(fill="x", pady=(0, 8))
        self.progress_bar.set(0)

        self.progress_text = ctk.CTkLabel(
            prog_inner, text="0%  |  0.0 MiB/s  |  ETA: --:--",
            text_color="gray55", font=ctk.CTkFont(size=12)
        )
        self.progress_text.pack()

        # Download / Cancel buttons — grid so toggling doesn't shift layout
        self.btn_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.btn_frame.pack(pady=(4, 0))

        self.download_btn = ctk.CTkButton(
            self.btn_frame, text="⬇   START DOWNLOAD",
            width=265, height=50,
            font=ctk.CTkFont(size=15, weight="bold"),
            corner_radius=10,
            command=self.start_download
        )
        self.download_btn.grid(row=0, column=0, padx=8)
        self.download_btn.grid_remove()  # Hidden until analyze completes

        self.cancel_btn = ctk.CTkButton(
            self.btn_frame, text="✕   CANCEL",
            width=130, height=50,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#C0392B", hover_color="#96281B",
            corner_radius=10,
            command=self.cancel_download
        )
        self.cancel_btn.grid(row=0, column=1, padx=8)
        self.cancel_btn.grid_remove()  # Hidden until download starts

    # --- Update Check ---

    def _check_for_updates(self):
        """Check GitHub Releases API for a new version. Runs in background."""
        def on_result(info):
            if info:
                self.after(0, lambda: self._show_update_dialog(info))
        check_for_updates(APP_VERSION, on_result)

    def _show_update_dialog(self, info):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Update Available")
        dialog.geometry("500x440")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.focus()

        # Center dialog over main window
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 500) // 2
        y = self.winfo_y() + (self.winfo_height() - 440) // 2
        dialog.geometry(f"500x440+{x}+{y}")

        # Green header
        header = ctk.CTkFrame(dialog, fg_color="#1a6b3c", corner_radius=0, height=72)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="🎉  New Update Available!",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Version row
        ver_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        ver_frame.pack(fill="x", padx=20, pady=(14, 0))
        ctk.CTkLabel(
            ver_frame,
            text=f"v{info['current_version']}  →  v{info['latest_version']}",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(side="left")
        ctk.CTkLabel(
            ver_frame,
            text=info["published_at"],
            text_color="gray55",
            font=ctk.CTkFont(size=12)
        ).pack(side="right")

        # Release notes
        ctk.CTkLabel(
            dialog, text="What's New:",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
        ).pack(fill="x", padx=20, pady=(10, 4))

        notes_box = ctk.CTkTextbox(dialog, height=160, corner_radius=10, font=ctk.CTkFont(size=12))
        notes_box.pack(fill="x", padx=20)
        notes_box.insert("1.0", info["release_notes"])
        notes_box.configure(state="disabled")

        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(16, 20))

        def open_download():
            import webbrowser
            webbrowser.open(info["release_url"])
            dialog.destroy()

        ctk.CTkButton(
            btn_frame, text="⬇   Download Now",
            width=210, height=46,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1a6b3c", hover_color="#145530",
            corner_radius=10,
            command=open_download
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame, text="Later",
            width=100, height=46,
            fg_color=("gray78", "gray30"), hover_color=("gray68", "gray40"),
            corner_radius=10,
            command=dialog.destroy
        ).pack(side="right")

    # --- Helpers ---

    def _paste_url(self):
        try:
            text = self.clipboard_get()
            self.url_entry.delete(0, 'end')
            self.url_entry.insert(0, text)
        except Exception:
            pass

    def check_system_requirements(self):
        if not self.engine.check_ffmpeg():
            self.status_label.configure(
                text="●  FFmpeg not found. Will auto-install on first use.",
                text_color="orange"
            )

    def browse_folder(self):
        folder = ctk.filedialog.askdirectory(title="Select Download Folder")
        if folder:
            self.path_var.set(folder)

    def cancel_download(self):
        self.engine.cancel()
        self.progress_text.configure(text="Cancelling... Please wait.", text_color="orange")
        self.cancel_btn.configure(state="disabled")

    def _reset_buttons(self):
        self.analyze_btn.configure(state="normal")
        self.cancel_btn.grid_remove()
        self.download_btn.grid()
        self.download_btn.configure(state="normal")

    # --- Settings ---

    def open_settings(self):
        self.main_container.pack_forget()
        self.settings_btn.configure(text="🔙  Back", command=self.close_settings)

        if hasattr(self, "settings_container") and self.settings_container.winfo_exists():
            self.settings_container.pack(fill="both", expand=True, padx=20, pady=14)
            return

        self.settings_container = ctk.CTkFrame(self, fg_color="transparent")
        self.settings_container.pack(fill="both", expand=True, padx=20, pady=14)

        ctk.CTkLabel(
            self.settings_container, text="Settings",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w", pady=(0, 16))

        # Theme card
        theme_card = ctk.CTkFrame(self.settings_container, corner_radius=12)
        theme_card.pack(fill="x", pady=(0, 10))
        t_inner = ctk.CTkFrame(theme_card, fg_color="transparent")
        t_inner.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(t_inner, text="Appearance Theme", font=ctk.CTkFont(size=13)).pack(side="left")
        theme_var = ctk.StringVar(value=config.get("theme", "Dark"))
        def on_theme_change(choice):
            self.after(50, lambda: (ctk.set_appearance_mode(choice), config.set("theme", choice)))
        ctk.CTkOptionMenu(t_inner, variable=theme_var, values=["Dark", "Light", "System"], command=on_theme_change, width=140).pack(side="right")

        # Video path card
        vpath_card = ctk.CTkFrame(self.settings_container, corner_radius=12)
        vpath_card.pack(fill="x", pady=(0, 10))
        v_inner = ctk.CTkFrame(vpath_card, fg_color="transparent")
        v_inner.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(v_inner, text="Default Video Download Path:", font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(0, 6))
        v_row = ctk.CTkFrame(v_inner, fg_color="transparent")
        v_row.pack(fill="x")
        video_path_var = ctk.StringVar(value=config.get("default_video_path"))
        v_entry = ctk.CTkEntry(v_row, textvariable=video_path_var, height=36)
        v_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        def save_video_path(*_):
            val = video_path_var.get().strip()
            if val:
                err = config.set("default_video_path", val)
                if err:
                    messagebox.showerror("Save Error", err)
                if not self.audio_only_var.get():
                    self.path_var.set(val)

        v_entry.bind("<FocusOut>", save_video_path)

        def browse_video():
            f = ctk.filedialog.askdirectory()
            if f:
                video_path_var.set(f)
                save_video_path()

        ctk.CTkButton(v_row, text="Browse", width=90, height=36, command=browse_video).pack(side="left")

        # Audio path card
        apath_card = ctk.CTkFrame(self.settings_container, corner_radius=12)
        apath_card.pack(fill="x", pady=(0, 10))
        a_inner = ctk.CTkFrame(apath_card, fg_color="transparent")
        a_inner.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(a_inner, text="Default Audio Download Path:", font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(0, 6))
        a_row = ctk.CTkFrame(a_inner, fg_color="transparent")
        a_row.pack(fill="x")
        audio_path_var = ctk.StringVar(value=config.get("default_audio_path"))
        a_entry = ctk.CTkEntry(a_row, textvariable=audio_path_var, height=36)
        a_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        def save_audio_path(*_):
            val = audio_path_var.get().strip()
            if val:
                err = config.set("default_audio_path", val)
                if err:
                    messagebox.showerror("Save Error", err)
                if self.audio_only_var.get():
                    self.path_var.set(val)

        a_entry.bind("<FocusOut>", save_audio_path)

        def browse_audio():
            f = ctk.filedialog.askdirectory()
            if f:
                audio_path_var.set(f)
                save_audio_path()

        ctk.CTkButton(a_row, text="Browse", width=90, height=36, command=browse_audio).pack(side="left")

    def close_settings(self):
        if hasattr(self, "settings_container") and self.settings_container.winfo_exists():
            self.settings_container.pack_forget()
        self.main_container.pack(fill="both", expand=True, padx=20, pady=14)
        self.settings_btn.configure(text="⚙️  Settings", command=self.open_settings)

    # --- History ---

    def open_history(self):
        self.main_container.pack_forget()
        self.history_btn.configure(text="🔙  Back", command=self.close_history)
        self.settings_btn.configure(state="disabled")

        # Always destroy and rebuild for fresh data
        if hasattr(self, "history_container") and self.history_container.winfo_exists():
            self.history_container.destroy()

        self.history_container = ctk.CTkFrame(self, fg_color="transparent")
        self.history_container.pack(fill="both", expand=True, padx=20, pady=14)

        header = ctk.CTkFrame(self.history_container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header, text="Download History", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkButton(
            header, text="🗑  Clear All", width=100,
            fg_color="#C0392B", hover_color="#96281B",
            command=lambda: [history.clear_history(), self.open_history()]
        ).pack(side="right")

        scroll = ctk.CTkScrollableFrame(self.history_container, corner_radius=12)
        scroll.pack(fill="both", expand=True)

        hist_data = history.get_history()
        if not hist_data:
            ctk.CTkLabel(
                scroll, text="No download history found.",
                text_color="gray55", font=ctk.CTkFont(size=13)
            ).pack(pady=50)
        else:
            for item in hist_data:
                card = ctk.CTkFrame(scroll, corner_radius=10)
                card.pack(fill="x", pady=4)
                inner = ctk.CTkFrame(card, fg_color="transparent")
                inner.pack(fill="x", padx=12, pady=8)

                icon = "🎵" if item['type'] == 'audio' else "🎬"
                ctk.CTkLabel(inner, text=icon, font=ctk.CTkFont(size=18), width=28).pack(side="left", padx=(0, 10))

                info_col = ctk.CTkFrame(inner, fg_color="transparent")
                info_col.pack(side="left", fill="x", expand=True)
                ctk.CTkLabel(
                    info_col, text=item['title'],
                    font=ctk.CTkFont(size=13, weight="bold"),
                    anchor="w", wraplength=500, justify="left"
                ).pack(anchor="w")
                ctk.CTkLabel(
                    info_col,
                    text=f"{item['date']}   •   {item['type'].upper()} ({item['format'].upper()})",
                    text_color="gray55", font=ctk.CTkFont(size=11), anchor="w"
                ).pack(anchor="w", pady=(2, 0))

                def open_folder(p=item['path']):
                    if os.path.exists(p) and os.name == 'nt':
                        os.startfile(p)

                ctk.CTkButton(
                    inner, text="📂", width=42, height=36,
                    fg_color=("gray78", "gray28"), hover_color=("gray68", "gray38"),
                    command=open_folder
                ).pack(side="right")

    def close_history(self):
        if hasattr(self, "history_container") and self.history_container.winfo_exists():
            self.history_container.destroy()
        self.main_container.pack(fill="both", expand=True, padx=20, pady=14)
        self.history_btn.configure(text="🕒  History", command=self.open_history)
        self.settings_btn.configure(state="normal")

    # --- Thumbnail ---

    def load_thumbnail(self, url):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
            img.thumbnail((215, 120), Image.LANCZOS)
            w, h = img.size
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
            self.after(0, lambda: self._show_thumbnail(ctk_img))
        except Exception:
            pass

    def _show_thumbnail(self, ctk_img):
        self.thumb_label.configure(image=ctk_img, text="")
        self._thumb_ref = ctk_img

    # --- Analyze ---

    def start_analyze(self):
        url = self.url_entry.get().strip()
        if not url:
            return
        self.analyze_btn.configure(state="disabled")
        self.status_label.configure(text="●  Analyzing link... Please wait.", text_color="yellow")
        threading.Thread(target=self.process_analysis, args=(url,), daemon=True).start()

    def process_analysis(self, url):
        if not self.engine.check_ffmpeg():
            self.after(0, lambda: self.status_label.configure(text="●  FFmpeg not found. Auto-installing...", text_color="orange"))
            success = self.engine.install_ffmpeg_winget()
            if not success:
                self.after(0, lambda: self.status_label.configure(text="●  FFmpeg install failed. Please install manually.", text_color="red"))
                self.after(0, lambda: self.analyze_btn.configure(state="normal"))
                return
            self.after(0, lambda: self.status_label.configure(text="●  FFmpeg installed! Analyzing...", text_color="green"))

        info = self.engine.get_info(url)
        self.current_video_info = info

        # Auto-update yt-dlp on 403
        if info.get('type') == 'error' and '403' in info.get('message', ''):
            self.after(0, lambda: self.status_label.configure(text="●  403 Error. Auto-updating yt-dlp...", text_color="orange"))
            if self.engine.update_ytdlp():
                self.after(0, lambda: self.status_label.configure(text="●  Update success! Click Analyze again.", text_color="green"))
            else:
                self.after(0, lambda: self.status_label.configure(text="●  Auto-update failed.", text_color="red"))
            self.after(0, lambda: self.analyze_btn.configure(state="normal"))
            return

        def update_ui():
            if info.get('type') == 'error':
                msg = info.get('message', 'Unknown error').split('\n')[0]
                msg = (msg[:80] + '...') if len(msg) > 80 else msg
                self.status_label.configure(text=f"●  Error: {msg}", text_color="red")
                self.analyze_btn.configure(state="normal")
                return

            title = info.get('title', 'Unknown')
            self.title_label.configure(text=title)

            if info.get('type') == 'video':
                self.status_label.configure(text="●  Single Video   •   Ready to Download", text_color="#2ECC71")
                if info.get('thumb'):
                    threading.Thread(target=self.load_thumbnail, args=(info['thumb'],), daemon=True).start()

                # Populate dropdown based on current mode
                if self.audio_only_var.get():
                    # Audio mode — show real server audio formats
                    audio_formats = info.get('audio_formats', [])
                    if audio_formats:
                        vals = ["Best Quality"] + [af['label'] for af in audio_formats]
                    else:
                        vals = ["Best Quality"]
                    self.quality_dropdown.configure(values=vals)
                else:
                    # Video mode — show video resolutions
                    formats = info.get('formats', [])
                    vals = ["Best Quality"] + [f['res'] for f in formats]
                    self.quality_dropdown.configure(values=vals)
                self.quality_dropdown.set("Best Quality")

            elif info.get('type') == 'playlist':
                count = info.get('count', 0)
                self.status_label.configure(text=f"●  Playlist   •   {count} videos   •   Ready", text_color="#2ECC71")
                self.quality_dropdown.configure(values=["Best Quality"])
                self.quality_dropdown.set("Best Quality")

            self.analyze_btn.configure(state="normal")
            self.download_btn.grid()

        self.after(0, update_ui)

    # --- Audio Mode ---

    def toggle_audio_mode(self):
        if self.audio_only_var.get():
            # Show real server audio formats only if a video has been analyzed
            if self.current_video_info and self.current_video_info.get('type') == 'video':
                audio_formats = self.current_video_info.get('audio_formats', [])
                vals = ["Best Quality"] + [af['label'] for af in audio_formats] if audio_formats else ["Best Quality"]
            else:
                vals = ["Best Quality"]  # No analyze done yet
            self.quality_dropdown.configure(values=vals)
            self.format_var.set("Best Quality")
            self.ext_dropdown.configure(values=["mp3", "wav", "flac"])
            self.ext_var.set("mp3")
            self.path_var.set(config.get("default_audio_path"))
        else:
            self.ext_dropdown.configure(values=["mp4", "mkv"])
            self.ext_var.set("mp4")
            self.path_var.set(config.get("default_video_path"))
            if self.current_video_info and self.current_video_info.get('type') == 'video':
                formats = self.current_video_info.get('formats', [])
                self.quality_dropdown.configure(values=["Best Quality"] + [f['res'] for f in formats])
            else:
                self.quality_dropdown.configure(values=["Best Quality"])
            self.format_var.set("Best Quality")

    # --- Progress Hook ---

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                pct_str = ANSI_ESCAPE_RE.sub('', d.get('_percent_str', '0%')).strip()
                spd_str = ANSI_ESCAPE_RE.sub('', d.get('_speed_str', 'N/A')).strip()
                eta_str = ANSI_ESCAPE_RE.sub('', d.get('_eta_str', 'N/A')).strip()

                try:
                    pf = float(pct_str.replace('%', '')) / 100.0
                except ValueError:
                    pf = None

                text = f"{pct_str}  |  Speed: {spd_str}  |  ETA: {eta_str}"

                info_dict = d.get('info_dict', {})
                p_idx = info_dict.get('playlist_index')
                p_cnt = info_dict.get('playlist_count') or info_dict.get('n_entries')
                if p_idx and p_cnt:
                    text = f"[Video {p_idx}/{p_cnt}]  " + text

                if pf is not None:
                    self.after(0, lambda v=pf: self._set_progress(v))
                self.after(0, lambda t=text: self.progress_text.configure(text=t))
            except Exception:
                pass

        elif d['status'] == 'finished':
            self.after(0, lambda: self.progress_text.configure(text="⚙  Merging files... please wait.", text_color="yellow"))

    # --- Download ---

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            return

        is_audio = self.audio_only_var.get()
        selected_res = self.format_var.get()
        selected_ext = self.ext_var.get()
        custom_path = self.path_var.get().strip() or None

        format_id = 'best'
        audio_quality = '320'

        if is_audio:
            if selected_res != "Best Quality" and self.current_video_info:
                # Find the real server audio format_id from the label
                audio_formats = self.current_video_info.get('audio_formats', [])
                for af in audio_formats:
                    if af['label'] == selected_res:
                        format_id = af['id']
                        audio_quality = str(af['abr'])  # Use actual bitrate for ffmpeg
                        break
        else:
            if selected_res != "Best Quality" and self.current_video_info:
                for f in self.current_video_info.get('formats', []):
                    if f['res'] == selected_res:
                        format_id = f['id']
                        break

        self.analyze_btn.configure(state="disabled")
        self.download_btn.grid_remove()
        self.cancel_btn.grid()
        self.cancel_btn.configure(state="normal")
        self._progress_current = 0.0
        self._set_progress(0.0)
        self.progress_text.configure(text="Starting download...", text_color="gray60")

        self._download_thread = threading.Thread(
            target=self.process_download,
            args=(url, format_id, is_audio, custom_path, audio_quality, selected_ext),
            daemon=True
        )
        self._download_thread.start()

    def process_download(self, url, format_id, is_audio, custom_path, audio_quality, selected_ext):
        if is_audio:
            result = self.engine.download(
                url, format_id, is_audio, self.progress_hook,
                custom_path=custom_path, audio_quality=audio_quality, audio_format=selected_ext
            )
        else:
            result = self.engine.download(
                url, format_id, is_audio, self.progress_hook,
                custom_path=custom_path, audio_quality=audio_quality, video_format=selected_ext
            )

        # Auto-update yt-dlp on 403
        if result.get("status") != "success" and "403" in result.get('message', ''):
            self.after(0, lambda: self.progress_text.configure(text="403 Error. Auto-updating yt-dlp...", text_color="orange"))
            if self.engine.update_ytdlp():
                self.after(0, lambda: self.progress_text.configure(text="Update success! Try downloading again.", text_color="green"))
            else:
                self.after(0, lambda: self.progress_text.configure(text="Auto-update failed.", text_color="red"))
            self.after(0, self._reset_buttons)
            return

        def update_ui():
            if result.get("status") == "success":
                self._set_progress(1.0)
                self.progress_text.configure(text="✅  All Tasks Completed Successfully!", text_color="#2ECC71")
                self.status_label.configure(text="●  Download Finished", text_color="#2ECC71")

                title = self.current_video_info.get('title', 'Unknown') if self.current_video_info else 'Unknown'
                media_type = "audio" if is_audio else "video"
                save_path = result.get('save_path', custom_path or config.get(f"default_{media_type}_path"))
                history.add_item(title, media_type, selected_ext, save_path)
            else:
                msg = result.get('message', '')
                if "Cancelled by user" in msg:
                    self._progress_target = 0.0
                    self._progress_current = 0.0
                    self.progress_bar.set(0)
                    self._progress_animating = False
                    self.progress_text.configure(text="Download Cancelled.", text_color="orange")
                    self.status_label.configure(text="●  Cancelled", text_color="orange")
                else:
                    self.progress_text.configure(text="❌  Download Failed!", text_color="red")
                    clean = msg.split('\n')[0]
                    clean = (clean[:65] + '...') if len(clean) > 65 else clean
                    self.status_label.configure(text=f"●  Error: {clean}", text_color="red")
            self._reset_buttons()

        self.after(0, update_ui)


if __name__ == "__main__":
    app = SyntioxDLApp()
    app.mainloop()
