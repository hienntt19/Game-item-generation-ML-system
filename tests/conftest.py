import os
import sys
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api_gateway.database import GenerationRequest, get_db
from api_gateway.main import app
from api_gateway.services import get_mq_channel


@pytest.fixture()
def sample_request():
    return {
        "prompt": "tsuki_advtr, a samoyed dog smiling, white background, thick outlines, pastel color, cartoon style, hand-drawn, 2D icon, game item, 2D game style, minimalist",
        "negative_prompt": "",
        "num_inference_steps": 50,
        "guidance_scale": 7.5,
        "seed": 50,
    }


@pytest.fixture()
def mock_db_session():
    return MagicMock(spec=Session)


@pytest.fixture
def mock_mq_channel():
    return MagicMock()


@pytest.fixture()
def client(mock_db_session, mock_mq_channel):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_mq_channel] = lambda: mock_mq_channel

    test_client = TestClient(app)

    yield test_client

    app.dependency_overrides.clear()
