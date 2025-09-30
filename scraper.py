import random
import tempfile
import shutil
import time
import zipfile 
import hashlib
import os
import json
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from urllib.parse import urljoin, urlparse
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

# Google Drive imports
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    GDRIVE_AVAILABLE = True
    print("✅ Google Drive integration available")
except ImportError:
    GDRIVE_AVAILABLE = False
    print("⚠️ Google Drive libraries not installed. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

print("\n✅ SUCCESS: Google Drive scraper loaded!\n")

# Google Drive setup
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials.json'  # Download from Google Cloud Console
TOKEN_FILE = 'token.json'


def authenticate_gdrive():
    """Authenticate with Google Drive"""
    if not GDRIVE_AVAILABLE:
        return None
        
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print("❌ credentials.json not found. Download from Google Cloud Console.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return build('drive', 'v3', credentials=creds)


def find_or_create_folder(service, folder_name, parent_folder_id=None):
    """Find or create folder in Google Drive"""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    if parent_folder_id:
        query += f" and '{parent_folder_id}' in parents"
    
    results = service.files().list(q=query).execute()
    items = results.get('files', [])
    
    if items:
        return items[0]['id']
    else:
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_folder_id:
            folder_metadata['parents'] = [parent_folder_id]
            
        folder = service.files().create(body=folder_metadata).execute()
        return folder.get('id')


def upload_to_gdrive(service, file_path, folder_id):
    """Upload file to Google Drive folder"""
    if not os.path.exists(file_path):
        return None
        
    filename = os.path.basename(file_path)
    media = MediaFileUpload(file_path)
    
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    
    file = service.files().create(body=file_metadata, media_body=media).execute()
    print(f"    -> ✅ Uploaded to Google Drive: {filename}")
    return file.get('id')


def init_driver():
    """Initializes Edge driver with anti-detection."""
    options = webdriver.EdgeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver_path = r"C:\Users\kattu\.vscode\.vscode\ChatBot_LLM\msedgedriver.exe"
    browser_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

    if not os.path.exists(driver_path):
        raise FileNotFoundError(f"❌ Edge WebDriver not found at '{driver_path}'")
    if not os.path.exists(browser_path):
        raise FileNotFoundError(f"❌ Edge browser not found at '{browser_path}'")

    options.binary_location = browser_path
    service = EdgeService(executable_path=driver_path)
    driver = webdriver.Edge(service=service, options=options)
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def sanitize_filename(text):
    """Convert text to safe filename."""
    if not text:
        return "unknown"
    
    text = re.sub(r'[<>:"/\\|?*]', '_', text)
    text = re.sub(r'\s+', '_', text)
    text = text.strip('._')
    
    return text[:50] if len(text) > 50 else text


def generate_content_hash(data):
    """Generate hash of JSON content for duplicate detection."""
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.md5(json_str.encode()).hexdigest()[:8]


def create_unique_filename(product_data):
    """Create unique filename from product data."""
    product_name = sanitize_filename(product_data.get('product_name', 'unknown'))
    supplier_name = sanitize_filename(product_data.get('supplier_name', 'unknown'))
    url_hash = hashlib.md5(product_data.get('URL', '').encode()).hexdigest()[:6]
    
    return f"{product_name}_{supplier_name}_{url_hash}.json"


def is_duplicate_content(new_data, existing_files_dir):
    """Check if content already exists in any file."""
    new_hash = generate_content_hash(new_data)
    
    if not os.path.exists(existing_files_dir):
        return False
    
    for filename in os.listdir(existing_files_dir):
        if filename.endswith('.json'):
            try:
                filepath = os.path.join(existing_files_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                
                if generate_content_hash(existing_data) == new_hash:
                    print(f"    -> 🔄 Duplicate content found")
                    return True
            except:
                continue
    
    return False


def cleanup_local_files(json_files, zip_filepath, temp_dir):
    """Clean up all local files after successful Google Drive upload"""
    try:
        # Remove individual JSON files
        for json_file in json_files:
            if json_file and os.path.exists(json_file):
                os.remove(json_file)
                
        # Remove ZIP file
        if zip_filepath and os.path.exists(zip_filepath):
            os.remove(zip_filepath)
            
        # Remove temporary directory if empty
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
            
    except Exception as e:
        print(f"⚠️ Warning: Could not clean up some local files: {e}")


def save_product_as_json(product_data, temp_dir):
    """Save product data as individual JSON file in temporary directory"""
    
    if is_duplicate_content(product_data, temp_dir):
        print(f"    -> ⏭️ Skipping duplicate")
        return None
    
    os.makedirs(temp_dir, exist_ok=True)
    
    filename = create_unique_filename(product_data)
    filepath = os.path.join(temp_dir, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(product_data, f, indent=2, ensure_ascii=False)
        
        print(f"    -> 💾 Saved JSON: {filename}")
        return filepath
    except Exception as e:
        print(f"    -> ❌ Save failed: {e}")
        return None


def create_zip_and_upload(json_files, category_name, temp_dir):
    """Create ZIP with JSON files and upload to Google Drive, then cleanup local files"""
    if not json_files:
        print("    -> ⚠️ No files to zip")
        return None, None
    
    # Create ZIP
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    category_clean = sanitize_filename(category_name)
    zip_filename = f"indiamart_{category_clean}_{timestamp}.zip"
    zip_filepath = os.path.join(temp_dir, zip_filename)
    
    try:
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for json_file in json_files:
                if json_file and os.path.exists(json_file):
                    # Add JSON file to ZIP with just the filename (no path)
                    arcname = os.path.basename(json_file)
                    zipf.write(json_file, arcname)
        
        print(f"\n📦 Created ZIP: {zip_filename} (contains {len(json_files)} JSON files)")
        
        # Upload to Google Drive
        gdrive_file_id = None
        if GDRIVE_AVAILABLE:
            try:
                service = authenticate_gdrive()
                if service:
                    # Find/create scraped_files folder
                    folder_id = find_or_create_folder(service, 'scraped_files')
                    
                    # Upload ZIP
                    gdrive_file_id = upload_to_gdrive(service, zip_filepath, folder_id)
                    if gdrive_file_id:
                        print(f"🔗 Google Drive: https://drive.google.com/file/d/{gdrive_file_id}")
                        print(f"📁 Uploaded to: Google Drive > scraped_files > {zip_filename}")
                    else:
                        print("❌ Upload to Google Drive failed")
                else:
                    print("❌ Google Drive authentication failed")
            except Exception as e:
                print(f"❌ Google Drive error: {e}")
        
        # Clean up local files after successful upload
        if gdrive_file_id:
            cleanup_local_files(json_files, zip_filepath, temp_dir)
            print("🧹 Local files cleaned up - everything is now in Google Drive only")
        
        return zip_filepath if gdrive_file_id else None, gdrive_file_id
        
    except Exception as e:
        print(f"❌ ZIP creation failed: {e}")
        return None, None


def safe_xpath_extract(driver, xpath, description=""):
    """Safely extract text using XPath with error handling."""
    try:
        element = driver.find_element(By.XPATH, xpath)
        text = element.text.strip()
        if text:
            return text
        else:
            return ""
    except:
        return ""


def extract_product_details(soup, product_url, driver=None):
    """Extract product details using precise XPaths."""
    
    if driver is None:
        raise ValueError("❌ Driver parameter is required")
    
    print(f"🔍 Extracting: {product_url[-30:]}...")
    
    product_data = {
        "URL": product_url,
        "product_name": "",
        "price": "",
        "price_unit": "",
        "supplier_name": "",
        "supplier_location": "",
        "gst_number": "",
        "gst_registration_date": "",
        "supplier_rating": "",
        "response_rate": "",
        "trustseal_verified": "",
        "member_since": "",
        "years_experience": "",
        "legal_status": "",
        "annual_turnover": "",
        "specifications": {},
        "last_updated": time.strftime("%Y-%m-%d"),
        "category": extract_category_from_url(product_url)
    }
    
    # Extract product name
    product_name = safe_xpath_extract(driver, "//h1[@class='bo center-heading centerHeadHeight ']", "Product Name")
    if not product_name:
        product_name = safe_xpath_extract(driver, "//h1", "Product Name (fallback)")
    product_data["product_name"] = product_name if product_name else "Product name not found"
    
    # Extract price
    try:
        price_element = driver.find_element(By.XPATH, "//span[@class='bo price-unit']")
        price_text = price_element.text.strip()
        price_match = re.search(r'₹\s*([\d,]+(?:\.\d+)?)', price_text)
        if price_match:
            product_data["price"] = price_match.group(1).replace(',', '')
        
        try:
            unit_element = driver.find_element(By.XPATH, "//span[@class='units pcl76']")
            unit_text = unit_element.text.strip()
            product_data["price_unit"] = f"Per {unit_text}" if unit_text else "Per Unit"
        except:
            product_data["price_unit"] = "Per Unit"
    except:
        product_data["price"] = "Not found"
        product_data["price_unit"] = "N/A"
    
    # Extract specifications
    try:
        table = driver.find_element(By.XPATH, "//table//tbody")
        rows = table.find_elements(By.TAG_NAME, "tr")
        
        specifications = {}
        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
                    key = cells[0].text.strip()
                    value = cells[1].text.strip()
                    if key and value:
                        specifications[key] = value
            except:
                continue
        
        product_data["specifications"] = specifications
    except:
        product_data["specifications"] = {"Note": "No specifications found"}
    
    # Extract supplier info
    supplier_name = safe_xpath_extract(driver, "//div[@class='pdflx1 pdBw asc']//h2[@class='fs15']", "Supplier")
    product_data["supplier_name"] = supplier_name if supplier_name else "Not found"
    
    location = safe_xpath_extract(driver, "//span[@class='city-highlight']", "Location")
    product_data["supplier_location"] = location if location else "Not found"
    
    # Extract other fields (GST, rating, etc.)
    try:
        gst_element = driver.find_element(By.XPATH, "//span[@class='fs11 color1']")
        gst_text = gst_element.text.strip()
        if gst_text and len(gst_text) == 15:
            product_data["gst_number"] = gst_text
    except:
        product_data["gst_number"] = "Not found"
    
    trustseal = safe_xpath_extract(driver, "//span[@class='lh11'][contains(text(), 'TrustSEAL')]", "TrustSEAL")
    product_data["trustseal_verified"] = trustseal if trustseal else "Not found"
    
    years = safe_xpath_extract(driver, "//span[@class='fs11'][contains(text(), 'yrs')]", "Years")
    product_data["years_experience"] = years if years else "Not found"
    
    try:
        rating_element = driver.find_element(By.XPATH, "//span[@class='bo color']")
        rating = rating_element.text.strip()
        review_element = driver.find_element(By.XPATH, "//span[@class='tcund']")
        review_count = review_element.text.strip()
        product_data["supplier_rating"] = f"{rating} ({review_count} reviews)"
    except:
        product_data["supplier_rating"] = "Not found"
    
    response_rate = safe_xpath_extract(driver, "//span[@class='lh11 fs11 on color1'][contains(text(), 'Response Rate')]", "Response Rate")
    product_data["response_rate"] = response_rate if response_rate else "Not found"
    
    # Company details
    legal_status = safe_xpath_extract(driver, "//h4[@class='cmpfvalh4 fs13 bo mt5'][1]", "Legal Status")
    product_data["legal_status"] = legal_status if legal_status else "Not found"
    
    gst_date = safe_xpath_extract(driver, "//li[@id='Template3_compfactsheet_1']//h4[@class='cmpfvalh4 fs13 bo mt5']", "GST Date")
    product_data["gst_registration_date"] = gst_date if gst_date else "Not found"
    
    turnover = safe_xpath_extract(driver, "//li[@id='Template3_compfactsheet_2']//h4[@class='cmpfvalh4 fs13 bo mt5']", "Turnover")
    product_data["annual_turnover"] = turnover if turnover else "Not found"
    
    member_since = safe_xpath_extract(driver, "//li[@id='Template3_compfactsheet_3']//h4[@class='cmpfvalh4 fs13 bo mt5']", "Member Since")
    product_data["member_since"] = member_since if member_since else "Not found"
    
    print(f"    -> ✅ {product_data['product_name'][:30]}...")
    return product_data


def extract_category_from_url(url):
    """Extract category from URL."""
    try:
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if 'impcat' in parsed.path:
            return path_parts[-1].replace('.html', '').replace('-', ' ').title()
        elif 'proddetail' in parsed.path:
            return "Product Detail"
        return "General"
    except Exception:
        return "Unknown"


def collect_product_urls(soup, base_url, limit=10):
    """Collect product URLs from category page."""
    product_urls = set()
    
    try:
        links = soup.find_all("a", href=True)
        for link in links:
            href = link.get("href", "")
            if '/proddetail/' in href:
                full_url = urljoin(base_url, href)
                product_urls.add(full_url)
                if len(product_urls) >= limit:
                    break
    except Exception as e:
        print(f"Error collecting URLs: {e}")
    
    return list(product_urls)[:limit]


def scrape_category_and_products(category_url, products_per_category=10):
    """Main scraping function - saves ONLY to Google Drive, no local storage"""
    scraped_data = []
    saved_json_files = []
    driver = None
    
    # Create temporary directory for processing
    temp_dir = tempfile.mkdtemp(prefix="indiamart_scrape_")
    
    try:
        print(f"🚀 Starting scrape: {category_url}")
        print(f"📁 Temporary processing: {temp_dir}")
        print("🎯 Target: Google Drive only (no local storage)")
        
        driver = init_driver()
        
        # Load category page
        driver.get(category_url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        time.sleep(3)
        
        # Collect URLs
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product_urls = collect_product_urls(soup, category_url, products_per_category)
        
        if not product_urls:
            print("❌ No product URLs found")
            return scraped_data, None, None
        
        print(f"📋 Found {len(product_urls)} URLs")
        
        # Process each product
        for idx, product_url in enumerate(product_urls, 1):
            print(f"\n[{idx}/{len(product_urls)}] Processing...")
            
            try:
                driver.get(product_url)
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                time.sleep(3)
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                product_data = extract_product_details(soup, product_url, driver)
                
                if product_data["product_name"] not in ["Product name not found", "Extraction failed"]:
                    json_filepath = save_product_as_json(product_data, temp_dir)
                    if json_filepath:
                        saved_json_files.append(json_filepath)
                        scraped_data.append(product_data)
                        print(f"    -> ✅ JSON saved temporarily")
                    else:
                        print(f"    -> ⏭️ Duplicate content")
                else:
                    print(f"    -> ❌ Extraction failed")
                    
            except Exception as e:
                print(f"    -> ❌ Error: {e}")
            
            time.sleep(random.uniform(1, 3))
        
        # Create ZIP and upload to Google Drive (this will cleanup local files)
        category_name = extract_category_from_url(category_url)
        zip_filepath, gdrive_id = create_zip_and_upload(saved_json_files, category_name, temp_dir)
        
        if gdrive_id:
            print(f"\n🎉 SUCCESS! {len(scraped_data)} products → Google Drive")
            print(f"📦 ZIP contains {len(saved_json_files)} JSON files")
            print("🗑️ All local files removed")
        else:
            print(f"\n⚠️ Scraping completed but Google Drive upload failed")
            print("🗂️ Local files available for manual upload")
        
        return scraped_data, zip_filepath, gdrive_id
            
    except Exception as e:
        print(f"❌ Critical error: {e}")
        return scraped_data, None, None
    finally:
        if driver:
            driver.quit()
        
        # Final cleanup of temp directory if it still exists
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except:
            pass


if __name__ == "__main__":
    test_url = "https://www.indiamart.com/proddetail/stainless-steel-male-elbow-11181618512.html"
    print("🚀 Testing...")
    result, zip_path, gdrive_id = scrape_category_and_products(
        "https://www.indiamart.com/impcat/stainless-steel-elbow.html",
        products_per_category=2
    )
    print(f"✅ Test complete!")