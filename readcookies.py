import sqlite3
db = r'C:\Users\lvhaosir\AppData\Local\Temp\opencode\chrome_cookies.db'
c = sqlite3.connect(db)
cur = c.cursor()
cur.execute("SELECT name,host_key,length(encrypted_value),hex(substr(encrypted_value,1,8)) FROM cookies WHERE host_key LIKE '%douyin%' OR host_key LIKE '%toutiao%' OR host_key LIKE '%byted%'")
rows = cur.fetchall()
print("count", len(rows))
for r in rows:
    print(r)
