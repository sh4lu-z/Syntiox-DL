import json
import os

class ConfigManager:
    def __init__(self):
        self.config_dir = os.path.join(os.path.expanduser('~'), '.sh4lu-z', 'syntiox dl')
        self.config_path = os.path.join(self.config_dir, 'config.json')
        self.config = {
            "theme": "Dark",
            "default_video_path": os.path.join(os.path.expanduser('~'), 'Videos', 'Syntiox DL'),
            "default_audio_path": os.path.join(os.path.expanduser('~'), 'Music', 'Syntiox DL')
        }
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.config.update(loaded)
            except Exception:
                pass
        else:
            self.save_config()

    def save_config(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            return None
        except Exception as e:
            return f"Failed to save settings: {str(e)}"

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        return self.save_config()

# Global singleton instance
config = ConfigManager()
