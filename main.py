import customtkinter as ctk
import threading
import requests
import re
import os
import sys
import json
from PIL import Image
from io import BytesIO
from core.engine import SyntioxEngine

# Setup_Global_App_Theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Pre-compiled ANSI escape regex
ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

APP_NAME = "Syntiox DL"
APP_VERSION = "1.0.0"

def get_app_data_dir():
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    path = os.path.join(appdata, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path

def get_asset_path(filename):
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'assets', filename)

def load_settings():
    settings_file = os.path.join(get_app_data_dir(), 'settings.json')
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_settings(settings):
    settings_file = os.path.join(get_app_data_dir(), 'settings.json')
    try:
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass

LICENSE_TEXT = """MIT License

Copyright (c) 2026 shaluka gimhan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""


class FirstRunDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Welcome to Syntiox DL")
        self.geometry("550x480")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.result = {"accepted": False, "desktop_shortcut": False, "start_menu": False}
        
        # Set icon
        icon_path = get_asset_path('icon.ico')
        if os.path.exists(icon_path):
            self.after(200, lambda: self.iconbitmap(icon_path))
        
        # Title
        ctk.CTkLabel(self, text="Welcome to Syntiox DL!", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(20, 5))
        ctk.CTkLabel(self, text=f"Version {APP_VERSION}", text_color="gray60").pack(pady=(0, 15))
        
        # License
        ctk.CTkLabel(self, text="License Agreement (MIT)", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=25)
        
        self.license_box = ctk.CTkTextbox(self, width=490, height=200, font=ctk.CTkFont(size=11))
        self.license_box.pack(padx=25, pady=(5, 15))
        self.license_box.insert("1.0", LICENSE_TEXT)
        self.license_box.configure(state="disabled")
        
        # Options
        self.desktop_var = ctk.BooleanVar(value=True)
        self.startmenu_var = ctk.BooleanVar(value=True)
        
        ctk.CTkCheckBox(self, text="Create Desktop Shortcut", variable=self.desktop_var).pack(anchor="w", padx=30, pady=3)
        ctk.CTkCheckBox(self, text="Add to Start Menu (enables Windows Search)", variable=self.startmenu_var).pack(anchor="w", padx=30, pady=3)
        
        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(btn_frame, text="I Agree & Continue", width=200, height=40, font=ctk.CTkFont(size=14, weight="bold"), command=self.accept).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Decline & Exit", width=140, height=40, fg_color="gray30", hover_color="gray40", command=self.decline).pack(side="left")
        
        self.protocol("WM_DELETE_WINDOW", self.decline)
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def accept(self):
        self.result = {
            "accepted": True,
            "desktop_shortcut": self.desktop_var.get(),
            "start_menu": self.startmenu_var.get()
        }
        self.destroy()
    
    def decline(self):
        self.result = {"accepted": False, "desktop_shortcut": False, "start_menu": False}
        self.destroy()


def create_shortcut(target_path, shortcut_path, icon_path=None):
    try:
        import subprocess
        ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target_path}"
$Shortcut.WorkingDirectory = "{os.path.dirname(target_path)}"
'''
        if icon_path and os.path.exists(icon_path):
            ps_script += f'$Shortcut.IconLocation = "{icon_path}"\n'
        ps_script += '$Shortcut.Save()'
        
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            startupinfo=startupinfo
        )
        return True
    except Exception:
        return False


def setup_shortcuts(desktop=True, start_menu=True):
    if getattr(sys, 'frozen', False):
        exe_path = sys.executable
    else:
        exe_path = os.path.abspath(sys.argv[0])
    
    icon_path = get_asset_path('icon.ico')
    
    if desktop:
        desktop_dir = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
        shortcut_path = os.path.join(desktop_dir, f'{APP_NAME}.lnk')
        create_shortcut(exe_path, shortcut_path, icon_path)
    
    if start_menu:
        start_menu_dir = os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs')
        os.makedirs(start_menu_dir, exist_ok=True)
        shortcut_path = os.path.join(start_menu_dir, f'{APP_NAME}.lnk')
        create_shortcut(exe_path, shortcut_path, icon_path)


class SyntioxDLApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Main_Window_Config
        self.title("Syntiox DL - Pro Downloader")
        self.geometry("850x650")
        self.resizable(False, False)
        
        # Set window icon
        icon_ico = get_asset_path('icon.ico')
        icon_png = get_asset_path('icon.png')
        
        if os.path.exists(icon_ico):
            self.after(200, lambda: self.iconbitmap(icon_ico))
        
        if os.path.exists(icon_png):
            try:
                self._icon_img = Image.open(icon_png)
                self.iconphoto(False, ctk.CTkImage(light_image=self._icon_img, dark_image=self._icon_img, size=(32, 32))._light_image)
            except Exception:
                pass
        
        # Init_Backend_Engine
        self.engine = SyntioxEngine()
        self.current_video_info = None
        self._download_thread = None
        
        self.setup_ui()
        self.check_system_requirements()
        
        # First run check
        self.after(300, self.check_first_run)

    def check_first_run(self):
        settings = load_settings()
        if not settings.get('license_accepted'):
            dialog = FirstRunDialog(self)
            self.wait_window(dialog)
            
            if not dialog.result['accepted']:
                self.destroy()
                return
            
            settings['license_accepted'] = True
            settings['version'] = APP_VERSION
            save_settings(settings)
            
            # Create shortcuts in background
            if dialog.result['desktop_shortcut'] or dialog.result['start_menu']:
                threading.Thread(
                    target=setup_shortcuts,
                    args=(dialog.result['desktop_shortcut'], dialog.result['start_menu']),
                    daemon=True
                ).start()

    def setup_ui(self):
        # Header_Section
        self.header_label = ctk.CTkLabel(self, text="SYNTIOX DL", font=ctk.CTkFont(size=28, weight="bold"))
        self.header_label.pack(pady=(20, 10))
        
        # Input_Section
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(pady=10, padx=20, fill="x")
        
        self.url_entry = ctk.CTkEntry(self.input_frame, placeholder_text="Enter YouTube or Playlist URL here...", width=600, height=40)
        self.url_entry.pack(side="left", padx=(0, 10))
        
        self.analyze_btn = ctk.CTkButton(self.input_frame, text="Analyze", width=120, height=40, command=self.start_analyze)
        self.analyze_btn.pack(side="left")
        
        # Info_Display_Section
        self.info_frame = ctk.CTkFrame(self, height=200)
        self.info_frame.pack(pady=15, padx=20, fill="x")
        self.info_frame.pack_propagate(False)

        self.thumb_label = ctk.CTkLabel(self.info_frame, text="No Video Loaded", width=250, height=140, fg_color="gray20")
        self.thumb_label.pack(side="left", padx=20, pady=20)
        
        self.details_frame = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        self.details_frame.pack(side="left", padx=10, pady=20, fill="both", expand=True)
        
        self.title_label = ctk.CTkLabel(self.details_frame, text="Title: N/A", font=ctk.CTkFont(size=16, weight="bold"), wraplength=450, justify="left")
        self.title_label.pack(anchor="w", pady=(0, 5))
        
        self.status_label = ctk.CTkLabel(self.details_frame, text="Type: N/A | Status: Waiting", text_color="gray60")
        self.status_label.pack(anchor="w")
        
        # Options_Section
        self.options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.options_frame.pack(pady=10, padx=20, fill="x")
        
        self.format_var = ctk.StringVar(value="best")
        self.quality_dropdown = ctk.CTkOptionMenu(self.options_frame, variable=self.format_var, values=["Wait for analyze..."], width=200)
        self.quality_dropdown.pack(side="left", padx=(0, 20))
        
        self.audio_only_var = ctk.BooleanVar(value=False)
        self.audio_checkbox = ctk.CTkCheckBox(self.options_frame, text="Audio Only (MP3)", variable=self.audio_only_var, command=self.toggle_audio_mode)
        self.audio_checkbox.pack(side="left")
        
        # Path_Section
        self.path_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.path_frame.pack(pady=5, padx=20, fill="x")
        
        self.path_var = ctk.StringVar(value="")
        self.path_entry = ctk.CTkEntry(self.path_frame, textvariable=self.path_var, placeholder_text="Default Download Folder...", width=500)
        self.path_entry.pack(side="left", padx=(0, 10))
        
        self.browse_btn = ctk.CTkButton(self.path_frame, text="Browse", width=80, command=self.browse_folder)
        self.browse_btn.pack(side="left")
        
        # Progress_Section
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(pady=10, padx=20, fill="x")
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=810)
        self.progress_bar.pack(pady=(0, 10))
        self.progress_bar.set(0)
        
        self.progress_text = ctk.CTkLabel(self.progress_frame, text="0% | 0.0 MiB/s | ETA: 00:00", text_color="gray60")
        self.progress_text.pack()
        
        # Download_Button
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=20)

        self.download_btn = ctk.CTkButton(self.btn_frame, text="START DOWNLOAD", width=250, height=50, font=ctk.CTkFont(size=16, weight="bold"), state="disabled", command=self.start_download)
        self.download_btn.pack(side="left", padx=10)

        self.cancel_btn = ctk.CTkButton(self.btn_frame, text="CANCEL", width=120, height=50, font=ctk.CTkFont(size=16, weight="bold"), fg_color="red", hover_color="darkred", state="disabled", command=self.cancel_download)
        self.cancel_btn.pack(side="left")

    def check_system_requirements(self):
        if not self.engine.check_ffmpeg():
            self.status_label.configure(text="FFmpeg not found. Will auto-install on first use.", text_color="yellow")

    def browse_folder(self):
        folder = ctk.filedialog.askdirectory(title="Select Download Folder")
        if folder:
            self.path_var.set(folder)

    def cancel_download(self):
        self.engine.cancel()
        self.progress_text.configure(text="Cancelling... Please wait.", text_color="yellow")
        self.cancel_btn.configure(state="disabled")

    def load_thumbnail(self, url):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            img_data = Image.open(BytesIO(response.content))
            img_data.thumbnail((250, 140))
            ctk_img = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(250, 140))
            self.after(0, lambda: self.thumb_label.configure(image=ctk_img, text=""))
            self._thumb_ref = ctk_img
        except Exception:
            pass

    def start_analyze(self):
        url = self.url_entry.get().strip()
        if not url:
            return
            
        self.analyze_btn.configure(state="disabled")
        self.status_label.configure(text="Status: Analyzing link... Please wait.", text_color="yellow")
        
        thread = threading.Thread(target=self.process_analysis, args=(url,), daemon=True)
        thread.start()

    def process_analysis(self, url):
        # Auto-install ffmpeg if missing
        if not self.engine.check_ffmpeg():
            self.after(0, lambda: self.status_label.configure(text="Status: FFmpeg not found. Auto-installing... (May take a minute)", text_color="yellow"))
            success = self.engine.install_ffmpeg_winget()
            if not success:
                self.after(0, lambda: self.status_label.configure(text="Status: FFmpeg install failed. Please install manually.", text_color="red"))
                self.after(0, lambda: self.analyze_btn.configure(state="normal"))
                return
            else:
                self.after(0, lambda: self.status_label.configure(text="Status: FFmpeg installed! Analyzing...", text_color="green"))

        info = self.engine.get_info(url)
        self.current_video_info = info
        
        # Auto-update yt-dlp on 403
        if info.get('type') == 'error' and '403' in info.get('message', ''):
            self.after(0, lambda: self.status_label.configure(text="Status: 403 Error. Auto-updating yt-dlp...", text_color="yellow"))
            if self.engine.update_ytdlp():
                self.after(0, lambda: self.status_label.configure(text="Status: Update Success! Please click Analyze again.", text_color="green"))
            else:
                self.after(0, lambda: self.status_label.configure(text="Status: Auto-update failed.", text_color="red"))
            self.after(0, lambda: self.analyze_btn.configure(state="normal"))
            return
        
        def update_ui():
            if info.get('type') == 'error':
                msg = info.get('message', 'Unknown error')
                clean_msg = msg.split('\n')[0]
                clean_msg = (clean_msg[:80] + '...') if len(clean_msg) > 80 else clean_msg
                self.status_label.configure(text=f"Error: {clean_msg}", text_color="red")
                self.analyze_btn.configure(state="normal")
                return

            self.title_label.configure(text=f"Title: {info.get('title', 'Unknown')}")
            
            if info.get('type') == 'video':
                self.status_label.configure(text="Type: Single Video | Status: Ready", text_color="green")
                if info.get('thumb'):
                    threading.Thread(target=self.load_thumbnail, args=(info['thumb'],), daemon=True).start()
                
                formats = info.get('formats', [])
                dropdown_values = ["Best Quality"] + [f['res'] for f in formats]
                self.quality_dropdown.configure(values=dropdown_values)
                self.quality_dropdown.set("Best Quality")
                
            elif info.get('type') == 'playlist':
                count = info.get('count', 0)
                self.status_label.configure(text=f"Type: Playlist ({count} videos) | Status: Ready", text_color="green")
                self.quality_dropdown.configure(values=["Best Quality"])
                self.quality_dropdown.set("Best Quality")
                
            self.analyze_btn.configure(state="normal")
            self.download_btn.configure(state="normal")
            
        self.after(0, update_ui)

    def toggle_audio_mode(self):
        if self.audio_only_var.get():
            self.quality_dropdown.configure(state="normal", values=["Best Quality", "320kbps", "256kbps", "192kbps", "128kbps"])
            self.format_var.set("Best Quality")
        else:
            self.quality_dropdown.configure(state="normal")
            if self.current_video_info and self.current_video_info.get('type') == 'video':
                formats = self.current_video_info.get('formats', [])
                dropdown_values = ["Best Quality"] + [f['res'] for f in formats]
                self.quality_dropdown.configure(values=dropdown_values)
            else:
                self.quality_dropdown.configure(values=["Best Quality"])
            self.format_var.set("Best Quality")

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                percent_str = d.get('_percent_str', '0%').strip()
                speed_str = d.get('_speed_str', 'N/A').strip()
                eta_str = d.get('_eta_str', 'N/A').strip()
                
                percent_clean = ANSI_ESCAPE_RE.sub('', percent_str).strip()
                speed_clean = ANSI_ESCAPE_RE.sub('', speed_str).strip()
                eta_clean = ANSI_ESCAPE_RE.sub('', eta_str).strip()
                
                try:
                    percent_float = float(percent_clean.replace('%', '')) / 100.0
                except ValueError:
                    percent_float = None
                
                _pf = percent_float
                _text = f"{percent_clean} | Speed: {speed_clean} | ETA: {eta_clean}"
                
                if _pf is not None:
                    self.after(0, lambda: self.progress_bar.set(_pf))
                self.after(0, lambda: self.progress_text.configure(text=_text))
            except Exception:
                pass
                
        elif d['status'] == 'finished':
            self.after(0, lambda: self.progress_text.configure(text="Download Complete! Merging files...", text_color="yellow"))

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            return
            
        is_audio = self.audio_only_var.get()
        selected_res = self.format_var.get()
        custom_path = self.path_var.get().strip() or None
        
        format_id = 'best'
        audio_quality = '320'
        
        if is_audio:
            if selected_res != "Best Quality":
                audio_quality = selected_res.replace("kbps", "")
        else:
            if selected_res != "Best Quality" and self.current_video_info:
                for f in self.current_video_info.get('formats', []):
                    if f['res'] == selected_res:
                        format_id = f['id']
                        break
                    
        self.download_btn.configure(state="disabled")
        self.analyze_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.progress_text.configure(text="Starting download...", text_color="gray60")
        
        self._download_thread = threading.Thread(target=self.process_download, args=(url, format_id, is_audio, custom_path, audio_quality), daemon=True)
        self._download_thread.start()

    def process_download(self, url, format_id, is_audio, custom_path, audio_quality):
        result = self.engine.download(url, format_id, is_audio, self.progress_hook, custom_path=custom_path, audio_quality=audio_quality)
        
        # Auto-update yt-dlp on 403 errors
        if result.get("status") != "success" and "403" in result.get('message', ''):
            self.after(0, lambda: self.progress_text.configure(text="403 Error. Auto-updating yt-dlp...", text_color="yellow"))
            if self.engine.update_ytdlp():
                self.after(0, lambda: self.progress_text.configure(text="Update Success! Please try downloading again.", text_color="green"))
            else:
                self.after(0, lambda: self.progress_text.configure(text="Auto-update failed.", text_color="red"))
            self.after(0, lambda: self._reset_buttons())
            return

        def update_ui():
            if result.get("status") == "success":
                self.progress_text.configure(text="All Tasks Completed Successfully!", text_color="green")
                self.status_label.configure(text="Status: Download Finished", text_color="green")
                self.progress_bar.set(1.0)
            else:
                msg = result.get('message', '')
                if "Cancelled by user" in msg:
                    self.progress_text.configure(text="Download Cancelled!", text_color="orange")
                    self.status_label.configure(text="Status: Cancelled", text_color="orange")
                    self.progress_bar.set(0)
                else:
                    self.progress_text.configure(text="Download Failed!", text_color="red")
                    clean_msg = msg.split('\n')[0]
                    clean_msg = (clean_msg[:60] + '...') if len(clean_msg) > 60 else clean_msg
                    self.status_label.configure(text=f"Error: {clean_msg}", text_color="red")
                
            self._reset_buttons()

        self.after(0, update_ui)

    def _reset_buttons(self):
        self.download_btn.configure(state="normal")
        self.analyze_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")

if __name__ == "__main__":
    app = SyntioxDLApp()
    app.mainloop()
