#!/usr/bin/env python3
"""
Download Douyin video using public API approaches.
"""

import json
import re
import subprocess
import sys
import requests
from pathlib import Path

def download_video(share_url: str, output_dir: Path) -> bool:
    output_dir.mkdir(exist_ok=True)
    
    # Resolve short URL first
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    resp = requests.get(share_url, headers=headers, allow_redirects=True, timeout=30)
    final_url = resp.url
    
    video_id_match = re.search(r'/video/(\d+)', final_url)
    if not video_id_match:
        print("Could not extract video ID")
        return False
    
    video_id = video_id_match.group(1)
    print(f"Video ID: {video_id}")
    
    # Method 1: Try using a public Douyin API endpoint
    api_urls = [
        f"https://www.iesdouyin.com/aweme/v1/web/aweme/detail/?aweme_id={video_id}",
        f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={video_id}",
    ]
    
    for api_url in api_urls:
        try:
            api_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.douyin.com/',
                'Accept': 'application/json',
            }
            resp = requests.get(api_url, headers=api_headers, timeout=15)
            if resp.status_code == 200 and resp.text.strip():
                data = resp.json()
                # Navigate to find video URL
                detail = data.get('aweme_detail', {}) or data.get('data', {})
                video = detail.get('video', {})
                play_addr = video.get('play_addr', {})
                url_list = play_addr.get('url_list', [])
                if url_list:
                    video_url = url_list[0]
                    print(f"Found video URL: {video_url[:80]}...")
                    return download_from_url(video_url, output_dir)
        except Exception as e:
            print(f"API {api_url} failed: {e}")
    
    # Method 2: Try downloading with yt-dlp
    print("Method 2: Trying yt-dlp...")
    try:
        with open('cookies.txt', 'w') as f:
            f.write("# placeholder\n")
        subprocess.run([
            'yt-dlp', '--cookies', 'cookies.txt',
            '-o', str(output_dir / 'video.mp4'),
            share_url
        ], timeout=120, capture_output=True)
        if (output_dir / 'video.mp4').exists() and (output_dir / 'video.mp4').stat().st_size > 100000:
            print("Downloaded with yt-dlp")
            return True
    except Exception as e:
        print(f"yt-dlp failed: {e}")
    
    print("All methods failed")
    return False

def download_from_url(video_url: str, output_dir: Path) -> bool:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.douyin.com/',
    }
    
    resp = requests.get(video_url, headers=headers, stream=True, timeout=60)
    if resp.status_code != 200:
        print(f"HTTP {resp.status_code}")
        return False
    
    output_path = output_dir / "video.mp4"
    with open(output_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    
    size = output_path.stat().st_size
    print(f"Downloaded: {output_path} ({size} bytes)")
    return size > 100000

def main():
    if len(sys.argv) < 2:
        print("Usage: python download_douyin_api.py <share_url> [output_dir]")
        sys.exit(1)
    
    share_url = sys.argv[1]
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("douyin_output")
    
    if download_video(share_url, output_dir):
        print("Success!")
    else:
        print("Failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
