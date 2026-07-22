"""感知哈希：用于重复/近似重复照片检测。纯 Pillow 实现，无重型依赖。"""
import hashlib

from PIL import Image


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _bits_to_hex(bits: list[int]) -> str:
    value = 0
    for b in bits:
        value = (value << 1) | (1 if b else 0)
    return f"{value:0{len(bits) // 4}x}"


def ahash(img: Image.Image, size: int = 8) -> str:
    """均值哈希。"""
    g = img.convert("L").resize((size, size), Image.LANCZOS)
    px = list(g.getdata())
    avg = sum(px) / len(px)
    return _bits_to_hex([1 if p > avg else 0 for p in px])


def dhash(img: Image.Image, size: int = 8) -> str:
    """差分哈希：对轻微裁剪/压缩鲁棒。"""
    g = img.convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(g.getdata())
    bits = []
    for row in range(size):
        for col in range(size):
            bits.append(1 if px[row * (size + 1) + col] > px[row * (size + 1) + col + 1] else 0)
    return _bits_to_hex(bits)


def phash(img: Image.Image, size: int = 32, factor: int = 4) -> str:
    """DCT 感知哈希（8x8 低频块），对缩放/重压缩最鲁棒。"""
    import math

    small = size // factor  # 8
    g = img.convert("L").resize((size, size), Image.LANCZOS)
    px = [[g.getpixel((x, y)) for x in range(size)] for y in range(size)]

    # 分离式 2D DCT-II，只需要左上 small x small 低频系数
    cos = [[math.cos((2 * i + 1) * u * math.pi / (2 * size)) for i in range(size)] for u in range(size)]
    rows = [[sum(px[y][x] * cos[u][x] for x in range(size)) for u in range(small)] for y in range(size)]
    dct = [[sum(rows[y][u] * cos[v][y] for y in range(size)) for u in range(small)] for v in range(small)]

    flat = [dct[v][u] for v in range(small) for u in range(small)]
    # 去掉直流分量后取中位数
    ac = flat[1:]
    med = sorted(ac)[len(ac) // 2]
    return _bits_to_hex([1 if c > med else 0 for c in flat])


def hamming(hex_a: str, hex_b: str) -> int:
    return bin(int(hex_a, 16) ^ int(hex_b, 16)).count("1")
