
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import sys
import os

# Add backend directory to path so we can import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, get_target_worksheet_name

# Use a test client
@pytest.fixture
def client():
    return TestClient(app)

# Mock gspread completely
@pytest.fixture
def mock_gspread(mocker):
    mock_gc = MagicMock()
    mock_sh = MagicMock()
    mock_worksheet = MagicMock()
    
    # Setup the chain: gc.open_by_key -> sh.worksheet -> worksheet
    mock_gc.open_by_key.return_value = mock_sh
    mock_sh.worksheet.return_value = mock_worksheet
    mock_sh.add_worksheet.return_value = mock_worksheet
    
    # Mock the global variables in main
    mocker.patch("main.gc", mock_gc)
    mocker.patch("main.sh", mock_sh)
    
    return {
        "gc": mock_gc,
        "sh": mock_sh,
        "worksheet": mock_worksheet
    }

# Mock Gemini
@pytest.fixture
def mock_gemini(mocker):
    mock_model = MagicMock()
    mock_response = MagicMock()
    
    # Valid JSON response
    mock_response.text = '```json\n{"summary": "Test Summary", "category": "Tool", "author": "Test Author"}\n```'
    mock_model.generate_content.return_value = mock_response
    
    mocker.patch("google.generativeai.GenerativeModel", return_value=mock_model)
    
    return {
        "model": mock_model,
        "response": mock_response
    }
