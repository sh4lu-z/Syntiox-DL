import customtkinter as ctk
import threading
import requests
from PIL import Image
from io import BytesIO
from core.engine import SyntioxEngine

# Setup_Global_App_Theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SyntioxDLApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Main_Window_Config
        self.title("Syntiox DL - Pro Downloader")
        self.geometry("850x650")
        self.resizable(False, False)
        
        # Init_Backend_Engine
        self.engine = SyntioxEngine()
        self.current_video_info = None
        
        self.setup_ui()
        self.check_system_requirements()

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
        self.info_frame.pack_propagate(False) # Keep_Fixed_Size
        
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
        
        # Progress_Section
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(pady=10, padx=20, fill="x")
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=810)
        self.progress_bar.pack(pady=(0, 10))
        self.progress_bar.set(0)
        
        self.progress_text = ctk.CTkLabel(self.progress_frame, text="0% | 0.0 MiB/s | ETA: 00:00", text_color="gray60")
        self.progress_text.pack()
        
        # Download_Button
        self.download_btn = ctk.CTkButton(self, text="START DOWNLOAD", width=300, height=50, font=ctk.CTkFont(size=16, weight="bold"), state="disabled", command=self.start_download)
        self.download_btn.pack(pady=20)

    def check_system_requirements(self):
        # Validate_FFmpeg
        if not self.engine.check_ffmpeg():
            self.status_label.configure(text="Warning: FFmpeg not found! High quality merges might fail.", text_color="red")

    def load_thumbnail(self, url):
        # Fetch_And_Display_Image_In_Background
        try:
            response = requests.get(url)
            img_data = Image.open(BytesIO(response.content))
            img_data.thumbnail((250, 140)) # Resize_To_Fit
            ctk_img = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(250, 140))
            self.thumb_label.configure(image=ctk_img, text="")
        except Exception:
            pass

    def start_analyze(self):
        # Run_Analysis_In_Separate_Thread
        url = self.url_entry.get().strip()
        if not url:
            return
            
        self.analyze_btn.configure(state="disabled")
        self.status_label.configure(text="Status: Analyzing link... Please wait.", text_color="yellow")
        
        thread = threading.Thread(target=self.process_analysis, args=(url,))
        thread.start()

    def process_analysis(self, url):
        # Engine_Call_For_Info
        info = self.engine.get_info(url)
        self.current_video_info = info
        
        if info.get('type') == 'error':
            self.status_label.configure(text="Status: Error fetching details!", text_color="red")
            self.analyze_btn.configure(state="normal")
            return

        self.title_label.configure(text=f"Title: {info.get('title', 'Unknown')}")
        
        if info.get('type') == 'video':
            self.status_label.configure(text="Type: Single Video | Status: Ready", text_color="green")
            if info.get('thumb'):
                self.load_thumbnail(info['thumb'])
            
            # Populate_Quality_Dropdown
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

    def toggle_audio_mode(self):
        # Disable_Quality_Select_If_Audio_Only
        if self.audio_only_var.get():
            self.quality_dropdown.configure(state="disabled")
        else:
            self.quality_dropdown.configure(state="normal")

    def progress_hook(self, d):
        # Update_UI_During_Download
        if d['status'] == 'downloading':
            try:
                percent_str = d.get('_percent_str', '0%').strip()
                speed_str = d.get('_speed_str', '0 MiB/s').strip()
                eta_str = d.get('_eta_str', '00:00').strip()
                
                # Clean_ANSI_Escape_Codes_From_yt-dlp_output
                percent_clean = ''.join(c for c in percent_str if c.isprintable() and c != '\x1b')
                
                try:
                    percent_float = float(percent_clean.replace('%', '')) / 100.0
                    # self.after පාවිච්චි කරලා Main Thread එකෙන් UI එක Update කිරීම
                    self.after(0, lambda: self.progress_bar.set(percent_float))
                except ValueError:
                    pass
                
                # Text එකත් Main Thread එකෙන් Update කිරීම
                self.after(0, lambda: self.progress_text.configure(text=f"{percent_clean} | Speed: {speed_str} | ETA: {eta_str}"))
            except Exception:
                pass
                
        elif d['status'] == 'finished':
            self.after(0, lambda: self.progress_text.configure(text="Download Complete! Merging files...", text_color="yellow"))

    def start_download(self):
        # Run_Download_In_Separate_Thread
        url = self.url_entry.get().strip()
        is_audio = self.audio_only_var.get()
        selected_res = self.format_var.get()
        
        format_id = 'best'
        if not is_audio and selected_res != "Best Quality" and self.current_video_info:
            # Match_Selected_Resolution_With_Format_ID
            for f in self.current_video_info.get('formats', []):
                if f['res'] == selected_res:
                    format_id = f['id']
                    break
                    
        self.download_btn.configure(state="disabled")
        self.analyze_btn.configure(state="disabled")
        
        thread = threading.Thread(target=self.process_download, args=(url, format_id, is_audio))
        thread.start()

    def process_download(self, url, format_id, is_audio):
        # Engine_Call_For_Download
        result = self.engine.download(url, format_id, is_audio, self.progress_hook)
        
        if result.get("status") == "success":
            self.progress_text.configure(text="All Tasks Completed Successfully!", text_color="green")
            self.status_label.configure(text="Status: Download Finished", text_color="green")
            self.progress_bar.set(1.0)
        else:
            self.progress_text.configure(text="Download Failed!", text_color="red")
            self.status_label.configure(text=f"Error: {result.get('message')}", text_color="red")
            
        self.download_btn.configure(state="normal")
        self.analyze_btn.configure(state="normal")

if __name__ == "__main__":
    app = SyntioxDLApp()
    app.mainloop()