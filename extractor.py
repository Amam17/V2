import os
import sys
import requests

# Network Credentials - Brute force clean ALL invisible line breaks
PROJECT_ID = os.getenv("PROJECT_ID", "").replace('\n', '').replace('\r', '').strip()
HUAWEI_COOKIE = os.getenv("HUAWEI_COOKIE", "").replace('\n', '').replace('\r', '').strip()
HUAWEI_CSRF_TOKEN = os.getenv("HUAWEI_CSRF_TOKEN", "").replace('\n', '').replace('\r', '').strip()

print("--- INITIATING MEGACORE CLOUD SYNC ---")
if not all([PROJECT_ID, HUAWEI_COOKIE, HUAWEI_CSRF_TOKEN]):
    print("CRITICAL ERROR: One or more GitHub Secrets are missing or completely blank.")
    sys.exit(1)

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
    
    print("\n--- JSON MAPPER DIAGNOSTIC ---")
    print(f"Status Code: {response.status_code}")
    print(f"Raw Huawei Response:\n{response.text[:1500]}")
    print("------------------------------\n")
    print("Status: Diagnostic map generated. Halting script.")

if __name__ == "__main__":
    fetch_vouchers()
