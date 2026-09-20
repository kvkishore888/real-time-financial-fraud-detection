const form=document.querySelector('#form');
function loadDemo(){const vals={amount:4800,transactions_last_10m:7,amount_last_10m:9200,distance_from_home_km:850,account_age_days:12,merchant_risk:.82,hour:1,new_device:'true',related_accounts:5,shared_devices:3,shared_ips:2,shared_beneficiaries:4,account_id:'acct-risky',device_id:'device-shared',ip_address:'ip-shared',beneficiary_id:'beneficiary-shared'};Object.entries(vals).forEach(([k,v])=>form.elements[k].value=v);form.requestSubmit()}
form.addEventListener('submit',async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(form));['amount','transactions_last_10m','amount_last_10m','distance_from_home_km','account_age_days','merchant_risk','hour'].forEach(k=>data[k]=Number(data[k]));data.new_device=data.new_device==='true';const res=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const out=await res.json();if(!res.ok)return alert(out.error);render(out);loadEvents()});
function render(o){document.querySelector('#score').textContent=o.transaction.score;document.querySelector('#decision').textContent=o.transaction.decision;document.querySelector('#risk').textContent=o.transaction.risk_level+' risk';document.querySelector('#reasons').innerHTML=o.reasons.map(r=>`<div class="reason">${r}</div>`).join('');document.querySelector('#bars').innerHTML=Object.entries(o.signals).map(([k,v])=>`<div class="bar"><div class="bar-top"><span>${k.replaceAll('_',' ')}</span><b>${v}%</b></div><div class="track"><div class="fill" style="width:${v}%"></div></div></div>`).join('');document.querySelector('#history').innerHTML=`<b>Account history evidence</b><br>Average amount: ${o.account_history.avg_amount} · Transactions/30d: ${o.account_history.transactions_last_30d} · Previous fraud flags: ${o.account_history.previous_fraud_flags} · Failed attempts: ${o.account_history.failed_attempts_30d}`;const n=o.network;document.querySelector('#network').innerHTML=`<b>Discovered network evidence</b><br>Related accounts: ${n.related_accounts} · Shared devices: ${n.shared_devices} · Shared IPs: ${n.shared_ips} · Shared beneficiaries: ${n.shared_beneficiaries}`}
async function loadEvents(){const rows=await (await fetch('/api/events')).json();document.querySelector('#events').innerHTML=rows.length?rows.map(x=>`<tr><td>${new Date(x.timestamp).toLocaleTimeString()}</td><td>$${Number(x.amount).toLocaleString()}</td><td>${x.score}</td><td><span class="pill ${x.decision}">${x.decision}</span></td></tr>`).join(''):'<tr><td colspan="4" class="empty">No transactions yet.</td></tr>'}
loadEvents();

const uploadForm=document.querySelector('#uploadForm');
uploadForm.addEventListener('submit',async e=>{
  e.preventDefault();
  const file=document.querySelector('#datasetFile').files[0];
  if(!file)return;
  const body=new FormData(); body.append('file',file);
  const res=await fetch('/api/analyze-dataset',{method:'POST',body});
  const out=await res.json();
  if(!res.ok)return alert(out.error);
  document.querySelector('#datasetSummary').textContent=out.filename+' · '+out.rows_processed+' rows · ALLOW '+out.summary.ALLOW+' · STEP-UP '+out.summary['STEP-UP']+' · REVIEW '+out.summary.REVIEW+' · BLOCK '+out.summary.BLOCK;
  document.querySelector('#datasetResults').innerHTML=out.results.map(x=>'<tr><td>'+x.row+'</td><td>$'+Number(x.amount).toLocaleString()+'</td><td>'+x.score+'</td><td><span class="pill '+x.decision+'">'+x.decision+'</span></td><td>'+x.reasons[0]+'</td></tr>').join('');
});
function downloadSample(){
  const csv='amount,transactions_last_10m,amount_last_10m,distance_from_home_km,account_age_days,merchant_risk,hour,new_device,related_accounts,shared_devices,shared_ips,shared_beneficiaries\n450,1,450,4,720,0.05,14,false,0,0,0,0\n750,2,1400,15,400,0.30,13,false,5,3,3,4\n4800,7,9200,850,12,0.82,1,true,5,3,3,4\n';
  const blob=new Blob([csv],{type:'text/csv'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='fraudshield_sample.csv'; a.click(); URL.revokeObjectURL(a.href);
}

(function(){
 const root=document.documentElement,main=document.querySelector('#appMain'),buttons=[...document.querySelectorAll('.layout-btn')],cards=[...document.querySelectorAll('.interactive-card')];
 function setLayout(name){root.dataset.layout=name;buttons.forEach(b=>b.classList.toggle('active',b.dataset.layout===name));localStorage.setItem('fraudshield-layout',name)}
 setLayout(localStorage.getItem('fraudshield-layout')||'balanced');
 buttons.forEach(b=>b.addEventListener('click',()=>setLayout(b.dataset.layout)));
 let raf=0,tx=0,ty=0;
 addEventListener('mousemove',e=>{if(matchMedia('(prefers-reduced-motion: reduce)').matches||innerWidth<800)return;tx=(e.clientX/innerWidth-.5)*2;ty=(e.clientY/innerHeight-.5)*2;if(raf)return;raf=requestAnimationFrame(()=>{cards.forEach(card=>{const d=Number(card.dataset.depth||5);card.style.setProperty('--mx',(tx*d).toFixed(2)+'px');card.style.setProperty('--my',(ty*d*.65).toFixed(2)+'px')});main?.style.setProperty('--cursor-x',(tx*100).toFixed(1)+'%');main?.style.setProperty('--cursor-y',(ty*100).toFixed(1)+'%');raf=0})},{passive:true});
 addEventListener('mouseleave',()=>cards.forEach(c=>{c.style.setProperty('--mx','0px');c.style.setProperty('--my','0px')}));
})();
