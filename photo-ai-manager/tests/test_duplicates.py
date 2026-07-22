import shutil

from fastapi.testclient import TestClient

from app.main import app


def client():
    return TestClient(app)


def upload(c, path, name=None):
    with open(path, "rb") as f:
        r = c.post("/api/photos/upload", files=[("files", (name or path.name, f, "image/png"))])
    assert r.status_code == 200
    return r.json()["imported"][0]


def test_exact_duplicate_detection(tmp_path):
    from tests.conftest import make_image
    a = make_image(tmp_path / "a.png", noise_seed=1)
    b = tmp_path / "b.png"
    shutil.copy(a, b)

    c = client()
    r1 = upload(c, a)
    r2 = upload(c, b)
    assert r1["duplicate_of"] is None
    assert r2["duplicate_of"] == r1["id"]

    dups = c.get("/api/duplicates").json()
    assert len(dups["exact"]) == 1
    ids = {p["id"] for p in dups["exact"][0]["photos"]}
    assert ids == {r1["id"], r2["id"]}


def test_near_duplicate_detection(tmp_path):
    from PIL import Image
    from tests.conftest import make_image
    a = make_image(tmp_path / "a.png", noise_seed=5, size=(400, 300))
    # 缩放后重新保存 → 内容相同但字节不同 → 近似重复
    img = Image.open(a).resize((200, 150))
    b = tmp_path / "b.png"
    img.save(b)

    c = client()
    upload(c, a)
    upload(c, b)
    dups = c.get("/api/duplicates").json()
    assert len(dups["near"]) == 1
    assert len(dups["near"][0]["photos"]) == 2
