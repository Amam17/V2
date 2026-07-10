import fitz
import pytesseract
import cv2
import re
import os
import json
import numpy as np
from datetime import datetime
import csv

PDF_FILE = "vouchers.pdf"
CSV_FILE = "vouchers.csv"

def pdf_to_images(pdf_path, dpi=150):
    doc = fitz.open(pdf_path)
    images = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        mat = fitz.Matrix(dpi/72, dpi/72)
        pix = page.get_pixmap(matrix=mat)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        images.append(img)
    doc.close()
    return images

def extract_from_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    text = pytesseract.image_to_string(thresh, lang='eng')
    
    # Look for both patterns
    # Pattern 1: Validity period: X days
    pattern_new = r"Passcode:\s*(\d{8}).*?Validity period:\s*([0-9]+)\s*days"
    # Pattern 2: Expiration time: YYYY-MM-DD HH:MM:SS
    pattern_used = r"Passcode:\s*(\d{8}).*?Expiration time:\s*([\d\-:\s]+)"
    
    matches = []
    # Try new pattern first
    new_matches = re.findall(pattern_new, text, re.DOTALL)
    for code, days in new_matches:
        matches.append({
            'passcode': code.strip(),
            'type': 'new',
            'days': int(days.strip())
        })
    
    # Try used pattern
    used_matches = re.findall(pattern_used, text, re.DOTALL)
    for code, exp_time in used_matches:
        # Check if this code was already found as new (avoid duplicates)
        if not any(m['passcode'] == code.strip() for m in matches):
            matches.append({
                'passcode': code.strip(),
                'type': 'used',
                'expiration': exp_time.strip()
            })
    
    return matches

def load_existing_vouchers():
    if not os.path.exists(CSV_FILE):
        return {}
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        existing = {}
        for row in reader:
            if row.get('passcode'):
                existing[row['passcode']] = row
        return existing

def append_vouchers(new_vouchers):
    existing = load_existing_vouchers()
    today = datetime.now().date().isoformat()
    
    # Prepare all rows
    rows = []
    for item in new_vouchers:
        code = item['passcode']
        if code in existing:
            continue  # skip duplicates
        
        if item['type'] == 'new':
            days = item['days']
            expiry = (datetime.now().date() + timedelta(days=days)).isoformat()
            row = {
                'passcode': code,
                'generation_date': today,
                'validity_days': days,
                'expiry_date': expiry,
                'status': 'available',
                'sale_price': '0.00',
                'sold_date': '',
                'assigned_agent': ''
            }
        else:  # used
            exp_str = item['expiration']
            try:
                exp_dt = datetime.strptime(exp_str, '%Y-%m-%d %H:%M:%S')
                if exp_dt > datetime.now():
                    status = 'in-use'
                else:
                    status = 'expired'
            except:
                status = 'expired'  # fallback
            row = {
                'passcode': code,
                'generation_date': '',
                'validity_days': '',
                'expiry_date': exp_str,
                'status': status,
                'sale_price': '0.00',
                'sold_date': '',
                'assigned_agent': ''
            }
        rows.append(row)
    
    if not rows:
        print("No new vouchers to add.")
        return
    
    # Merge with existing
    all_vouchers = list(existing.values()) + rows
    
    # Write back
    headers = ['passcode', 'generation_date', 'validity_days', 'expiry_date', 
               'status', 'sale_price', 'sold_date', 'assigned_agent']
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(all_vouchers)
    
    print(f"Added {len(rows)} new vouchers. Total: {len(all_vouchers)}")

def main():
    if not os.path.exists(PDF_FILE):
        print(f"Error: {PDF_FILE} not found.")
        return
    
    print("Converting PDF to images...")
    images = pdf_to_images(PDF_FILE, dpi=150)
    print(f"Found {len(images)} page(s).")
    
    all_extracted = []
    for img in images:
        extracted = extract_from_image(img)
        all_extracted.extend(extracted)
    
    print(f"Extracted {len(all_extracted)} voucher entries.")
    
    if all_extracted:
        append_vouchers(all_extracted)
    else:
        print("No vouchers found in PDF.")

if __name__ == "__main__":
    from datetime import timedelta
    main()
