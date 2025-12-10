# LinkedIn Knowledge Base Saver

A powerful automation tool that captures LinkedIn posts, summarizes them using Google Gemini AI, and saves them to a structured Google Sheet.

## 🚀 Features

- **Chrome Extension**: Adds a "Save to Knowledge Base" option to the right-click context menu.
- **AI-Powered**: Uses Google Gemini (1.5 Flash) to:
  - Summarize content in Hebrew.
  - Classify posts (MCP, RAG, Repo, Tool, Automation, Learning, AI).
  - Extract Author and URL.
- **Smart Routing**: Automatically saves posts to specific tabs in Google Sheets based on the AI classification.
- **Duplicate Prevention**: (Basic logic via appending new rows).

## 🛠️ Architecture

- **Client**: Chrome Extension (Manifest V3)
- **Server**: Python FastAPI (`localhost:8000`)
- **AI Engine**: Google Gemini API
- **Database**: Google Sheets

## 📋 Prerequisites

- Python 3.9+
- Google Chrome
- **Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/))
- **Google Cloud Service Account** (with Sheets & Drive API enabled)

## 📦 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Amitro123/LinkedIn-KnowledgeBase.git
cd LinkedIn-KnowledgeBase
```

### 2. Backend Setup
Navigate to the backend directory and install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

**Configuration**:
1. Copy `.env.example` to `.env`.
2. Add your `GEMINI_API_KEY`.
3. Add your Google Service Account JSON file as `service_account.json` in the `backend/` folder.
4. Update `GOOGLE_CREDENTIALS_PATH` in `.env` if named differently.

**Start the Server**:
```bash
uvicorn main:app --reload
```

### 3. Extension Setup
1. Open Chrome and navigate to `chrome://extensions`.
2. Enable **Developer Mode** (top right).
3. Click **Load unpacked**.
4. Select the `extension/` directory from this repository.

## 📝 Usage

1. Browse LinkedIn.
2. Find a post you want to save.
3. **Right-click** on the post text or area.
4. Select **Save to Knowledge Base**.
5. You will receive an alert confirmation once the post is processed and saved.

## 🔧 Google Sheets Setup

The system requires a Google Sheet with the following tabs:
- `MCP`
- `RAG`
- `Repos in github`
- `Tools`
- `Automation flow`
- `Learning`
- `AI`

**Important**: You must share your Google Sheet with the `client_email` found in your `service_account.json` file (give "Editor" access).

## 📄 License
MIT
