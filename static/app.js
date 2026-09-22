const form=document.querySelector('#form');
const DEMO_PROFILES={
  'ALLOW':{amount:850,transactions_last_10m:1,amount_last_10m:850,distance_from_home_km:8,account_age_days:420,merchant_risk:.10,hour:14,new_device:'false'},
  'STEP-UP':{amount:2500,transactions_last_10m:3,amount_last_10m:5000,distance_from_home_km:80,account_age_days:300,merchant_risk:.25,hour:14,new_device:'true'},
  'REVIEW':{amount:5000,transactions_last_10m:5,amount_last_10m:9000,distance_from_home_km:350,account_age_days:40,merchant_risk:.60,hour:2,new_device:'true'},
  'BLOCK':{amount:25000,transactions_last_10m:12,amount_last_10m:50000,distance_from_home_km:1000,account_age_days:1,merchant_risk:1.00,hour:1,new_device:'true'}
};
function loadDecisionDemo(decision){
  const vals={...DEMO_PROFILES[decision],
    account_id:'demo-'+decision.toLowerCase().replace('-','')+'-'+Date.now(),
    device_id:'device-'+decision.toLowerCase().replace('-','')+'-'+Date.now(),
    ip_address:'ip-'+decision.toLowerCase().replace('-','')+'-'+Date.now(),
    beneficiary_id:'beneficiary-'+decision.toLowerCase().replace('-','')+'-'+Date.now(),
    related_accounts:decision==='BLOCK'?5:0,
    shared_devices:decision==='BLOCK'?3:0,
    shared_ips:decision==='BLOCK'?3:0,
    shared_beneficiaries:decision==='BLOCK'?4:0,
    device_change_days:decision==='BLOCK'?1:365,
    demo_scenario:decision};
  Object.entries(vals).forEach(([k,v])=>{if(form.elements[k])form.elements[k].value=v});
  // Demo buttons only load the scenario. The popup appears after the user clicks Analyze transaction.
}
function loadDemo(){loadDecisionDemo('BLOCK')}
form.addEventListener('submit',async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(form));['amount','transactions_last_10m','amount_last_10m','distance_from_home_km','account_age_days','merchant_risk','hour'].forEach(k=>data[k]=Number(data[k]));data.new_device=data.new_device==='true';data.demo_scenario=data.demo_scenario||'';const res=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const out=await res.json();if(!res.ok)return alert(out.error);render(out);showDecisionPopup(out);loadEvents()});

function showDecisionPopup(o){
  const t=o.transaction;
  const configs={
    'ALLOW':{icon:'✓',title:'Transaction Allowed',subtitle:'This transaction appears consistent with the account profile.',className:'ALLOW',action:'The transaction can proceed normally.'},
    'STEP-UP':{icon:'!',title:'Additional Verification Required',subtitle:'Some unusual signals were detected. Verify the transaction before proceeding.',className:'STEP-UP',action:'Request additional authentication such as OTP or biometric verification.'},
    'REVIEW':{icon:'!',title:'Transaction Sent for Review',subtitle:'Multiple risk signals require further investigation.',className:'REVIEW',action:'Hold the transaction for manual or enhanced fraud review.'},
    'BLOCK':{icon:'×',title:'Transaction Blocked',subtitle:'Strong risk signals indicate potentially fraudulent activity.',className:'BLOCK',action:'Stop the transaction and flag it for investigation.'}
  };
  const c=configs[t.decision]||configs.REVIEW;
  let modal=document.querySelector('#decisionModal');
  if(!modal){
    modal=document.createElement('div');
    modal.id='decisionModal';
    modal.className='decision-modal';
    modal.innerHTML='<div class="decision-backdrop"></div><div class="decision-dialog" role="dialog" aria-modal="true"><button class="decision-close" type="button" aria-label="Close">×</button><div id="decisionIcon" class="decision-icon"></div><div class="decision-eyebrow">REAL-TIME DECISION</div><h2 id="decisionTitle"></h2><p id="decisionSubtitle"></p><div class="decision-score"><span>Risk Score</span><strong id="decisionScore"></strong><b id="decisionRisk"></b></div><div class="decision-reasons"><div class="decision-label">Key Evidence</div><div id="decisionReasons"></div></div><div class="decision-action"><div class="decision-label">Recommended Action</div><p id="decisionAction"></p></div><button id="decisionDone" class="decision-done" type="button">Continue</button></div>';
    document.body.appendChild(modal);
    const close=()=>{modal.classList.remove('show');document.body.classList.remove('modal-open')};
    modal.querySelector('.decision-backdrop').addEventListener('click',close);
    modal.querySelector('.decision-close').addEventListener('click',close);
    modal.querySelector('#decisionDone').addEventListener('click',close);
    document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});
  }
  modal.className='decision-modal '+c.className;
  modal.querySelector('#decisionIcon').textContent=c.icon;
  modal.querySelector('#decisionTitle').textContent=c.title;
  modal.querySelector('#decisionSubtitle').textContent=c.subtitle;
  modal.querySelector('#decisionScore').textContent=t.score+'/100';
  modal.querySelector('#decisionRisk').textContent=t.risk_level+' RISK';
  modal.querySelector('#decisionReasons').innerHTML=(o.reasons||[]).slice(0,c.className==='BLOCK'?8:4).map(r=>'<div class="decision-reason">✓ '+r+'</div>').join('');
  modal.querySelector('#decisionAction').textContent=c.action;
  requestAnimationFrame(()=>{modal.classList.add('show');document.body.classList.add('modal-open')});
}

function render(o){document.querySelector('#score').textContent=o.transaction.score;document.querySelector('#decision').textContent=o.transaction.decision;document.querySelector('#risk').textContent=o.transaction.risk_level+' risk';document.querySelector('#reasons').innerHTML=o.reasons.map(r=>`<div class="reason">${r}</div>`).join('');document.querySelector('#bars').innerHTML=Object.entries(o.signals).map(([k,v])=>`<div class="bar"><div class="bar-top"><span>${k.replaceAll('_',' ')}</span><b>${v}%</b></div><div class="track"><div class="fill" style="width:${v}%"></div></div></div>`).join('');document.querySelector('#history').innerHTML=`<b>Account history evidence</b><br>Average amount: ${o.account_history.avg_amount} · Transactions/30d: ${o.account_history.transactions_last_30d} · Previous fraud flags: ${o.account_history.previous_fraud_flags} · Failed attempts: ${o.account_history.failed_attempts_30d}`;const n=o.network;document.querySelector('#network').innerHTML=`<b>Discovered network evidence</b><br>Related accounts: ${n.related_accounts} · Shared devices: ${n.shared_devices} · Shared IPs: ${n.shared_ips} · Shared beneficiaries: ${n.shared_beneficiaries}`}
async function loadEvents(){const rows=await (await fetch('/api/events')).json();document.querySelector('#events').innerHTML=rows.length?rows.map(x=>`<tr><td>${new Date(x.timestamp).toLocaleTimeString()}</td><td>₹${Number(x.amount).toLocaleString('en-IN')}</td><td>${x.score}</td><td><span class="pill ${x.decision}">${x.decision}</span></td></tr>`).join(''):'<tr><td colspan="4" class="empty">No transactions yet.</td></tr>'}
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
  document.querySelector('#datasetResults').innerHTML=out.results.map(x=>'<tr><td>'+x.row+'</td><td>₹'+Number(x.amount).toLocaleString('en-IN')+'</td><td>'+x.score+'</td><td><span class="pill '+x.decision+'">'+x.decision+'</span></td><td>'+x.reasons[0]+'</td></tr>').join('');
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
