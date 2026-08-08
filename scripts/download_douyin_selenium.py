#!/usr/bin/env python3
"""
Download Douyin video using Selenium.
"""

import argparse
import json
import os
import re
import time
import sys
import requests
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def download_douyin_video(url: str, output_dir: Path) -> bool:
    """Download Douyin video using Selenium."""
    print("Setting up Chrome driver...")
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Enable performance logging to capture network requests
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    try:
        # Initialize driver using managed ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Execute CDP commands to prevent detection
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })
        
        print(f"Navigating to: {url}")
        driver.get(url)
        
        # Wait for page to load
        print("Waiting for page to load...")
        time.sleep(10)
        
        # Get the final URL
        final_url = driver.current_url
        print(f"Final URL: {final_url}")
        
        # Extract video ID
        video_id_match = re.search(r'/video/(\d+)', final_url)
        if not video_id_match:
            print("Could not extract video ID")
            driver.quit()
            return False
        
        video_id = video_id_match.group(1)
        print(f"Video ID: {video_id}")
        
        # Try to find video element
        try:
            video_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "video"))
            )
            print("Found video element")
            
            # Get video src
            video_src = video_element.get_attribute('src')
            if video_src:
                print(f"Video source: {video_src[:100]}...")
        except Exception as e:
            print(f"Could not find video element: {e}")
        
        # Get performance logs to find video URL
        print("Analyzing network requests...")
        logs = driver.get_log('performance')
        
        video_urls = []
        for log in logs:
            try:
                message = json.loads(log['message'])['message']
                if message['method'] == 'Network.responseReceived':
                    response_url = message['params']['response']['url']
                    content_type = message['params']['response'].get('mimeType', '')
                    
                    # Check if it's a video URL
                    if ('video' in content_type or 
                        'douyin' in response_url and 'video' in response_url or
                        response_url.endswith('.mp4') or
                        'play' in response_url):
                        video_urls.append(response_url)
            except:
                pass
        
        print(f"Found {len(video_urls)} potential video URLs")
        
        # Also try to extract from page source
        page_source = driver.page_source
        
        # Look for video URLs in page source
        video_url_patterns = [
            r'"playAddr":\s*"([^"]+)"',
            r'"play_addr":\s*\{[^}]*"url_list":\s*\["([^"]+)"',
            r'"download_addr":\s*\{[^}]*"url_list":\s*\["([^"]+)"',
            r'src="(https?://[^"]+\.mp4[^"]*)"',
            r'"video":\s*\{[^}]*"play_addr":\s*\{[^}]*"url_list":\s*\["([^"]+)"',
        ]
        
        for pattern in video_url_patterns:
            matches = re.findall(pattern, page_source)
            if matches:
                video_urls.extend(matches)
        
        # Remove duplicates
        video_urls = list(set(video_urls))
        
        if not video_urls:
            print("Could not find any video URLs")
            # Save page source for debugging
            debug_file = output_dir / "debug_page.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(page_source)
            print(f"Saved page source to: {debug_file}")
            driver.quit()
            return False
        
        # Filter and prioritize video URLs
        # Prefer URLs with higher quality indicators
        # NOTE: only skip clearly-fake placeholders. Real douyinvod.com URLs may
        # contain "default"/"watermark"/"cover" in their path, so don't filter those.
        placeholder_tokens = [
            'uuu_', 'placeholder', 'preview',
            'loading_effect', 'play_effect', 'playing_effect',
        ]
        prioritized_urls = []
        for url in video_urls:
            # Skip non-video URLs
            if not any(ext in url.lower() for ext in ['.mp4', 'video', 'play', 'aweme']):
                continue
            # Skip placeholder / preview / effect videos (e.g. Douyin's uuu_265.mp4 loading clip)
            url_lower = url.lower()
            if any(token in url_lower for token in placeholder_tokens):
                print(f"Skipping placeholder URL: {url[:100]}...")
                continue
            # Skip small preview images
            if 'thumbnail' in url_lower or 'cover' in url_lower or 'image' in url_lower:
                continue
            # Prioritize higher quality URLs
            if 'play' in url_lower or 'download' in url_lower or '1080' in url:
                prioritized_urls.insert(0, url)
            else:
                prioritized_urls.append(url)
        
        video_urls = prioritized_urls if prioritized_urls else video_urls
        print(f"Found {len(video_urls)} video URLs")
        
        # Try to download each video URL
        for i, video_url in enumerate(video_urls):
            print(f"\nTrying URL {i+1}: {video_url[:100]}...")
            
            try:
                # Get cookies from Selenium
                cookies = driver.get_cookies()
                cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                
                # Download with requests
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.douyin.com/',
                    'Accept': '*/*',
                }
                
                response = requests.get(video_url, headers=headers, cookies=cookies_dict, stream=True, timeout=30)
                
                if response.status_code == 200:
                    # Check if it's actually a video
                    content_type = response.headers.get('content-type', '')
                    if 'video' in content_type or 'octet-stream' in content_type:
                        output_file = output_dir / f"video_{i+1}.mp4"
                        with open(output_file, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        file_size = output_file.stat().st_size
                        print(f"Downloaded: {output_file} ({file_size} bytes)")
                        
                        if file_size > 100000:  # More than 100KB
                            # Rename to final name
                            final_file = output_dir / "video.mp4"
                            if final_file.exists():
                                final_file.unlink()
                            output_file.rename(final_file)
                            print(f"Renamed to: {final_file}")
                            driver.quit()
                            return True
                        else:
                            print(f"File too small, trying next URL...")
                            output_file.unlink()
                    else:
                        print(f"Not a video content type: {content_type}")
                else:
                    print(f"HTTP error: {response.status_code}")
                    
            except Exception as e:
                print(f"Download error: {e}")
        
        print("Could not download video from any URL")
        driver.quit()
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Download Douyin video using Selenium.")
    parser.add_argument("url", help="Douyin video URL")
    parser.add_argument("-o", "--output", default=None, help="Output directory (default: output/YYYYMMDD_HHmmss)")
    args = parser.parse_args()
    
    if args.output is None:
        args.output = f"output/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    url = args.url
    print(f"Downloading Douyin video: {url}")
    
    if download_douyin_video(url, output_dir):
        print("\nDownload completed successfully!")
    else:
        print("\nDownload failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
