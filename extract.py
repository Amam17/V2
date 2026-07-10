import fitz
import pytesseract
import cv2
import re
import os
import numpy as np
from datetime import datetime, timedelta
import csv

PDF_FILE = "vouchers.pdf"
CSV_FILE = "vouchers.csv"

def pdf_to_images(pdf_path, dpi=200):
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
    
    # Debug: print first 500 chars to logs
    print("=== RAW OCR TEXT (first 500 chars) ===")
    print(text[:500])
    print("=======================================")
    
    # More flexible patterns
    pattern_new = r"Passcode[:\s]*(\d{8}).*?Validity\s*period[:\s]*([0-9]+)\s*days"
    pattern_used = r"Passcode[:\s]*(\d{8}).*?Expiration\s*time[:\s]*([\d\-:\s]+)"
    
    matches = []
    new_matches = re.findall(pattern_new, text, re.DOTALL | re.IGNORECASE)
    for code, days in new_matches:
        matches.append({
            'passcode': code.strip(),
            'type': 'new',
            'days': int(days.strip())
        })
    
    used_matches = re.findall(pattern_used, text, re.DOTALL | re.IGNORECASE)
    for code, exp_time in used_matches:
        if not any(m['passcode'] == code.strip() for m in matches):
            matches.append({
                'passcode': code.strip(),
                'type': 'used',
                'expiration': exp_time.strip()
            })
    
    # Fallback: if no matches, try extracting just 8-digit codes near "Passcode"
    if len(matches) == 0:
        fallback_pattern = r"Passcode[:\s]*(\d{8})"
        fallback_matches = re.findall(fallback_pattern, text, re.IGNORECASE)
        for code in fallback_matches:
            matches.append({
                'passcode': code.strip(),
                'type': 'new',
                'days': 30
            })
        if fallback_matches:
            print(f"⚠️ Fallback: extracted {len(fallback_matches)} vouchers using simple pattern.")
    
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
    
    rows = []
    duplicates = 0
    for item in new_vouchers:
        code = item['passcode']
        if code in existing:
            duplicates += 1
            continue
        
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
        else:
            exp_str = item['expiration']
            try:
                exp_dt = datetime.strptime(exp_str, '%Y-%m-%d %H:%M:%S')
                if exp_dt > datetime.now():
                    status = 'in-use'
                else:
                    status = 'expired'
            except:
                status = 'expired'
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
        print(f"No new vouchers to add. {duplicates} duplicates skipped.")
        return
    
    all_vouchers = list(existing.values()) + rows
    
    headers = ['passcode', 'generation_date', 'validity_days', 'expiry_date', 
               'status', 'sale_price', 'sold_date', 'assigned_agent']
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(all_vouchers)
    
    print(f"Added {len(rows)} new vouchers. Skipped {duplicates} duplicates. Total: {len(all_vouchers)}")

def main():
    if not os.path.exists(PDF_FILE):
        print(f"Error: {PDF_FILE} not found.")
        return
    
    print("Converting PDF to images...")
    images = pdf_to_images(PDF_FILE, dpi=200)
    print(f"Found {len(images)} page(s).")
    
    all_extracted = []
    for idx, img in enumerate(images):
        print(f"\n--- Processing page {idx+1} ---")
        extracted = extract_from_image(img)
        print(f"Page {idx+1}: extracted {len(extracted)} vouchers.")
        all_extracted.extend(extracted)
    
    print(f"\nTotal extracted: {len(all_extracted)} voucher entries.")
    
    if all_extracted:
        append_vouchers(all_extracted)
    else:
        print("No vouchers found in PDF.")

if __name__ == "__main__":
    main() 
