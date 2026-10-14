import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app
from app.core.config import settings

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def create_dummy_image_bytes(color=(255, 0, 0), size=(100, 100)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def test_system_status(client):
    res = client.get(f"{settings.url_prefix}/api/v1/system/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["workers"]["max"] == 3
    assert data["streams"]["max"] == 10
    assert data["ffmpeg_available"] is True

def test_container_healthcheck_endpoint(client):
    """Test healthcheck endpoint used by Docker HEALTHCHECK command."""
    # Prefix-based endpoint: http://localhost:5000{prefix}/api/status
    res_prefix = client.get(f"{settings.url_prefix}/api/status")
    assert res_prefix.status_code == 200
    assert res_prefix.json()["status"] == "healthy"

    # Root fallback endpoint: http://localhost:5000/api/status
    res_root = client.get("/api/status")
    assert res_root.status_code == 200
    assert res_root.json()["status"] == "healthy"

def test_root_redirect(client):
    """Test root redirect to base prefix dashboard."""
    res = client.get("/", follow_redirects=False)
    assert res.status_code == 307
    assert res.headers["location"] == settings.url_prefix

def test_bgm_list_and_bright_presets(client):
    res = client.get(f"{settings.url_prefix}/api/v1/bgm")
    assert res.status_code == 200
    data = res.json()
    assert "tracks" in data
    assert data["total"] >= 5
    titles = [t["title"] for t in data["tracks"]]
    assert "Sunny Morning Walk" in titles
    assert "Upbeat Joyful Ukulele" in titles
    assert "Playful Summer Smile" in titles

def test_delete_bgm_track(client):
    """Test registering a custom BGM track and deleting it."""
    dummy_audio = io.BytesIO(b"ID3" + b"\x00" * 200)
    upload_res = client.post(
        f"{settings.url_prefix}/api/v1/bgm",
        files={"file": ("temp_test_bgm.mp3", dummy_audio, "audio/mpeg")},
        data={"title": "Temporary Test BGM Track", "mood": "Test", "artist": "Tester"}
    )
    assert upload_res.status_code == 201
    track_id = upload_res.json()["id"]

    # Verify track is present
    list_res = client.get(f"{settings.url_prefix}/api/v1/bgm")
    assert any(t["id"] == track_id for t in list_res.json()["tracks"])

    # Delete track
    del_res = client.delete(f"{settings.url_prefix}/api/v1/bgm/{track_id}")
    assert del_res.status_code == 200
    assert del_res.json()["message"] == "BGM track deleted successfully"

    # Verify track is removed
    list_after = client.get(f"{settings.url_prefix}/api/v1/bgm")
    assert not any(t["id"] == track_id for t in list_after.json()["tracks"])

    # Deleting again returns 404
    del_404 = client.delete(f"{settings.url_prefix}/api/v1/bgm/{track_id}")
    assert del_404.status_code == 404

def test_dashboard_page(client):
    res = client.get(settings.url_prefix)
    assert res.status_code == 200
    assert "FOTOSTREAM" in res.text
    assert "1080p Standard" in res.text
    assert "동영상 생성 큐 등록" in res.text

def test_job_upload_with_resolution_options(client):
    # Test uploading with default 1080p
    img1 = ("images", ("test1.jpg", create_dummy_image_bytes((255, 100, 100)), "image/jpeg"))
    img2 = ("images", ("test2.jpg", create_dummy_image_bytes((100, 255, 100)), "image/jpeg"))

    res = client.post(
        f"{settings.url_prefix}/api/v1/jobs",
        files=[img1, img2],
        data={"title": "Test Slideshow 1080p Default"}
    )
    assert res.status_code == 202
    data = res.json()
    assert data["resolution"] == "1080p"
    assert data["status"] == "QUEUED"

    # Test uploading with custom 1920p (Max Ultra-HD)
    img3 = ("images", ("test3.jpg", create_dummy_image_bytes((100, 100, 255)), "image/jpeg"))
    res_1920p = client.post(
        f"{settings.url_prefix}/api/v1/jobs",
        files=[img3],
        data={"title": "Test Slideshow 1920p Ultra", "resolution": "1920p"}
    )
    assert res_1920p.status_code == 202
    data_1920p = res_1920p.json()
    assert data_1920p["resolution"] == "1920p"

    # Test invalid resolution rejection
    img4 = ("images", ("test4.jpg", create_dummy_image_bytes((50, 50, 50)), "image/jpeg"))
    res_invalid = client.post(
        f"{settings.url_prefix}/api/v1/jobs",
        files=[img4],
        data={"resolution": "9999p"}
    )
    assert res_invalid.status_code == 400
