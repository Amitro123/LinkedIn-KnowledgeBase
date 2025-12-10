import os
import sys
import datetime
import json
import logging
import traceback
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import gspread
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core.exceptions import ResourceExhausted
import re
import unicodedata
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup Local Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("activity.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

if not SPREADSHEET_ID:
    raise ValueError("Error: SPREADSHEET_ID is missing from .env file!")

# Initialize Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logging.warning("WARNING: GEMINI_API_KEY not found in .env")

# Define Permissive Safety Settings
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# Global variables for resources
gc: Optional[gspread.Client] = None
sh: Optional[gspread.Spreadsheet] = None

# Global variables for resources
gc: Optional[gspread.Client] = None
sh: Optional[gspread.Spreadsheet] = None

logging.info("Starting up... Connecting to Google Sheets...")
try:
    if GOOGLE_CREDENTIALS_PATH and os.path.exists(GOOGLE_CREDENTIALS_PATH):
        gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_PATH)
        # Open by Key (ID)
        sh = gc.open_by_key(SPREADSHEET_ID)
        logging.info(f"Connected to Spreadsheet ID: {SPREADSHEET_ID}")
    else:
        logging.warning("WARNING: GOOGLE_CREDENTIALS_PATH not found or invalid.")
except Exception as e:
    logging.error(f"Error connecting to Google Sheets: {e}")
    # Fail fast: Re-raise exception to crash if critical connection fails (optional, but requested for optimization/fail-fast)
    # Raising here prevents the app from starting without a DB connection.
    raise e

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PostData(BaseModel):
    text: str
    author: str
    url: str

# Gemini System Prompt
# Gemini System Prompt
SYSTEM_PROMPT = """
Analyze this LinkedIn post.
1. **Summary**: Write a concise ENGLISH summary focusing on the tool's value/function. (Max 2 sentences)
2. **Category**: Classify strictly into ONE: ['MCP', 'RAG', 'Repo', 'Tool', 'Automation', 'Learning', 'Trend', 'General_AI'].
3. **Author**: Extract the author name.
4. **Verdict**: If no external link is found, treat as 'Trend' or 'Learning'.

Output valid JSON: { "summary": "...", "category": "...", "author": "..." }
"""

def get_target_worksheet_name(category: str) -> str:
    """Routes category to specific tab name."""
    mapping = {
        'MCP': 'MCP',
        'RAG': 'RAG',
        'Repo': 'Repos in github',
        'Tool': 'Tools',
        'Automation': 'Automation flow',
        'Learning': 'Learning',
        'Trend': 'Trends', # Note: Prompt says 'Trend', Sheet says 'Trends'
        'General_AI': 'AI'
    }
    return mapping.get(category, 'AI') # Default to 'AI'

def clean_text(text: str) -> str:
    """Normalize text to remove weird unicode characters (like mathematical bold)."""
    if not text:
        return ""
    # Normalize NFKD to decompose characters (e.g. 𝐇 -> H)
    normalized = unicodedata.normalize('NFKD', text)
    # Filter non-printable characters if needed, but usually just encoding to ASCII and back works or just keeping it normalized
    return normalized

def log_error_to_sheet(failed_url: str, error_msg: str):
    """Logs error to System_Logs tab in Google Sheets."""
    if not sh:
        return
    
    try:
        try:
            worksheet = sh.worksheet("System_Logs")
        except gspread.WorksheetNotFound:
            worksheet = sh.add_worksheet(title="System_Logs", rows=1000, cols=5)
            worksheet.append_row(["Date", "Timestamp", "Failed_URL", "Error_Message"])
            
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        worksheet.append_row([today, timestamp, failed_url, str(error_msg)])
    except Exception as e:
        # If logging to sheet fails, rely on local log
        logging.error(f"Failed to log to System_Logs sheet: {e}")

@app.post("/process")
async def process_post(data: PostData):
    try:
        if not data.text:
           raise HTTPException(status_code=400, detail="No text provided")
        
        logging.info(f"Received post from {data.author}")
        
        # 1. Call Gemini
        category = "General_AI"
        summary = ""
        author_ai = data.author # Fallback
        
        try:
            # Normalize inputs
            clean_author = clean_text(data.author)
            clean_url = clean_text(data.url)
            clean_post_text = clean_text(data.text)
            
            prompt = f"{SYSTEM_PROMPT}\n\nInput Post Author: {clean_author}\nInput Post URL: {clean_url}\nInput Post Text:\n{clean_post_text}"
            
            try:
                # Try primary model (2.5-flash)
                model = genai.GenerativeModel('gemini-2.5-flash-lite')
                response = model.generate_content(prompt, safety_settings=safety_settings)
            except ResourceExhausted:
                # Fallback to 1.5-flash if quota exceeded
                logging.warning("Quota reached for gemini-2.5-flash-lite. Falling back to gemini-1.5-flash.")
                model = genai.GenerativeModel('gemini-2.5-flash-lite')
                response = model.generate_content(prompt, safety_settings=safety_settings)
            
            # Clean response to ensure json
            text_response = response.text.strip()
            
            # Regex to extract JSON block
            json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
            if json_match:
                text_response = json_match.group(0)
                
            ai_data = json.loads(text_response)
            
            category = ai_data.get("category", "General_AI")
            summary = ai_data.get("summary", "")
            # Use AI extracted author if valid, else fallback to scraper author
            if ai_data.get("author") and ai_data.get("author") != "Unknown Author":
                author_ai = ai_data.get("author")
                
            logging.info(f"AI Result - Category: {category}, Summary: {summary}")
    
        except Exception as e:
            logging.error(f"Gemini Error: {e}")
            logging.error(f"Gemini Processing Error: {traceback.format_exc()}")
            # Sanitize text for logging to prevent encoding errors
            safe_text = clean_text(data.text[:50])
            summary = "Error processing using AI. Raw text: " + safe_text + "..."
            category = "General_AI"
            # We don't raise here, we try to save what we have or log if critical
    
        # 2. Save to Google Sheets
        if not sh:
            logging.error("Spreadsheet not available. Skipping save.")
            raise HTTPException(status_code=503, detail="Google Sheets connection not active")

        # If we reach here, sh is available
        target_tab_name = get_target_worksheet_name(category)
        
        # Try to get worksheet
        try:
            worksheet = sh.worksheet(target_tab_name)
        except gspread.WorksheetNotFound:
            # If tab doesn't exist, maybe create it or fallback to 'AI'?
            logging.info(f"Tab '{target_tab_name}' not found. Attempting to create.")
            worksheet = sh.add_worksheet(title=target_tab_name, rows=100, cols=10)
            # Add headers if new
            worksheet.append_row(["Date", "Link", "Name", "Function", "Category"])

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Columns: [Date, Link, Name (Author), Function (Summary), Category]
        row = [
            today,
            data.url,
            author_ai,
            summary,
            category
        ]
        
        worksheet.append_row(row)
        logging.info(f"Row appended to tab '{target_tab_name}'.")
    
        return {"status": "success", "category": category, "summary": summary, "tab": target_tab_name}

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status codes
        raise
    except Exception as e:
        # GLOBAL CATCH-ALL for unexpected errors
        error_msg = f"Fatal Error in process_post: {e}"
        logging.error(error_msg)
        logging.exception("Fatal error in process_post")
        
        # Log to Google Sheet System_Logs
        log_error_to_sheet(data.url, str(e))
        
        # Return proper HTTP error status
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
