"""FastAPI 应用：照片管理 + AI 分类 + 学习反馈 + 查重的 HTTP 接口。"""
import os
import shutil
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel

from . import classifier, db, duplicates, hashing, imaging
from .claude_backend import available as claude_available

app = FastAPI(title="AI 照片分类管理")

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}


@app.on_event("startup")
def startup() -> None:
    db.init()


def _import_file(src_path: str, original_name: str) -> dict:
    """把一张图片纳入图库：查重、哈希、缩略图、AI 分类。"""
    sha = hashing.sha256_file(src_path)
    existing = db.find_by_sha(sha)

    img = Image.open(src_path)
    ext = os.path.splitext(original_name)[1].lower() or ".jpg"
    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(db.photos_dir(), stored_name)
    shutil.copy2(src_path, dest)

    photo_id = db.add_photo(
        filename=original_name,
        path=dest,
        sha256=sha,
        phash=hashing.phash(img),
        dhash=hashing.dhash(img),
        width=img.size[0],
        height=img.size[1],
        taken_at=imaging.taken_at(img),
    )
    imaging.make_thumbnail(dest, os.path.join(db.thumbs_dir(), f"{photo_id}.jpg"))
    labels = classifier.classify_photo(photo_id, dest)
    return {
        "id": photo_id,
        "filename": original_name,
        "labels": labels,
        "duplicate_of": existing["id"] if existing else None,
    }


@app.post("/api/photos/upload")
async def upload(files: list[UploadFile] = File(...)):
    results = []
    for f in files:
        ext = os.path.splitext(f.filename or "")[1].lower()
        if ext not in ALLOWED_EXT:
            results.append({"filename": f.filename, "error": "不支持的格式"})
            continue
        tmp = os.path.join(db.DATA_DIR, f"upload_{uuid.uuid4().hex}{ext}")
        try:
            with open(tmp, "wb") as out:
                shutil.copyfileobj(f.file, out)
            results.append(_import_file(tmp, f.filename or "unnamed"))
        except Exception as e:
            results.append({"filename": f.filename, "error": str(e)})
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    return {"imported": results}


class FolderReq(BaseModel):
    path: str


@app.post("/api/import-folder")
def import_folder(req: FolderReq):
    if not os.path.isdir(req.path):
        raise HTTPException(400, "目录不存在")
    results = []
    for root, _dirs, names in os.walk(req.path):
        for name in sorted(names):
            if os.path.splitext(name)[1].lower() in ALLOWED_EXT:
                try:
                    results.append(_import_file(os.path.join(root, name), name))
                except Exception as e:
                    results.append({"filename": name, "error": str(e)})
    return {"imported": results}


@app.get("/api/photos")
def list_photos(dimension: str | None = None, label: str | None = None):
    out = []
    for p in db.all_photos():
        labels = {
            r["dimension"]: {
                "label": r["label"], "source": r["source"], "confidence": r["confidence"],
            }
            for r in db.get_labels(p["id"])
        }
        if dimension and label:
            row = labels.get(dimension)
            if not row or row["label"] != label:
                continue
        out.append({
            "id": p["id"],
            "filename": p["filename"],
            "width": p["width"],
            "height": p["height"],
            "taken_at": p["taken_at"],
            "labels": labels,
        })
    return {"photos": out}


@app.get("/api/photos/{photo_id}/thumb")
def thumb(photo_id: int):
    path = os.path.join(db.thumbs_dir(), f"{photo_id}.jpg")
    if not os.path.exists(path):
        raise HTTPException(404)
    return FileResponse(path, media_type="image/jpeg")


@app.get("/api/photos/{photo_id}/image")
def image(photo_id: int):
    photo = db.get_photo(photo_id)
    if photo is None or not os.path.exists(photo["path"]):
        raise HTTPException(404)
    return FileResponse(photo["path"])


class LabelReq(BaseModel):
    dimension: str
    label: str


@app.post("/api/photos/{photo_id}/label")
def set_label(photo_id: int, req: LabelReq):
    if req.dimension not in classifier.DIMENSIONS:
        raise HTTPException(400, "维度必须是 person/scene/category")
    if not req.label.strip():
        raise HTTPException(400, "标签不能为空")
    try:
        result = classifier.correct_label(photo_id, req.dimension, req.label.strip())
    except KeyError:
        raise HTTPException(404, "照片不存在")
    return result


class ConfirmReq(BaseModel):
    dimension: str


@app.post("/api/photos/{photo_id}/confirm")
def confirm(photo_id: int, req: ConfirmReq):
    try:
        ok = classifier.confirm_label(photo_id, req.dimension)
    except KeyError:
        raise HTTPException(404, "照片不存在")
    if not ok:
        raise HTTPException(400, "该维度还没有标签")
    return {"ok": True}


@app.delete("/api/photos/{photo_id}")
def delete(photo_id: int):
    photo = db.get_photo(photo_id)
    if photo is None:
        raise HTTPException(404)
    db.delete_photo(photo_id)
    for path in (photo["path"], os.path.join(db.thumbs_dir(), f"{photo_id}.jpg")):
        if os.path.exists(path):
            os.remove(path)
    return {"ok": True}


@app.get("/api/duplicates")
def dup():
    return duplicates.find_duplicates()


@app.get("/api/labels")
def labels():
    return db.known_labels()


@app.get("/api/stats")
def stats():
    s = db.stats()
    s["claude_enabled"] = claude_available()
    return s


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
