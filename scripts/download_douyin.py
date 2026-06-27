#!/usr/bin/env python3
"""
Download Douyin video using requests and yt-dlp with cookies.
"""

import requests
import json
import re
import subprocess
import sys
from pathlib import Path

def get_video_url(url: str) -> str:
    """Extract video URL from Douyin share link."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # Follow redirects
    session = requests.Session()
    response = session.get(url, headers=headers, allow_redirects=True)
    final_url = response.url
    
    print(f"Final URL: {final_url}")
    
    # Extract video ID from URL
    video_id_match = re.search(r'/video/(\d+)', final_url)
    if not video_id_match:
        print("Could not extract video ID")
        return None
    
    video_id = video_id_match.group(1)
    print(f"Video ID: {video_id}")
    
    # Try to get video info from API
    api_url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={video_id}"
    
    api_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.douyin.com/',
        'Accept': 'application/json',
    }
    
    try:
        api_response = session.get(api_url, headers=api_headers)
        if api_response.status_code == 200:
            data = api_response.json()
            if 'aweme_detail' in data:
                video_url = data['aweme_detail'].get('video', {}).get('play_addr', {}).get('url_list', [None])[0]
                if video_url:
                    return video_url
    except Exception as e:
        print(f"API request failed: {e}")
    
    return None

def download_with_ytdlp(url: str, output_path: str) -> bool:
    """Download using yt-dlp with cookies from browser."""
    cmd = [
        "yt-dlp",
        "-o", output_path,
        "--cookies-from-browser", "chrome",
        url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True
        else:
            print(f"yt-dlp error: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error running yt-dlp: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python download_douyin.py <douyin_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    output_dir = Path("douyin_output")
    output_dir.mkdir(exist_ok=True)
    
    print(f"Downloading: {url}")
    
    # Try to get direct video URL
    video_url = get_video_url(url)
    if video_url:
        print(f"Found video URL: {video_url}")
        # Download with requests
        try:
            response = requests.get(video_url, stream=True)
            if response.status_code == 200:
                output_file = output_dir / "video.mp4"
                with open(output_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Downloaded to: {output_file}")
                return
        except Exception as e:
            print(f"Direct download failed: {e}")
    
    # Fallback to yt-dlp
    print("Trying yt-dlp with browser cookies...")
    output_template = str(output_dir / "video.mp4")
    if download_with_ytdlp(url, output_template):
        print("Download successful")
    else:
        print("Download failed. Please ensure you are logged into Douyin in your browser.")

if __name__ == "__main__":
    main()
