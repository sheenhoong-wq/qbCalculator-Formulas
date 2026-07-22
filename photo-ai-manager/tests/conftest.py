import os
import sys

import pytest
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["PHOTO_AI_DISABLE_CLAUDE"] = "1"  # 测试不走网络

from app import db  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    db.init(str(tmp_path / "data"))
    yield


def make_image(path, color=(200, 30, 30), size=(320, 240), noise_seed=None, text=None):
    img = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(img)
    if noise_seed is not None:
        import random
        rnd = random.Random(noise_seed)
        for _ in range(300):
            x, y = rnd.randrange(size[0]), rnd.randrange(size[1])
            draw.point((x, y), fill=(rnd.randrange(256),) * 3)
    if text:
        draw.text((10, 10), text, fill=(255, 255, 255))
    img.save(path)
    return path
