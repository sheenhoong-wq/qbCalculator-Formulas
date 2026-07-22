import math

from PIL import Image

from app.features import cosine, extract
from tests.conftest import make_image


def test_deterministic(tmp_path):
    img = Image.open(make_image(tmp_path / "a.png", noise_seed=1))
    assert extract(img) == extract(img)


def test_normalized(tmp_path):
    v = extract(Image.open(make_image(tmp_path / "a.png", noise_seed=1)))
    assert abs(math.sqrt(sum(x * x for x in v)) - 1.0) < 1e-6


def test_similar_images_high_cosine(tmp_path):
    a = extract(Image.open(make_image(tmp_path / "a.png", color=(20, 120, 40), noise_seed=1)))
    b = extract(Image.open(make_image(tmp_path / "b.png", color=(22, 118, 42), noise_seed=2)))
    c = extract(Image.open(make_image(tmp_path / "c.png", color=(240, 240, 250), noise_seed=3)))
    assert cosine(a, b) > cosine(a, c)
    assert cosine(a, b) > 0.95
