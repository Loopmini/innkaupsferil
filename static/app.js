'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = (n, currency) => `${new Intl.NumberFormat('is-IS', {maximumFractionDigits:2}).format(n)} ${esc(currency)}`;
const date = s => s ? new Date(s).toLocaleDateString('is-IS') : 'Dagsetning vantar';
const stale = o => o.price !== null && Date.now() - Date.parse(o.observed_at) > 30*86400000;
let pageLimit=60, browseAll=false;
const sourceLabel=o=>({market:'Opinn markaður',purchase:'Fyrri innkaup',reference:'Vörutilvísun',import:'Innlesið verð'}[o.source_kind]||'Innlesið verð');
const priceCell=o=>o.unit_price!=null?`<strong>${money(o.unit_price,o.currency)} / ${esc(o.unit)}</strong><small>Án VSK · ${o.pack_quantity} ${esc(o.unit)} / pakkning</small><small>Pakkning: ${money(o.price,o.currency)} ${o.vat_included?'m. VSK':'án VSK'}</small>`:o.price!=null?`<strong>${money(o.price,o.currency)} / pakkning</strong><small>${o.vat_included===true?'Með VSK':'VSK óstaðfest'} · ${o.pack_quantity?o.pack_quantity+' '+esc(o.unit):'magn sölueiningar óstaðfest'}</small>`:`<span class="muted">${esc(o.price_status||'Verð vantar')}</span>`;
const attrsLabel=o=>{const a=ProductSearch.attributes(o);return a.kind==='drill'?[a.diameter_mm!=null?a.diameter_mm+' mm':'',({steel:'Stál / málmur',wood:'Tré',masonry:'Steinn / múr',tile:'Flísar / gler'})[a.usage]||'Notkun óstaðfest',a.inferred?'Greint úr lýsingu':'Staðfest vörueinkenni'].filter(Boolean).join(' · '):'';};
const link=o=>o.url?`<a href="${esc(o.url)}" target="_blank" rel="noopener noreferrer">${o.link_kind==='category'?'Birgjaflokkur ↗':'Skoða hjá birgi ↗'}</a>`:'Vörutengil vantar';
let state = {offers:[], projects:[], items:[], history:[], suppliers:[]};
async function api(path, data) {
  const res = await fetch('/api/' + path, data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
  const value = await res.json(); if(!res.ok) throw Error(value.error || 'Villa í samskiptum'); return value;
}
function options(values, first='') {return (first ? `<option value="">${esc(first)}</option>` : '') + values.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');}
async function refresh() {
  const oldCategory=$('category').value, oldSupplier=$('supplier').value, oldProject=$('project-select').value;
  state = await api('catalogue');
  $('category').innerHTML=options([...new Set(state.offers.map(o=>ProductGroups.classify(o)))].sort(),'Allir flokkar');
  $('supplier').innerHTML=options([...new Set(state.offers.map(o=>o.supplier))].sort(),'Allir birgjar');
  $('category').value=oldCategory; $('supplier').value=oldSupplier;
  const projects = state.projects.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join('');
  $('project-select').innerHTML=projects; $('add-project').innerHTML=projects;
  if(state.projects.some(p=>String(p.id)===oldProject)) $('project-select').value=oldProject;
  const purchases=state.offers.filter(o=>o.source_kind==='purchase'),market=state.offers.filter(o=>o.source_kind==='market');
  $('stats').innerHTML = [[purchases.length,'Vörur úr innkaupagögnum'],[market.length,'Vörufærslur af markaði'],[market.filter(o=>o.price!=null).length,'Birt opinber verð'],[market.filter(o=>o.price==null).length,'Markaðsverð vantar']].map(([n,label])=>`<div class="stat"><span>${label}</span><strong>${n}</strong></div>`).join('');
  const m=state.metadata?.project;
  $('coverage').textContent=(m?`${m.invoiceProducts} vöruskráningar úr ${m.invoiceRows} reikningslínum · ${m.dateStart}–${m.dateEnd}. Magn er reikningsmagn, ekki mæld notkun. Kaupverð vantar. `:'Einkagögn úr verkefni hafa ekki verið sett í þessa uppsetningu. ')+(state.metadata?.market?.scope||'')+' Nettóverð birtist aðeins þegar VSK og pakkastærð eru þekkt.';
  renderProducts(); renderProjects(); renderSuppliers(); renderSync(state.metadata?.sync||{});
}
function table(headers, rows) {return `<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`;}
function renderProducts() {
  if(!$('search').value.trim()&&!$('category').value&&!browseAll){
    const filtered=state.offers.filter(o=>(!$('supplier').value||o.supplier===$('supplier').value)&&(!$('source-filter').value||o.source_kind===$('source-filter').value));
    const groups={};for(const o of filtered){const group=ProductGroups.classify(o);(groups[group]||=[]).push(o);}
    $('catalogue-title').textContent='Vöruflokkar';$('result-count').textContent=Object.keys(groups).length+' flokkar';
    $('search-summary').textContent='Veldu flokk eða leitaðu beint að vöru. Flokkayfirlitið er sjálfvirkt greint úr heitum og fyrri flokkun birgja.';
    $('products').innerHTML='<div class="cards category-cards">'+Object.entries(groups).sort(([a],[b])=>a.localeCompare(b,'is')).map(([name,items])=>`<button class="card category-card" data-category="${esc(name)}"><h3>${esc(name)}</h3><strong>${items.length} vörufærslur</strong><p>${new Set(items.map(o=>o.supplier)).size} birgjar · ${items.filter(o=>o.price!=null).length} með verði</p><span>Skoða flokk →</span></button>`).join('')+'</div><p><button id="browse-all">Sýna allar vörur í lista</button></p>';
    return;
  }
  $('catalogue-title').textContent=$('category').value||'Leitarniðurstöður';
  const query=ProductSearch.parse($('search').value);
  const rows=state.offers.filter(o=>(!$('category').value || ProductGroups.classify(o)===$('category').value)&&(!$('supplier').value||o.supplier===$('supplier').value)&&(!$('source-filter').value||o.source_kind===$('source-filter').value)&&ProductSearch.matches(o,query));
  rows.sort((a,b)=>(a.source_kind==='market'?0:1)-(b.source_kind==='market'?0:1)||a.name.localeCompare(b.name,'is'));
  $('result-count').textContent=`${rows.length} vörufærslur`;
  const market=rows.filter(o=>o.source_kind==='market');
  $('search-summary').textContent=`${market.length} markaðsfærslur hjá ${new Set(market.map(o=>o.supplier)).size} birgjum í gagnagrunni`+(market.length?': '+[...new Set(market.map(o=>o.supplier))].join(', '):'')+'. Leitin nær aðeins til innlesinna gagna; fyrri innkaup staðfesta ekki núverandi framboð.';
  $('products').innerHTML='<p><button id="back-categories">← Til baka í flokka</button></p>'+(rows.length?table(['VARA / VÖRUNÚMER','BIRGIR / UPPRUNI','VERÐ','MAGN Í FYRRI GÖGNUM',''],rows.slice(0,pageLimit).map(o=>`<tr><td><b>${esc(o.name)}</b><small>${esc(o.sku||'Vörunúmer afbrigðis vantar')} · ${esc(o.subcategory||o.category||'Óflokkað')}</small><small>${esc(attrsLabel(o))}</small></td><td>${esc(o.supplier)}<small><span class="pill ${o.source_kind==='purchase'?'warn':''}">${sourceLabel(o)}</span></small></td><td>${priceCell(o)}<small>${esc(o.availability||'')} ${o.source_kind==='market'?'· Heimild skoðuð '+date(o.observed_at):''}</small></td><td>${o.source_kind==='purchase'?`${esc(o.quantity)} ${esc(o.unit)}<small>${date(o.observed_at)} · síðasta færsla</small>`:'—'}</td><td><button data-detail="${o.id}">Skoða</button></td></tr>`).join(''))+(rows.length>pageLimit?'<p><button id="show-more">Sýna fleiri</button></p>':''):`<div class="empty"><h2>Engar vörur passa við leitina</h2><p>Prófaðu annað leitarorð eða síu. Gögnin ná ekki enn til allra verslana.</p></div>`);
}
function detail(id) {
  const o=state.offers.find(x=>x.id===id);if(!o)return;
  const peers=state.offers.filter(x=>x.match_key===o.match_key && x.currency===o.currency && x.unit===o.unit);
  const alternatives=state.offers.filter(x=>x.source_kind==='market'&&x.match_key!==o.match_key&&ProductSearch.comparable(o,x));
  function offerRows(list){return table(['BIRGIR / VARA','VERÐ','HEIMILD / FRAMBOÐ',''],list.map(x=>`<tr><td>${esc(x.supplier)}<small>${esc(x.name)}</small><small>${esc(x.sku||'Vörunúmer vantar')}</small></td><td>${priceCell(x)}</td><td>${link(x)}<small>${esc(x.availability||'Lagerstaða óstaðfest')}</small><small>${date(x.observed_at)}</small></td><td>${x.net_price!=null?`<button data-add="${x.id}">Á lista</button>`:'—'}</td></tr>`).join(''));}
  $('detail').innerHTML=`<h2>${esc(o.name)}</h2><p class="muted">${esc(o.supplier)} · ${esc(o.sku)} · ${sourceLabel(o)}</p><p>${esc(attrsLabel(o))}</p>`+offerRows(peers)+`<p class="muted">${esc(o.note||'')} ${esc(o.link_note||'')}</p>`;
  if(o.source_kind==='purchase'){
    $('detail').innerHTML+=`<h3>Reikningsmagn úr verkefninu</h3><p>${esc(o.quantity)} ${esc(o.unit)} samtals. ${Object.entries(o.quantities||{}).map(([y,q])=>`${esc(y)}: ${esc(q)} ${esc(o.unit)}`).join(' · ')}</p><p class="muted">Kaupverð vantar í V3. Ekki hægt að reikna sparnað gagnvart fyrri kaupum. ${esc(o.classification_status||'')}</p>`+table(['DAGSETNING','REIKNINGUR','MAGN','UPPRUNI'],(o.lines||[]).map(l=>`<tr><td>${date(l.date)}</td><td>${esc(l.invoice)}</td><td>${esc(l.quantity)} ${esc(l.unit)}</td><td>${esc(l.file)}<small>${esc(l.sourceSheet)} · lína ${esc(l.sourceRow)}</small></td></tr>`).join(''));
  }
  $('detail').innerHTML+=`<h3>Mögulegar sambærilegar vörur á opnum markaði</h3><p class="muted">Sama þvermál og notkun samkvæmt lýsingu. Þetta er ekki staðfest jafngildi: bera þarf saman lengd, festingu, efnisgerð, húðun og pakkastærð. HSS-G og kobaltborar eru ekki sjálfkrafa jafngildir.</p>`+(alternatives.length?offerRows(alternatives):'<p>Engar aðrar sambærilegar markaðsvörur eru komnar í grunninn.</p>');
  const history=state.history.filter(h=>h.offer_id===id);
  if(history.length)$('detail').innerHTML+='<h3>Verðsaga</h3>'+table(['DAGSETNING','VERÐ ÁN VSK / EININGU'],history.map(h=>`<tr><td>${date(h.observed_at)}</td><td>${money(h.price/(h.vat_included?1+h.vat_rate/100:1)/h.pack_quantity,h.currency)} / ${esc(h.unit)}</td></tr>`).join(''));
  if(o.links?.length)$('detail').innerHTML+='<h3>Heimildir fyrri flokkunar</h3><p class="muted">Flokkunarheimild getur verið flokkasíða eða svipuð vara; hún er ekki sjálfkrafa staðfest vörutenging.</p>'+o.links.filter(l=>l.url).map(l=>`<p><a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">${esc(l.label)}</a><small> ${esc(l.evidence)}</small></p>`).join('');
  if(o.collector){
    $('detail').insertAdjacentHTML('beforeend','<div id="auto-history"></div>');
    api('market-history?key='+encodeURIComponent(o.history_key||o.key)).then(rows=>{if(!$('auto-history')||$('detail').dataset.productId!==String(id))return;$('auto-history').innerHTML='<h3>Saga sjálfvirkra athugana</h3>'+table(['DAGSETNING','BIRT VERÐ / SÖLUEININGU','FRAMBOÐ'],rows.map(r=>`<tr><td>${date(r.observed_at)}</td><td>${r.price==null?'Verð vantar':money(r.price,r.currency)}</td><td>${esc(r.availability)}</td></tr>`).join(''));}).catch(()=>{});
  }
  $('detail').dataset.productId=String(id);
  if(!$('detail-dialog').open)$('detail-dialog').showModal();
}
function renderProjects() {
  const pid=Number($('project-select').value);
  const rows=state.items.filter(i=>i.project_id===pid).map(i=>({...i,offer:state.offers.find(o=>o.id===i.offer_id)})).filter(i=>i.offer);
  if(!rows.length){$('project-items').innerHTML='<div class="empty"><h2>Innkaupalistinn er tómur</h2><p>Stofnaðu verkefni og veldu „Á lista“ í vörusamanburði.</p></div>';return;}
  const totals={}; rows.forEach(i=>{const o=i.offer; const key=o.supplier+' · '+o.currency; totals[key]=(totals[key]||0)+o.net_price*i.quantity;});
  $('project-items').innerHTML=table(['VARA','BIRGIR','PAKKNINGAR','SAMTALS ÁN VSK',''],rows.map(i=>`<tr><td>${esc(i.offer.name)}<small>${i.offer.pack_quantity} ${esc(i.offer.unit)} / pakkning</small></td><td>${esc(i.offer.supplier)}</td><td><input aria-label="Fjöldi pakkninga fyrir ${esc(i.offer.name)}" type="number" min="0" step="1" value="${i.quantity}" data-qty="${i.offer.id}"></td><td>${money(i.quantity*i.offer.net_price,i.offer.currency)}</td><td><button data-remove="${i.offer.id}">Fjarlægja</button></td></tr>`).join(''))+`<div class="totals">${Object.entries(totals).map(([key,n])=>`${esc(key)}: <b>${money(n,key.split(' · ').pop())}</b>`).join('<br>')}</div><p class="muted">Áætlaður vörukostnaður á nýjustu innlesnu verðum. Flutningur og afslættir eru ekki innifalin. Þetta er innkaupalisti; engin pöntun er send.</p>`;
}
function renderSuppliers() {
  $('supplier-cards').innerHTML=[...new Set([...state.suppliers,...state.offers.map(o=>o.supplier)])].sort().map(s=>{const rows=state.offers.filter(o=>o.supplier===s),connection=state.metadata?.connections?.suppliers?.find(c=>c.supplier===s);return `<div class="card"><h3>${esc(s)}</h3><p class="muted">${rows.filter(o=>o.source_kind==='purchase').length} úr innkaupum · ${rows.filter(o=>o.source_kind==='market').length} af markaði</p><span class="pill ${rows.length?'':'warn'}">${rows.length?'Gögn í grunni':'Gögn vantar'}</span>${connection?`<p>${esc(connection.finding)}</p><p class="muted">${esc(connection.next_step)}</p><a href="${esc(connection.url)}" target="_blank" rel="noopener noreferrer">Vefur birgis ↗</a>`:''}</div>`;}).join('');
}
function renderSync(info){
  $('refresh-market').disabled=!!info.running;
  $('refresh-market').textContent=info.running?'Uppfærsla í gangi…':'↻ Uppfæra markaðsverð';
  $('sync-summary').textContent='Sjálfvirk uppfærsla á 24 klst. fresti meðan forritið keyrir. '+(info.finished_at?'Síðasta keyrsla: '+new Date(info.finished_at).toLocaleString('is-IS')+'. ':'')+'Aðgangshöfnun eða villa merkir að eldri verð geta enn birst. Verðathugunardagur hverrar vöru ræður ferskleika.';
  const labels={ok:'Tenging virkar',partial:'Hluti listans sóttur',blocked:'Aðgangi hafnað',error:'Villa í tengingu',not_connected:'Tenging ólokið'};
  const names={thor:'Þór hf.',husa:'Húsasmiðjan',byko:'BYKO',sindri:'Sindri',fossberg:'Fossberg',isol:'Ísól',rubix:'Rúbix',vatnsvirkinn:'Vatnsvirkinn',vatnogveitur:'Vatn og veitur',ronning:'Röning',iskraft:'Ískraft',reykjafell:'Reykjafell',hampidjan:'Hampiðjan',isfell:'Ísfell',landvelar:'Landvélar',barki:'Barki',wurth:'Würth'};
  $('sync-sources').innerHTML=table(['BIRGIR','STAÐA','ÞEKJA','UPPLÝSINGAR'],Object.entries(info.sources||{}).map(([key,v])=>`<tr><td>${esc(names[key]||key)}</td><td><span class="pill ${v.status==='ok'?'':'warn'}">${esc(labels[v.status]||v.status)}</span></td><td>${v.loaded||0}${v.expected?' / '+v.expected:''}<small>${!['thor','landvelar'].includes(key)?'Slóðafjöldi er ekki staðfestur fjöldi einstakra afbrigða.':''}</small></td><td>${esc(v.scope||'')}<small>${esc(v.error||(v.errors?.length?v.errors.length+' vörusíður skiluðu villu.':''))}</small></td></tr>`).join(''));
}
$('refresh-market').onclick=()=>run(async()=>{const result=await api('refresh-market',{});$('status').textContent=result.started?'Söfnun hafin. Þú getur haldið áfram að nota kerfið.':'Uppfærsla er þegar í gangi.';renderSync(await api('sync-status'));});
let wasSyncing=false;
setInterval(()=>run(async()=>{const info=await api('sync-status');renderSync(info);if(wasSyncing&&!info.running)await refresh();wasSyncing=!!info.running;}),15000);
async function run(fn){try{await fn();}catch(e){$('status').textContent=e.message;}}
document.addEventListener('click',e=>{
  const b=e.target.closest('button');if(!b)return;
  if(b.dataset.category){$('category').value=b.dataset.category;browseAll=false;pageLimit=60;renderProducts();}
  if(b.id==='browse-all'){browseAll=true;renderProducts();}
  if(b.id==='back-categories'){$('category').value='';$('search').value='';browseAll=false;pageLimit=60;renderProducts();}
  if(b.id==='show-more'){pageLimit+=60;renderProducts();}
  if(b.dataset.query){$('search').value=b.dataset.query;$('category').value='';$('supplier').value='';$('source-filter').value='';pageLimit=60;renderProducts();}
  if(b.dataset.view){for(const id of ['catalogue','projects','suppliers','bom'])$(id).hidden=id!==b.dataset.view;document.querySelectorAll('.nav').forEach(n=>n.classList.toggle('active',n===b));$('heading').textContent={catalogue:'Vörugrunnur',projects:'Innkaupalistar',suppliers:'Birgjar',bom:'BOM-samanburður'}[b.dataset.view];}
  if(b.dataset.close)$(b.dataset.close).close();
  if(b.dataset.detail)detail(Number(b.dataset.detail));
  if(b.dataset.add){$('detail-dialog').close();if(!state.projects.length){$('project-dialog').showModal();$('status').textContent='Stofnaðu fyrst verkefni og bættu svo vörunni á listann.';return;}$('add-offer').value=b.dataset.add;$('add-dialog').showModal();}
  if(b.dataset.remove)run(async()=>{await api('items',{project_id:Number($('project-select').value),offer_id:Number(b.dataset.remove),quantity:0});await refresh();});
});
function filterChanged(){pageLimit=60;renderProducts();}
$('search').addEventListener('input',filterChanged);['category','supplier','source-filter'].forEach(id=>$(id).addEventListener('change',filterChanged));
$('project-select').addEventListener('change',renderProjects);
$('project-items').addEventListener('change',e=>{if(e.target.dataset.qty)run(async()=>{try{await api('items',{project_id:Number($('project-select').value),offer_id:Number(e.target.dataset.qty),quantity:e.target.value});}finally{await refresh();}});});
$('import-open').onclick=()=>{$('import-error').textContent='';$('import-dialog').showModal();};
$('project-new').onclick=()=>$('project-dialog').showModal();
$('import-form').onsubmit=async e=>{e.preventDefault();$('import-submit').disabled=true;try{const f=$('csv-file').files[0];if(f.size>5000000)throw Error('Hámark 5 MB.');const r=await api('import',{csv:await f.text()});await refresh();$('import-dialog').close();$('status').textContent=`${r.imported} vörufærslur lesnar inn.`;}catch(err){$('import-error').textContent=err.message;}finally{$('import-submit').disabled=false;}};
$('project-form').onsubmit=e=>{e.preventDefault();run(async()=>{await api('projects',{name:$('project-name').value});$('project-dialog').close();$('project-name').value='';await refresh();});};
$('add-form').onsubmit=e=>{e.preventDefault();run(async()=>{const pid=Number($('add-project').value),oid=Number($('add-offer').value),existing=state.items.find(i=>i.project_id===pid&&i.offer_id===oid);await api('items',{project_id:pid,offer_id:oid,quantity:Number($('add-quantity').value)+(existing?.quantity||0)});$('add-dialog').close();await refresh();$('status').textContent='Vara komin á innkaupalista.';});};
run(refresh);
