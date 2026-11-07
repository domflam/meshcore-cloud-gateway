'use strict';
const $ = id => document.getElementById(id);
const number = (value, digits=1) => typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('fr-FR', {minimumFractionDigits:digits, maximumFractionDigits:digits}) : '—';
let lastData = null, busy = false, deferredInstall;
const clock = new Intl.DateTimeFormat('fr-FR',{hour:'2-digit',minute:'2-digit'});
const CHARTS = [
  {field:'temperature_c',label:'Température',unit:'°C',color:'var(--chart-temperature)',padding:.3},
  {field:'humidity_pct',label:'Humidité',unit:'%',color:'var(--chart-humidity)',padding:1,floor:0,ceiling:100},
  {field:'pressure_hpa',label:'Pression',unit:'hPa',color:'var(--chart-pressure)',padding:.5,floor:0},
  {field:'wind_speed_mps',label:'Vent',unit:'m/s',color:'var(--chart-wind)',padding:.3,floor:0}
];
function chart(history, config) {
  const model=weatherChartModel(history,config.field,config), pts=model.points;
  $('point-count-'+config.field).textContent = `${pts.length} relevé${pts.length>1?'s':''} disponible${pts.length>1?'s':''}`;
  const svg=$('chart-'+config.field), note=$('history-note-'+config.field);
  note.hidden=true;
  if(config.field==='wind_speed_mps' && pts.some(p=>p.simulated===true)) {
    note.hidden=false;
    note.textContent=pts.every(p=>p.simulated===true)?'Vent simulé · valeur virtuelle à 0,0 m/s. Aucun vent réel mesuré.':'Les portions en pointillés correspondent aux mesures simulées.';
  }
  if(pts.length<2 || model.last===model.first) {
    svg.innerHTML='<p class="empty">Encore un peu de patience : deux relevés à des heures différentes suffisent pour tracer la courbe.</p>';
    svg.setAttribute('aria-label',config.label+' : historique insuffisant');return;
  }
  const width=Math.max(svg.clientWidth,240);
  const x=p=>60+(p.time-model.first)/(model.last-model.first)*(width-75);
  const y=v=>137-(v-model.low)/(model.high-model.low)*110;
  let grid='';
  for(let i=0;i<3;i++){const v=model.low+(model.high-model.low)*i/2;grid+=`<line x1="60" x2="${width-15}" y1="${y(v)}" y2="${y(v)}" stroke="var(--chart-grid)" stroke-dasharray="3 5"/><text x="2" y="${y(v)+4}">${number(v)}</text>`;}
  const segments=[];
  for(const point of pts){if(point.breakBefore||!segments.length)segments.push([]);segments.at(-1).push(point);}
  const gradient='area-'+config.field;
  const lines=segments.map(segment=>{
    const path=segment.map((p,i)=>`${i?'L':'M'}${x(p).toFixed(2)},${y(p.value).toFixed(2)}`).join(' ');
    const fill=segment.length>1?`<path d="${path} L${x(segment.at(-1))},145 L${x(segment[0])},145 Z" fill="url(#${gradient})"/>`:'';
    const dash=segment[0].simulated===true?'stroke-dasharray="6 5"':'';
    return fill+`<path d="${path}" fill="none" stroke="${config.color}" stroke-width="2.2" ${dash} stroke-linejoin="round" vector-effect="non-scaling-stroke"/>`+segment.map(p=>`<circle cx="${x(p)}" cy="${y(p.value)}" r="2.5" fill="${config.color}"/>`).join('');
  }).join('');
  svg.innerHTML=`<svg viewBox="0 0 ${width} 170" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="${gradient}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${config.color}" stop-opacity=".18"/><stop offset="1" stop-color="${config.color}" stop-opacity="0"/></linearGradient></defs>${grid}${lines}<text x="60" y="165">${clock.format(new Date(model.first))}</text><text x="${width-15}" y="165" text-anchor="end">${clock.format(new Date(model.last))}</text></svg>`;
  svg.setAttribute('aria-label', `${config.label} de ${number(model.min)} à ${number(model.max)} ${config.unit}, ${pts.length} relevés`);
  if(config.field==='temperature_c')$('temp-range').textContent=`Min ${number(model.min)}° · Max ${number(model.max)}°`;
}
function freshness(){
  if(!lastData)return;
  const status=$('status');
  if(lastData.mode==='demo'){status.textContent='Exemple daté';status.classList.add('stale');return;}
  if(!navigator.onLine){status.textContent='Hors ligne';status.classList.add('stale');return;}
  const time=Date.parse(lastData.latest?.observed_at), age=(Date.now()-time)/60000;
  const staleAfter=lastData.stale_after_minutes ?? 30;
  status.classList.toggle('stale', !Number.isFinite(age)||age>staleAfter||age< -5);
  status.textContent=!lastData.latest?'Aucun relevé depuis 24 h':!Number.isFinite(age)?'Date inconnue':age< -5?'Horloge à vérifier':age>staleAfter?'Dernier relevé ancien':'Mesures récentes';
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
  for(const config of CHARTS)chart(data.history||[],config);
  freshness();
}
async function refresh(){
  if(busy)return;busy=true;$('refresh').disabled=true;
  try{
    const response=await fetch('/api/weather',{cache:'no-store',credentials:'same-origin'});
    const data=await response.json();
    if(!response.ok)throw Error(data.error||'Lecture indisponible');
    lastData=data;$('error').hidden=true;render(data);
  }catch(e){
    $('error').textContent=lastData?'Actualisation impossible. Les dernières valeurs affichées sont conservées ; vérifie leur date.':e.message;
    $('error').hidden=false;$('status').textContent='Lecture indisponible';$('status').classList.add('stale');
  }finally{busy=false;$('refresh').disabled=false;}
}
$('refresh').addEventListener('click',refresh);
window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();deferredInstall=e;$('install').hidden=false;});
$('install').addEventListener('click',async()=>{if(!deferredInstall)return;await deferredInstall.prompt();await deferredInstall.userChoice;deferredInstall=null;$('install').hidden=true;});
window.addEventListener('appinstalled',()=>{$('install').hidden=true;});
let resizeTimer;
window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if(lastData)for(const config of CHARTS)chart(lastData.history||[],config);},150);});
window.addEventListener('online',refresh);window.addEventListener('offline',freshness);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
if('serviceWorker' in navigator && window.isSecureContext)navigator.serviceWorker.register('/sw.js').catch(()=>{});
refresh();setInterval(()=>{if(!document.hidden)refresh();},90000);setInterval(freshness,30000);
