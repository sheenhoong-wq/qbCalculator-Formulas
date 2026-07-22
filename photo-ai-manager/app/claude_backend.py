"""可选的 Claude 视觉分类后端。

配置了 Anthropic 凭据（ANTHROPIC_API_KEY 或 `ant auth login`）时自动启用，
未配置时静默禁用，应用退回到本地启发式分类。学习层（learning.py）
始终优先于本后端——用户教过的东西不会被 AI 覆盖。
"""
import base64
import io
import json
import os
import threading

from PIL import Image

MODEL = os.environ.get("PHOTO_AI_MODEL", "claude-opus-4-8")
MAX_EDGE = 1024  # 发送前缩小，控制图片 token 开销

_lock = threading.Lock()
_client = None
_available: bool | None = None

DIMENSION_NAMES = {"person": "人物", "scene": "场景", "category": "种类"}

SCHEMA = {
    "type": "object",
    "properties": {
        "person": {"type": "string", "description": "照片中的人物；无人物填 '无'"},
        "scene": {"type": "string", "description": "场景，如 户外/室内/海边/城市/夜景"},
        "category": {"type": "string", "description": "种类，如 人像/风景/美食/宠物/文档/截图"},
    },
    "required": ["person", "scene", "category"],
    "additionalProperties": False,
}


def available() -> bool:
    global _available, _client
    if os.environ.get("PHOTO_AI_DISABLE_CLAUDE"):
        return False
    with _lock:
        if _available is None:
            try:
                import anthropic
                # 零参构造：自动解析 API key / auth token / ant 登录档案
                _client = anthropic.Anthropic()
                _available = bool(
                    os.environ.get("ANTHROPIC_API_KEY")
                    or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                    or _has_profile()
                )
            except Exception:
                _available = False
        return _available


def _has_profile() -> bool:
    cfg = os.environ.get("ANTHROPIC_CONFIG_DIR") or os.path.expanduser("~/.config/anthropic")
    return os.path.isdir(os.path.join(cfg, "credentials"))


def _encode_image(path: str) -> tuple[str, str]:
    img = Image.open(path)
    img = img.convert("RGB")
    if max(img.size) > MAX_EDGE:
        img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode(), "image/jpeg"


def classify(path: str, known: dict[str, list[str]]) -> dict[str, str] | None:
    """用 Claude 视觉给照片打三个维度的标签。失败/refusal 返回 None。"""
    if not available():
        return None
    try:
        import anthropic

        data, media_type = _encode_image(path)
        vocab_lines = [
            f"- {DIMENSION_NAMES[d]}({d}) 已有标签: {', '.join(labels[:30]) or '（暂无）'}"
            for d, labels in known.items()
        ]
        prompt = (
            "请为这张照片分类，输出人物(person)、场景(scene)、种类(category)三个维度的中文标签。\n"
            "优先复用下面已有的标签词汇，确实不匹配时才创建新标签；标签要简短（2-6个字）。\n"
            + "\n".join(vocab_lines)
        )
        response = _client.messages.create(
            model=MODEL,
            max_tokens=1024,
            thinking={"type": "adaptive"},
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image",
                     "source": {"type": "base64", "media_type": media_type, "data": data}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        if response.stop_reason == "refusal":
            return None
        text = next((b.text for b in response.content if b.type == "text"), None)
        if not text:
            return None
        result = json.loads(text)
        return {d: str(result[d]).strip() for d in ("person", "scene", "category") if result.get(d)}
    except Exception:
        # 网络/限流/凭据问题都不应阻塞导入流程，静默回退到本地分类
        return None
