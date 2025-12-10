
from main import get_target_worksheet_name
import pytest

def test_get_target_worksheet_name():
    assert get_target_worksheet_name("MCP") == "MCP"
    assert get_target_worksheet_name("Trend") == "Trends"
    assert get_target_worksheet_name("Unknown Category") == "AI" # Default

def test_process_post_success(client, mock_gspread, mock_gemini):
    payload = {
        "text": "Check out this amazing new MCP tool for automation!",
        "author": "John Doe",
        "url": "https://linkedin.com/post/123"
    }
    
    response = client.post("/process", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["category"] == "Tool"
    assert data["summary"] == "Test Summary"
    assert data["tab"] == "Tools"
    
    # Verify Gemini was called
    mock_gemini["model"].generate_content.assert_called_once()
    
    # Verify Sheet interaction
    mock_gspread["sh"].worksheet.assert_called_with("Tools")
    mock_gspread["worksheet"].append_row.assert_called_once()

def test_process_post_no_text(client):
    payload = {
        "text": "",
        "author": "John Doe",
        "url": "https://linkedin.com/post/123"
    }
    response = client.post("/process", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "No text provided"

def test_process_post_gemini_failure(client, mock_gspread, mock_gemini):
    # Simulate an exception from Gemini
    mock_gemini["model"].generate_content.side_effect = Exception("API Error")
    
    payload = {
        "text": "Some text",
        "author": "Jane Doe",
        "url": "https://linkedin.com/post/456"
    }
    
    response = client.post("/process", json=payload)
    
    # Should still succeed but with fallback values
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "General_AI" # Fallback
    assert "Error processing" in data["summary"]
    
    # Should log to AI tab
    mock_gspread["sh"].worksheet.assert_called_with("AI")

def test_process_post_sheet_connection_error(client, mock_gspread, mocker):
    # Simulate sh being None (connection failed at startup)
    mocker.patch("main.sh", None)
    
    payload = {
        "text": "Some text",
        "author": "Jane Doe",
        "url": "https://linkedin.com/post/456"
    }
    
    response = client.post("/process", json=payload)
    
    # Should return 503 Service Unavailable
    assert response.status_code == 503
    assert response.json()["detail"] == "Google Sheets connection not active"
