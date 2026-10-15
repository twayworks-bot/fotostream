import io
import time
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app
from app.core.config import settings
from app.services.stream_manager import stream_registry

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def create_dummy_image(color=(120, 180, 240), size=(320, 240)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def test_full_synthesis_and_streaming_e2e(client):
    """End-to-end test: upload images, wait for worker completion, verify video and streaming."""
    # 1. Upload 3 photos
    img1 = ("images", ("photo1.jpg", create_dummy_image((255, 100, 100)), "image/jpeg"))
    img2 = ("images", ("photo2.jpg", create_dummy_image((100, 255, 100)), "image/jpeg"))
    img3 = ("images", ("photo3.jpg", create_dummy_image((100, 100, 255)), "image/jpeg"))

    res = client.post(
        f"/{settings.DEFAULT_PREFIX}/api/v1/jobs",
        files=[img1, img2, img3],
        data={"title": "E2E Slideshow Test"}
    )
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    # 2. Poll until job completes (with timeout 30s)
    max_wait = 30
    start_t = time.time()
    completed = False
    video_id = None

    while time.time() - start_t < max_wait:
        poll_res = client.get(f"/{settings.DEFAULT_PREFIX}/api/v1/jobs/{job_id}")
        assert poll_res.status_code == 200
        job_data = poll_res.json()
        if job_data["status"] == "COMPLETED":
            completed = True
            video_id = job_data["video_id"]
            break
        elif job_data["status"] == "FAILED":
            pytest.fail(f"Job synthesis failed: {job_data.get('error_message')}")
        time.sleep(1)

    assert completed is True, "Job synthesis timed out"
    assert video_id is not None

    # 3. Verify video detail API
    v_res = client.get(f"/{settings.DEFAULT_PREFIX}/api/v1/videos/{video_id}")
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["resolution"] == "1920x1080"
    assert v_data["file_size"] > 0
    # Must be <= 100MB
    assert v_data["file_size"] <= 100 * 1024 * 1024
    # Must be <= 600s
    assert v_data["duration"] <= 600

    # 4. Verify HTTP 206 Partial Content Video Streaming
    stream_url = f"/{settings.DEFAULT_PREFIX}/api/v1/videos/{video_id}/stream"
    range_res = client.get(stream_url, headers={"Range": "bytes=0-1023"})
    assert range_res.status_code == 206
    assert "Content-Range" in range_res.headers
    assert range_res.headers["Content-Range"].startswith("bytes 0-1023/")
    assert len(range_res.content) == 1024

def test_pure_9_16_vertical_video_synthesis(client):
    """Verify that when all photos are 9:16 portrait, video is produced in 1080x1920 vertical format."""
    # 2 vertical photos (9:16 aspect: 180x320)
    p1 = ("images", ("vert1.jpg", create_dummy_image((240, 80, 80), size=(180, 320)), "image/jpeg"))
    p2 = ("images", ("vert2.jpg", create_dummy_image((80, 240, 80), size=(180, 320)), "image/jpeg"))

    res = client.post(
        f"/{settings.DEFAULT_PREFIX}/api/v1/jobs",
        files=[p1, p2],
        data={"title": "Vertical 9:16 Shorts Slideshow"}
    )
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    max_wait = 30
    start_t = time.time()
    video_id = None

    while time.time() - start_t < max_wait:
        poll_res = client.get(f"/{settings.DEFAULT_PREFIX}/api/v1/jobs/{job_id}")
        assert poll_res.status_code == 200
        job_data = poll_res.json()
        if job_data["status"] == "COMPLETED":
            video_id = job_data["video_id"]
            break
        elif job_data["status"] == "FAILED":
            pytest.fail(f"Vertical job synthesis failed: {job_data.get('error_message')}")
        time.sleep(1)

    assert video_id is not None
    v_res = client.get(f"/{settings.DEFAULT_PREFIX}/api/v1/videos/{video_id}")
    assert v_res.status_code == 200
    v_data = v_res.json()
    # Verified: exactly 1080x1920 vertical 9:16 resolution!
    assert v_data["resolution"] == "1080x1920"
    assert v_data["file_size"] > 0

def test_non_9_16_portrait_photos_synthesizes_vertical_no_crop(client):
    """Verify that non-9:16 portrait photos (e.g. 3:4 or 4:5) also produce 9:16 vertical video without cropping."""
    # 2 portrait photos (3:4 aspect: 240x320)
    p1 = ("images", ("portrait_3_4_a.jpg", create_dummy_image((120, 200, 80), size=(240, 320)), "image/jpeg"))
    p2 = ("images", ("portrait_3_4_b.jpg", create_dummy_image((80, 120, 200), size=(240, 320)), "image/jpeg"))

    res = client.post(
        f"/{settings.DEFAULT_PREFIX}/api/v1/jobs",
        files=[p1, p2],
        data={"title": "3:4 Portrait to 9:16 Vertical Video"}
    )
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    max_wait = 30
    start_t = time.time()
    video_id = None

    while time.time() - start_t < max_wait:
        poll_res = client.get(f"/{settings.DEFAULT_PREFIX}/api/v1/jobs/{job_id}")
        assert poll_res.status_code == 200
        job_data = poll_res.json()
        if job_data["status"] == "COMPLETED":
            video_id = job_data["video_id"]
            break
        elif job_data["status"] == "FAILED":
            pytest.fail(f"Job failed: {job_data.get('error_message')}")
        time.sleep(1)

    assert video_id is not None
    v_res = client.get(f"/{settings.DEFAULT_PREFIX}/api/v1/videos/{video_id}")
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["resolution"] == "1080x1920"
    assert v_data["file_size"] > 0


def test_concurrent_streaming_limit(client):
    """Verify that when 10 streaming slots are full, 11th request receives HTTP 429."""
    # Temporarily force active streams to 10
    original_streams = stream_registry.current_streams
    stream_registry.current_streams = 10

    try:
        # Request any video stream (or mock existing)
        videos_res = client.get(f"/{settings.DEFAULT_PREFIX}/api/v1/videos")
        videos = videos_res.json().get("videos", [])
        if videos:
            vid = videos[0]["id"]
            res = client.get(f"/{settings.DEFAULT_PREFIX}/api/v1/videos/{vid}/stream")
            assert res.status_code == 429
            assert "Maximum concurrent streaming limit" in res.json()["detail"]
    finally:
        stream_registry.current_streams = original_streams
