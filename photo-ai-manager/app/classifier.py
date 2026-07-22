"""混合分类器：学习层 → Claude 视觉 → 本地启发式，逐级回退。

优先级设计保证"教过的永远优先"：
1. learned —— 用户纠正过的相似照片（kNN），置信度最高；
2. ai(claude) —— 配置了 API 时用视觉大模型做零样本分类；
3. ai(heuristic) —— 无网络/无凭据时的本地颜色启发式，保证开箱可用。
"""
from PIL import Image

from . import claude_backend, db, learning
from .features import extract

DIMENSIONS = ("person", "scene", "category")


def _heuristic(vector: list[float], img: Image.Image) -> dict[str, tuple[str, float]]:
    """基于特征向量的粗分类。刻意保守：给出宽泛标签等待用户来教。"""
    # 向量布局见 features.extract: h[12] s[4] v[4] top[3] bottom[3] mean std edge aspect skin
    h = vector[0:12]
    v_hist = vector[16:20]
    top = vector[20:23]
    mean_l = vector[26]
    skin = vector[30]

    norm = sum(h) or 1.0
    green = (h[3] + h[4]) / norm          # 色相 90°-150° 附近
    blue = (h[6] + h[7]) / norm           # 色相 180°-240° 附近
    dark = v_hist[0] / (sum(v_hist) or 1.0)

    if skin > 0.25:
        scene, category = "室内", "人像"
    elif dark > 0.6 and mean_l < 0.2:
        scene, category = "夜景", "风景"
    elif blue > 0.35 and top[2] > top[0]:
        scene, category = "户外", "风景"
    elif green > 0.35:
        scene, category = "户外", "自然"
    else:
        scene, category = "未分类", "未分类"

    person = "有人" if skin > 0.25 else "无"
    return {
        "person": (person, 0.3),
        "scene": (scene, 0.3),
        "category": (category, 0.3),
    }


def classify_photo(photo_id: int, path: str, use_claude: bool = True) -> dict:
    """给照片打全部三个维度的标签并写入数据库。返回 {dim: {label, source, confidence}}。"""
    img = Image.open(path)
    vector = extract(img)

    results: dict[str, dict] = {}
    pending = []  # 学习层没把握的维度

    for dim in DIMENSIONS:
        hit = learning.predict(dim, vector)
        if hit:
            label, conf = hit
            results[dim] = {"label": label, "source": "learned", "confidence": conf}
        else:
            pending.append(dim)

    if pending and use_claude and claude_backend.available():
        ai = claude_backend.classify(path, db.known_labels())
        if ai:
            for dim in list(pending):
                if ai.get(dim):
                    results[dim] = {"label": ai[dim], "source": "ai", "confidence": 0.7}
                    pending.remove(dim)

    if pending:
        fallback = _heuristic(vector, img)
        for dim in pending:
            label, conf = fallback[dim]
            results[dim] = {"label": label, "source": "ai", "confidence": conf}

    for dim, r in results.items():
        db.set_label(photo_id, dim, r["label"], r["source"], r["confidence"])
    return results


def correct_label(photo_id: int, dimension: str, new_label: str) -> dict:
    """用户纠正标签 → 记录纠正、学习、并立刻重分类其余照片中受影响的。"""
    photo = db.get_photo(photo_id)
    if photo is None:
        raise KeyError(photo_id)
    old = {r["dimension"]: r["label"] for r in db.get_labels(photo_id)}.get(dimension)

    db.add_correction(photo_id, dimension, old, new_label)
    db.set_label(photo_id, dimension, new_label, "user", 1.0)

    vector = extract(Image.open(photo["path"]))
    learning.learn(dimension, new_label, vector, photo_id)

    # 立刻把学到的知识应用到其它非用户标注的照片上
    updated = _repropagate(dimension, exclude_photo=photo_id)
    return {"old": old, "new": new_label, "repropagated": updated}


def confirm_label(photo_id: int, dimension: str) -> bool:
    """用户确认 AI 标签正确 → 同样作为训练样本学习（正反馈）。"""
    photo = db.get_photo(photo_id)
    if photo is None:
        raise KeyError(photo_id)
    row = next((r for r in db.get_labels(photo_id) if r["dimension"] == dimension), None)
    if row is None:
        return False
    db.set_label(photo_id, dimension, row["label"], "user", 1.0)
    vector = extract(Image.open(photo["path"]))
    learning.learn(dimension, row["label"], vector, photo_id)
    return True


def _repropagate(dimension: str, exclude_photo: int | None = None) -> int:
    """对某维度所有非用户标注的照片重跑学习层预测，返回更新条数。"""
    updated = 0
    for photo in db.all_photos():
        if photo["id"] == exclude_photo:
            continue
        row = next(
            (r for r in db.get_labels(photo["id"]) if r["dimension"] == dimension), None
        )
        if row is not None and row["source"] == "user":
            continue  # 不覆盖用户手动标注
        try:
            vector = extract(Image.open(photo["path"]))
        except Exception:
            continue
        hit = learning.predict(dimension, vector)
        if hit and (row is None or hit[0] != row["label"]):
            db.set_label(photo["id"], dimension, hit[0], "learned", hit[1])
            updated += 1
    return updated
