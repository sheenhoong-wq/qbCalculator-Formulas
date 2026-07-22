from PIL import Image

from app import learning
from app.features import extract
from tests.conftest import make_image


def img_vec(tmp_path, name, color, seed):
    return extract(Image.open(make_image(tmp_path / name, color=color, noise_seed=seed)))


def test_empty_store_returns_none(tmp_path):
    v = img_vec(tmp_path, "a.png", (10, 200, 10), 1)
    assert learning.predict("scene", v) is None


def test_learns_from_correction(tmp_path):
    # 教：三张绿色调照片 = 草地
    for i in range(3):
        learning.learn("scene", "草地", img_vec(tmp_path, f"g{i}.png", (20, 150 + i * 5, 30), i))
    # 一张新的相似照片应命中"草地"
    hit = learning.predict("scene", img_vec(tmp_path, "new.png", (22, 152, 32), 99))
    assert hit is not None
    label, conf = hit
    assert label == "草地"
    assert conf > 0.5


def test_dissimilar_photo_not_matched(tmp_path):
    learning.learn("scene", "草地", img_vec(tmp_path, "g.png", (20, 150, 30), 1))
    # 全白照片与草地训练样本差异大，不应盲目套用学到的标签
    hit = learning.predict("scene", img_vec(tmp_path, "w.png", (250, 250, 250), 2))
    assert hit is None or hit[0] != "草地" or hit[1] < 0.9


def test_correction_overrides_earlier_teaching(tmp_path):
    # 先教错，再用更多正确样本纠正——多数票应翻转
    v_base = (30, 60, 180)
    learning.learn("category", "风景", img_vec(tmp_path, "a.png", v_base, 1))
    for i in range(4):
        learning.learn("category", "海洋", img_vec(tmp_path, f"b{i}.png", v_base, 10 + i))
    hit = learning.predict("category", img_vec(tmp_path, "q.png", v_base, 99))
    assert hit is not None and hit[0] == "海洋"
