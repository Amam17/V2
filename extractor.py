import os
import sys
import requests
from supabase import create_client, Client

# Network and Database Credentials - with .strip() to automatically clean invisible characters
PROJECT_ID = os.getenv("PROJECT_ID", "").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
HUAWEI_COOKIE = os.getenv("HUAWEI_COOKIE", "").strip()
HUAWEI_CSRF_TOKEN = os.getenv("HUAWEI_CSRF_TOKEN", "").strip()

print("--- INITIATING MEGACORE CLOUD SYNC ---")
if not all([PROJECT_ID, SUPABASE_URL, SUPABASE_KEY, HUAWEI_COOKIE, HUAWEI_CSRF_TOKEN]):
    print("CRITICAL ERROR: One or more GitHub Secrets are missing or completely blank.")
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
        "pageIndex": 1,
        "pageSize": 500
    }

    response = requests.post(list_url, json=payload, headers=headers)
    if response.status_code == 200:
        print("Huawei network connection established. Data extracted.")
        data = response.json().get("data", [])
        
        if isinstance(data, dict):
            data = data.get("list", data.get("records", []))
            
        return data
    else:
        print(f"Extraction failed. Status Code: {response.status_code}")
        print(f"HUAWEI FIREWALL RESPONSE: {response.text}")
        sys.exit(1)

def sync_to_database(vouchers):
    print(f"Formatting {len(vouchers)} active records for Supabase insertion...")
    db_payload = []
    for v in vouchers:
        username = v.get("userName", v.get("username", ""))
        
        if username:
            db_record = {
                "voucher_code": str(username),
                "agent_id": str(v.get("userType", "Passcode User")),
                "account_status": "Online",
                "creation_date": v.get("loginTime", v.get("accessTime", "UNKNOWN"))
            }
            db_payload.append(db_record)

    if db_payload:
        print("Pushing data payload to database...")
        supabase.table("active_vouchers").upsert(db_payload, on_conflict="voucher_code").execute()
        print("Database sync complete. Server shutting down cleanly.")
    else:
        print("No valid voucher data found after parsing.")

if __name__ == "__main__":
    voucher_data = fetch_vouchers()
    
    if voucher_data:
        print(f"Success: {len(voucher_data)} live portal users found.")
        sync_to_database(voucher_data)
    else:
        print("Status: 0 live portal users found on the network at this time. Database sync skipped.")
