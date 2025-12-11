# 🧠 LinkedIn Brain Node (AI Knowledge Base)
![Project Architecture](assets/banner.png)

**Turn your LinkedIn "Saved Posts" graveyard into an active, querying AI brain.**

This project is a developer-focused automation pipeline that captures LinkedIn posts via a Chrome Extension, processes them using **Google Gemini 2.5 Flash**, and structures them into a Google Sheet designed specifically to feed a **Google Gem (Custom AI Agent)** for RAG (Retrieval-Augmented Generation).

> **⚠️ Note for Users**: This is a **Developer Tool (Open Source)**. To use it, you must run a local Python server and set up your own Google Cloud credentials. It is **not** a "Plug & Play" extension from the Chrome Store.

---

## 🚀 The Flow

1. **Ingestion**: You right-click a post → "Save to Knowledge Base".

2. **Processing**: The Python backend analyzes the post using **Gemini 2.5 Flash** to extract:
   - **Summary**: Concise, value-driven summary (English/Hebrew).
   - **Category**: Smart classification (RAG, Tools, Agents, Trends, etc.).
   - **Tech Details**: External links (GitHub, Docs) & Author.

3. **Storage**: Data is routed to specific tabs in a Google Sheet.

4. **Retrieval (The Magic 💎)**: You connect **Google Gems** to this Sheet to chat with your knowledge base (e.g., *"What is the latest RAG tool I saved?"*).

---

## ✨ Features

### Smart Chrome Extension:
- Context-aware scraping (finds links in the post body **OR** the first comment).
- Ignores internal LinkedIn clutter.

### Advanced AI Logic:
- Uses **Gemini 2.5 Flash** for high speed and low latency.
- Handles edge cases (no link found) and sanitizes JSON outputs.
- Bypasses safety filters for professional slang.

### Robust Backend:
- **FastAPI** server with Background Tasks optimization.
- **Global Connection Reuse** for `gspread` (Speed optimization).
- **Error Handling**: Never crashes; logs failures to a local `activity.log` AND a `System_Logs` tab in the Sheet.

---

## 🛠️ Architecture

- **Client**: Chrome Extension (Manifest V3)
- **Server**: Python FastAPI (localhost:8000 or Render for prod)
- **AI Model**: Google Gemini 2.5 Flash
- **Database**: Google Sheets (Structured for RAG)

---

## 📋 Prerequisites

- Python 3.9+
- Google Chrome (Developer Mode enabled)
- **Gemini API Key** (Get it from [Google AI Studio](https://aistudio.google.com/))
- **Google Cloud Service Account** (JSON file) with **Google Sheets API** & **Google Drive API** enabled.

---

## 📦 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Amitro123/LinkedIn-KnowledgeBase.git
cd LinkedIn-KnowledgeBase
```

### 2. Backend Setup
Navigate to the backend directory:

**Windows (PowerShell):**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
```

**Mac/Linux:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Configuration (.env):**  
Create a `.env` file in the `backend/` folder:
```
GEMINI_API_KEY="your_key_here"
GOOGLE_CREDENTIALS_PATH="service_account.json"
SPREADSHEET_ID="your_google_sheet_id"
```

- Place your `service_account.json` file inside the `backend/` folder.
- **CRITICAL**: Share your Google Sheet with the `client_email` found inside your `service_account.json` (Give it "Editor" permission).

**Start the Server:**
```bash
uvicorn main:app --reload
```

### 3. Extension Setup
1. Open Chrome → `chrome://extensions`.
2. Enable **Developer Mode** (top right).
3. Click **Load unpacked**.
4. Select the `extension/` directory from this repository.

---

## 🔧 Google Sheets Structure

Create a new Google Sheet and create these **exact tabs** (case sensitive for the router):

- `AI` (Default)
- `MCP`
- `RAG`
- `Repos in github`
- `Tools`
- `Automation flow`
- `Learning`
- `Trends`
- `System_Logs` (For error tracking)

**Header Row (Row 1)** for all content tabs:  
`Date | Link | Name | Function | Category`

**Header Row for System_Logs**:  
`Date | Timestamp | Failed_URL | Error_Message`

---

## 💎 Phase 2: Connecting Google Gems (Retrieval)

To complete the cycle, go to **Gemini Advanced** and create a new Gem:

1. **Name**: My Knowledge Brain

2. **Instructions**:
   ```
   You are my technical knowledge assistant. Your source of truth is the Google Sheet named '[Your Sheet Name]'. When I ask a question, search the relevant tabs (Tools, RAG, etc.) and provide answers based ONLY on the rows in that sheet. Always provide the URL from the 'Link' column.
   ```

3. **Extension**: Enable "Google Workspace" extension for this Gem.

Now you can ask: *"Show me the latest automation tools I saved."*

---

## 📄 License
MIT License. Feel free to fork and improve!
