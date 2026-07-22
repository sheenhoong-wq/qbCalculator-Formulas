const DIM_NAMES = { person: "人物", scene: "场景", category: "种类" };
let allPhotos = [];
let knownLabels = {};

const $ = (id) => document.getElementById(id);

function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(t._timer);
  t._timer = setTimeout(() => (t.hidden = true), 3000);
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  return res.json();
}

async function refresh() {
  const [photos, labels, stats] = await Promise.all([
    api("/api/photos"), api("/api/labels"), api("/api/stats"),
  ]);
  allPhotos = photos.photos;
  knownLabels = labels;
  $("stats").textContent =
    `共 ${stats.photos} 张 · 已学习 ${stats.training_examples} 个样本 · 纠正 ${stats.corrections} 次` +
    (stats.claude_enabled ? " · Claude 视觉已启用" : " · 本地模式");
  renderGrid();
  renderFilterOptions();
}

function currentFilter() {
  const dim = $("filter-dim").value;
  const label = $("filter-label").value;
  return dim && label ? { dim, label } : null;
}

function renderFilterOptions() {
  const dim = $("filter-dim").value;
  const sel = $("filter-label");
  if (!dim) { sel.hidden = true; sel.innerHTML = ""; return; }
  const labels = knownLabels[dim] || [];
  sel.innerHTML = `<option value="">（选择标签）</option>` +
    labels.map((l) => `<option>${escapeHtml(l)}</option>`).join("");
  sel.hidden = false;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function renderGrid() {
  const grid = $("grid");
  const filter = currentFilter();
  const photos = filter
    ? allPhotos.filter((p) => p.labels[filter.dim]?.label === filter.label)
    : allPhotos;

  grid.innerHTML = photos.map((p) => {
    const rows = Object.keys(DIM_NAMES).map((dim) => {
      const l = p.labels[dim];
      if (!l) return "";
      return `<div class="tagrow">
        <span class="dim">${DIM_NAMES[dim]}</span>
        <span class="tag ${l.source}" title="来源: ${l.source} (点击修改)"
              onclick="editLabel(${p.id}, '${dim}', '${escapeHtml(l.label)}')">${escapeHtml(l.label)}</span>
        ${l.source !== "user" ? `<button class="confirm" title="分对了，帮我学习" onclick="confirmLabel(${p.id}, '${dim}')">✓</button>` : ""}
      </div>`;
    }).join("");
    return `<div class="card">
      <img src="/api/photos/${p.id}/thumb" loading="lazy" onclick="window.open('/api/photos/${p.id}/image')">
      <div class="meta">
        <div class="fname">${escapeHtml(p.filename)}
          <button class="del" title="删除" onclick="delPhoto(${p.id})">🗑</button></div>
        ${rows}
      </div>
    </div>`;
  }).join("") || `<p style="color:#888">还没有照片，点上方「上传照片」开始吧。</p>`;
}

window.editLabel = (photoId, dim, current) => {
  const labels = knownLabels[dim] || [];
  const overlay = document.createElement("div");
  overlay.className = "editor";
  overlay.innerHTML = `<div class="panel">
    <h3>修改「${DIM_NAMES[dim]}」标签（当前：${escapeHtml(current)}）</h3>
    <div class="choices">${labels.map((l) =>
      `<span class="tag learned" data-label="${escapeHtml(l)}">${escapeHtml(l)}</span>`).join("")}</div>
    <input type="text" placeholder="或输入新标签…" value="">
    <div class="row">
      <button class="btn" data-act="cancel">取消</button>
      <button class="btn primary" data-act="save">保存并学习</button>
    </div>
  </div>`;
  document.body.appendChild(overlay);
  const input = overlay.querySelector("input");
  input.focus();
  const submit = async (label) => {
    if (!label.trim()) return;
    overlay.remove();
    try {
      const r = await api(`/api/photos/${photoId}/label`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dimension: dim, label: label.trim() }),
      });
      toast(r.repropagated > 0
        ? `已学习！并自动更新了 ${r.repropagated} 张相似照片的分类`
        : "已学习，下次遇到相似照片会记得。");
      refresh();
    } catch (e) { toast("失败：" + e.message); }
  };
  overlay.addEventListener("click", (ev) => {
    if (ev.target === overlay || ev.target.dataset.act === "cancel") overlay.remove();
    else if (ev.target.dataset.act === "save") submit(input.value);
    else if (ev.target.dataset.label !== undefined) submit(ev.target.dataset.label);
  });
  input.addEventListener("keydown", (ev) => { if (ev.key === "Enter") submit(input.value); });
};

window.confirmLabel = async (photoId, dim) => {
  try {
    await api(`/api/photos/${photoId}/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dimension: dim }),
    });
    toast("已确认，这个样本帮我学得更准了 ✓");
    refresh();
  } catch (e) { toast("失败：" + e.message); }
};

window.delPhoto = async (photoId) => {
  if (!confirm("确定删除这张照片？")) return;
  try {
    await api(`/api/photos/${photoId}`, { method: "DELETE" });
    refresh();
  } catch (e) { toast("失败：" + e.message); }
};

async function renderDups() {
  const d = await api("/api/duplicates");
  const box = $("dups");
  const group = (g, title) => `<div class="dup-group">
    <h3>${title}（${g.photos.length} 张）</h3>
    <div class="thumbs">${g.photos.map((p) =>
      `<div class="item"><img src="/api/photos/${p.id}/thumb"
         onclick="window.open('/api/photos/${p.id}/image')"><br>${escapeHtml(p.filename)}
         <button class="del" onclick="delPhoto(${p.id}); renderDups()">🗑</button></div>`).join("")}
    </div></div>`;
  const html =
    d.exact.map((g) => group(g, "🔴 完全相同")).join("") +
    d.near.map((g) => group(g, "🟡 高度相似")).join("");
  box.innerHTML = html || `<p style="color:#888">没有发现重复照片 🎉</p>`;
}

$("file-input").addEventListener("change", async (ev) => {
  const files = ev.target.files;
  if (!files.length) return;
  const fd = new FormData();
  for (const f of files) fd.append("files", f);
  toast(`正在导入 ${files.length} 张照片并进行 AI 分类…`);
  try {
    const r = await api("/api/photos/upload", { method: "POST", body: fd });
    const dups = r.imported.filter((x) => x.duplicate_of).length;
    toast(`导入完成：${r.imported.length} 张` + (dups ? `，其中 ${dups} 张疑似重复` : ""));
    ev.target.value = "";
    refresh();
  } catch (e) { toast("上传失败：" + e.message); }
});

$("tab-photos").addEventListener("click", () => {
  $("grid").hidden = false; $("dups").hidden = true;
  $("tab-photos").classList.add("active"); $("tab-dups").classList.remove("active");
});
$("tab-dups").addEventListener("click", () => {
  $("grid").hidden = true; $("dups").hidden = false;
  $("tab-dups").classList.add("active"); $("tab-photos").classList.remove("active");
  renderDups();
});
$("filter-dim").addEventListener("change", () => { renderFilterOptions(); renderGrid(); });
$("filter-label").addEventListener("change", renderGrid);

refresh();
