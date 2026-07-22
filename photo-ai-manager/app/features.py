"""图像特征向量：HSV 颜色直方图 + 亮度/边缘统计 + 肤色占比。

这是"学习"能力的基础——用户每次纠正一个标签，我们把这张照片的
特征向量和正确标签存为训练样本；之后遇到相似照片时 kNN 优先命中。
"""
import math

from PIL import Image

FEATURE_SIZE = 48  # 特征计算用的缩略边长


def _skin_ratio(pixels_rgb) -> float:
    """粗略肤色像素占比（RGB 规则），辅助识别人像。"""
    n = 0
    for r, g, b in pixels_rgb:
        if r > 95 and g > 40 and b > 20 and r > g and r > b and abs(r - g) > 15:
            n += 1
    return n / max(1, len(pixels_rgb))


def extract(img: Image.Image) -> list[float]:
    w0, h0 = img.size
    rgb = img.convert("RGB").resize((FEATURE_SIZE, FEATURE_SIZE), Image.LANCZOS)
    hsv = rgb.convert("HSV")
    rgb_px = list(rgb.getdata())
    hsv_px = list(hsv.getdata())
    n = len(hsv_px)

    # HSV 直方图：H 12 桶、S 4 桶、V 4 桶
    h_hist = [0.0] * 12
    s_hist = [0.0] * 4
    v_hist = [0.0] * 4
    for h, s, v in hsv_px:
        h_hist[min(11, h * 12 // 256)] += 1
        s_hist[min(3, s * 4 // 256)] += 1
        v_hist[min(3, v * 4 // 256)] += 1
    h_hist = [x / n for x in h_hist]
    s_hist = [x / n for x in s_hist]
    v_hist = [x / n for x in v_hist]

    # 上/下半图平均色（区分"上蓝天下绿地"这类构图）
    half = n // 2
    def avg_rgb(px):
        m = max(1, len(px))
        return [sum(p[i] for p in px) / m / 255.0 for i in range(3)]
    top_rgb = avg_rgb(rgb_px[:half])
    bottom_rgb = avg_rgb(rgb_px[half:])

    # 亮度统计
    lum = [(0.299 * r + 0.587 * g + 0.114 * b) / 255.0 for r, g, b in rgb_px]
    mean_l = sum(lum) / n
    var_l = sum((x - mean_l) ** 2 for x in lum) / n

    # 边缘密度（水平+垂直梯度均值），衡量画面复杂度
    size = FEATURE_SIZE
    grad = 0.0
    for y in range(size - 1):
        for x in range(size - 1):
            c = lum[y * size + x]
            grad += abs(c - lum[y * size + x + 1]) + abs(c - lum[(y + 1) * size + x])
    edge = grad / (2 * (size - 1) * (size - 1))

    aspect = w0 / max(1, h0)
    skin = _skin_ratio(rgb_px)

    vec = (
        h_hist + s_hist + v_hist + top_rgb + bottom_rgb
        + [mean_l, math.sqrt(var_l), edge, min(aspect, 3.0) / 3.0, skin]
    )
    # L2 归一化，便于用余弦相似度
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
