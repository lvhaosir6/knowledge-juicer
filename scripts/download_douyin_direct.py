#!/usr/bin/env python3
"""
Direct Douyin video downloader using requests + cookies.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
import requests

def load_cookies(cookie_file: str) -> dict:
    """Load cookies from Netscape format file."""
    cookies = {}
    with open(cookie_file, 'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.strip().split('\t')
            if len(parts) >= 7:
                cookies[parts[5]] = parts[6]
    return cookies

def get_video_url_from_detail_api(video_id: str, cookies: dict) -> str:
    """Try to get video URL from Douyin detail API."""
    detail_url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={video_id}&device_platform=webapp&aid=6383"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.douyin.com/',
    }
    
    resp = requests.get(detail_url, headers=headers, cookies=cookies, timeout=30)
    if resp.status_code != 200:
        return None
    
    data = resp.json()
    aweme_detail = data.get('aweme_detail', {})
    video = aweme_detail.get('video', {})
    
    # Try play_addr first
    play_addr = video.get('play_addr', {})
    if play_addr.get('url_list'):
        return play_addr['url_list'][0]
    
    # Try download_addr
    download_addr = video.get('download_addr', {})
    if download_addr.get('url_list'):
        return download_addr['url_list'][0]
    
    return None

def get_video_play_api(video_id: str, cookies: dict) -> str:
    """Try Douyin play API."""
    play_url = f"https://www.douyin.com/video/{video_id}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    resp = requests.get(play_url, headers=headers, cookies=cookies, timeout=30)
    
    if resp.status_code != 200:
        return None
    
    # Look for video URLs in the HTML
    patterns = [
        r'playAddr[^,]*"([^"]+)"',
        r'"play_addr"[^}]*"url_list"[^[]*\["([^"]+)"',
        r'"video_id_str"\s*:\s*"(\d+)"',
        r'<video[^>]*src="([^"]+)"',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, resp.text)
        if matches:
            return matches[0]
    
    return None

def download_video(url: str, output_path: Path) -> bool:
    """Download video from URL."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.douyin.com/',
    }
    
    resp = requests.get(url, headers=headers, stream=True, timeout=60)
    if resp.status_code != 200:
        return False
    
    content_type = resp.headers.get('content-type', '')
    if 'video' not in content_type and 'octet-stream' not in content_type and 'mp4' not in content_type.lower():
        return False
    
    with open(output_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return output_path.stat().st_size > 100000

def main():
    parser = argparse.ArgumentParser(description="Direct Douyin video downloader using requests + cookies.")
    parser.add_argument("url", help="Douyin share URL")
    parser.add_argument("-o", "--output", default=None, help="Output directory (default: output/YYYYMMDD_HHmmss)")
    args = parser.parse_args()
    
    if args.output is None:
        args.output = f"output/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    share_url = args.url
    # Resolve share URL
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    resp = requests.get(share_url, headers=headers, allow_redirects=True, timeout=30)
    final_url = resp.url
    
    video_id_match = re.search(r'/video/(\d+)', final_url)
    if not video_id_match:
        print(f"Could not extract video ID from: {final_url}")
        sys.exit(1)
    
    video_id = video_id_match.group(1)
    print(f"Video ID: {video_id}")
    
    # Load cookies
    if not Path("cookies.txt").exists():
        print("No cookies.txt found. Please run get_douyin_cookies.py first.")
        sys.exit(1)
    
    cookies = load_cookies("cookies.txt")
    print(f"Loaded {len(cookies)} cookies")
    
    # Method 1: Try detail API
    print("Trying detail API...")
    video_url = get_video_url_from_detail_api(video_id, cookies)
    if video_url:
        print(f"Found video URL from detail API")
        if download_video(video_url, output_dir / "video.mp4"):
            print(f"Downloaded to: {output_dir / 'video.mp4'}")
            return
    
    # Method 2: Try play page
    print("Trying play API...")
    video_url = get_video_play_api(video_id, cookies)
    if video_url and video_url.startswith('http'):
        print(f"Found video URL from play page")
        if download_video(video_url, output_dir / "video.mp4"):
            print(f"Downloaded to: {output_dir / 'video.mp4'}")
            return
    
    print("All methods failed.")
    sys.exit(1)

if __name__ == "__main__":
    main()
