import os
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
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup Local Logging
logging.basicConfig(
    filename='activity.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
# CRITICAL: Specific Spreadsheet ID provided by user
SPREADSHEET_ID = "1wWktmD3QEHIlV9ct_NH_i0UQ5ceyxMrMTTidihBmoSU"

# Initialize Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY not found in .env")

# Global variables for resources
gc: Optional[gspread.Client] = None
sh: Optional[gspread.Spreadsheet] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    global gc, sh
    
    print("Starting up... Connecting to Google Sheets...")
    try:
        if GOOGLE_CREDENTIALS_PATH and os.path.exists(GOOGLE_CREDENTIALS_PATH):
            gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_PATH)
            # Open by Key (ID)
            sh = gc.open_by_key(SPREADSHEET_ID)
            print(f"Connected to Spreadsheet ID: {SPREADSHEET_ID}")
        else:
            print("WARNING: GOOGLE_CREDENTIALS_PATH not found or invalid.")
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        logging.error(f"Startup Connection Error: {traceback.format_exc()}")
    
    yield
    # Shutdown logic
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

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
SYSTEM_PROMPT = """
Analyze this LinkedIn post.

Summary: Write a concise English summary focusing on value/function (max 2 sentences).
Category: Classify strictly into ONE of these: ['MCP', 'RAG', 'Repo', 'Tool', 'Automation', 'Learning', 'Trend', 'General_AI'].
Author: Extract the author name.

Verdict: If no external link is found in text or comments, assume it is a 'Trend' or 'Learning' post. 
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
        
        print(f"Received post from {data.author}")
        
        # 1. Call Gemini
        category = "General_AI"
        summary = ""
        author_ai = data.author # Fallback
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(f"{SYSTEM_PROMPT}\n\nInput Post Author: {data.author}\nInput Post URL: {data.url}\nInput Post Text:\n{data.text}")
            
            # Clean response to ensure json
            text_response = response.text.strip()
            if text_response.startswith("```json"):
                text_response = text_response[7:-3].strip()
            elif text_response.startswith("```"):
                text_response = text_response[3:-3].strip()
                
            ai_data = json.loads(text_response)
            
            category = ai_data.get("category", "General_AI")
            summary = ai_data.get("summary", "")
            # Use AI extracted author if valid, else fallback to scraper author
            if ai_data.get("author") and ai_data.get("author") != "Unknown Author":
                author_ai = ai_data.get("author")
                
            print(f"AI Result - Category: {category}, Summary: {summary}")
    
        except Exception as e:
            print(f"Gemini Error: {e}")
            logging.error(f"Gemini Processing Error: {traceback.format_exc()}")
            summary = "Error processing using AI. Raw text: " + data.text[:50] + "..."
            category = "General_AI"
            # We don't raise here, we try to save what we have or log if critical
    
        # 2. Save to Google Sheets
        if sh:
            target_tab_name = get_target_worksheet_name(category)
            
            # Try to get worksheet
            try:
                worksheet = sh.worksheet(target_tab_name)
            except gspread.WorksheetNotFound:
                # If tab doesn't exist, maybe create it or fallback to 'AI'?
                print(f"Tab '{target_tab_name}' not found. Attempting to create.")
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
            print(f"Row appended to tab '{target_tab_name}'.")
                
        else:
            print("Spreadsheet not available. Skipping save.")
            raise HTTPException(status_code=503, detail="Google Sheets connection not active")
    
        return {"status": "success", "category": category, "summary": summary, "tab": target_tab_name}

    except Exception as e:
        # GLOBAL CATCH-ALL
        error_msg = f"Fatal Error in process_post: {str(e)}"
        print(error_msg)
        logging.error(traceback.format_exc())
        
        # Log to Google Sheet System_Logs
        log_error_to_sheet(data.url, str(e))
        
        # Do not crash the client, return a 500 but handled
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
