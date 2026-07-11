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
    
    # Split text into blocks starting with "Passcode"
    # This captures each voucher entry as a separate block
    block_pattern = r"Passcode[:\s]*(\d{8})(.*?)(?=Passcode[:\s]*\d{8}|$)"
    blocks = re.findall(block_pattern, text, re.DOTALL | re.IGNORECASE)
    
    matches = []
    for code, rest in blocks:
        # Extract price (e.g., "#300" or "# 500")
        price_match = re.search(r'#\s*([\d.]+)', rest)
        price = price_match.group(1) if price_match else '0.00'
        
        # Check if it's a new voucher (has Validity period)
        validity_match = re.search(r'Validity\s*period[:\s]*([0-9]+)\s*days', rest, re.IGNORECASE)
        if validity_match:
            days = int(validity_match.group(1))
            matches.append({
                'passcode': code.strip(),
                'type': 'new',
                'days': days,
                'price': price
            })
            continue
        
        # Check if it's a used voucher (has Expiration time)
        exp_match = re.search(r'Expiration\s*time[:\s]*([\d\-:\s]+)', rest, re.IGNORECASE)
        if exp_match:
            exp_time = exp_match.group(1).strip()
            matches.append({
                'passcode': code.strip(),
                'type': 'used',
                'expiration': exp_time,
                'price': price
            })
            continue
        
        # Fallback: if no pattern matched, treat as new with 30 days
        matches.append({
            'passcode': code.strip(),
            'type': 'new',
            'days': 30,
            'price': price
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

def append_or_update_vouchers(new_vouchers):
    existing = load_existing_vouchers()
    today = datetime.now().date().isoformat()
    
    new_rows = []
    updated_rows = 0
    
    for item in new_vouchers:
        code = item['passcode']
        price = item.get('price', '0.00')
        
        # Determine the new data for this voucher
        if item['type'] == 'new':
            days = item['days']
            expiry = (datetime.now().date() + timedelta(days=days)).isoformat()
            status = 'available'
            generation_date = today
            validity_days = days
            exp_date = expiry
        else:  # used
            exp_str = item['expiration']
            try:
                exp_dt = datetime.strptime(exp_str, '%Y-%m-%d %H:%M:%S')
                if exp_dt > datetime.now():
                    status = 'in-use'
                else:
                    status = 'expired'
            except:
                status = 'expired'
            exp_date = exp_str
            generation_date = ''
            validity_days = ''
        
        # Check if passcode exists
        if code in existing:
            # UPDATE existing record
            existing[code]['status'] = status
            existing[code]['expiry_date'] = exp_date
            existing[code]['validity_days'] = validity_days
            existing[code]['generation_date'] = generation_date
            
            # ONLY update price if existing price is 0 or empty
            # This preserves any manual price the user might have set
            existing_price = float(existing[code].get('sale_price', '0') or '0')
            if existing_price == 0:
                existing[code]['sale_price'] = price
            
            updated_rows += 1
        else:
            # ADD new voucher
            new_row = {
                'passcode': code,
                'generation_date': generation_date,
                'validity_days': validity_days,
                'expiry_date': exp_date,
                'status': status,
                'sale_price': price,
                'sold_date': '',
                'assigned_agent': ''
            }
            new_rows.append(new_row)
    
    if not new_rows and updated_rows == 0:
        print("No changes detected.")
        return
    
    all_vouchers = list(existing.values()) + new_rows
    
    headers = ['passcode', 'generation_date', 'validity_days', 'expiry_date', 
               'status', 'sale_price', 'sold_date', 'assigned_agent']
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(all_vouchers)
    
    print(f"✅ Updated {updated_rows} existing vouchers.")
    print(f"✅ Added {len(new_rows)} new vouchers.")
    print(f"📊 Total vouchers in system: {len(all_vouchers)}")

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
        append_or_update_vouchers(all_extracted)
    else:
        print("No vouchers found in PDF.")

if __name__ == "__main__":
    main() 
