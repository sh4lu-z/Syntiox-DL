import json
import os
from datetime import datetime

class HistoryManager:
    def __init__(self):
        self.history_dir = os.path.join(os.path.expanduser('~'), '.sh4lu-z', 'syntiox dl')
        self.history_path = os.path.join(self.history_dir, 'history.json')
        self.history = []
        self.load_history()

    def load_history(self):
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []
        else:
            self.history = []

    def save_history(self):
        try:
            os.makedirs(self.history_dir, exist_ok=True)
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=4)
        except Exception:
            pass

    def add_item(self, title, media_type, format_ext, path):
        item = {
            "title": title,
            "type": media_type,
            "format": format_ext,
            "path": path,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.history.insert(0, item) # Add to the beginning
        # Keep only the last 50 items to prevent the file from growing too large
        if len(self.history) > 50:
            self.history = self.history[:50]
        self.save_history()

    def get_history(self):
        return self.history

    def clear_history(self):
        self.history = []
        self.save_history()

# Global singleton instance
history = HistoryManager()
