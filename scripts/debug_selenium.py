import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

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

print("Starting Chrome...")
service = Service(ChromeDriverManager().install())
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
for v in videos:
    src = v.get_attribute('src')
    print(f'  Video src: {src[:100] if src else "None"}')

# Check for error page
if 'err' in driver.title.lower() or '404' in driver.title:
    print("Error page detected!")

driver.quit()
print("Done")
