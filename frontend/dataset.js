async function loadData(){
  const [statsRes,sampleRes]=await Promise.all([fetch('/api/dataset/stats'),fetch('/api/dataset/sample?limit=12')]);
  const stats=await statsRes.json(), rows=await sampleRes.json();
  const mb=(stats.file_size_bytes/1048576).toFixed(1);
  document.getElementById('datasetStats').innerHTML=`
    <div class="stat-card"><span>Total Records</span><strong>${Number(stats.row_count).toLocaleString()}</strong><small>synthetic labeled cases</small></div>
    <div class="stat-card"><span>Columns</span><strong>${stats.column_count}</strong><small>ML + analytics fields</small></div>
    <div class="stat-card"><span>Dataset Size</span><strong>${mb} MB</strong><small>bundled CSV</small></div>
    <div class="stat-card"><span>Avg. Resolution</span><strong>${stats.average_resolution_hours}h</strong><small>resolved synthetic cases</small></div>`;
  document.getElementById('datasetMeta').textContent=`${Number(stats.row_count).toLocaleString()} rows · ${mb} MB`;
  bars('categoryBars',stats.category_counts); bars('statusBars',stats.status_counts);
  document.getElementById('datasetRows').innerHTML=rows.map(r=>`<tr><td>${e(r.complaint_code)}</td><td>${e(r.ward)}</td><td>${e(r.category)}</td><td>${e(r.severity)}</td><td>${e(r.status)}</td><td>${e(r.source)}</td><td>${e(r.model_confidence)}</td><td>${e(r.reported_at.slice(0,10))}</td></tr>`).join('');
}
function bars(id,obj){const el=document.getElementById(id); const max=Math.max(...Object.values(obj)); el.innerHTML=Object.entries(obj).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`<div class="bar-row"><div><span>${e(k)}</span><strong>${Number(v).toLocaleString()}</strong></div><div class="bar-track"><i style="width:${(v/max*100).toFixed(1)}%"></i></div></div>`).join('');}
function e(v){const d=document.createElement('div');d.textContent=String(v??'');return d.innerHTML;}
loadData().catch(()=>{document.getElementById('datasetMeta').textContent='Dataset unavailable';});
