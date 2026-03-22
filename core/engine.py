import yt_dlp
import os
import shutil

class SyntioxLogger:
    def debug(self, msg):
        print(f"[YT-DLP LOG] {msg}")

    def warning(self, msg):
        print(f"[WARNING] {msg}")

    def error(self, msg):
        print(f"[ERROR] {msg}")

class SyntioxEngine:
    def __init__(self):
        self.download_folder = "downloads"
        self.is_cancelled = False 
        
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)

    def check_ffmpeg(self):
        return shutil.which("ffmpeg") is not None or os.path.exists("ffmpeg.exe")

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
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' in info:
                    videos = []
                    for entry in info['entries']:
                        if entry.get('url'): 
                            videos.append({
                                'title': entry.get('title'), 
                                'url': entry.get('url')
                            })
                    return {
                        'type': 'playlist', 
                        'title': info.get('title'), 
                        'count': len(videos), 
                        'videos': videos
                    }
                else:
                    formats = self._extract_formats(info)
                    return {
                        'type': 'video', 
                        'title': info.get('title'), 
                        'thumb': info.get('thumbnail'), 
                        'duration': info.get('duration'),
                        'uploader': info.get('uploader'),
                        'formats': formats
                    }
        except Exception as e:
            return {"type": "error", "message": str(e)}

    def _extract_formats(self, info):
   
        formats_dict = {}
        for f in info.get('formats', []):
            vcodec = f.get('vcodec', '')
            ext = f.get('ext', '')
            height = f.get('height')
            format_id = f.get('format_id')
            
            if vcodec != 'none' and height:
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

    def download(self, url, format_id, is_audio, progress_hook):
        self.is_cancelled = False
        
  
        
        resolution_tag = "" if is_audio else f"_[{format_id}p]" if format_id != 'best' else "_[Best]"

        ydl_opts = {
            'outtmpl': f'{self.download_folder}/%(title)s{resolution_tag}.%(ext)s',
            'progress_hooks': [progress_hook],
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

        if is_audio:
            ydl_opts.update({
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192', 
                }],
            })
        else:
            if format_id == 'best':
          
                ydl_opts['format'] = 'bestvideo[vcodec^=avc]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:
         
                ydl_opts['format'] = f"{format_id}+bestaudio[ext=m4a]/{format_id}+bestaudio/best"
            
            ydl_opts['merge_output_format'] = 'mp4'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)
                filesize_bytes = info_dict.get('filesize') or info_dict.get('filesize_approx') or 0
                if filesize_bytes > 0:
                    filesize_mb = filesize_bytes / (1024 * 1024)
                 

                ydl.download([url])
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}