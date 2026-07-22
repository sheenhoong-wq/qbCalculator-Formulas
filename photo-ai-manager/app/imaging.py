"""缩略图与 EXIF 元数据。"""
import os

from PIL import Image

THUMB_EDGE = 320
EXIF_DATETIME_ORIGINAL = 36867
EXIF_DATETIME = 306


def make_thumbnail(src_path: str, thumb_path: str) -> None:
    img = Image.open(src_path).convert("RGB")
    img.thumbnail((THUMB_EDGE, THUMB_EDGE), Image.LANCZOS)
    os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
    img.save(thumb_path, format="JPEG", quality=82)


def taken_at(img: Image.Image) -> str | None:
    try:
        exif = img.getexif()
        raw = exif.get(EXIF_DATETIME_ORIGINAL) or exif.get(EXIF_DATETIME)
        if raw:
            # EXIF 格式 "YYYY:MM:DD HH:MM:SS" → ISO
            return str(raw).replace(":", "-", 2)
    except Exception:
        pass
    return None
