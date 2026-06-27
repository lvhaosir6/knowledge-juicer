#!/usr/bin/env python3
"""
Get Douyin cookies using Selenium.
"""

import json
import time
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_douyin_cookies(url: str, output_file: str) -> bool:
    """Get cookies from Douyin using Selenium."""
    print("Setting up Chrome driver...")
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        # Initialize driver
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
        time.sleep(5)
        
        # Get cookies
        cookies = driver.get_cookies()
        print(f"Found {len(cookies)} cookies")
        
        # Save cookies in Netscape format
        with open(output_file, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# http://curl.haxx.se/rfc/cookie_spec.html\n")
            f.write("# This is a generated file!  Do not edit.\n\n")
            
            for cookie in cookies:
                domain = cookie.get('domain', '')
                flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                path = cookie.get('path', '/')
                secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                expiry = str(int(cookie.get('expiry', 0)))
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                
                f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
        
        print(f"Cookies saved to: {output_file}")
        
        # Also save as JSON for reference
        json_file = output_file.replace('.txt', '.json')
        with open(json_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f"Cookies JSON saved to: {json_file}")
        
        driver.quit()
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python get_douyin_cookies.py <douyin_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    output_file = "cookies.txt"
    
    print(f"Getting cookies for: {url}")
    
    if get_douyin_cookies(url, output_file):
        print("Cookies retrieved successfully!")
        print(f"You can now use: yt-dlp --cookies {output_file} <video_url>")
    else:
        print("Failed to get cookies!")
        sys.exit(1)

if __name__ == "__main__":
    main()
