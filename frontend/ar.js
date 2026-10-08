const video = document.getElementById('cameraVideo');
const canvas = document.getElementById('captureCanvas');
const startBtn = document.getElementById('startCameraBtn');
const captureBtn = document.getElementById('captureBtn');
const retakeBtn = document.getElementById('retakeBtn');
const fallbackImage = document.getElementById('fallbackImage');
const previewWrap = document.getElementById('capturePreviewWrap');
const preview = document.getElementById('capturePreview');
const form = document.getElementById('arIssueForm');
const message = document.getElementById('arMessage');
const category = document.getElementById('arCategory');
const hudCategory = document.getElementById('hudCategory');
const cameraState = document.getElementById('cameraState');
const gpsState = document.getElementById('gpsState');
const headingState = document.getElementById('headingState');
const hudHeading = document.getElementById('hudHeading');
const hudCoords = document.getElementById('hudCoords');
const latInput = document.getElementById('arLatitude');
const lonInput = document.getElementById('arLongitude');
const locationText = document.getElementById('arLocationText');
const gpsBtn = document.getElementById('arGpsBtn');
const submitBtn = document.getElementById('arSubmitBtn');
let stream = null, capturedBlob = null, map = null, marker = null;
const DEFAULT_CENTER = [18.6298, 73.7997];

function initMap(){
  if(typeof L==='undefined') return;
  map=L.map('arMap').setView(DEFAULT_CENTER,12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
  map.on('click', e=>setLocation(e.latlng.lat,e.latlng.lng,true));
  setTimeout(()=>map.invalidateSize(),150);
}
function setLocation(lat,lon,focus=false){
  latInput.value=Number(lat).toFixed(7); lonInput.value=Number(lon).toFixed(7);
  locationText.textContent=`${Number(lat).toFixed(6)}, ${Number(lon).toFixed(6)}`;
  hudCoords.textContent=`${Number(lat).toFixed(5)}, ${Number(lon).toFixed(5)}`;
  gpsState.textContent='GPS locked ✓'; gpsState.classList.add('ok');
  if(map){
    if(!marker){ marker=L.marker([lat,lon],{draggable:true}).addTo(map); marker.on('dragend',()=>{const p=marker.getLatLng();setLocation(p.lat,p.lng,false)}); }
    else marker.setLatLng([lat,lon]);
    if(focus) map.setView([lat,lon],17,{animate:true});
  }
}
function requestGps(){
  if(!navigator.geolocation){ gpsState.textContent='GPS unsupported'; return; }
  gpsState.textContent='Locating…';
  navigator.geolocation.getCurrentPosition(p=>setLocation(p.coords.latitude,p.coords.longitude,true),()=>{gpsState.textContent='GPS denied';},{enableHighAccuracy:true,timeout:15000,maximumAge:0});
}
async function startCamera(){
  try{
    stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});
    video.srcObject=stream; cameraState.textContent='Camera live ✓'; cameraState.classList.add('ok'); captureBtn.disabled=false; startBtn.textContent='Camera Active'; startBtn.disabled=true; requestGps();
  }catch(e){ cameraState.textContent='Camera permission denied'; message.innerHTML='<div class="notice error">Camera could not start. Use “Upload Instead” to attach evidence.</div>'; }
}
function capture(){
  if(!video.videoWidth) return;
  canvas.width=video.videoWidth; canvas.height=video.videoHeight;
  canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);
  canvas.toBlob(blob=>{ capturedBlob=blob; preview.src=URL.createObjectURL(blob); previewWrap.classList.remove('hidden'); captureBtn.disabled=true; retakeBtn.disabled=false; cameraState.textContent='Evidence captured ✓'; },'image/jpeg',0.9);
}
function resetCapture(){ capturedBlob=null; fallbackImage.value=''; previewWrap.classList.add('hidden'); captureBtn.disabled=!stream; retakeBtn.disabled=true; cameraState.textContent=stream?'Camera live ✓':'Camera offline'; }

startBtn.addEventListener('click',startCamera); captureBtn.addEventListener('click',capture); retakeBtn.addEventListener('click',resetCapture); gpsBtn.addEventListener('click',requestGps);
category.addEventListener('change',()=>hudCategory.textContent=category.value||'Awaiting category');
fallbackImage.addEventListener('change',()=>{ const f=fallbackImage.files[0]; if(!f)return; capturedBlob=f; preview.src=URL.createObjectURL(f); previewWrap.classList.remove('hidden'); retakeBtn.disabled=false; cameraState.textContent='Uploaded evidence ✓'; });

window.addEventListener('deviceorientation',e=>{
  let h=e.webkitCompassHeading ?? (e.alpha!=null ? 360-e.alpha : null);
  if(h!=null){ h=Math.round((h+360)%360); headingState.textContent=`Heading ${h}°`; hudHeading.textContent=`${h}°`; }
});

form.addEventListener('submit',async e=>{
  e.preventDefault();
  if(!capturedBlob){ message.innerHTML='<div class="notice error">Capture or upload photo evidence first.</div>'; return; }
  if(!latInput.value||!lonInput.value){ message.innerHTML='<div class="notice error">Lock GPS or place the pin on the map first.</div>'; return; }
  const fd=new FormData(form); fd.set('image',capturedBlob,'ar-civic-evidence.jpg');
  submitBtn.disabled=true; submitBtn.textContent='Submitting AR report…'; message.innerHTML='<div class="notice info">Geotagging evidence and checking nearby duplicates…</div>';
  try{
    const r=await fetch('/api/issues',{method:'POST',body:fd}); const d=await r.json();
    if(!r.ok){ message.innerHTML=`<div class="notice error">${esc(d.detail||'Submission failed')}</div>`; return; }
    message.innerHTML=`<div class="success-box"><div class="success-icon">✓</div><div class="success-content"><span class="success-kicker">AR Report Registered</span><h3>Complaint #${d.issue.id} entered the municipal workflow.</h3><p>Source: <b>AR Camera</b> · Department: <b>${esc(d.issue.department)}</b></p><div class="success-actions"><a class="button-link" href="/track?id=${d.issue.id}">Track Report</a><a class="button-link ghost" href="/api/issues/${d.issue.id}/report.pdf">Download PDF</a></div></div></div>`;
  }catch(err){ message.innerHTML='<div class="notice error">Cannot connect to CivicSense server.</div>'; }
  finally{ submitBtn.disabled=false; submitBtn.textContent='Submit AR Civic Report →'; }
});
function esc(v){const d=document.createElement('div');d.textContent=String(v??'');return d.innerHTML;}
initMap();
