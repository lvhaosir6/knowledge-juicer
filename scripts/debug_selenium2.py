import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

options = Options()
options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

# Use existing ChromeDriver directly
chromedriver_path = r"C:\Users\lvhaosir\.wdm\drivers\chromedriver\win64\149.0.7827.155\chromedriver-win64\chromedriver.exe"

print("Starting Chrome...")
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=options)

# CDP commands
driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
    'source': '''
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
    '''
})

print("Navigating to Douyin...")
driver.get('https://www.douyin.com/video/7657228028354825526')
time.sleep(5)

print(f'URL: {driver.current_url}')
print(f'Title: {driver.title}')

page_source = driver.page_source
print(f'Page source length: {len(page_source)}')

# Check for video elements
videos = driver.find_elements('tag name', 'video')
print(f'Video elements found: {len(videos)}')
for i, v in enumerate(videos):
    src = v.get_attribute('src')
    print(f'  Video {i} src: {src[:120] if src else "None"}')
    poster = v.get_attribute('poster')
    print(f'  Video {i} poster: {poster[:120] if poster else "None"}')

driver.quit()
print("Done")
