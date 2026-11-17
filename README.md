# AI Invoice & Receipt Extractor

A clean Streamlit web application for extracting key fields from PDF invoices and receipts using the Groq API.

## Features

- **Multiple PDF upload**: Upload one or more PDF invoices/receipts simultaneously
- **AI-powered extraction**: Uses Groq's `openai/gpt-oss-120b` model to extract structured data
- **Key fields extracted**:
  - Vendor Name
  - Invoice Number
  - Date
  - Subtotal
  - Tax
  - Total Amount
  - Currency
  - Line Items (description, quantity, unit price, total)
- **Interactive table view**: See all extracted results in an organized dataframe
- **Detailed expandable views**: Per-file details with metrics and line-item tables
- **Download as Excel (.xlsx)**: Full extraction with summary and per-invoice detail sheets
- **Download as CSV**: Summary CSV of all extracted data
- **Environment-based API key**: Loads `GROQ_API_KEY` from `.env` file

## Setup

1. **Clone or navigate to the project directory:**
   ```bash
   f:\projects\invoice_extractor
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a `.env` file** in the project root with your Groq API key:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   ```

4. **Run the application:**
   ```bash
   streamlit run app.py
   ```

## Usage

1. Launch the app with `streamlit run app.py`
2. Enter your sidebar or ensure `GROQ_API_KEY` is set in `.env`
3. Upload one or more PDF invoice/receipt files
4. Click **"Extract Data"** to process the files
5. View extracted results in the interactive table
6. Use the expanders to see detailed information per file
7. Download results as **Excel** or **CSV**

## Technical Details

- Built with **Streamlit** for the web interface
- PDF text extraction via **pypdf**
- AI extraction via **Groq API** using `openai/gpt-oss-120b` model
- Data processing with **pandas**
- Excel export via **openpyxl**

## Dependencies

See `requirements.txt` for the full list of required packages.

## License

This project is for personal/educational use. Ensure you have proper usage rights for the Groq API.