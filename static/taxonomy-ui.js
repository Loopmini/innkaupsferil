'use strict';
const specLabels={thickness_mm:'Þykkt (mm)',width_mm:'Breidd (mm)',length_mm:'Lengd (mm)',strength_class:'Styrkleikaflokkur',treatment:'Yfirborðsmeðhöndlun',material:'Efni / viðartegund',standard:'Staðall',diameter_mm:'Þvermál (mm)',nominal_size:'Nafnstærð (DN)',pressure_class:'Þrýstiflokkur'};
const taxGroups=()=>state.metadata?.taxonomy?.groups||[];
const taxLeaves=()=>taxGroups().flatMap(t=>t.children.flatMap(s=>s.children.map(l=>({...l,path:[t.name,s.name,l.name]}))));
function keepOptions(el,values,first){const before=el.value;el.innerHTML=options(values,first);el.value=values.includes(before)?before:'';}
function taxonomyFilters(){
 if(!taxGroups().length)return;
 Object.assign(specLabels,state.metadata?.specification_fields||{});
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
 const chosen=sub?.children.find(l=>l.name===$('type-filter').value)?.id||sub?.id||top?.id||'';
 const relevantKeys=typeof familySpecKeys==='function'?familySpecKeys(chosen):Object.keys(specLabels);
 for(const k of Object.keys(specLabels)){const label=$('filter-'+k).closest('label');const relevant=!chosen||relevantKeys.includes(k);label.hidden=!relevant;if(!relevant)$('filter-'+k).value='';}
 const base=state.offers.filter(o=>!top||o.classification?.path[0]===top.name);
 for(const k of Object.keys(specLabels))keepOptions($('filter-'+k),['Óþekkt',...[...new Set(base.map(o=>o.specifications?.[k]).filter(v=>v!=null).map(String))].sort((a,b)=>a.localeCompare(b,'is',{numeric:true}))],'Öll gildi');
}
function renderTaxonomyProducts(){
 taxonomyFilters();
 const top=$('category').value,sub=$('subcategory-filter').value,type=$('type-filter').value;
 const query=ProductSearch.parse($('search').value);
 const rawQuery=$('search').value.trim().toLowerCase();
 const exactIds=new Set(rawQuery?state.offers.filter(o=>[o.sku,o.manufacturer_part,o.gtin].some(v=>v&&String(v).trim().toLowerCase()===rawQuery)).map(o=>o.id):[]);
 const filtered=state.offers.filter(o=>{
  if(exactIds.size)return exactIds.has(o.id);
  const p=o.classification?.path||[];
  if(top&&p[0]!==top||sub&&p[1]!==sub||type&&p[2]!==type)return false;
  if($('supplier').value&&o.supplier!==$('supplier').value||$('source-filter').value&&o.source_kind!==$('source-filter').value)return false;
  if($('brand-filter').value&&o.brand!==$('brand-filter').value||$('unit-filter').value&&o.unit!==$('unit-filter').value)return false;
  const review=$('review-filter').value;
  if(review==='classification'&&!o.classification?.needs_review)return false;
  if(review==='specs'&&!o.missing_specifications?.length&&!o.specification_conflicts?.length)return false;
  for(const k of Object.keys(specLabels)){const v=$('filter-'+k).value;if(v&&(v==='Óþekkt'?o.specifications?.[k]!=null:String(o.specifications?.[k])!==v))return false;}
  return ProductSearch.matches(o,$('search').value);
 });
 renderFamilyResults(filtered);
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
 $('detail').insertAdjacentHTML('beforeend',`<section class="card"><h3>Flokkun og eiginleikar fyrir innkaup</h3><p>${c.path.map(esc).join(' → ')} ${c.needs_review?'<span class="pill warn">Til yfirferðar</span>':''}</p><p class="muted">${esc(c.source)}: ${esc(c.evidence)}</p><p>Vantar: ${(o.missing_specifications||[]).map(k=>esc(specLabels[k])).join(', ')||'Engin skyldumál fyrir þennan flokk'}. Ósamræmi: ${(o.specification_conflicts||[]).map(k=>esc(specLabels[k])).join(', ')||'Ekkert greint'}.</p><p>Sölueining: ${esc(o.unit||'Óþekkt')} · Pakkastærð: ${esc(o.pack_quantity??'Óþekkt')}. Verðgrunnur er aðeins uppfærður með staðfestum verðgögnum.</p><form id="taxonomy-form"><label>Yfirflokkur<select id="edit-top"></select></label><label>Undirflokkur<select id="edit-sub"></select></label><label>Vörutegund<select id="edit-type"></select></label><div class="spec-grid">${Object.entries(specLabels).map(([k,label])=>`<label>${label}<input data-spec-edit="${k}" id="edit-${k}" ${numericSpec(k)?'type="number" min="0.001" step="any"':'maxlength="120"'} value="${esc(values[k]??'')}" placeholder="Óþekkt"><small>${esc(o.specification_evidence?.[k]||'Heimild vantar')}</small></label>`).join('')}</div><label><input type="checkbox" id="keep-separate" ${original.keep_separate?'checked':''}> Halda þessari færslu aðskildri frá öðrum birgjatilboðum</label><label>Leitartög (aðskilin með kommu)<input id="edit-tags" value="${esc((original.search_tags||[]).join(', '))}"></label><p class="muted">Einn aðalstaður í flokkuninni. Skráðu aðeins eiginleika sem þú getur staðfest. Tómt gildi merkir óþekkt. Mál greind úr texta sýna heimild og má leiðrétta.</p><button type="submit">Vista flokkun og eiginleika</button> <button type="button" id="reset-enrichment">Fjarlægja þessar handvirku breytingar</button><p id="taxonomy-status" role="status"></p></form></section><section class="card"><h3>Bæta vöru á BOM</h3><form id="bom-add-product"><label>Efnislisti<select id="bom-target"><option value="">Nýr efnislisti</option></select></label><label>Heiti nýs lista<input id="bom-target-name" maxlength="120" placeholder="T.d. Pallaverkefni"></label><label>Magn<input id="bom-target-quantity" type="number" min="0.001" step="any" value="1" required></label><label>Eining magns<select id="bom-target-unit">${options(['stk','m','m2','m3','kg','l'],'Veldu einingu')}</select></label><p class="muted">Vörunni er bætt við sem samþykktu vali. Óþekkt verð eða ólík eining getur enn komið í veg fyrir kostnaðarútreikning. Auðkenni og skráðir eiginleikar fylgja sem kröfur.</p><button>Bæta á BOM</button><p id="bom-add-status" role="status"></p></form></section>`);
 const top=$('edit-top'),sub=$('edit-sub'),type=$('edit-type');
 top.innerHTML=taxGroups().map(t=>`<option value="${t.id}">${esc(t.name)}</option>`).join('');top.value=c.id.split('.')[0];
 function fillSub(){sub.innerHTML=taxGroups().find(t=>t.id===top.value).children.map(s=>`<option value="${s.id}">${esc(s.name)}</option>`).join('');sub.value=taxGroups().find(t=>t.id===top.value).children[0].id;fillType();}
 function fillType(){const children=taxGroups().find(t=>t.id===top.value).children.find(s=>s.id===sub.value).children;type.innerHTML=children.map(l=>`<option value="${l.id}">${esc(l.name)}</option>`).join('');type.value=children[0].id;}
 fillSub();sub.value=c.id.split('.').slice(0,2).join('.');fillType();type.value=c.id;top.onchange=fillSub;sub.onchange=fillType;
 function showFields(){const fields=familySpecKeys(type.value);for(const k of Object.keys(specLabels))$('edit-'+k).closest('label').hidden=!fields.includes(k)&&values[k]==null;}
 $('taxonomy-form').addEventListener('change',showFields);showFields();
 $('taxonomy-form').onsubmit=async e=>{e.preventDefault();const form=e.target,box=$('taxonomy-status');form.querySelectorAll('button').forEach(b=>b.disabled=true);try{const specs={...(original.specifications||{})};for(const k of Object.keys(specLabels)){const raw=$('edit-'+k).value.trim();const v=raw?(numericSpec(k)?Number(raw):raw):null;if(v!==(values[k]??null))specs[k]=v;}await api('product-enrichment',{id:o.id,keep_separate:$('keep-separate').checked,classification_id:type.value,specifications:specs,search_tags:$('edit-tags').value.split(',').map(s=>s.trim()).filter(Boolean)});await refresh();if(form.isConnected){detail(o.id);$('taxonomy-status').textContent='Flokkun og eiginleikar vistuð.';}}catch(err){if(box.isConnected)box.textContent=err.message;}finally{form.querySelectorAll('button').forEach(b=>b.disabled=false);}};
 $('reset-enrichment').onclick=()=>run(async()=>{await api('product-enrichment',{id:o.id,reset:true});await refresh();detail(o.id);});
 if(typeof renderOfferConditions==='function')renderOfferConditions(o);
 const target=$('bom-target'),form=$('bom-add-product');$('bom-target-unit').value=o.unit||'';
 api('boms').then(rows=>{if(target.isConnected)target.innerHTML='<option value="">Nýr efnislisti</option>'+rows.map(r=>`<option value="${r.id}">${esc(r.name)}</option>`).join('');}).catch(()=>{});
 form.onsubmit=async e=>{e.preventDefault();const box=$('bom-add-status'),button=form.querySelector('button');button.disabled=true;try{const r=await api('bom-add',{id:Number(target.value)||0,name:$('bom-target-name').value,offer_id:o.id,quantity:Number($('bom-target-quantity').value),unit:$('bom-target-unit').value});await loadBOMLists(r.id);await selectBOM(r.id);if(box.isConnected)box.textContent='Vara komin á BOM. Skoðaðu BOM-samanburð í valmyndinni.';}catch(err){if(box.isConnected)box.textContent=err.message;}finally{button.disabled=false;}};
}

if(state.metadata?.taxonomy)renderProducts();
