let refreshTimer = null;
let trackMap = null;
let trackMarker = null;
const steps = ["Reported", "Assigned", "In Progress", "Resolved"];

const params = new URLSearchParams(window.location.search);
if (params.get("id")) {
  document.getElementById("complaintId").value = params.get("id");
  trackComplaint();
}

document.getElementById("complaintId").addEventListener("keydown", (event) => {
  if (event.key === "Enter") trackComplaint();
});

async function trackComplaint() {
  const id = document.getElementById("complaintId").value;
  const box = document.getElementById("trackResult");
  if (!id) {
    box.innerHTML = '<div class="notice error">Enter a complaint ID to begin tracking.</div>';
    return;
  }

  box.innerHTML = '<div class="card empty-state"><div class="loader"></div><p>Loading complaint status…</p></div>';
  try {
    const [issueResponse, historyResponse] = await Promise.all([
      fetch(`/api/issues/${id}`),
      fetch(`/api/issues/${id}/history`)
    ]);
    const data = await issueResponse.json();
    if (!issueResponse.ok) {
      box.innerHTML = `<div class="notice error">${escapeHtml(data.detail || "Complaint not found.")}</div>`;
      stopRefresh();
      return;
    }
    const history = historyResponse.ok ? await historyResponse.json() : [];
    renderIssue(data, history);
    startRefresh();
  } catch (error) {
    box.innerHTML = '<div class="notice error">Cannot connect to the CivicSense server.</div>';
  }
}

function renderIssue(data, history) {
  const activeIndex = steps.indexOf(data.status);
  document.getElementById("trackResult").innerHTML = `
    <section class="card track-summary-card">
      <div class="track-summary-head">
        <div><span class="eyebrow">Complaint Receipt</span><h2>#${data.id} · ${escapeHtml(data.category)}</h2><p>Submitted ${formatDate(data.created_at)}</p></div>
        <div class="track-actions"><span class="status status-${slug(data.status)}">${escapeHtml(data.status)}</span><a class="secondary button-anchor" href="/api/issues/${data.id}/report.pdf">↓ Download PDF Report</a></div>
      </div>

      <div class="issue-detail premium-detail">
        <div class="evidence-panel"><img src="${data.image_url}" alt="Issue evidence"><span>Photo evidence submitted by citizen</span></div>
        <div class="detail-grid">
          <div class="detail-item wide"><span>Issue Description</span><strong>${escapeHtml(data.description)}</strong></div>
          <div class="detail-item"><span>Department</span><strong>${escapeHtml(data.department)}</strong></div>
          <div class="detail-item"><span>Severity</span><strong>${escapeHtml(data.severity)}</strong></div>
          <div class="detail-item"><span>Assigned Team</span><strong>${escapeHtml(data.assigned_to || "Awaiting assignment")}</strong></div>
          <div class="detail-item"><span>Capture Source</span><strong>${escapeHtml(data.source || "Citizen Web")}</strong></div>
          <div class="detail-item"><span>Last Updated</span><strong>${formatDate(data.updated_at)}</strong></div>
          <div class="detail-item wide note-item"><span>Latest Authority Note</span><strong>${escapeHtml(data.authority_note || "Waiting for authority update.")}</strong></div>
        </div>
      </div>
    </section>

    <section class="card timeline-card">
      <div class="section-heading"><div><span class="eyebrow">Live Workflow</span><h3>Resolution Progress</h3></div><span class="progress-label">${Math.max(1, activeIndex + 1)} of 4 stages</span></div>
      <div class="timeline">
        ${steps.map((step, index) => `<div class="timeline-step ${index <= activeIndex ? "done" : ""} ${index === activeIndex ? "current" : ""}"><span>${index < activeIndex ? "✓" : index + 1}</span><p>${step}</p><small>${index < activeIndex ? "Completed" : index === activeIndex ? "Current stage" : "Pending"}</small></div>`).join("")}
      </div>
    </section>

    <section class="track-grid">
      <div class="card map-card-track">
        <div class="section-heading"><div><span class="eyebrow">Exact Location</span><h3>Problem Map</h3></div><a class="text-link" target="_blank" rel="noopener" href="https://www.google.com/maps?q=${data.latitude},${data.longitude}">Open in Google Maps ↗</a></div>
        <div id="trackMap" class="map map-track"></div>
        <div class="location-readout"><span>📍</span><div><b>${escapeHtml(data.location_label || "Citizen-selected map location")}</b><small>${Number(data.latitude).toFixed(6)}, ${Number(data.longitude).toFixed(6)}</small></div></div>
      </div>

      <div class="card history-panel">
        <div class="section-heading"><div><span class="eyebrow">Audit Trail</span><h3>Complaint Activity</h3></div></div>
        <div class="history-list">
          ${history.length ? history.slice().reverse().map((item, index) => `
            <div class="history-row"><span class="history-dot ${index === 0 ? "latest" : ""}"></span><div><b>${escapeHtml(item.status)}</b><p>${escapeHtml(item.note || "Status updated")}</p><small>${formatDate(item.changed_at)}</small></div></div>
          `).join("") : '<p class="muted">No activity history yet.</p>'}
        </div>
      </div>
    </section>`;

  initTrackMap(data);
}

function initTrackMap(data) {
  if (typeof L === "undefined") {
    document.getElementById("trackMap").innerHTML = '<div class="map-fallback">Map could not load. Check your internet connection.</div>';
    return;
  }
  if (trackMap) {
    trackMap.remove();
    trackMap = null;
  }
  trackMap = L.map("trackMap").setView([data.latitude, data.longitude], 17);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "&copy; OpenStreetMap contributors" }).addTo(trackMap);
  trackMarker = L.marker([data.latitude, data.longitude]).addTo(trackMap).bindPopup(`#${data.id} · ${escapeHtml(data.category)}`).openPopup();
  setTimeout(() => trackMap.invalidateSize(), 80);
}

function startRefresh() {
  document.getElementById("liveIndicator").classList.remove("hidden");
  clearInterval(refreshTimer);
  refreshTimer = setInterval(trackComplaint, 10000);
}
function stopRefresh() {
  clearInterval(refreshTimer);
  document.getElementById("liveIndicator").classList.add("hidden");
}
function slug(v) { return String(v).toLowerCase().replaceAll(" ", "-"); }
function formatDate(v) { return new Date(v).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }); }
function escapeHtml(value) { const d = document.createElement("div"); d.textContent = String(value ?? ""); return d.innerHTML; }
