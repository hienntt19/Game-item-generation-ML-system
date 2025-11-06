import json
import uuid
from unittest.mock import MagicMock, patch

from api_gateway.database import GenerationRequest
from api_gateway.result_consumer import ResultConsumer

MOCK_REQUEST_ID = uuid.uuid4()


# -------------TEST FOR /generate endpoint -------------#
# TC1: Send valid request successfully
def test_generate_task_success(
    client, mock_db_session, mock_mq_channel, sample_request
):
    mock_db_session.reset_mock()
    mock_mq_channel.reset_mock()

    def set_request_id(db_request_obj):
        db_request_obj.request_id = MOCK_REQUEST_ID

    mock_db_session.refresh.side_effect = set_request_id

    response = client.post("/api/v1/generate", json=sample_request)

    assert response.status_code == 202
    assert response.json() == {"request_id": str(MOCK_REQUEST_ID)}

    mock_db_session.add.assert_called_once()
    added_object = mock_db_session.add.call_args[0][0]
    assert (
        added_object.prompt
        == "tsuki_advtr, a samoyed dog smiling, white background, thick outlines, pastel color, cartoon style, hand-drawn, 2D icon, game item, 2D game style, minimalist"
    )

    mock_db_session.commit.assert_called_once()
    mock_mq_channel.basic_publish.assert_called_once()


# TC2: Send invalid request (missing required field)
def test_generate_task_invalid_request(client, sample_request):
    invalid_request = sample_request.copy()
    del invalid_request["prompt"]

    response = client.post("/api/v1/generate", json=invalid_request)

    assert response.status_code == 422
    assert "detail" in response.json()
    assert response.json()["detail"][0]["msg"] == "Field required"


# -------------TEST FOR /status/{request_id} endpoint -------------#
# TC3: Check status of completed request and get result
def test_get_status_completed(client, mock_db_session):
    mock_db_session.reset_mock()

    mock_db_record = GenerationRequest(
        request_id=MOCK_REQUEST_ID,
        status="Completed",
        image_url="http://example.com/generated_image.png",
    )

    mock_db_session.query.return_value.filter.return_value.first.return_value = (
        mock_db_record
    )

    response = client.get(f"/api/v1/status/{MOCK_REQUEST_ID}")

    assert response.status_code == 200
    assert response.json() == {
        "request_id": str(MOCK_REQUEST_ID),
        "status": "Completed",
        "image_url": "http://example.com/generated_image.png",
    }


# TC4: Check status of request_id that does not exist
def test_get_status_not_found(client, mock_db_session):
    mock_db_session.reset_mock()

    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    response = client.get("/api/v1/status/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


# TC5: Test logic of consumer when receive valid messages and update db successfully
@patch("api_gateway.result_consumer.SessionLocal")
def test_result_consumer_on_message_success(mock_SessionLocal):
    mock_db_session = MagicMock()
    mock_SessionLocal.return_value = mock_db_session

    consumer = ResultConsumer()

    mock_ch = MagicMock()
    mock_method = MagicMock()
    mock_properties = MagicMock()

    message_payload = {
        "request_id": str(MOCK_REQUEST_ID),
        "status": "Completed",
        "image_url": "http://example.com/new_image.png",
    }
    body = json.dumps(message_payload).encode("utf-8")

    consumer._on_message(mock_ch, mock_method, mock_properties, body)

    mock_SessionLocal.assert_called_once()

    mock_db_session.query.assert_called_once_with(GenerationRequest)
    mock_db_session.query.return_value.filter.assert_called_once()

    update_call = mock_db_session.query.return_value.filter.return_value.update
    update_call.assert_called_once_with(
        {
            "status": "Completed",
            "image_url": "http://example.com/new_image.png",
        }
    )

    mock_db_session.commit.assert_called_once()
    mock_db_session.close.assert_called_once()

    mock_ch.basic_ack.assert_called_once()


# TC6: Test logic of consumer when getting error
@patch("api_gateway.result_consumer.SessionLocal")
def test_result_consumer_on_message_error(mock_SessionLocal):
    mock_db_session = MagicMock()
    mock_SessionLocal.return_value = mock_db_session

    consumer = ResultConsumer()
    mock_ch = MagicMock()
    mock_method = MagicMock()
    mock_properties = MagicMock()

    message_payload = {
        "request_id": "this-is-not-a-uuid",
        "status": "Failed",
        "image_url": None,
    }
    body = json.dumps(message_payload).encode("utf-8")

    consumer._on_message(mock_ch, mock_method, mock_properties, body)

    mock_SessionLocal.assert_called_once()
    mock_db_session.commit.assert_not_called()
    mock_db_session.close.assert_called_once()

    mock_ch.basic_ack.assert_called_once()
