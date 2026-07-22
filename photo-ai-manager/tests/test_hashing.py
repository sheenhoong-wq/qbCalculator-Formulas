from PIL import Image

from app.hashing import ahash, dhash, hamming, phash
from tests.conftest import make_image


def test_identical_images_same_hash(tmp_path):
    p = make_image(tmp_path / "a.png", noise_seed=1)
    img = Image.open(p)
    assert phash(img) == phash(Image.open(p))
    assert hamming(phash(img), phash(img)) == 0


def _structured_image(size=(400, 300)):
    """渐变 + 色块：模拟真实照片的低频结构（纯噪点是感知哈希的最坏情况）。"""
    from PIL import ImageDraw
    img = Image.new("RGB", size)
    for x in range(size[0]):
        for y in range(size[1]):
            img.putpixel((x, y), (x * 255 // size[0], y * 255 // size[1], 128))
    ImageDraw.Draw(img).rectangle([100, 80, 250, 200], fill=(200, 50, 50))
    return img


def test_resized_image_low_distance(tmp_path):
    img = _structured_image()
    resized = img.resize((200, 150))
    assert hamming(phash(img), phash(resized)) <= 8
    assert hamming(dhash(img), dhash(resized)) <= 6


def test_different_images_high_distance(tmp_path):
    a = Image.open(make_image(tmp_path / "a.png", color=(255, 0, 0), noise_seed=3))
    # 用结构截然不同的图（一半黑一半白）而不是仅换颜色
    b = Image.new("RGB", (320, 240))
    for x in range(320):
        for y in range(240):
            b.putpixel((x, y), (255, 255, 255) if x > 160 else (0, 0, 0))
    assert hamming(phash(a), phash(b)) > 8


def test_hash_hex_format(tmp_path):
    img = Image.open(make_image(tmp_path / "a.png"))
    for h in (ahash(img), dhash(img), phash(img)):
        assert len(h) == 16
        int(h, 16)  # 合法十六进制
