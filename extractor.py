import os
import sys
import requests
from supabase import create_client, Client

# Network and Database Credentials
PROJECT_ID = os.getenv("PROJECT_ID", "").replace('\n', '').replace('\r', '').strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").replace('\n', '').replace('\r', '').strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").replace('\n', '').replace('\r', '').strip()
HUAWEI_COOKIE = os.getenv("HUAWEI_COOKIE", "").replace('\n', '').replace('\r', '').strip()
HUAWEI_CSRF_TOKEN = os.getenv("HUAWEI_CSRF_TOKEN", "").replace('\n', '').replace('\r', '').strip()

print("--- INITIATING MEGACORE CLOUD SYNC ---")
if not all([PROJECT_ID, SUPABASE_URL, SUPABASE_KEY, HUAWEI_COOKIE, HUAWEI_CSRF_TOKEN]):
    print("CRITICAL ERROR: One or more GitHub Secrets are missing.")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_vouchers():
    print("Authenticating via injected session tokens...")
    list_url = "https://w3m.huawei.com/mcloud/umag/ProxyForText/qiankuncloud_sin/proxy/v1/network/orchestrate/onlineuser/users"
    
    headers = {
        "x-project-id": PROJECT_ID,
        "countrycode": "NG",
        "Cookie": HUAWEI_COOKIE,
        "X-Csrf-Token": HUAWEI_CSRF_TOKEN,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "deviceGroupId": "d8a81e9b-15a5-421a-93ae-260d193496f2",
        "pageIndex": 1,
        "pageSize": 500,
        "beginTime": "",
        "endTime": "",
        "onlineuserTerminalIp": "",
        "ssid": "",
        "userName": "",
        "deviceIp": ""
    }

    response = requests.post(list_url, json=payload, headers=headers)
    
    # --- DIAGNOSTIC X-RAY ---
    print("\n--- DIAGNOSTIC DATA DUMP ---")
    # Truncating to 1000 characters so we don't flood your log, but enough to see the folder names
    print(f"Raw Response: {response.text[:1000]}") 
    print("----------------------------\n")
    
    if response.status_code == 200:
        data = response.json().get("data", [])
        if isinstance(data, dict):
            data = data.get("list", data.get("records", data.get("portalUsers", [])))
        return data
    else:
        print("Extraction failed.")
        sys.exit(1)

if __name__ == "__main__":
    fetch_vouchers()
    print("Status: Diagnostic complete. Halting before database sync.")
