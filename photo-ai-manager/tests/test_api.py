from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import make_image


def client():
    return TestClient(app)


def upload(c, path):
    with open(path, "rb") as f:
        r = c.post("/api/photos/upload", files=[("files", (path.name, f, "image/png"))])
    assert r.status_code == 200
    return r.json()["imported"][0]


def test_upload_classifies_all_dimensions(tmp_path):
    c = client()
    result = upload(c, make_image(tmp_path / "a.png", color=(20, 150, 30), noise_seed=1))
    assert set(result["labels"].keys()) == {"person", "scene", "category"}
    for r in result["labels"].values():
        assert r["label"]
        assert r["source"] in ("ai", "learned")


def test_correction_learns_and_repropagates(tmp_path):
    c = client()
    # 上传 4 张相似的蓝色调照片
    ids = [
        upload(c, make_image(tmp_path / f"{i}.png", color=(30, 60, 200), noise_seed=i))["id"]
        for i in range(4)
    ]
    # 纠正第一张为"海洋"
    r = c.post(f"/api/photos/{ids[0]}/label",
               json={"dimension": "category", "label": "海洋"})
    assert r.status_code == 200
    body = r.json()
    assert body["new"] == "海洋"
    # 学习后其余相似照片应被自动更新为学习结果
    assert body["repropagated"] >= 1

    photos = {p["id"]: p for p in c.get("/api/photos").json()["photos"]}
    assert photos[ids[0]]["labels"]["category"]["label"] == "海洋"
    assert photos[ids[0]]["labels"]["category"]["source"] == "user"
    learned = [ids[i] for i in range(1, 4)
               if photos[ids[i]]["labels"]["category"]["label"] == "海洋"]
    assert learned, "相似照片应通过学习获得新标签"

    # 新上传的相似照片应直接命中学习层
    new = upload(c, make_image(tmp_path / "new.png", color=(31, 61, 201), noise_seed=42))
    assert new["labels"]["category"]["label"] == "海洋"
    assert new["labels"]["category"]["source"] == "learned"


def test_confirm_feeds_learning(tmp_path):
    c = client()
    pid = upload(c, make_image(tmp_path / "a.png", color=(20, 150, 30), noise_seed=1))["id"]
    r = c.post(f"/api/photos/{pid}/confirm", json={"dimension": "scene"})
    assert r.status_code == 200
    stats = c.get("/api/stats").json()
    assert stats["training_examples"] == 1


def test_user_label_not_overwritten(tmp_path):
    c = client()
    ids = [
        upload(c, make_image(tmp_path / f"{i}.png", color=(200, 40, 40), noise_seed=i))["id"]
        for i in range(3)
    ]
    # 手动标注第 2 张为"日落"
    c.post(f"/api/photos/{ids[1]}/label", json={"dimension": "scene", "label": "日落"})
    # 再教别的照片为"火焰"——用户标注的"日落"不能被覆盖
    c.post(f"/api/photos/{ids[0]}/label", json={"dimension": "scene", "label": "火焰"})
    photos = {p["id"]: p for p in c.get("/api/photos").json()["photos"]}
    assert photos[ids[1]]["labels"]["scene"]["label"] == "日落"
    assert photos[ids[1]]["labels"]["scene"]["source"] == "user"


def test_labels_and_stats_endpoints(tmp_path):
    c = client()
    pid = upload(c, make_image(tmp_path / "a.png", noise_seed=1))["id"]
    c.post(f"/api/photos/{pid}/label", json={"dimension": "person", "label": "小明"})
    labels = c.get("/api/labels").json()
    assert "小明" in labels["person"]
    stats = c.get("/api/stats").json()
    assert stats["photos"] == 1
    assert stats["corrections"] == 1


def test_delete_photo(tmp_path):
    c = client()
    pid = upload(c, make_image(tmp_path / "a.png", noise_seed=1))["id"]
    assert c.delete(f"/api/photos/{pid}").status_code == 200
    assert c.get("/api/photos").json()["photos"] == []
    assert c.get(f"/api/photos/{pid}/thumb").status_code == 404


def test_invalid_requests(tmp_path):
    c = client()
    assert c.post("/api/photos/999/label",
                  json={"dimension": "scene", "label": "x"}).status_code == 404
    pid = upload(c, make_image(tmp_path / "a.png", noise_seed=1))["id"]
    assert c.post(f"/api/photos/{pid}/label",
                  json={"dimension": "bad", "label": "x"}).status_code == 400
    assert c.post(f"/api/photos/{pid}/label",
                  json={"dimension": "scene", "label": "  "}).status_code == 400
