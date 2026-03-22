# Security Policy

## Supported Versions

Currently, only the latest version of **Syntiox DL** receives security updates. We strongly recommend always pulling the latest changes from the `main` branch and keeping your dependencies up to date.

| Version | Supported          |
| ------- | ------------------ |
| Latest (main) | :white_check_mark: |
| Older Versions| :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability within Syntiox DL, please **DO NOT** open a public issue. 

Instead, please report it directly to the maintainer by contacting:
* **Email:** sh4lu.z@gmail.com
* **GitHub:** Reach out privately or via <a href="https://sh4lu-z.vercel.app/">
    <img src="https://img.shields.io/badge/More_details-000000?style=for-the-badge&logo=google-chrome&logoColor=white" alt="More details" />
  </a>

All security vulnerabilities will be promptly addressed, and a patch will be deployed as soon as possible.

## ⚠️ Important Security Guidelines for Users

Because this application interacts with your local system and third-party platforms (YouTube, Instagram, Facebook), please strictly adhere to the following safety practices:

### 1. Browser Cookies Safety
If you use the `'cookiesfrombrowser'` feature to download age-restricted or private videos (e.g., from Instagram or Private Facebook Groups), the script temporarily accesses your active browser session. 
* **Never** share your generated executable (`.exe`) or logs with others if it contains your personal cookie data.
* **Do not** run this script on public or shared computers while logged into your personal social media accounts.

### 2. Trusted FFmpeg Binaries
Syntiox DL requires `ffmpeg` to merge video and audio streams. 
* **ONLY** download `ffmpeg.exe` from official, trusted sources (such as the [BtbN GitHub Releases](https://github.com/BtbN/FFmpeg-Builds/releases) linked in the README). 
* Never place unverified `.exe` files in the project folder, as they can execute malicious code on your machine.

### 3. Keep `yt-dlp` Updated
The core extraction engine, `yt-dlp`, is frequently updated to bypass restrictions and patch vulnerabilities. Always ensure you are running the latest version by executing:
```bash
pip install --upgrade yt-dlp
