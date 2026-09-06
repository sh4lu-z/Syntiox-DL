import requests
import threading

GITHUB_OWNER = "sh4lu-z"
GITHUB_REPO = "Syntiox-DL"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


def _parse_version(v):
    try:
        return tuple(int(x) for x in v.lstrip("v").split("."))
    except Exception:
        return None


def check_for_updates(current_version, callback, timeout=8):
    """Non-blocking update check via GitHub Releases API. callback(info or None)."""
    def _check():
        try:
            resp = requests.get(
                RELEASES_API,
                timeout=timeout,
                headers={"Accept": "application/vnd.github+json"}
            )
            resp.raise_for_status()
            data = resp.json()

            latest_tag = data.get("tag_name", "")
            latest_ver = _parse_version(latest_tag)
            current_ver = _parse_version(current_version)

            if latest_ver and current_ver and latest_ver > current_ver:
                notes = data.get("body", "No release notes available.").strip()
                if len(notes) > 800:
                    notes = notes[:800] + "\n..."
                callback({
                    "latest_version": latest_tag.lstrip("v"),
                    "current_version": current_version,
                    "release_name": data.get("name", latest_tag),
                    "release_notes": notes,
                    "release_url": data.get("html_url", RELEASES_PAGE),
                    "published_at": data.get("published_at", "")[:10],
                })
            else:
                callback(None)
        except Exception:
            callback(None)  # Silent fail — never crash the app

    threading.Thread(target=_check, daemon=True).start()