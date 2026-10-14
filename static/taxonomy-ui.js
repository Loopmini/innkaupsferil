'use strict';
const specLabels={thickness_mm:'Þykkt (mm)',width_mm:'Breidd (mm)',length_mm:'Lengd (mm)',strength_class:'Styrkleikaflokkur',treatment:'Yfirborðsmeðhöndlun',material:'Efni / viðartegund',standard:'Staðall'};
const taxGroups=()=>state.metadata?.taxonomy?.groups||[];
const taxLeaves=()=>taxGroups().flatMap(t=>t.children.flatMap(s=>s.children.map(l=>({...l,path:[t.name,s.name,l.name]}))));
function keepOptions(el,values,first){const before=el.value;el.innerHTML=options(values,first);el.value=values.includes(before)?before:'';}
function taxonomyFilters(){
 if(!taxGroups().length)return;
 keepOptions($('category'),taxGroups().map(t=>t.name),'Allir yfirflokkar');
 if(!$('taxonomy-filters')){
  $('search-summary').insertAdjacentHTML('beforebegin',`<div id="taxonomy-filters" class="toolbar"><label>Undirflokkur<select id="subcategory-filter"></select></label><label>Vörutegund<select id="type-filter"></select></label><label>Framleiðandi<select id="brand-filter"></select></label><label>Sölueining<select id="unit-filter"></select></label><label>Yfirferð<select id="review-filter"><option value="">Allar vörur</option><option value="classification">Flokkun óviss</option><option value="specs">Eiginleika vantar / ósamræmi</option></select></label></div><details id="spec-filter-panel"><summary>Sía eftir stærðum og tæknilegum eiginleikum</summary><div class="toolbar">${Object.entries(specLabels).map(([k,label])=>`<label>${label}<select data-spec-filter="${k}" id="filter-${k}"></select></label>`).join('')}</div><p class="muted">Aðeins skráð gildi passa við síu. Óþekkt gildi eru ekki áætluð; velja má „Óþekkt“.</p></details>`);
  $('taxonomy-filters').onchange=()=>{pageLimit=60;renderProducts();};
  $('spec-filter-panel').onchange=()=>{pageLimit=60;renderProducts();};
 }
 const top=taxGroups().find(t=>t.name===$('category').value);
 keepOptions($('subcategory-filter'),top?top.children.map(s=>s.name):[],'Allir undirflokkar');
 const sub=top?.children.find(s=>s.name===$('subcategory-filter').value);
 keepOptions($('type-filter'),sub?sub.children.map(l=>l.name):[],'Allar vörutegundir');
 keepOptions($('brand-filter'),[...new Set(state.offers.map(o=>o.brand).filter(Boolean))].sort(),'Allir framleiðendur');
 keepOptions($('unit-filter'),[...new Set(state.offers.map(o=>o.unit).filter(Boolean))].sort(),'Allar einingar');
 const base=state.offers.filter(o=>!top||o.classification?.path[0]===top.name);
 for(const k of Object.keys(specLabels))keepOptions($('filter-'+k),['Óþekkt',...[...new Set(base.map(o=>o.specifications?.[k]).filter(v=>v!=null).map(String))].sort((a,b)=>a.localeCompare(b,'is',{numeric:true}))],'Öll gildi');
}
function renderTaxonomyProducts(){
 taxonomyFilters();
 const top=$('category').value,sub=$('subcategory-filter').value,type=$('type-filter').value;
 const query=ProductSearch.parse($('search').value);
 const filtered=state.offers.filter(o=>{
  const p=o.classification?.path||[];
  if(top&&p[0]!==top||sub&&p[1]!==sub||type&&p[2]!==type)return false;
  if($('supplier').value&&o.supplier!==$('supplier').value||$('source-filter').value&&o.source_kind!==$('source-filter').value)return false;
  if($('brand-filter').value&&o.brand!==$('brand-filter').value||$('unit-filter').value&&o.unit!==$('unit-filter').value)return false;
  const review=$('review-filter').value;
  if(review==='classification'&&!o.classification?.needs_review)return false;
  if(review==='specs'&&!o.missing_specifications?.length&&!o.specification_conflicts?.length)return false;
  for(const k of Object.keys(specLabels)){const v=$('filter-'+k).value;if(v&&(v==='Óþekkt'?o.specifications?.[k]!=null:String(o.specifications?.[k])!==v))return false;}
  return ProductSearch.matches(o,query);
 });
 const topNode=taxGroups().find(t=>t.name===top),subNode=topNode?.children.find(s=>s.name===sub);
 const nodes=!top?taxGroups():!sub?topNode?.children:!type?subNode?.children:[];
 const level=!top?0:!sub?1:2;
 const hasFilter=$('search').value.trim()||$('brand-filter').value||$('unit-filter').value||$('review-filter').value||Object.keys(specLabels).some(k=>$('filter-'+k).value);
 $('catalogue-title').textContent=[top,sub,type].filter(Boolean).join(' → ')||'Vöruflokkar';
 $('result-count').textContent=`${filtered.length} vörufærslur`;
 $('search-summary').textContent=`${new Set(filtered.map(o=>o.supplier)).size} birgjar · ${filtered.filter(o=>o.classification?.needs_review).length} með óvissa flokkun. Flokkun er fyrir vöruleit og innkaup. Tómir flokkar bíða vörugagna.`;
 let html=(top||sub||type)?'<p><button id="tax-back">← Til baka um eitt þrep</button> <button id="tax-reset">Hreinsa allar síur</button></p>':'<p><button id="tax-reset">Hreinsa allar síur</button></p>';
 if(nodes?.length&&!hasFilter&&!browseAll){
  html+='<div class="cards">'+nodes.map(n=>{const items=filtered.filter(o=>o.classification?.path[level]===n.name);return `<button class="card category-card" data-tax-level="${level}" data-tax-name="${esc(n.name)}"><h3>${esc(n.name)}</h3><strong>${items.length} vörufærslur</strong><p>${items.length?`${new Set(items.map(o=>o.supplier)).size} birgjar · ${items.filter(o=>o.price!=null).length} með verði`:'Bíður vörugagna'}</p><span>Skoða →</span></button>`;}).join('')+'</div><p><button id="browse-all">Sýna vörur í þessum flokkum</button></p>';
 }else{
  filtered.sort((a,b)=>a.name.localeCompare(b.name,'is'));
  html+=filtered.length?table(['VARA / FLOKKUN','BIRGIR / AUÐKENNI','VERÐGRUNNUR',''],filtered.slice(0,pageLimit).map(o=>`<tr><td><b>${esc(o.name)}</b><small>${o.classification.path.map(esc).join(' → ')}</small>${o.classification.needs_review?'<span class="pill warn">Flokkun til yfirferðar</span>':''}<small>${Object.entries(o.specifications||{}).map(([k,v])=>`${esc(specLabels[k])}: ${esc(v)}`).join(' · ')}</small>${o.missing_specifications?.length||o.specification_conflicts?.length?'<span class="pill warn">Eiginleika vantar / yfirferð</span>':''}</td><td>${esc(o.supplier)}<small>Vörunr.: ${esc(o.sku||'Vantar')} · MPN: ${esc(o.manufacturer_part||'Vantar')}</small><small>${esc(o.brand||'Framleiðandi óþekktur')} · ${sourceLabel(o)}</small></td><td>${priceCell(o)}<small>${date(o.observed_at)}</small></td><td><button data-detail="${o.id}">Skoða</button></td></tr>`).join(''))+(filtered.length>pageLimit?'<p><button id="show-more">Sýna fleiri</button></p>':''):'<div class="empty">Engar vörur með þessum gögnum. Flokkurinn er tilbúinn fyrir innlestur.</div>';
 }
 $('products').innerHTML=html;
}
document.addEventListener('click',e=>{
 const b=e.target.closest('button');if(!b)return;
 if(b.dataset.taxLevel!==undefined){const ids=['category','subcategory-filter','type-filter'];$(ids[Number(b.dataset.taxLevel)]).value=b.dataset.taxName;browseAll=false;pageLimit=60;renderProducts();}
 if(b.id==='tax-back'){if($('type-filter').value)$('type-filter').value='';else if($('subcategory-filter').value)$('subcategory-filter').value='';else $('category').value='';browseAll=false;renderProducts();}
 if(b.id==='tax-reset'){for(const id of ['category','subcategory-filter','type-filter','brand-filter','unit-filter','review-filter','supplier','source-filter','search'])$(id).value='';for(const k of Object.keys(specLabels))$('filter-'+k).value='';browseAll=false;renderProducts();}
});
function productTaxonomyPanel(o){
 if(!o.classification)return;
 $('classification-form').hidden=true;
 const c=o.classification,values=o.specifications||{},original=o.product_enrichment||{};
 $('detail').insertAdjacentHTML('beforeend',`<section class="card"><h3>Flokkun og eiginleikar fyrir innkaup</h3><p>${c.path.map(esc).join(' → ')} ${c.needs_review?'<span class="pill warn">Til yfirferðar</span>':''}</p><p class="muted">${esc(c.source)}: ${esc(c.evidence)}</p><p>Vantar: ${(o.missing_specifications||[]).map(k=>esc(specLabels[k])).join(', ')||'Engin skyldumál fyrir þennan flokk'}. Ósamræmi: ${(o.specification_conflicts||[]).map(k=>esc(specLabels[k])).join(', ')||'Ekkert greint'}.</p><p>Sölueining: ${esc(o.unit||'Óþekkt')} · Pakkastærð: ${esc(o.pack_quantity??'Óþekkt')}. Verðgrunnur er aðeins uppfærður með staðfestum verðgögnum.</p><form id="taxonomy-form"><label>Yfirflokkur<select id="edit-top"></select></label><label>Undirflokkur<select id="edit-sub"></select></label><label>Vörutegund<select id="edit-type"></select></label><div class="spec-grid">${Object.entries(specLabels).map(([k,label])=>`<label>${label}<input data-spec-edit="${k}" id="edit-${k}" ${k.endsWith('_mm')?'type="number" min="0.001" step="any"':'maxlength="120"'} value="${esc(values[k]??'')}" placeholder="Óþekkt"><small>${esc(o.specification_evidence?.[k]||'Heimild vantar')}</small></label>`).join('')}</div><label>Leitartög (aðskilin með kommu)<input id="edit-tags" value="${esc((original.search_tags||[]).join(', '))}"></label><p class="muted">Einn aðalstaður í flokkuninni. Skráðu aðeins eiginleika sem þú getur staðfest. Tómt gildi merkir óþekkt. Mál greind úr texta sýna heimild og má leiðrétta.</p><button type="submit">Vista flokkun og eiginleika</button> <button type="button" id="reset-enrichment">Fjarlægja þessar handvirku breytingar</button><p id="taxonomy-status" role="status"></p></form></section><section class="card"><h3>Bæta vöru á BOM</h3><form id="bom-add-product"><label>Efnislisti<select id="bom-target"><option value="">Nýr efnislisti</option></select></label><label>Heiti nýs lista<input id="bom-target-name" maxlength="120" placeholder="T.d. Pallaverkefni"></label><label>Magn<input id="bom-target-quantity" type="number" min="0.001" step="any" value="1" required></label><label>Eining magns<select id="bom-target-unit">${options(['stk','m','m2','m3','kg','l'],'Veldu einingu')}</select></label><p class="muted">Vörunni er bætt við sem samþykktu vali. Óþekkt verð eða ólík eining getur enn komið í veg fyrir kostnaðarútreikning. Auðkenni og skráðir eiginleikar fylgja sem kröfur.</p><button>Bæta á BOM</button><p id="bom-add-status" role="status"></p></form></section>`);
 const top=$('edit-top'),sub=$('edit-sub'),type=$('edit-type');
 top.innerHTML=taxGroups().map(t=>`<option value="${t.id}">${esc(t.name)}</option>`).join('');top.value=c.id.split('.')[0];
 function fillSub(){sub.innerHTML=taxGroups().find(t=>t.id===top.value).children.map(s=>`<option value="${s.id}">${esc(s.name)}</option>`).join('');sub.value=taxGroups().find(t=>t.id===top.value).children[0].id;fillType();}
 function fillType(){const children=taxGroups().find(t=>t.id===top.value).children.find(s=>s.id===sub.value).children;type.innerHTML=children.map(l=>`<option value="${l.id}">${esc(l.name)}</option>`).join('');type.value=children[0].id;}
 fillSub();sub.value=c.id.split('.').slice(0,2).join('.');fillType();type.value=c.id;top.onchange=fillSub;sub.onchange=fillType;
 $('taxonomy-form').onsubmit=async e=>{e.preventDefault();const form=e.target,box=$('taxonomy-status');form.querySelectorAll('button').forEach(b=>b.disabled=true);try{const specs={...(original.specifications||{})};for(const k of Object.keys(specLabels)){const raw=$('edit-'+k).value.trim();const v=raw?(k.endsWith('_mm')?Number(raw):raw):null;if(v!==(values[k]??null))specs[k]=v;}await api('product-enrichment',{id:o.id,classification_id:type.value,specifications:specs,search_tags:$('edit-tags').value.split(',').map(s=>s.trim()).filter(Boolean)});await refresh();if(form.isConnected){detail(o.id);$('taxonomy-status').textContent='Flokkun og eiginleikar vistuð.';}}catch(err){if(box.isConnected)box.textContent=err.message;}finally{form.querySelectorAll('button').forEach(b=>b.disabled=false);}};
 $('reset-enrichment').onclick=()=>run(async()=>{await api('product-enrichment',{id:o.id,reset:true});await refresh();detail(o.id);});
 const target=$('bom-target'),form=$('bom-add-product');$('bom-target-unit').value=o.unit||'';
 api('boms').then(rows=>{if(target.isConnected)target.innerHTML='<option value="">Nýr efnislisti</option>'+rows.map(r=>`<option value="${r.id}">${esc(r.name)}</option>`).join('');}).catch(()=>{});
 form.onsubmit=async e=>{e.preventDefault();const box=$('bom-add-status'),button=form.querySelector('button');button.disabled=true;try{const r=await api('bom-add',{id:Number(target.value)||0,name:$('bom-target-name').value,offer_id:o.id,quantity:Number($('bom-target-quantity').value),unit:$('bom-target-unit').value});await loadBOMLists(r.id);await selectBOM(r.id);if(box.isConnected)box.textContent='Vara komin á BOM. Skoðaðu BOM-samanburð í valmyndinni.';}catch(err){if(box.isConnected)box.textContent=err.message;}finally{button.disabled=false;}};
}

if(state.metadata?.taxonomy)renderProducts();
