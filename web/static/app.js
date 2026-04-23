function formatEventType(type) {
  return (type || "").toLowerCase();
}

function renderEventTag(type) {
  const cls = formatEventType(type);
  return `<span class="event-tag ${cls}">${escapeHtml(type || "-")}</span>`;
}

function formatTime(tsMs) {
  if (!tsMs) return "-";
  const date = new Date(Number(tsMs));
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("zh-CN", { hour12: false });
}

function secondsToText(total) {
  total = Number(total || 0);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

async function fetchJson(url, options) {
  const resp = await fetch(url, options);
  if (!resp.ok) {
    throw new Error(`${resp.status} ${resp.statusText}`);
  }
  return await resp.json();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
