import os
import requests
import json

# Pulling credentials directly from GitHub Secrets (No placeholders)
HUAWEI_EMAIL = os.getenv("HUAWEI_EMAIL")
HUAWEI_PASSWORD = os.getenv("HUAWEI_PASSWORD")
PROJECT_ID = os.getenv("PROJECT_ID")

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
            print("Authentication successful. Session captured.")
            if 'x-csrf-token' in response.headers:
                self.csrf_token = response.headers['x-csrf-token']
                self.session.headers.update({"x-csrf-token": self.csrf_token})
            return True
        else:
            print(f"Authentication failed. Status Code: {response.status_code}")
            return False

    def fetch_vouchers(self):
        if not self.csrf_token:
            print("Warning: Missing CSRF security token.")

        print("Fetching MegaNet WiFi backend API data...")
        list_url = "https://w3m.huawei.com/mcloud/umag/ProxyForText/qiankuncloud_sin/proxy/v1/networkconfigs/guestmgr/guest/list"
        
        headers = {
            "x-project-id": PROJECT_ID,
            "countrycode": "NG"
        }
        
        payload = {
            "userType": 6
        }

        response = self.session.post(list_url, json=payload, headers=headers)

        if response.status_code == 200:
            data = response.json()
            vouchers = data.get("data", [])
            print(f"Successfully retrieved {len(vouchers)} active records.")
            return vouchers
        else:
            print(f"Failed to fetch data. Status Code: {response.status_code}")
            return None

if __name__ == "__main__":
    app = HuaweiAutomation()
    if app.login():
        voucher_data = app.fetch_vouchers()
        if voucher_data:
            print("\n--- Network Data Payload Successfully Extracted ---")
            print(json.dumps(voucher_data[0], indent=4))
