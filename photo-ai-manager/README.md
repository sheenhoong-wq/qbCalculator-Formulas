# 📷 AI 照片分类管理

一个**会学习**的 AI 照片分类管理软件：自动按 **人物 / 场景 / 种类** 三个维度给照片打标签，
分类错了你直接改，它会**记住并举一反三**；还能自动找出**完全相同**和**高度相似**的重复照片。

## 核心特性

| 功能 | 说明 |
|---|---|
| 🤖 自动分类 | 导入照片时自动识别人物、场景、种类三个维度 |
| 🧠 **越用越聪明** | 点错误标签直接改 → 立即学习 → 自动更新其它相似照片 → 以后遇到相似照片直接分对 |
| ✓ 正反馈 | 点 ✓ 确认分对了，同样会作为学习样本，让判断更稳 |
| 🔍 重复检测 | SHA-256 找完全相同的文件；感知哈希（pHash + dHash）找缩放/压缩过的相似照片 |
| 🏷 标签筛选 | 按任意维度、任意标签过滤照片 |
| 🔒 本地优先 | 照片和学习数据全部存在你自己的电脑上（SQLite），不依赖云端 |

## 学习是怎么工作的？

1. 每张照片都会被提取一个**特征向量**（颜色分布、明暗、构图、肤色占比等）。
2. 你纠正或确认一个标签时，`(特征向量, 正确标签)` 被存入训练库。
3. 之后分类任何照片时，先在训练库里找**最相似的 K 张**做加权投票（kNN）——
   只有足够相似、票数足够集中才采信，避免瞎猜。
4. 训练库没把握的，才交给 Claude 视觉大模型（可选）或本地启发式规则。
5. **优先级：你教过的 > AI 判断 > 本地规则**，你手动标注的标签永远不会被 AI 覆盖。

纠正一次，相似的照片全部自动更新——纠得越多，分得越准。

## 安装与运行

需要 Python 3.10+：

```bash
cd photo-ai-manager
pip install -r requirements.txt
python run.py            # 打开 http://localhost:8000
```

### 让手机也能用（Android / iOS / 平板）

本软件是 Web 架构：**服务器跑在 Windows / Linux / macOS / NAS 上，
任何设备的浏览器都能使用**，且共享同一个照片库和同一个"学习大脑"
（手机上纠正的标签，电脑上同样生效）。

```bash
python run.py --lan      # 会打印手机访问地址，如 http://192.168.1.5:8000
```

手机和电脑连同一个 WiFi，浏览器打开该地址即可。界面已适配手机屏幕。

## 启用 Claude 视觉分类（可选，推荐）

默认使用本地规则分类（无需网络）。配置 Anthropic API Key 后，
自动升级为 Claude 视觉大模型分类，首次识别准确率大幅提升：

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # Windows: set ANTHROPIC_API_KEY=...
python run.py
```

- 模型默认 `claude-opus-4-8`，可用环境变量 `PHOTO_AI_MODEL` 更换。
- 图片发送前会压缩到 1024px 以内以控制费用。
- 设置 `PHOTO_AI_DISABLE_CLAUDE=1` 可强制纯本地模式。
- 无论是否启用 Claude，**学习层始终优先**——教过的东西不会被大模型覆盖。

## 数据存储

默认在 `photo-ai-manager/data/`（可用环境变量 `PHOTO_DATA_DIR` 修改）：

```
data/
  app.db      # SQLite：照片索引、标签、训练样本、纠正历史
  photos/     # 照片原图
  thumbs/     # 缩略图
```

备份这个目录 = 备份全部照片和学习成果。

## 运行测试

```bash
python -m pytest tests/ -q
```

## 项目结构

```
app/
  main.py            # FastAPI 接口
  db.py              # SQLite 数据层
  classifier.py      # 混合分类器（学习层 → Claude → 启发式）
  learning.py        # kNN 学习引擎（核心的"会学习"）
  features.py        # 图像特征向量提取
  claude_backend.py  # Claude 视觉分类（可选）
  hashing.py         # 感知哈希（查重）
  duplicates.py      # 重复照片聚类
  imaging.py         # 缩略图 / EXIF
static/              # 网页前端（中文界面）
tests/               # 20 个自动化测试
```
