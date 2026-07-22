"""学习引擎：基于用户反馈的 kNN 分类。

工作方式：
1. 用户纠正/确认标签 → learn() 把 (特征向量, 正确标签) 存入训练库。
2. 分类新照片时 predict() 先查训练库：找 k 个最相似样本做加权投票。
3. 相似度足够高才采信，否则交给下游（Claude 视觉 / 启发式）。

纠得越多，训练库越大，命中越准——这就是"她会学习修改"。
"""
from . import db
from .features import cosine

K = 5
MIN_SIMILARITY = 0.90   # 最近邻至少要这么像才采信学习结果
MIN_MARGIN = 0.10       # 第一名标签的票数需领先第二名


def learn(dimension: str, label: str, vector: list[float], photo_id: int | None = None) -> None:
    db.add_training_example(dimension, label, vector, photo_id)


def predict(dimension: str, vector: list[float]) -> tuple[str, float] | None:
    """返回 (label, confidence)；训练样本不足或不够相似时返回 None。"""
    examples = db.training_examples(dimension)
    if not examples:
        return None

    scored = sorted(
        ((cosine(vector, feat), label) for label, feat in examples),
        key=lambda t: -t[0],
    )[:K]

    best_sim = scored[0][0]
    if best_sim < MIN_SIMILARITY:
        return None

    # 相似度加权投票
    votes: dict[str, float] = {}
    for sim, label in scored:
        if sim > 0:
            votes[label] = votes.get(label, 0.0) + sim
    total = sum(votes.values()) or 1.0
    ranked = sorted(votes.items(), key=lambda t: -t[1])
    top_label, top_score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    if (top_score - second) / total < MIN_MARGIN:
        return None

    confidence = min(0.99, best_sim * (top_score / total))
    return top_label, confidence
