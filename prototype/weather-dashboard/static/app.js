'use strict';
const $ = id => document.getElementById(id);
const number = (value, digits=1) => typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('fr-FR', {minimumFractionDigits:digits, maximumFractionDigits:digits}) : '—';
let lastData = null, busy = false, deferredInstall;
const clock = new Intl.DateTimeFormat('fr-FR',{hour:'2-digit',minute:'2-digit'});
function chart(history) {
  const pts = history.filter(p=>typeof p.temperature_c === 'number' && Number.isFinite(p.temperature_c) && Number.isFinite(Date.parse(p.observed_at)));
  $('point-count').textContent = `${pts.length} relevé${pts.length>1?'s':''} disponible${pts.length>1?'s':''}`;
  const svg = $('chart');
  if(pts.length<2) {svg.innerHTML='<p class="empty">Encore un peu de patience : deux relevés suffisent pour tracer la courbe.</p>';return;}
  const times=pts.map(p=>Date.parse(p.observed_at)), vals=pts.map(p=>p.temperature_c);
  const min=Math.min(...vals), max=Math.max(...vals), low=min-.3, high=max+.3;
  const x=i=>42+(times[i]-times[0])/(times.at(-1)-times[0]||1)*850;
  const y=v=>137-(v-low)/(high-low)*110;
  const path=pts.map((p,i)=>`${i?'L':'M'}${x(i).toFixed(2)},${y(p.temperature_c).toFixed(2)}`).join(' ');
  let grid='';
  for(let i=0;i<3;i++){const v=low+(high-low)*i/2;grid+=`<line x1="42" x2="892" y1="${y(v)}" y2="${y(v)}" stroke="#e7eadf" stroke-dasharray="3 5"/><text x="2" y="${y(v)+4}">${number(v)}</text>`;}
  svg.innerHTML=`<svg viewBox="0 0 930 170" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9cad81" stop-opacity=".22"/><stop offset="1" stop-color="#9cad81" stop-opacity="0"/></linearGradient></defs>${grid}<path d="${path} L892,145 L42,145 Z" fill="url(#area)"/><path d="${path}" fill="none" stroke="#6e8757" stroke-width="2.2" stroke-linejoin="round" vector-effect="non-scaling-stroke"/><circle cx="${x(pts.length-1)}" cy="${y(vals.at(-1))}" r="3" fill="#6e8757"/><text x="42" y="165">${clock.format(new Date(times[0]))}</text><text x="892" y="165" text-anchor="end">${clock.format(new Date(times.at(-1)))}</text></svg>`;
  svg.setAttribute('aria-label', `Température de ${number(min)} à ${number(max)} degrés Celsius, ${pts.length} relevés`);
  $('temp-range').textContent=`Min ${number(min)}° · Max ${number(max)}°`;
}
function freshness(){
  if(!lastData)return;
  const status=$('status');
  if(lastData.mode==='demo'){status.textContent='Exemple daté';status.classList.add('stale');return;}
  if(!navigator.onLine){status.textContent='Hors ligne';status.classList.add('stale');return;}
  const time=Date.parse(lastData.latest?.observed_at), age=(Date.now()-time)/60000;
  status.classList.toggle('stale', !Number.isFinite(age)||age>5||age< -5);
  status.textContent=!lastData.latest?'Aucun relevé depuis 24 h':!Number.isFinite(age)?'Date inconnue':age< -5?'Horloge à vérifier':age>5?'Dernier relevé ancien':'Mesures récentes';
}
function render(data){
  const p=data.latest;
  $('demo').hidden=data.mode!=='demo';
  $('temperature').textContent=number(p?.temperature_c);
  $('humidity').textContent=number(p?.humidity_pct,0);
  $('pressure').textContent=number(p?.pressure_hpa);
  $('wind').textContent=number(p?.wind_speed_mps);
  $('voltage').textContent=number(p?.voltage_v,2)+' V';
  $('node').textContent=data.node_id;
  $('simulated').hidden=p?.wind_simulated!==true;
  $('wind-note').textContent=p?.wind_simulated===true?'Valeur virtuelle · anémomètre à venir':p?.wind_speed_mps==null?'Aucune mesure disponible':p?.wind_simulated===false?'Vitesse mesurée à la station':'Origine de la mesure non précisée';
  $('last-seen').textContent=p?'Dernier relevé : '+new Date(p.observed_at).toLocaleString('fr-FR'):'Aucun relevé sur les dernières 24 heures';
  $('temp-range').textContent='En attente de mesures';
  chart(data.history||[]);freshness();
}
function showLogin(){
  lastData=null;
  $('dashboard').hidden=true;$('login').hidden=false;$('logout').hidden=true;
  $('password').focus();
}
async function refresh(){
  if(busy)return;busy=true;$('refresh').disabled=true;
  try{
    const response=await fetch('/api/weather',{cache:'no-store',credentials:'same-origin'});
    if(response.status===401){showLogin();return;}
    const data=await response.json();
    if(!response.ok)throw Error(data.error||'Lecture indisponible');
    lastData=data;$('error').hidden=true;$('login').hidden=true;$('dashboard').hidden=false;
    $('logout').hidden=data.mode==='demo';render(data);
  }catch(e){
    $('error').textContent=lastData?'Actualisation impossible. Les dernières valeurs affichées sont conservées ; vérifie leur date.':e.message;
    $('error').hidden=false;$('status').textContent='Lecture indisponible';$('status').classList.add('stale');
  }finally{busy=false;$('refresh').disabled=false;}
}
$('refresh').addEventListener('click',refresh);
$('login-form').addEventListener('submit',async e=>{
  e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;
  try{const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:$('password').value})});const data=await r.json();if(!r.ok)throw Error(data.error);$('password').value='';$('login-error').textContent='';await refresh();}catch(e){$('login-error').textContent=e.message;}finally{button.disabled=false;}
});
$('logout').addEventListener('click',async()=>{try{const r=await fetch('/api/logout',{method:'POST'});if(!r.ok)throw Error();showLogin();}catch{$('error').textContent='Déconnexion impossible. Réessaie.';$('error').hidden=false;}});
window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();deferredInstall=e;$('install').hidden=false;});
$('install').addEventListener('click',async()=>{if(!deferredInstall)return;await deferredInstall.prompt();await deferredInstall.userChoice;deferredInstall=null;$('install').hidden=true;});
window.addEventListener('appinstalled',()=>{$('install').hidden=true;});
window.addEventListener('online',refresh);window.addEventListener('offline',freshness);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
if('serviceWorker' in navigator && window.isSecureContext)navigator.serviceWorker.register('/sw.js').catch(()=>{});
refresh();setInterval(()=>{if(!document.hidden)refresh();},90000);setInterval(freshness,30000);
