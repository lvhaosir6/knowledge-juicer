#!/usr/bin/env python3
"""
Download Douyin video using Playwright.
"""

import argparse
import asyncio
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

async def download_douyin_video(url: str, output_dir: Path) -> bool:
    """Download Douyin video using Playwright."""
    print(f"Starting Playwright browser...")
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        try:
            # Navigate to the URL
            print(f"Navigating to: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait for page to load
            await page.wait_for_timeout(3000)
            
            # Get the final URL
            final_url = page.url
            print(f"Final URL: {final_url}")
            
            # Extract video ID
            video_id_match = re.search(r'/video/(\d+)', final_url)
            if not video_id_match:
                print("Could not extract video ID")
                return False
            
            video_id = video_id_match.group(1)
            print(f"Video ID: {video_id}")
            
            # Try to find video element
            video_element = await page.query_selector('video')
            if video_element:
                # Get video src
                video_src = await video_element.get_attribute('src')
                if video_src:
                    print(f"Found video source: {video_src[:100]}...")
                    
                    # Download the video
                    async with page.expect_download() as download_info:
                        # Click on video or trigger download
                        await video_element.click()
                    
                    download = await download_info.value
                    output_file = output_dir / "video.mp4"
                    await download.save_as(str(output_file))
                    print(f"Downloaded to: {output_file}")
                    return True
            
            # If direct download fails, try to get video URL from network requests
            print("Trying to intercept video URL from network...")
            
            # Monitor network requests
            video_urls = []
            
            def handle_response(response):
                if 'video' in response.url and response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'video' in content_type:
                        video_urls.append(response.url)
            
            page.on('response', handle_response)
            
            # Reload page to capture network requests
            await page.reload(wait_until='networkidle')
            await page.wait_for_timeout(5000)
            
            if video_urls:
                print(f"Found {len(video_urls)} video URLs")
                # Use the first video URL
                video_url = video_urls[0]
                print(f"Downloading from: {video_url[:100]}...")
                
                # Download using requests
                import requests
                response = requests.get(video_url, stream=True)
                if response.status_code == 200:
                    output_file = output_dir / "video.mp4"
                    with open(output_file, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"Downloaded to: {output_file}")
                    return True
            
            # Try to extract video URL from page content
            print("Trying to extract video URL from page content...")
            content = await page.content()
            
            # Look for video URLs in the page
            video_url_patterns = [
                r'"playAddr":\s*"([^"]+)"',
                r'"play_addr":\s*"([^"]+)"',
                r'"download_addr":\s*"([^"]+)"',
                r'src="(https?://[^"]+\.mp4[^"]*)"',
            ]
            
            for pattern in video_url_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    video_url = matches[0]
                    print(f"Found video URL: {video_url[:100]}...")
                    
                    # Download using requests
                    import requests
                    response = requests.get(video_url, stream=True)
                    if response.status_code == 200:
                        output_file = output_dir / "video.mp4"
                        with open(output_file, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        print(f"Downloaded to: {output_file}")
                        return True
            
            print("Could not find video URL")
            return False
            
        except Exception as e:
            print(f"Error: {e}")
            return False
        
        finally:
            await browser.close()

def main():
    parser = argparse.ArgumentParser(description="Download Douyin video using Playwright.")
    parser.add_argument("url", help="Douyin video URL")
    parser.add_argument("-o", "--output", default=None, help="Output directory (default: output/YYYYMMDD_HHmmss)")
    args = parser.parse_args()
    
    if args.output is None:
        args.output = f"output/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    url = args.url
    print(f"Downloading Douyin video: {url}")
    
    # Run the async function
    success = asyncio.run(download_douyin_video(url, output_dir))
    
    if success:
        print("Download completed successfully!")
    else:
        print("Download failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
