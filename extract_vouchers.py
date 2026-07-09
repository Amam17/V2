import fitz
import pytesseract
import cv2
import re
import pandas as pd
from datetime import datetime
import os
import numpy as np

PDF_FILE = "vouchers.pdf"
OUTPUT_CSV = "voucher_inventory.csv"

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

def extract_vouchers(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    text = pytesseract.image_to_string(thresh, lang='eng')
    pattern = r"Passcode:\s*(\d{8}).*?Expiration time:\s*([\d\-:\s]+)"
    matches = re.findall(pattern, text, re.DOTALL)
    vouchers = []
    for passcode, exp_time in matches:
        vouchers.append({
            "passcode": passcode.strip(),
            "expiration": exp_time.strip(),
            "status": "Available"
        })
    return vouchers

if not os.path.exists(PDF_FILE):
    print(f"❌ Error: {PDF_FILE} not found in this repository!")
    exit(1)

print(f"📄 Processing {PDF_FILE}...")
images = pdf_to_images(PDF_FILE, dpi=150)
print(f"✅ Found {len(images)} page(s).")

all_vouchers = []
for img in images:
    all_vouchers.extend(extract_vouchers(img))

df = pd.DataFrame(all_vouchers).drop_duplicates(subset="passcode")
try:
    df["expiration_dt"] = pd.to_datetime(df["expiration"], errors="coerce")
    df["is_expired"] = df["expiration_dt"] < datetime.now()
except:
    pass

df.to_csv(OUTPUT_CSV, index=False)
print(f"✅ Done! Extracted {len(df)} vouchers.")
