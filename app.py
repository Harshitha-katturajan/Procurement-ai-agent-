import streamlit as st
import time
from scraper import scrape_category_and_products

st.set_page_config(page_title="IndiaMART Scraper", layout="centered")

st.title("🛒 IndiaMART Scraper")

# Main input
category_url = st.text_input(
    "Category URL",
    placeholder="https://dir.indiamart.com/impcat/pipe-fittings.html"
)

col1, col2 = st.columns([1, 3])
with col1:
    product_count = st.number_input("Products", min_value=1, max_value=50, value=3)
with col2:
    start_scraping = st.button("🚀 Start Scraping", type="primary", use_container_width=True)

# Results section
if start_scraping:
    if not category_url or "indiamart.com" not in category_url:
        st.error("Please enter a valid IndiaMART category URL")
    else:
        # Progress indicator
        progress_placeholder = st.empty()
        terminal_placeholder = st.empty()
        
        with progress_placeholder.container():
            with st.status("🚀 Scraping in progress...", expanded=False) as status:
                try:
                    # Capture terminal output
                    import io
                    import sys
                    
                    # Redirect stdout to capture print statements
                    old_stdout = sys.stdout
                    sys.stdout = captured_output = io.StringIO()
                    
                    scraped_data, zip_path, gdrive_id = scrape_category_and_products(
                        category_url, 
                        products_per_category=product_count
                    )
                    
                    # Restore stdout
                    sys.stdout = old_stdout
                    terminal_output = captured_output.getvalue()
                    
                    if scraped_data:
                        status.update(
                            label=f"✅ Complete! {len(scraped_data)} products → Google Drive",
                            state="complete"
                        )
                    else:
                        status.update(label="❌ No products scraped", state="error")
                        
                except Exception as e:
                    sys.stdout = old_stdout
                    status.update(label=f"❌ Error: {str(e)}", state="error")
                    terminal_output = f"Error: {str(e)}"
        
        # Show results
        if 'scraped_data' in locals() and scraped_data:
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Scraped", len(scraped_data))
            col2.metric("Success Rate", f"{(len(scraped_data)/product_count)*100:.0f}%")
            if 'gdrive_id' in locals() and gdrive_id:
                col3.metric("Google Drive", "✅ Uploaded")
            else:
                col3.metric("Google Drive", "❌ Failed")
            
            # Google Drive link
            if 'gdrive_id' in locals() and gdrive_id:
                st.success(f"📁 Saved to Google Drive > scraped_files")
                st.link_button("🔗 Open Google Drive", f"https://drive.google.com/file/d/{gdrive_id}")
            
            # Collapsible JSON output
            with st.expander("📄 View Scraped Data", expanded=False):
                for i, product in enumerate(scraped_data, 1):
                    st.text(f"{i}. {product.get('product_name', 'Unknown')} - ₹{product.get('price', 'N/A')}")
                    if st.checkbox(f"Show details #{i}", key=f"details_{i}"):
                        st.json(product)
        
        # Terminal output (collapsible)
        if 'terminal_output' in locals():
            with st.expander("🖥️ Terminal Output", expanded=False):
                st.code(terminal_output, language=None)

# Setup instructions (sidebar)
with st.sidebar:
    st.header("⚙️ Setup")
    st.markdown("""
    **First time setup:**
    1. Install Google Drive API:
       ```bash
       pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
       ```
    
    2. Download `credentials.json` from [Google Cloud Console](https://console.cloud.google.com/)
    
    3. Place in same folder as scraper
    
    **How it works:**
    - Scrapes products → Individual JSON files
    - Checks for duplicates
    - Creates ZIP archive
    - Auto-uploads to Google Drive > scraped_files
    """)
    
    st.header("📁 File Structure")
    st.code("""
    Google Drive/scraped_files/
    └── indiamart_category_20241201_143022.zip
        ├── product1_supplier1_abc123.json
        ├── product2_supplier2_def456.json
        └── ...
    """)