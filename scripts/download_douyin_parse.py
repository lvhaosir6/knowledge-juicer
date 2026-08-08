#!/usr/bin/env python3
"""
Download Douyin video by parsing the public video page.
Uses requests only - no browser automation needed.
"""

import argparse
import re
import sys
import json
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

def download_video(share_url: str, output_dir: Path) -> bool:
    output_dir.mkdir(exist_ok=True)
    
    session = requests.Session()
    
    # Step 1: Follow redirect to get final URL
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    resp = session.get(share_url, headers=headers, allow_redirects=True, timeout=30)
    final_url = resp.url
    print(f"Final URL: {final_url}")
    
    video_id_match = re.search(r'/video/(\d+)', final_url)
    if not video_id_match:
        print("Could not extract video ID")
        return False
    
    video_id = video_id_match.group(1)
    print(f"Video ID: {video_id}")
    
    html = resp.text
    
    # Try to find video URL patterns in the page
    # Pattern 1: JSON data in script tags
    script_patterns = [
        r'<script[^>]*id="RENDER_DATA"[^>]*>({.*?})</script>',
        r'<script[^>]*>window\.__INITIAL_STATE__\s*=\s*({.*?});</script>',
        r'<script[^>]*>window\._SSR_HYDRATED_DATA\s*=\s*({.*?});</script>',
    ]
    
    for pattern in script_patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            print(f"Found script data with pattern: {pattern[:40]}")
            try:
                raw = match.group(1)
                # URL decode if needed
                if '%' in raw:
                    raw = unquote(raw)
                data = json.loads(raw)
                
                # Navigate JSON to find video URL
                def find_video_url(obj, depth=0):
                    if depth > 10:
                        return None
                    if isinstance(obj, dict):
                        for key, val in obj.items():
                            if key in ('playAddr', 'play_url', 'download_addr', 'src'):
                                if isinstance(val, str) and ('douyinvod' in val or 'douyin' in val):
                                    return val
                            if isinstance(val, dict):
                                for k2, v2 in val.items():
                                    if k2 in ('url_list',):
                                        if isinstance(v2, list) and v2:
                                            return v2[0]
                                result = find_video_url(val, depth + 1)
                                if result:
                                    return result
                            if isinstance(val, list):
                                for item in val:
                                    result = find_video_url(item, depth + 1)
                                    if result:
                                        return result
                    return None
                
                video_url = find_video_url(data)
                if video_url:
                    print(f"Found video URL from JSON: {video_url[:80]}...")
                    return download_from_url(video_url, output_dir, session)
            except Exception as e:
                print(f"JSON parse error: {e}")
    
    # Pattern 2: Direct video URL in HTML
    video_patterns = [
        r'(https?://[^"\']+douyinvod[^"\']+\.mp4[^"\']*)',
        r'(https?://[^"\']+douyin[^"\']+video[^"\']+)',
        r'"play_addr"[^}]*"url_list"\s*:\s*\["([^"]+)"',
        r'<video[^>]+src="([^"]+)"',
    ]
    
    for pattern in video_patterns:
        matches = re.findall(pattern, html)
        for m in matches:
            url = m.replace('\\u002F', '/').replace('\\/', '/')
            if 'douyinvod' in url or url.endswith('.mp4'):
                print(f"Found video URL from HTML: {url[:80]}...")
                return download_from_url(url, output_dir, session)
    
    print("Could not find video URL in page")
    return False

def download_from_url(video_url: str, output_dir: Path, session: requests.Session) -> bool:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.douyin.com/',
    }
    
    resp = session.get(video_url, headers=headers, stream=True, timeout=60)
    if resp.status_code != 200:
        print(f"Download failed: HTTP {resp.status_code}")
        return False
    
    output_path = output_dir / "video.mp4"
    with open(output_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    
    size = output_path.stat().st_size
    print(f"Downloaded: {output_path} ({size} bytes)")
    return size > 100000

def main():
    parser = argparse.ArgumentParser(description="Download Douyin video by parsing the public video page.")
    parser.add_argument("url", help="Douyin share URL")
    parser.add_argument("-o", "--output", default=None, help="Output directory (default: output/YYYYMMDD_HHmmss)")
    args = parser.parse_args()
    
    if args.output is None:
        args.output = f"output/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir = Path(args.output)
    
    print(f"Downloading: {args.url}")
    if download_video(args.url, output_dir):
        print("Success!")
    else:
        print("Failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
