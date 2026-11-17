"""
AI Invoice & Receipt Extractor - Streamlit Web App
Upload PDF invoices/receipts, extract key fields via Groq API (openai/gpt-oss-120b),
view results in an interactive table, and download as Excel or CSV.
"""
import os
import json
import io
from typing import List, Dict, Any, Optional
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from pypdf import PdfReader
import pandas as pd

# Load environment variables
load_dotenv()

# Configuration
GROQ_MODEL = "openai/gpt-oss-120b"


@st.cache_resource
def get_groq_client() -> Optional[Groq]:
    """Create and cache the Groq client from GROQ_API_KEY."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


def extract_text_from_pdf(pdf_file) -> str:
    """Extract text from an uploaded PDF file."""
    try:
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        st.error(f"Error extracting text from {getattr(pdf_file, 'name', 'PDF')}: {e}")
        return ""


def build_extraction_prompt(pdf_text: str) -> str:
    """Build the prompt for the LLM to extract structured invoice data."""
    return f"""You are an expert invoice/receipt data extraction system. Extract the following fields from the provided document text and return ONLY valid JSON.

Fields to extract:
- vendor_name (string): Name of the vendor/supplier
- invoice_number (string): Invoice/receipt number
- date (string): Invoice date in YYYY-MM-DD format if possible, otherwise as written
- subtotal (number): Subtotal amount before tax
- tax (number): Tax amount
- total_amount (number): Total amount paid
- currency (string): Currency code (e.g., USD, EUR, GBP)
- line_items (array): List of line items, each with: description, quantity, unit_price, total

Rules:
- If a field is not found, use null for strings and 0 for numbers
- For line_items, return empty array [] if none found
- Return ONLY the JSON object, no markdown, no extra text
- Numbers should be numeric types, not strings

Document text:
{pdf_text[:12000]}"""


def extract_invoice_data(client: Groq, pdf_text: str) -> Dict[str, Any]:
    """Call Groq API to extract structured invoice data."""
    prompt = build_extraction_prompt(pdf_text)

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        data = json.loads(content)

        # Ensure all fields exist with defaults
        result = {
            "vendor_name": data.get("vendor_name") or "Unknown",
            "invoice_number": data.get("invoice_number") or "N/A",
            "date": data.get("date") or "N/A",
            "subtotal": float(data.get("subtotal") or 0),
            "tax": float(data.get("tax") or 0),
            "total_amount": float(data.get("total_amount") or 0),
            "currency": data.get("currency") or "USD",
            "line_items": data.get("line_items") or [],
        }
        return result
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse LLM response as JSON.")
        return get_default_result()
    except Exception as e:
        st.error(f"Error calling Groq API: {e}")
        return get_default_result()


def get_default_result() -> Dict[str, Any]:
    """Return default extraction result."""
    return {"vendor_name": "Unknown", "invoice_number": "N/A", "date": "N/A", "subtotal": 0.0, "tax": 0.0, "total_amount": 0.0, "currency": "USD", "line_items": []}


def format_line_items_summary(line_items: List[Dict]) -> str:
    """Create a short summary of line items for the main table."""
    if not line_items:
        return "—"
    count = len(line_items)
    descriptions = [item.get("description", "")[:30] for item in line_items[:3]]
    summary = f"{count} item(s): " + "; ".join(descriptions)
    if count > 3:
        summary += f" ... (+{count - 3} more)"
    return summary


def create_excel_download(results: List[Dict[str, Any]]) -> bytes:
    """Create Excel file with summary sheet and detail sheets."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_rows = []
        for i, r in enumerate(results):
            summary_rows.append({
                "#": i + 1,
                "Vendor": r["vendor_name"],
                "Invoice #": r["invoice_number"],
                "Date": r["date"],
                "Subtotal": f"{r['currency']} {r['subtotal']:,.2f}",
                "Tax": f"{r['currency']} {r['tax']:,.2f}",
                "Total": f"{r['currency']} {r['total_amount']:,.2f}",
                "Currency": r["currency"],
                "Line Items": format_line_items_summary(r["line_items"]),
            })
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Summary", index=False)
        for i, r in enumerate(results):
            sheet_name = f"Invoice_{i+1}"[:31]
            items = r["line_items"]
            if items:
                detail_rows = [{
                    "Description": item.get("description", ""),
                    "Quantity": item.get("quantity", ""),
                    "Unit Price": item.get("unit_price", ""),
                    "Total": item.get("total", ""),
                } for item in items]
                detail_df = pd.DataFrame(detail_rows)
            else:
                detail_df = pd.DataFrame([{"Note": "No line items found"}])
            detail_df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output.read()


def create_csv_download(results: List[Dict[str, Any]]) -> str:
    """Create CSV content from results."""
    summary_rows = [{
        "#": i + 1,
        "Vendor": r["vendor_name"],
        "Invoice #": r["invoice_number"],
        "Date": r["date"],
        "Subtotal": f"{r['currency']} {r['subtotal']:,.2f}",
        "Tax": f"{r['currency']} {r['tax']:,.2f}",
        "Total": f"{r['currency']} {r['total_amount']:,.2f}",
        "Currency": r["currency"],
        "Line Items Count": len(r["line_items"]),
    } for i, r in enumerate(results)]
    return pd.DataFrame(summary_rows).to_csv(index=False)


def main():
    st.set_page_config(
        page_title="AI Invoice & Receipt Extractor",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown('<div class="main-header">📄 AI Invoice & Receipt Extractor</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload PDF invoices/receipts, extract key fields with AI, and export to Excel or CSV</div>', unsafe_allow_html=True)
    
    with st.sidebar:
        st.header("⚙️ Settings")
        client = get_groq_client()
        if client:
            st.success("✅ Groq API connected")
        else:
            st.error("❌ GROQ_API_KEY not found in .env")
            st.info("Add your Groq API key to `.env` file")
        st.divider()
        st.header("📋 Extraction Fields")
        st.markdown("""
- **Vendor Name**
- **Invoice Number**
- **Date**
- **Subtotal**
- **Tax**
- **Total Amount**
- **Currency**
- **Line Items** (description, qty, unit price, total)
        """)
        st.divider()
        st.caption(f"Model: `{GROQ_MODEL}`")
    
    if not client:
        st.stop()
    
    uploaded_files = st.file_uploader(
        "Drag & drop PDF invoices/receipts here",
        type=["pdf"],
        accept_multiple_files=True,
        help="Select one or more PDF files (max 200MB each)"
    )
    
    if not uploaded_files:
        st.info("👆 Upload one or more PDF files to begin extraction")
        return
    
    st.markdown(f"**{len(uploaded_files)} file(s) selected**")
    
    if st.button("🚀 Extract Data", type="primary", use_container_width=True):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        for idx, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Processing: {uploaded_file.name} ({idx+1}/{len(uploaded_files)})")
            pdf_text = extract_text_from_pdf(uploaded_file)
            if not pdf_text:
                st.warning(f"No text extracted from {uploaded_file.name}")
                results.append(get_default_result())
                progress_bar.progress((idx + 1) / len(uploaded_files))
                continue
            extracted = extract_invoice_data(client, pdf_text)
            extracted["source_file"] = uploaded_file.name
            results.append(extracted)
            progress_bar.progress((idx + 1) / len(uploaded_files))
        status_text.text("✅ Extraction complete!")
        st.session_state["results"] = results
        st.session_state["extracted"] = True
        st.rerun()
    
    if st.session_state.get("extracted", False):
        results = st.session_state["results"]
        st.divider()
        st.subheader("📊 Extracted Results")
        
        display_rows = []
        for i, r in enumerate(results):
            display_rows.append({
                "#": i + 1,
                "Source File": r.get("source_file", "N/A"),
                "Vendor": r["vendor_name"],
                "Invoice #": r["invoice_number"],
                "Date": r["date"],
                "Subtotal": f"{r['currency']} {r['subtotal']:,.2f}",
                "Tax": f"{r['currency']} {r['tax']:,.2f}",
                "Total": f"{r['currency']} {r['total_amount']:,.2f}",
                "Currency": r["currency"],
                "Line Items": format_line_items_summary(r["line_items"]),
            })
        df = pd.DataFrame(display_rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("📑 Detailed View")
        for i, r in enumerate(results):
            with st.expander(f"📄 {r['vendor_name']} — {r['invoice_number']} ({r.get('source_file', 'N/A')})"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Subtotal", f"{r['currency']} {r['subtotal']:,.2f}")
                    st.metric("Tax", f"{r['currency']} {r['tax']:,.2f}")
                with col2:
                    st.metric("Total", f"{r['currency']} {r['total_amount']:,.2f}")
                    st.metric("Currency", r["currency"])
                with col3:
                    st.metric("Date", r["date"])
                    st.metric("Invoice #", r["invoice_number"])
                st.markdown("**Line Items**")
                items = r["line_items"]
                if items:
                    items_df = pd.DataFrame(items)
                    st.dataframe(items_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No line items extracted")
        
        st.divider()
        st.subheader("💾 Download Results")
        col1, col2 = st.columns(2)
        with col1:
            excel_data = create_excel_download(results)
            st.download_button(
                label="📥 Download as Excel (.xlsx)",
                data=excel_data,
                file_name=f"invoice_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
            )
        with col2:
            csv_data = create_csv_download(results)
            st.download_button(
                label="📥 Download as CSV",
                data=csv_data,
                file_name=f"invoice_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )


if __name__ == "__main__":
    main()