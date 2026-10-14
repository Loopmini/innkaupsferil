'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = (n, currency) => `${new Intl.NumberFormat('is-IS', {maximumFractionDigits:2}).format(n)} ${esc(currency)}`;
const date = s => new Date(s).toLocaleDateString('is-IS');
const stale = o => Date.now() - Date.parse(o.observed_at) > 30*86400000;
let state = {offers:[], projects:[], items:[], history:[], suppliers:[]};
async function api(path, data) {
  const res = await fetch('/api/' + path, data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
  const value = await res.json(); if(!res.ok) throw Error(value.error || 'Villa í samskiptum'); return value;
}
function options(values, first='') {return (first ? `<option value="">${esc(first)}</option>` : '') + values.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');}
async function refresh() {
  const oldCategory=$('category').value, oldSupplier=$('supplier').value, oldProject=$('project-select').value;
  state = await api('catalogue');
  $('category').innerHTML=options([...new Set(state.offers.map(o=>o.category || 'Óflokkað'))].sort(),'Allir flokkar');
  $('supplier').innerHTML=options([...new Set(state.offers.map(o=>o.supplier))].sort(),'Allir birgjar');
  $('category').value=oldCategory; $('supplier').value=oldSupplier;
  const projects = state.projects.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join('');
  $('project-select').innerHTML=projects; $('add-project').innerHTML=projects;
  if(state.projects.some(p=>String(p.id)===oldProject)) $('project-select').value=oldProject;
  const groups = new Map(); state.offers.forEach(o=>groups.set(o.match_key, (groups.get(o.match_key)||new Set()).add(o.supplier)));
  $('stats').innerHTML = [[state.offers.length,'Vörufærslur'],[new Set(state.offers.map(o=>o.supplier)).size,'Birgjar með gögn'],[[...groups.values()].filter(s=>s.size>1).length,'Vörur hjá fleiri birgjum'],[state.offers.filter(stale).length,'Verð eldri en 30 daga']].map(([n,s])=>`<div class="stat"><span>${s}</span><strong>${n}</strong></div>`).join('');
  renderProducts(); renderProjects(); renderSuppliers();
}
function table(headers, rows) {return `<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`;}
function renderProducts() {
  const q=$('search').value.toLocaleLowerCase('is');
  const rows=state.offers.filter(o=>(!$('category').value || (o.category||'Óflokkað')===$('category').value)&&(!$('supplier').value||o.supplier===$('supplier').value)&&[o.name,o.sku,o.brand,o.gtin,o.manufacturer_part,o.supplier].join(' ').toLocaleLowerCase('is').includes(q));
  $('result-count').textContent=`${rows.length} vörufærslur`;
  $('products').innerHTML=rows.length?table(['VARA / VÖRUNÚMER','BIRGIR','EININGAVERÐ ÁN VSK','VERÐHEIMILD',''],rows.map(o=>`<tr><td><b>${esc(o.name)}</b><small>${esc(o.sku)} · ${esc(o.category||'Óflokkað')}</small></td><td>${esc(o.supplier)}<small>${esc(o.brand)}</small></td><td><strong>${money(o.unit_price,o.currency)} / ${esc(o.unit)}</strong><small>${o.pack_quantity} ${esc(o.unit)} / pakkning · ${money(o.net_price,o.currency)}</small></td><td><span class="pill ${stale(o)?'warn':''}">${date(o.observed_at)}</span><small>${stale(o)?'Eldra en 30 daga':'Dagsetning heimildar'}</small></td><td><button data-detail="${o.id}">Skoða</button></td></tr>`).join('')):`<div class="empty"><h2>${state.offers.length?'Engar vörur passa við leitina':'Byggjum upp vörugrunninn'}</h2><p>${state.offers.length?'Prófaðu annað leitarorð eða síu.':'Lestu inn fyrsta verðlistann. Hér birtast svo vörur, birgjar og sambærileg einingaverð.'}</p></div>`;
}
function detail(id) {
  const o=state.offers.find(x=>x.id===id);
  const peers=state.offers.filter(x=>x.match_key===o.match_key && x.currency===o.currency && x.unit===o.unit).sort((a,b)=>a.unit_price-b.unit_price);
  const related=state.offers.filter(x=>x.category && x.category===o.category && x.match_key!==o.match_key).slice(0,12);
  $('detail').innerHTML=`<h2>${esc(o.name)}</h2><p class="muted">${esc(o.brand)} · ${esc(o.manufacturer_part||o.sku)} · ${esc(o.category||'Óflokkað')}</p><p>${o.match_key.startsWith('unmatched:')?'Engin örugg vörutenging: GTIN eða framleiðandi ásamt framleiðslunúmeri vantar.':'Tenging byggð á '+(o.gtin?'GTIN':'framleiðanda og framleiðslunúmeri')+'. Samanburður sýnir sömu einingu og gjaldmiðil. Staðfestu vörulýsingu fyrir pöntun.'}</p>`+table(['BIRGIR','PAKKNING','VERÐ ÁN VSK / EININGU','HEIMILD',''],peers.map(x=>`<tr><td>${esc(x.supplier)}<small>${esc(x.sku)}</small></td><td>${x.pack_quantity} ${esc(x.unit)}</td><td>${money(x.unit_price,x.currency)} / ${esc(x.unit)}</td><td>${x.url?`<a href="${esc(x.url)}" target="_blank" rel="noopener noreferrer">Vara hjá birgi ↗</a>`:'Innlesinn verðlisti'}<small>${date(x.observed_at)}</small></td><td><button data-add="${x.id}">Á lista</button></td></tr>`).join(''))+`<h3>Verðsaga · ${esc(o.supplier)}</h3>`+table(['DAGSETNING','VERÐ ÁN VSK / EININGU'],state.history.filter(h=>h.offer_id===id).map(h=>`<tr><td>${date(h.observed_at)}</td><td>${money(h.price/(h.vat_included?1+h.vat_rate/100:1)/h.pack_quantity,h.currency)} / ${esc(h.unit)}</td></tr>`).join(''))+(related.length?`<h3>Aðrar vörur í sama flokki</h3><p class="muted">Þetta eru ekki staðfestar staðgönguvörur. Skoða þarf stærðir, efni og notkun.</p><div class="cards">${related.map(x=>`<button data-detail="${x.id}">${esc(x.name)}<br><small>${esc(x.supplier)}</small></button>`).join('')}</div>`:'');
  if(!$('detail-dialog').open) $('detail-dialog').showModal();
}
function renderProjects() {
  const pid=Number($('project-select').value);
  const rows=state.items.filter(i=>i.project_id===pid).map(i=>({...i,offer:state.offers.find(o=>o.id===i.offer_id)})).filter(i=>i.offer);
  if(!rows.length){$('project-items').innerHTML='<div class="empty"><h2>Innkaupalistinn er tómur</h2><p>Stofnaðu verkefni og veldu „Á lista“ í vörusamanburði.</p></div>';return;}
  const totals={}; rows.forEach(i=>{const o=i.offer; const key=o.supplier+' · '+o.currency; totals[key]=(totals[key]||0)+o.net_price*i.quantity;});
  $('project-items').innerHTML=table(['VARA','BIRGIR','PAKKNINGAR','SAMTALS ÁN VSK',''],rows.map(i=>`<tr><td>${esc(i.offer.name)}<small>${i.offer.pack_quantity} ${esc(i.offer.unit)} / pakkning</small></td><td>${esc(i.offer.supplier)}</td><td><input aria-label="Fjöldi pakkninga fyrir ${esc(i.offer.name)}" type="number" min="0" step="1" value="${i.quantity}" data-qty="${i.offer.id}"></td><td>${money(i.quantity*i.offer.net_price,i.offer.currency)}</td><td><button data-remove="${i.offer.id}">Fjarlægja</button></td></tr>`).join(''))+`<div class="totals">${Object.entries(totals).map(([key,n])=>`${esc(key)}: <b>${money(n,key.split(' · ').pop())}</b>`).join('<br>')}</div><p class="muted">Áætlaður vörukostnaður á nýjustu innlesnu verðum. Flutningur og afslættir eru ekki innifalin. Þetta er innkaupalisti; engin pöntun er send.</p>`;
}
function renderSuppliers() {
  $('supplier-cards').innerHTML=[...new Set([...state.suppliers,...state.offers.map(o=>o.supplier)])].sort().map(s=>{const rows=state.offers.filter(o=>o.supplier===s);return `<div class="card"><h3>${esc(s)}</h3><p class="muted">${rows.length} vörufærslur</p><span class="pill ${rows.length?'':'warn'}">${rows.length?'CSV-gögn innlesin':'Gögn vantar'}</span></div>`;}).join('');
}
async function run(fn){try{await fn();}catch(e){$('status').textContent=e.message;}}
document.addEventListener('click',e=>{
  const b=e.target.closest('button');if(!b)return;
  if(b.dataset.view){for(const id of ['catalogue','projects','suppliers'])$(id).hidden=id!==b.dataset.view;document.querySelectorAll('.nav').forEach(n=>n.classList.toggle('active',n===b));$('heading').textContent={catalogue:'Vörugrunnur',projects:'Innkaupalistar',suppliers:'Birgjar'}[b.dataset.view];}
  if(b.dataset.close)$(b.dataset.close).close();
  if(b.dataset.detail)detail(Number(b.dataset.detail));
  if(b.dataset.add){$('detail-dialog').close();if(!state.projects.length){$('project-dialog').showModal();$('status').textContent='Stofnaðu fyrst verkefni og bættu svo vörunni á listann.';return;}$('add-offer').value=b.dataset.add;$('add-dialog').showModal();}
  if(b.dataset.remove)run(async()=>{await api('items',{project_id:Number($('project-select').value),offer_id:Number(b.dataset.remove),quantity:0});await refresh();});
});
$('search').addEventListener('input',renderProducts);['category','supplier'].forEach(id=>$(id).addEventListener('change',renderProducts));
$('project-select').addEventListener('change',renderProjects);
$('project-items').addEventListener('change',e=>{if(e.target.dataset.qty)run(async()=>{try{await api('items',{project_id:Number($('project-select').value),offer_id:Number(e.target.dataset.qty),quantity:e.target.value});}finally{await refresh();}});});
$('import-open').onclick=()=>{$('import-error').textContent='';$('import-dialog').showModal();};
$('project-new').onclick=()=>$('project-dialog').showModal();
$('import-form').onsubmit=async e=>{e.preventDefault();$('import-submit').disabled=true;try{const f=$('csv-file').files[0];if(f.size>5000000)throw Error('Hámark 5 MB.');const r=await api('import',{csv:await f.text()});await refresh();$('import-dialog').close();$('status').textContent=`${r.imported} vörufærslur lesnar inn.`;}catch(err){$('import-error').textContent=err.message;}finally{$('import-submit').disabled=false;}};
$('project-form').onsubmit=e=>{e.preventDefault();run(async()=>{await api('projects',{name:$('project-name').value});$('project-dialog').close();$('project-name').value='';await refresh();});};
$('add-form').onsubmit=e=>{e.preventDefault();run(async()=>{const pid=Number($('add-project').value),oid=Number($('add-offer').value),existing=state.items.find(i=>i.project_id===pid&&i.offer_id===oid);await api('items',{project_id:pid,offer_id:oid,quantity:Number($('add-quantity').value)+(existing?.quantity||0)});$('add-dialog').close();await refresh();$('status').textContent='Vara komin á innkaupalista.';});};
run(refresh);
