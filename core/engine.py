import yt_dlp
import os
import shutil
import glob
import sys
import subprocess
from core.config import config

class SyntioxLogger:
    def debug(self, msg):
        print(f"[YT-DLP LOG] {msg}")

    def warning(self, msg):
        print(f"[WARNING] {msg}")

    def error(self, msg):
        print(f"[ERROR] {msg}")

class SyntioxEngine:
    def __init__(self):
        self._sanitize_path()
        self.is_cancelled = False 
        self.ffmpeg_path = self._find_ffmpeg()

    def _sanitize_path(self):
        # yt-dlp scans PATH for ffmpeg and JS runtimes (like node.js). 
        # On Windows 11, os.path.realpath on certain WindowsApps/Python paths raises WinError 448.
        # We proactively remove these bad paths from the environment PATH.
        if os.name != 'nt': return
        
        original_path = os.environ.get('PATH', '')
        clean_paths = []
        for p in original_path.split(os.pathsep):
            if not p: continue
            try:
                os.path.realpath(p)
                clean_paths.append(p)
            except OSError as e:
                if getattr(e, 'winerror', None) == 448:
                    pass # Ignore this path
                else:
                    clean_paths.append(p)
        os.environ['PATH'] = os.pathsep.join(clean_paths) 
        self.ffmpeg_path = self._find_ffmpeg()

    def _get_startupinfo(self):
        if os.name == 'nt':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            return si
        return None

    def update_ytdlp(self):
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
                startupinfo=self._get_startupinfo(),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            return True
        except Exception:
            return False

    def install_ffmpeg_winget(self):
        try:
            si = self._get_startupinfo()

            subprocess.run(
                ["winget", "--version"], check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=si
            )
            
            subprocess.check_call([
                "winget", "install", "Gyan.FFmpeg", "-e", 
                "--accept-package-agreements", "--accept-source-agreements", "--silent"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=si)
            
            self.ffmpeg_path = self._find_ffmpeg()
            return self.ffmpeg_path is not None
        except Exception:
            return False

    def _find_ffmpeg(self):
        # 1. Check in PATH
        path = shutil.which("ffmpeg")
        if path:
            return os.path.dirname(path)
            
        # 2. Check next to the running executable / script
        app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        local_ffmpeg = os.path.join(app_dir, "ffmpeg.exe")
        if os.path.exists(local_ffmpeg):
            return app_dir
            
        # 3. Check common Windows paths
        common_paths = [
            r"C:\ffmpeg\bin",
            r"C:\Program Files\ffmpeg\bin",
        ]
        
        user_profile = os.environ.get('USERPROFILE', '')
        if user_profile:
            common_paths.append(os.path.join(user_profile, r"scoop\apps\ffmpeg\current\bin"))
            
        for p in common_paths:
            if os.path.exists(os.path.join(p, "ffmpeg.exe")):
                return p
                
        # 4. Check Winget packages
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        if local_app_data:
            winget_path = os.path.join(local_app_data, r"Microsoft\WinGet\Packages")
            if os.path.exists(winget_path):
                search_pattern = os.path.join(winget_path, "*FFmpeg*", "**", "bin", "ffmpeg.exe")
                matches = glob.glob(search_pattern, recursive=True)
                if matches:
                    return os.path.dirname(matches[0])
                    
        return None

    def check_ffmpeg(self):
        return self.ffmpeg_path is not None

    def cancel(self):
        self.is_cancelled = True

    def get_info(self, url):
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'extractor_args': {'youtube': ['player_client=android,web']},
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
        }
        
        if self.ffmpeg_path:
            ydl_opts['ffmpeg_location'] = self.ffmpeg_path
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' in info:
                    videos = []
                    for entry in info['entries']:
                        if entry and entry.get('url'): 
                            videos.append({
                                'title': entry.get('title', 'Unknown'), 
                                'url': entry.get('url')
                            })
                    return {
                        'type': 'playlist', 
                        'title': info.get('title', 'Unknown Playlist'), 
                        'count': len(videos), 
                        'videos': videos
                    }
                else:
                    formats = self._extract_formats(info)
                    audio_formats = self._extract_audio_formats(info)
                    return {
                        'type': 'video',
                        'title': info.get('title', 'Unknown'),
                        'thumb': info.get('thumbnail'),
                        'duration': info.get('duration'),
                        'uploader': info.get('uploader'),
                        'formats': formats,
                        'audio_formats': audio_formats
                    }
        except Exception as e:
            import traceback
            error_log_path = os.path.join(os.path.expanduser('~'), 'syntiox_error.log')
            with open(error_log_path, 'w') as f:
                f.write(traceback.format_exc())
            return {"type": "error", "message": f"{str(e)} (See {error_log_path})"}

    def _extract_formats(self, info):
        formats_dict = {}
        for f in info.get('formats', []):
            vcodec = f.get('vcodec', '')
            ext = f.get('ext', '')
            height = f.get('height')
            format_id = f.get('format_id')
            
            if vcodec and vcodec != 'none' and height:
                res = f"{height}p"
                score = 0
                if 'avc' in vcodec: score += 10 
                if ext == 'mp4': score += 5      
                
                if res not in formats_dict or score > formats_dict[res]['score']:
                    formats_dict[res] = {
                        'id': format_id,
                        'res': res,
                        'ext': ext,
                        'score': score
                    }
                    
        sorted_formats = sorted(formats_dict.values(), key=lambda x: int(x['res'].replace('p','')), reverse=True)
        return [{'id': f['id'], 'res': f['res'], 'ext': f['ext']} for f in sorted_formats]

    def _extract_audio_formats(self, info):
        """Extract real audio-only streams from the server (actual bitrates)."""
        seen = {}
        for f in info.get('formats', []):
            vcodec = f.get('vcodec', '')
            acodec = f.get('acodec', '')
            abr = f.get('abr')
            format_id = f.get('format_id')
            ext = f.get('ext', '')

            # Audio-only streams with a known bitrate
            is_audio_only = (not vcodec or vcodec == 'none') and acodec and acodec != 'none'
            if not is_audio_only or not abr:
                continue

            abr_int = int(round(abr))
            # Prefer m4a over webm for the same bitrate (better compatibility)
            score = 10 if ext == 'm4a' else 0

            if abr_int not in seen or score > seen[abr_int]['score']:
                seen[abr_int] = {
                    'id': format_id,
                    'abr': abr_int,
                    'ext': ext,
                    'label': f"{abr_int} kbps ({ext.upper()})",
                    'score': score
                }

        sorted_audio = sorted(seen.values(), key=lambda x: x['abr'], reverse=True)
        return [{'id': f['id'], 'abr': f['abr'], 'ext': f['ext'], 'label': f['label']} for f in sorted_audio]

    def download(self, url, format_id='best', is_audio=False, progress_hook=None, custom_path=None, audio_quality='320', audio_format='mp3', video_format='mp4'):
        if self.is_cancelled:
            return {"status": "error", "message": "Cancelled"}
            
        if is_audio:
            resolution_tag = f"_[{audio_quality}kbps]"
        else:
            resolution_tag = "_[Best]"
        
        if custom_path:
            save_path = custom_path
        else:
            if is_audio:
                save_path = config.get("default_audio_path", os.path.join(os.path.expanduser('~'), 'Music', 'Syntiox DL'))
            else:
                save_path = config.get("default_video_path", os.path.join(os.path.expanduser('~'), 'Videos', 'Syntiox DL'))
                
        os.makedirs(save_path, exist_ok=True)

        def wrapped_hook(d):
            if self.is_cancelled:
                raise Exception("Cancelled by user")
            progress_hook(d)

        ydl_opts = {
            'outtmpl': os.path.join(save_path, f'%(title)s{resolution_tag}.%(ext)s'),
            'progress_hooks': [wrapped_hook],
            'live_from_start': True,
            'quiet': False,       
            'verbose': True,      
            'logger': SyntioxLogger(), 
            'nocheckcertificate': True,
            'source_address': '0.0.0.0', 
            'extractor_args': {'youtube': ['player_client=android,web']},
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            },
            'retries': 15,              
            'fragment_retries': 15,     
            'continuedl': True,         
        }
        
        if self.ffmpeg_path:
            ydl_opts['ffmpeg_location'] = self.ffmpeg_path

        if is_audio:
            # Use the specific server audio format_id if user picked one, else fallback to bestaudio
            if format_id and format_id != 'best':
                audio_fmt_str = f"{format_id}/bestaudio[ext=m4a]/bestaudio/best"
            else:
                audio_fmt_str = 'bestaudio[ext=m4a]/bestaudio/best'
            ydl_opts.update({
                'format': audio_fmt_str,
                'writethumbnail': True,
                'postprocessors': [
                    {
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': audio_format,
                        'preferredquality': audio_quality, 
                    },
                    {
                        'key': 'EmbedThumbnail',
                    }
                ],
            })
        else:
            if format_id == 'best':
                ydl_opts['format'] = 'bestvideo[vcodec^=avc]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:
                ydl_opts['format'] = f"{format_id}+bestaudio[ext=m4a]/{format_id}+bestaudio/best"
            
            ydl_opts['merge_output_format'] = video_format

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return {"status": "success", "message": "Download complete", "save_path": save_path}
        except Exception as e:
            return {"status": "error", "message": str(e)}