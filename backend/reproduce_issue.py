
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
import re

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Try to load from ../.env if not found
    load_dotenv("../.env")
    api_key = os.getenv("GEMINI_API_KEY")

print(f"API Key present: {bool(api_key)}")
genai.configure(api_key=api_key)

text = """
𝐘𝐨𝐮 𝐭𝐲𝐩𝐞 𝐚 𝐬𝐞𝐧𝐭𝐞𝐧𝐜𝐞. 𝐂𝐡𝐚𝐭𝐆𝐏𝐓 𝐚𝐧𝐬𝐰𝐞𝐫𝐬 𝐢𝐧𝐬𝐭𝐚𝐧𝐭𝐥𝐲.
But what just happened in those milliseconds?

Most people think it is magic. It is not. It is Transformers.
And understanding this architecture is the difference between using AI and building with it.
"""

SYSTEM_PROMPT = """
Analyze this LinkedIn post.
1. **Summary**: Write a concise ENGLISH summary focusing on the tool's value/function. (Max 2 sentences)
2. **Category**: Classify strictly into ONE: ['MCP', 'RAG', 'Repo', 'Tool', 'Automation', 'Learning', 'Trend', 'General_AI'].
3. **Author**: Extract the author name.
4. **Verdict**: If no external link is found, treat as 'Trend' or 'Learning'.

Output valid JSON: { "summary": "...", "category": "...", "author": "..." }
"""

model = genai.GenerativeModel('gemini-2.5-flash')

try:
    print("Sending request...")
    response = model.generate_content(f"{SYSTEM_PROMPT}\n\nInput Post Text:\n{text}")
    print("Response received.")
    print(f"Raw response text: {response.text}")
    
    text_response = response.text.strip()
    json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
    if json_match:
        text_response = json_match.group(0)
    
    data = json.loads(text_response)
    print("Parsed JSON:", data)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
