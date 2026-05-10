"""임시 진단 — Profile 4 Cookies DB 안의 naver 쿠키 이름·도메인 나열."""
from __future__ import annotations
import os
import sqlite3
import sys

profile = sys.argv[1] if len(sys.argv) > 1 else "Profile 4"
path = os.path.expandvars(rf"%LOCALAPPDATA%\Google\Chrome\User Data\{profile}\Network\Cookies")
if not os.path.exists(path):
    print(f"NOT FOUND: {path}")
    sys.exit(1)

conn = sqlite3.connect(path)
rows = conn.execute(
    "SELECT host_key, name, length(encrypted_value), expires_utc "
    "FROM cookies WHERE host_key LIKE '%naver%' ORDER BY host_key, name"
).fetchall()
print(f"naver cookies in {profile}: {len(rows)} rows")
for host, name, enc_len, expires in rows:
    print(f"  {host:<30} {name:<20} enc_len={enc_len} expires={expires}")
