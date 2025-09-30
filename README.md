IndiaMART Product Intelligence Engine
🛒 Project Overview
The IndiaMART Product Intelligence Engine is a comprehensive solution that combines web scraping, data pipeline, and advanced Retrieval-Augmented Generation (RAG) to turn raw e-commerce data into a searchable knowledge base.

It operates in two stages:

Data Ingestion (Scraping): A Streamlit-powered web application scrapes product details from IndiaMART, packages the data into standardized JSON files, and automatically uploads them to Google Drive.

Intelligence Engine (RAG/LLM): A separate Python script processes these raw JSON files, embeds them into a ChromaDB vector store, and uses the Qwen/Qwen3-0.6B LLM to answer complex, filtered queries about the product ecosystem (e.g., "Find stainless steel fittings under ₹500 from Mumbai").

✨ Features
GUI-Driven Scraping: Easy-to-use Streamlit interface for non-technical users.

Secure Data Handling: Uses Selenium with anti-detection features to scrape live product data.

Google Drive Integration: Seamlessly handles authentication and uploads scraped data (as a ZIP file containing JSONs) to a designated folder.

Vector Database (ChromaDB): Indexes structured product metadata and textual content for high-speed, relevant semantic search.

Intelligent Filtering: The LLM automatically extracts price, material, brand, and location constraints from natural language queries, applying filters before the semantic search for highly accurate results.

Qwen LLM Integration: Utilizes the quantized Qwen/Qwen3-0.6B model for data summarization, filter extraction, and natural language result formatting.

⚙️ Prerequisites
This project requires a Python environment and several specific dependencies, including the local LLM runtime.

Python 3.8+

Ollama (for LLM): The query engine relies on a locally running Ollama server.

Download and Install Ollama

Pull the specific model used:

ollama pull qwen3:0.5b # Or your desired version

Google Cloud Project: For Google Drive API access (credentials.json).

🚀 Installation and Setup
1. Clone the Repository
git clone [https://github.com/your-username/chatbot_llm.git](https://github.com/your-username/chatbot_llm.git)
cd chatbot_llm

2. Set up Virtual Environment and Dependencies
# Create and activate environment
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

# Install Python packages
pip install -r requirement.txt

3. Configure Credentials (Crucial!)
You must obtain and configure your Google Drive API credentials, as well as set up your environment variables.

Create a file named .env in the root directory:

# .env
# Add any other environment variables needed for your local LLM or services

Place your Google Drive API credentials file (client_secret_XYZ.json) in the root directory and rename it to credentials.json.

The system will generate secrets.toml and token.json upon first run for Streamlit and GDrive authentication. These are already added to .gitignore.

▶️ Usage
The project runs in two phases: Scraping and Querying.

Phase 1: Run the Scraper (Streamlit App)
This phase generates the data used by the LLM.

streamlit run app.py

The Streamlit app will open in your browser.

Enter the IndiaMART category URL.

Click "🚀 Start Scraping".

The scraper will run, create a zip file in a temporary location, and upload it to your linked Google Drive folder (e.g., scraped_files/).

Phase 2: Build the RAG Database (Query Engine)
This script processes the latest scraped ZIP file and builds the ChromaDB vector store.

python rag_system.py

Ensure your Ollama server is running before executing this.

The script will print status updates as it unzips, processes JSON files, generates LLM-powered product summaries, and indexes data into chroma_db/.

After processing, an interactive query session will start, allowing you to ask questions about the indexed product data (e.g., Find stainless steel fittings under ₹500).

🛠 Project Structure (Cleaned)
The final repository is organized for clarity and security:

.
├── .gitignore               # Ignores secrets, drivers, tokens, and database files
├── .env                     # Local environment variables (IGNORED)
├── app.py                   # Streamlit Frontend and Scraper Initiator
├── scraper.py               # Core Selenium/BS4 scraping logic, GDrive handling
├── rag_system.py            # Core RAG/LLM Pipeline (Qwen/ChromaDB)
├── gdrive_utils.py          # Google Drive helper functions
├── requirement.txt          # Python dependencies
├── credentials.json         # Google Drive API credentials (IGNORED)
├── msedgedriver.exe         # WebDriver executable (IGNORED)
├── token.json               # GDrive Auth Token (IGNORED)
├── LICENSE                  # Project License (e.g., MIT)
└── README.md                # This file

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.