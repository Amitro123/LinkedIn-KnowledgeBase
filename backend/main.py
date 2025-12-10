import os
import datetime
import json
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import gspread
import google.generativeai as genai
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

Summary: Write a Hebrew summary focusing on the function/value (max 2 sentences).
Category: Classify strictly into ONE of these: ['MCP', 'RAG', 'Repo', 'Tool', 'Automation', 'Learning', 'General_AI'].
Author: Extract the author name from the post content if possible, otherwise use provided default.

Output JSON: { "summary": "...", "category": "...", "author": "..." }
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
        'General_AI': 'AI',
        'Trends': 'Trends'
    }
    return mapping.get(category, 'AI') # Default to 'AI'

@app.post("/process")
async def process_post(data: PostData):
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
        summary = "Error processing using AI. Raw text: " + data.text[:50] + "..."
        category = "General_AI"

    # 2. Save to Google Sheets
    if sh:
        try:
            target_tab_name = get_target_worksheet_name(category)
            
            # Try to get worksheet
            try:
                worksheet = sh.worksheet(target_tab_name)
            except gspread.WorksheetNotFound:
                # If tab doesn't exist, maybe create it or fallback to 'AI'?
                # Requirement implies tabs exist. Let's try to create or fail safely.
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
            
        except Exception as e:
            print(f"GSpread Error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save to Google Sheets: {str(e)}")
    else:
        print("Spreadsheet not available. Skipping save.")
        raise HTTPException(status_code=503, detail="Google Sheets connection not active")

    return {"status": "success", "category": category, "summary": summary, "tab": target_tab_name}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
