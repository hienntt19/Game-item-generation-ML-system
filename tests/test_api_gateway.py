import uuid

from api_gateway.database import GenerationRequest

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


# -----------TEST FOR /update_db/{request_id} endpoint -------------#
# TC5: Update database record successfully
def test_update_db_success(client, mock_db_session):
    mock_db_session.reset_mock()

    existing_record = GenerationRequest(request_id=MOCK_REQUEST_ID, status="Pending")

    mock_db_session.query.return_value.filter.return_value.first.return_value = (
        existing_record
    )

    update_payload = {
        "status": "Completed",
        "image_url": "http://example.com/updated_image.png",
    }

    response = client.put(f"/api/v1/update_db/{MOCK_REQUEST_ID}", json=update_payload)

    assert response.status_code == 200
    assert response.json() == {"message": "Status updated successfully"}

    assert existing_record.status == "Completed"
    assert existing_record.image_url == "http://example.com/updated_image.png"

    mock_db_session.commit.assert_called_once()


# TC6: Update database for non-existent request_id
def test_update_db_not_found(client, mock_db_session):
    mock_db_session.reset_mock()

    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    update_payload = {"status": "Completed"}

    response = client.put(
        "/api/v1/update_db/00000000-0000-0000-0000-000000000000", json=update_payload
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "request_id not found"
    mock_db_session.commit.assert_not_called()
