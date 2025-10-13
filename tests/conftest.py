import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_gateway.api_gateway import app, get_db
from api_gateway.models import GenerationRequest

@pytest.fixture()
def sample_request():
    return {
        "prompt": "tsuki_advtr, a samoyed dog smiling, white background, thick outlines, pastel color, cartoon style, hand-drawn, 2D icon, game item, 2D game style, minimalist",
        "negative_prompt": "",
        "num_inference_steps": 50,
        "guidance_scale": 7.5,
        "seed": 50,
    }
    

@pytest.fixture(scope="module")
def mock_db_session():
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.update.return_value = None
    yield db
    

@pytest.fixture(scope="module")
def client(mock_db_session):
    def override_get_db():
        try: 
            yield mock_db_session
        finally:
            pass
        
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
        
    del app.dependency_overrides[get_db]
    

