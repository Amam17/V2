import os
import sys
import requests
import json
from supabase import create_client, Client

# Network and Database Credentials
HUAWEI_EMAIL = os.getenv("HUAWEI_EMAIL")
HUAWEI_PASSWORD = os.getenv("HUAWEI_PASSWORD")
PROJECT_ID = os.getenv("PROJECT_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("--- DIAGNOSTIC CHECK PHASE 2 ---")
if not HUAWEI_EMAIL: print("ERROR: HUAWEI_EMAIL is blank."); sys.exit(1)
if not HUAWEI_PASSWORD: print("ERROR: HUAWEI_PASSWORD is blank."); sys.exit(1)
if not PROJECT_ID: print("ERROR: PROJECT_ID is blank. Target URL will fail."); sys.exit(1)
if not SUPABASE_URL: print("ERROR: SUPABASE_URL is blank."); sys.exit(1)
print("SUCCESS: All 5 GitHub Secrets are securely loaded.")
print("--------------------------------\n")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class HuaweiAutomation:
    def __init__(self):
        self.session = requests.Session()
        self.csrf_token = None
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Origin": "https://ekit.huawei.com",
            "Referer": "https://ekit.huawei.com/"
        })

    def login(self):
        print("Initiating secure login sequence to Huawei Uniportal...")
        login_url = "https://uniportal.huawei.com/uniportal1/rest/hwidcenter/login"
        payload = {
            "loginAccount": HUAWEI_EMAIL,
            "uid": HUAWEI_EMAIL,
            "password": HUAWEI_PASSWORD,
            "encryptedPasswordSwitch": "off",
            "lang": "en_US",
            "targetUrl": f"https://ekit.huawei.com/#/smeCloud/Platform?projectId={PROJECT_ID}&platform=dashboard"
        }

        response = self.session.post(login_url, json=payload)
        
        if response.status_code == 200:
            print("Authentication successful.")
            if 'x-csrf-token' in response.headers:
                self.csrf_token = response.headers['x-csrf-token']
                self.session.headers.update({"x-csrf-token": self.csrf_token})
            return True
        else:
            print(f"Authentication failed. Status Code: {response.status_code}")
            # This line forces Huawei to reveal its internal error reason
            print(f"HUAWEI SERVER RESPONSE: {response.text}")
            sys.exit(1)

    def fetch_vouchers(self):
        print("Fetching MegaNet WiFi backend API data...")
        list_url = "https://w3m.huawei.com/mcloud/umag/ProxyForText/qiankuncloud_sin/proxy/v1/networkconfigs/guestmgr/guest/list"
        headers = {"x-project-id": PROJECT_ID, "countrycode": "NG"}
        payload = {"userType": 6}

        response = self.session.post(list_url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json().get("data", [])
        else:
            print(f"Failed to fetch data. Status Code: {response.status_code}")
            sys.exit(1)

def sync_to_database(vouchers):
    print(f"Formatting {len(vouchers)} records for database insertion...")
    db_payload = []
    for v in vouchers:
        db_record = {
            "voucher_code": v.get("userName", ""),
            "agent_id": v.get("path", "UNKNOWN_AGENT"),
            "account_status": str(v.get("accountStatus", "0")),
            "creation_date": v.get("createDate")
        }
        if db_record["voucher_code"]:
            db_payload.append(db_record)

    if db_payload:
        print("Pushing data to Supabase...")
        supabase.table("active_vouchers").upsert(db_payload, on_conflict="voucher_code").execute()
        print("Database sync complete.")
    else:
        print("No valid voucher data found.")

if __name__ == "__main__":
    app = HuaweiAutomation()
    if app.login():
        voucher_data = app.fetch_vouchers()
        if voucher_data:
            sync_to_database(voucher_data)
