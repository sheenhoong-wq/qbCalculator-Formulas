"""重复照片检测：精确重复（sha256）+ 近似重复（感知哈希汉明距离 + 并查集）。"""
from . import db
from .hashing import hamming

PHASH_THRESHOLD = 8  # 64 位 pHash 汉明距离 ≤8 视为近似重复
DHASH_THRESHOLD = 6  # dHash 对缩放更稳，任一命中即算相似


def find_duplicates() -> dict:
    photos = [dict(p) for p in db.all_photos()]

    # 精确重复
    by_sha: dict[str, list[dict]] = {}
    for p in photos:
        by_sha.setdefault(p["sha256"], []).append(p)
    exact = [
        {"type": "exact", "photos": _slim(group)}
        for group in by_sha.values()
        if len(group) > 1
    ]

    # 近似重复（并查集按 pHash 距离聚类）
    parent = list(range(len(photos)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(len(photos)):
        for j in range(i + 1, len(photos)):
            if photos[i]["sha256"] == photos[j]["sha256"]:
                continue  # 精确重复已单独列出
            if (
                hamming(photos[i]["phash"], photos[j]["phash"]) <= PHASH_THRESHOLD
                or hamming(photos[i]["dhash"], photos[j]["dhash"]) <= DHASH_THRESHOLD
            ):
                union(i, j)

    clusters: dict[int, list[dict]] = {}
    for i, p in enumerate(photos):
        clusters.setdefault(find(i), []).append(p)
    near = [
        {"type": "near", "photos": _slim(group)}
        for group in clusters.values()
        if len(group) > 1
    ]

    return {"exact": exact, "near": near}


def _slim(group):
    return [
        {"id": p["id"], "filename": p["filename"], "width": p["width"], "height": p["height"]}
        for p in group
    ]
