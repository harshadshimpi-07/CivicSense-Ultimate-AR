const statuses = ["Reported", "Assigned", "In Progress", "Resolved"];
const severities = ["Low", "Medium", "High", "Critical"];
let allIssues = [];
let adminMap = null;
let mapLayer = null;

function initAdminMap() {
  if (typeof L === "undefined") {
    document.getElementById("adminMap").innerHTML = '<div class="map-fallback">Map could not load. Check your internet connection.</div>';
    return;
  }
  adminMap = L.map("adminMap").setView([20.5937, 78.9629], 5);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(adminMap);
  mapLayer = L.layerGroup().addTo(adminMap);
  setTimeout(() => adminMap.invalidateSize(), 100);
}

async function checkDbStatus() {
  const badge = document.getElementById("dbBadge");
  if (!badge) return;
  try {
    const res = await fetch("/api/db/status");
    if (res.ok) {
      const data = await res.json();
      if (data.mode === "supabase" && data.supabase_connected) {
        badge.innerHTML = "☁ Supabase Cloud Active";
        badge.style.background = "rgba(45,212,191,0.2)";
        badge.style.borderColor = "#2dd4bf";
        badge.style.color = "#5eead4";
      } else {
        badge.innerHTML = "💾 Local SQLite (Supabase Ready)";
        badge.style.background = "rgba(255,255,255,0.1)";
        badge.style.borderColor = "rgba(255,255,255,0.2)";
        badge.style.color = "#cbd5e1";
      }
    }
  } catch (_) {
    badge.textContent = "Offline";
  }
}

async function loadIssues() {
  checkDbStatus();
  const grid = document.getElementById("issuesGrid");
  grid.innerHTML = '<div class="card empty-state"><div class="loader"></div><p>Loading civic reports…</p></div>';
  try {
    const response = await fetch("/api/issues");
    if (!response.ok) throw new Error("Could not load issues");
    allIssues = await response.json();
    renderStats();
    renderIssues();
  } catch (error) {
    grid.innerHTML = '<div class="card empty-state"><div class="notice error">Cannot connect to the CivicSense server.</div></div>';
  }
}

function renderStats() {
  const total = allIssues.length;
  const open = allIssues.filter(i => i.status !== "Resolved").length;
  const inProgress = allIssues.filter(i => i.status === "In Progress").length;
  const resolved = allIssues.filter(i => i.status === "Resolved").length;
  const urgent = allIssues.filter(i => ["High", "Critical"].includes(i.severity) && i.status !== "Resolved").length;
  const rate = total ? Math.round((resolved / total) * 100) : 0;
  const cards = [
    ["All Reports", total, "Citywide complaints", "◎"],
    ["Open Cases", open, "Need municipal action", "◌"],
    ["In Progress", inProgress, "Teams working", "↗"],
    ["Urgent", urgent, "High / critical open", "!"],
    ["Resolution Rate", `${rate}%`, `${resolved} resolved`, "✓"]
  ];
  document.getElementById("stats").innerHTML = cards.map(([label, count, sub, icon]) => `
    <div class="stat-card"><div class="stat-icon">${icon}</div><div><strong>${count}</strong><span>${label}</span><small>${sub}</small></div></div>`).join("");
}

function getFilteredIssues() {
  const search = document.getElementById("searchBox").value.trim().toLowerCase();
  const status = document.getElementById("statusFilter").value;
  const category = document.getElementById("categoryFilter").value;
  return allIssues.filter(issue => {
    const haystack = `${issue.id} ${issue.category} ${issue.reporter_name} ${issue.department} ${issue.description} ${issue.location_label || ""}`.toLowerCase();
    return (!search || haystack.includes(search)) && (!status || issue.status === status) && (!category || issue.category === category);
  });
}

function renderIssues() {
  const issues = getFilteredIssues();
  document.getElementById("resultCount").textContent = `${issues.length} ${issues.length === 1 ? "report" : "reports"}`;
  renderMap(issues);

  const grid = document.getElementById("issuesGrid");
  if (!issues.length) {
    grid.innerHTML = '<div class="card empty-state"><div class="empty-icon">⌕</div><h3>No matching complaints</h3><p>Try clearing one of the filters.</p></div>';
    return;
  }

  grid.innerHTML = issues.map(issue => `
    <article class="issue-card" id="issue-card-${issue.id}">
      <div class="issue-image-wrap">
        <img src="${issue.image_url}" alt="${escapeAttr(issue.category)} evidence">
        <span class="severity severity-${slug(issue.severity)}">${escapeHtml(issue.severity)} priority</span>
        <span class="case-id">#${issue.id}</span>
      </div>
      <div class="issue-card-body">
        <div class="issue-title"><div><span class="eyebrow">${escapeHtml(issue.department)}</span><h3>${escapeHtml(issue.category)}</h3></div><span class="status status-${slug(issue.status)}">${escapeHtml(issue.status)}</span></div>
        <p class="description">${escapeHtml(issue.description)}</p>
        <div class="location-mini"><span>📍</span><div><b>${escapeHtml(issue.location_label || "Map-selected civic location")}</b><small>${Number(issue.latitude).toFixed(5)}, ${Number(issue.longitude).toFixed(5)}</small></div></div>
        <div class="meta-grid">
          <p><span>Citizen</span>${escapeHtml(issue.reporter_name)}</p>
          <p><span>Capture source</span>${escapeHtml(issue.source || "Citizen Web")}</p>
          <p><span>Last update</span>${formatDate(issue.updated_at)}</p>
        </div>
        <div class="card-actions">
          <button class="secondary small" onclick="focusIssue(${issue.id})">📍 Show on Map</button>
          <a class="secondary small button-anchor" href="/track?id=${issue.id}" target="_blank">Track View</a>
          <a class="secondary small button-anchor" href="/api/issues/${issue.id}/report.pdf">↓ PDF Report</a>
        </div>

        <div class="admin-form">
          <div class="form-label-row"><strong>Municipal Action</strong><span>Update citizen-visible progress</span></div>
          <div class="grid-2 compact">
            <label>Status<select id="status-${issue.id}">${statuses.map(s => `<option ${s === issue.status ? "selected" : ""}>${s}</option>`).join("")}</select></label>
            <label>Severity<select id="severity-${issue.id}">${severities.map(s => `<option ${s === issue.severity ? "selected" : ""}>${s}</option>`).join("")}</select></label>
          </div>
          <label>Assigned Staff / Team<input id="assigned-${issue.id}" value="${escapeAttr(issue.assigned_to)}" placeholder="e.g. Ward 12 Road Team"></label>
          <label>Progress Note<textarea id="note-${issue.id}" rows="2" placeholder="What action was taken?">${escapeHtml(issue.authority_note || "")}</textarea></label>
          <button class="primary full" onclick="updateIssue(${issue.id}, this)">Save Municipal Update</button>
        </div>
      </div>
    </article>`).join("");
}

function renderMap(issues) {
  document.getElementById("mapSummary").textContent = issues.length ? `${issues.length} visible complaint locations. Click a marker to inspect the case.` : "No locations match the current filters.";
  if (!adminMap || !mapLayer) return;
  mapLayer.clearLayers();
  const bounds = [];

  issues.forEach(issue => {
    const lat = Number(issue.latitude);
    const lon = Number(issue.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
    const color = issue.status === "Resolved" ? "#16a34a" : (["High", "Critical"].includes(issue.severity) ? "#dc2626" : "#0f766e");
    const marker = L.circleMarker([lat, lon], {
      radius: 9, color: "#ffffff", weight: 2.5, fillColor: color, fillOpacity: 0.95
    }).addTo(mapLayer);
    marker.bindPopup(`
      <div class="map-popup"><b>#${issue.id} · ${escapeHtml(issue.category)}</b><br>
      <span>${escapeHtml(issue.status)} · ${escapeHtml(issue.severity)}</span><br>
      <small>${escapeHtml(issue.location_label || "Selected map location")}</small><br>
      <button onclick="window.focusIssue(${issue.id})">Open case</button></div>`);
    bounds.push([lat, lon]);
  });

  if (bounds.length === 1) adminMap.setView(bounds[0], 16);
  else if (bounds.length > 1) adminMap.fitBounds(bounds, { padding: [32, 32], maxZoom: 16 });
}

function focusIssue(id) {
  const issue = allIssues.find(item => item.id === id);
  if (!issue) return;
  if (adminMap) {
    adminMap.setView([issue.latitude, issue.longitude], 18, { animate: true });
    document.querySelector(".admin-map-card").scrollIntoView({ behavior: "smooth", block: "center" });
  }
  const card = document.getElementById(`issue-card-${id}`);
  if (card) {
    card.classList.add("pulse-card");
    setTimeout(() => card.classList.remove("pulse-card"), 1500);
  }
}
window.focusIssue = focusIssue;

async function updateIssue(id, button) {
  const payload = {
    status: document.getElementById(`status-${id}`).value,
    severity: document.getElementById(`severity-${id}`).value,
    assigned_to: document.getElementById(`assigned-${id}`).value,
    note: document.getElementById(`note-${id}`).value
  };
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Saving update…";
  try {
    const response = await fetch(`/api/issues/${id}/status`, {
      method: "PATCH",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) { alert(data.detail || "Could not update complaint."); return; }
    await loadIssues();
  } finally {
    button.disabled = false;
    button.textContent = original;
  }
}

function slug(v) { return String(v).toLowerCase().replaceAll(" ", "-"); }
function formatDate(v) { return new Date(v).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }); }
function escapeHtml(value) { const d = document.createElement("div"); d.textContent = String(value ?? ""); return d.innerHTML; }
function escapeAttr(value) { return escapeHtml(value).replaceAll('"', '&quot;'); }

initAdminMap();
loadIssues();
