import requests

cookies = {}
with open('cookies.txt') as f:
    for line in f:
        if not line.startswith('#') and line.strip():
            parts = line.strip().split('\t')
            if len(parts) >= 7:
                cookies[parts[5]] = parts[6]
print(f'Cookies: {len(cookies)}')

url = 'https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id=7657228028354825526'
headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer':'https://www.douyin.com/'}
resp = requests.get(url, headers=headers, cookies=cookies)
print(f'Status: {resp.status_code}')
print(f'Content length: {len(resp.text)}')
print(f'First 200 chars: {resp.text[:200]}')
