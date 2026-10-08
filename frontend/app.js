const form = document.getElementById("issueForm");
const locationBtn = document.getElementById("locationBtn");
const locationText = document.getElementById("locationText");
const locationState = document.getElementById("locationState");
const latitudeInput = document.getElementById("latitude");
const longitudeInput = document.getElementById("longitude");
const messageBox = document.getElementById("message");
const imageInput = document.getElementById("imageInput");
const imagePreview = document.getElementById("imagePreview");
const previewWrap = document.getElementById("previewWrap");
const removeImageBtn = document.getElementById("removeImageBtn");
const submitBtn = document.getElementById("submitBtn");

let reportMap = null;
let locationMarker = null;
const DEFAULT_CENTER = [20.5937, 78.9629];

function initMap() {
  if (typeof L === "undefined") {
    document.getElementById("reportMap").innerHTML = '<div class="map-fallback">Map could not load. Check your internet connection.</div>';
    return;
  }
  reportMap = L.map("reportMap", { zoomControl: true }).setView(DEFAULT_CENTER, 5);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(reportMap);

  reportMap.on("click", (event) => setSelectedLocation(event.latlng.lat, event.latlng.lng, true));
  setTimeout(() => reportMap.invalidateSize(), 100);
}

function setSelectedLocation(lat, lon, focus = false, accuracy = null) {
  latitudeInput.value = Number(lat).toFixed(7);
  longitudeInput.value = Number(lon).toFixed(7);
  locationText.textContent = `${Number(lat).toFixed(6)}, ${Number(lon).toFixed(6)}${accuracy ? ` · GPS accuracy ±${Math.round(accuracy)} m` : ""}`;
  locationState.textContent = "Location selected ✓";
  locationState.classList.add("selected");

  if (reportMap) {
    if (!locationMarker) {
      locationMarker = L.marker([lat, lon], { draggable: true }).addTo(reportMap);
      locationMarker.bindPopup("Issue location").openPopup();
      locationMarker.on("dragend", () => {
        const point = locationMarker.getLatLng();
        setSelectedLocation(point.lat, point.lng, false);
      });
    } else {
      locationMarker.setLatLng([lat, lon]);
    }
    if (focus) reportMap.setView([lat, lon], 17, { animate: true });
  }
}

imageInput.addEventListener("change", () => {
  const file = imageInput.files[0];
  if (!file) {
    previewWrap.classList.add("hidden");
    return;
  }
  imagePreview.src = URL.createObjectURL(file);
  previewWrap.classList.remove("hidden");
});

removeImageBtn.addEventListener("click", () => {
  imageInput.value = "";
  imagePreview.removeAttribute("src");
  previewWrap.classList.add("hidden");
});

locationBtn.addEventListener("click", () => {
  if (!navigator.geolocation) {
    locationText.textContent = "Geolocation is not supported by this browser. Click the map instead.";
    return;
  }

  locationBtn.disabled = true;
  locationBtn.textContent = "Locating…";
  locationState.textContent = "Reading GPS";

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const { latitude, longitude, accuracy } = position.coords;
      setSelectedLocation(latitude, longitude, true, accuracy);
      locationBtn.textContent = "◎ Re-center to Me";
      locationBtn.disabled = false;
    },
    (error) => {
      locationText.textContent = "GPS permission failed. Allow location access or click the map manually.";
      locationState.textContent = "Select on map";
      locationBtn.textContent = "◎ Use My Location";
      locationBtn.disabled = false;
      console.error(error);
    },
    { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
  );
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!latitudeInput.value || !longitudeInput.value) {
    messageBox.innerHTML = '<div class="notice error">📍 Please select the exact problem location on the map before submitting.</div>';
    document.querySelector(".location-section").scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }

  const formData = new FormData(form);
  submitBtn.disabled = true;
  submitBtn.textContent = "Checking & submitting…";
  messageBox.innerHTML = '<div class="notice info">Checking nearby duplicate reports and routing your complaint…</div>';

  try {
    const response = await fetch("/api/issues", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) {
      messageBox.innerHTML = `<div class="notice error">${escapeHtml(data.detail || "Something went wrong.")}</div>`;
      return;
    }

    messageBox.innerHTML = `
      <div class="success-box">
        <div class="success-icon">✓</div>
        <div class="success-content">
          <span class="success-kicker">Report Registered</span>
          <h3>Complaint #${data.issue.id} is now in the civic workflow.</h3>
          <p>Automatically routed to <b>${escapeHtml(data.issue.department)}</b>. Keep the complaint ID for tracking.</p>
          <div class="success-actions">
            <a class="button-link" href="/track?id=${data.issue.id}">Track Report</a>
            <a class="button-link ghost" href="/api/issues/${data.issue.id}/report.pdf">Download PDF</a>
          </div>
        </div>
      </div>`;

    form.reset();
    latitudeInput.value = "";
    longitudeInput.value = "";
    locationText.textContent = "No location selected";
    locationState.textContent = "Waiting for pin";
    locationState.classList.remove("selected");
    locationBtn.textContent = "◎ Use My Location";
    previewWrap.classList.add("hidden");
    if (locationMarker && reportMap) {
      reportMap.removeLayer(locationMarker);
      locationMarker = null;
      reportMap.setView(DEFAULT_CENTER, 5);
    }
    messageBox.scrollIntoView({ behavior: "smooth", block: "center" });
  } catch (error) {
    messageBox.innerHTML = '<div class="notice error">Cannot connect to CivicSense. Confirm the FastAPI server is running.</div>';
    console.error(error);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Submit Civic Report →";
  }
});

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}

initMap();
