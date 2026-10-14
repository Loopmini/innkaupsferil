'use strict';
/* Workspace composition reuses the existing forms and endpoints. No data migration. */
let workspace='catalogue',workspaceScroll={},productView='cards',supplierView='table',supplierSearch='',returnFocus=null;
const move=(node,parent)=>{if(node&&parent)parent.appendChild(node);};
function pane(id,title,parent){const e=document.createElement('section');e.id=id;if(title){const h=document.createElement('h2');h.textContent=title;e.appendChild(h);}parent.appendChild(e);return e;}
function tabs(parent,entries,selected){
 const bar=document.createElement('div');bar.className='workspace-tabs';bar.setAttribute('role','tablist');
 const choose=id=>{for(const [key,label,node]of entries){node.hidden=key!==id;const b=bar.querySelector('[data-tab="'+key+'"]');b.classList.toggle('active',key===id);b.setAttribute('aria-selected',String(key===id));b.tabIndex=key===id?0:-1;}};
 for(const [id,label,node]of entries){const b=document.createElement('button');b.type='button';b.dataset.tab=id;b.id=id+'-tab';b.textContent=label;b.setAttribute('role','tab');b.setAttribute('aria-controls',node.id);node.setAttribute('role','tabpanel');node.setAttribute('aria-labelledby',b.id);b.onclick=()=>choose(id);bar.appendChild(b);}
 bar.onkeydown=e=>{const bs=[...bar.querySelectorAll('button')],i=bs.indexOf(document.activeElement);if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const n=e.key==='Home'?0:e.key==='End'?bs.length-1:(i+(e.key==='ArrowRight'?1:-1)+bs.length)%bs.length;bs[n].click();bs[n].focus();}};
 parent.prepend(bar);choose(selected||entries[0][0]);return choose;
}
const main=document.querySelector('main'),admin=pane('administration','',main);
const adminUpload=pane('admin-upload','Hlaða upp skjali',admin),adminWeb=pane('admin-web','Sækja af vef birgis',admin),adminQuality=pane('admin-quality','Gagnagæði',admin),adminHistory=pane('admin-history','Saga og afrit',admin),adminSettings=pane('admin-settings','Stillingar',admin);
adminUpload.innerHTML+='<p>Verðlisti: CSV. Efnislisti/BOM: Excel, CSV eða límd tafla. Forskoðaðu, yfirfarðu frávik og staðfestu síðan. Innlestur breytir ekki gögnum við skjalaval.</p><p><button id="upload-price" class="primary">Hlaða upp verðlista</button> <button id="upload-bom">Hlaða upp efnislista / BOM</button></p>';
$('upload-price').onclick=()=>openPriceImport();$('upload-bom').onclick=()=>{showWorkspace('bom');$('bom-import-details').open=true;$('bom-name').focus();};
move(document.querySelector('.sync-controls'),adminWeb);move($('import-progress'),adminWeb);move($('sync-summary'),adminWeb);move($('sync-sources'),adminWeb);
for(const id of ['coverage','stats','data-health'])move($(id),adminQuality);
adminQuality.insertAdjacentHTML('beforeend','<p><button id="workspace-audit">Yfirferð alls vörusafns</button></p>');$('workspace-audit').onclick=showFamilyAudit;
move($('data-tools'),adminHistory);$('data-tools').open=true;
const aiNotice=$('ai-status').closest('.notice');move(aiNotice,adminSettings);
const chooseAdmin=tabs(admin,[['upload','Skjöl',adminUpload],['web','Vefuppfærslur',adminWeb],['quality','Gagnagæði',adminQuality],['history','Saga og afrit',adminHistory],['settings','Stillingar',adminSettings]]);
const header=main.querySelector('header');const actions=header.lastElementChild;move($('refresh-market'),adminWeb);move($('import-open'),adminUpload);actions.remove();header.querySelector('.eyebrow').remove();header.querySelector('.muted').textContent='Finndu vöruna og bættu við réttum lista.';
header.insertAdjacentHTML('beforeend','<button id="assistant-open">✦ Spjalla við Njörð</button>');$('assistant-open').onclick=()=>openAssistant();
const nav=document.querySelector('aside');nav.querySelectorAll('.nav').forEach(b=>b.remove());const foot=nav.querySelector('.aside-foot');for(const [id,label]of [['catalogue','Vörur'],['bom','Innkaupalistar'],['suppliers','Birgjar'],['administration','Gagnaumsjón']]){const b=document.createElement('button');b.dataset.view=id;b.className='nav';b.textContent=label;nav.insertBefore(b,foot);}
// Compatibility links used by existing event handlers remain available but off screen.
const oldProjectNav=document.createElement('button');oldProjectNav.dataset.view='projects';oldProjectNav.hidden=true;nav.appendChild(oldProjectNav);
main.insertAdjacentHTML('afterbegin','<p id="workspace-status" role="status"></p>');
function showWorkspace(id){
 if(id==='assistant'){openAssistant();return;}if(id==='projects'){id='bom';$('legacy-lists').open=true;}
 workspaceScroll[workspace]=window.scrollY;workspace=id;
 for(const key of ['catalogue','bom','suppliers','administration'])$(key).hidden=key!==id;
 $('heading').textContent={catalogue:'Vörur',bom:'Innkaupalistar',suppliers:'Birgjar',administration:'Gagnaumsjón'}[id]||'Njörður';
 document.querySelectorAll('.nav').forEach(b=>b.classList.toggle('active',b.dataset.view===id));
 window.scrollTo(0,workspaceScroll[id]||0);if(id==='administration')loadDataTools();updateContext();
}
function statusLine(){const info=state.metadata?.sync||{};const bad=$('data-health').textContent.startsWith('Hleðsluvilla:');$('workspace-status').innerHTML=(bad?'Ekki tókst að hlaða gögnum — fyrri sýn varðveitt.':info.running?'Uppfærsla í gangi.':info.error?'Villa í síðustu uppfærslu.':!state.offers.length?'Engin vörugögn fundust.':'')+' <button class="text-button" id="status-admin">Skoða stöðu</button>';$('status-admin').onclick=()=>{showWorkspace('administration');chooseAdmin(bad?'quality':'web');};}
const originalProgress=renderImportProgress;renderImportProgress=function(info){originalProgress(info);statusLine();};
// Search comes first. Preserve the actual inputs and their event handlers.
const cat=$('catalogue'),toolbar=cat.querySelector('.toolbar');cat.prepend(toolbar);cat.querySelector('.quick').remove();
const advanced=document.createElement('details');advanced.id='more-filters';advanced.innerHTML='<summary>Fleiri síur</summary>';toolbar.after(advanced);advanced.insertAdjacentHTML('beforeend','<label class="inline-check"><input id="show-empty-categories" type="checkbox"> Sýna tóma flokka í flokkasíum</label>');$('show-empty-categories').onchange=()=>renderProducts();
move($('source-filter').closest('label'),advanced);
const activeBar=document.createElement('div');activeBar.className='active-list-bar';activeBar.innerHTML='<label>Virkur innkaupalisti <select id="active-list"><option value="">Velja / stofna lista…</option></select></label><button id="active-open">Opna lista</button><button id="active-drafts">Innkaupadrög</button>';toolbar.after(activeBar);
$('active-open').onclick=()=>showWorkspace('bom');$('active-drafts').onclick=()=>{$('cart-open').click();};
const recent=$('recent-lists');const recentDetails=document.createElement('details');recentDetails.innerHTML='<summary>Nýlegir innkaupalistar</summary>';cat.appendChild(recentDetails);move(recent,recentDetails);
const crumbs=document.createElement('nav');crumbs.id='breadcrumbs';crumbs.setAttribute('aria-label','Flokkunarstígur');toolbar.before(crumbs);
const chips=document.createElement('div');chips.id='filter-chips';advanced.after(chips);
const viewBar=document.createElement('div');viewBar.className='workspace-tabs';viewBar.innerHTML='<button id="product-cards-view" aria-pressed="true">Spjöld</button><button id="product-table-view" aria-pressed="false">Tafla</button>';cat.querySelector('.section-title').appendChild(viewBar);
$('product-cards-view').onclick=()=>{productView='cards';renderProducts();};$('product-table-view').onclick=()=>{productView='table';renderProducts();};
const originalFilters=taxonomyFilters;taxonomyFilters=function(){originalFilters();if(!$('taxonomy-filters'))return;move($('taxonomy-filters'),advanced);move($('spec-filter-panel'),advanced);if(!$('show-empty-categories').checked){for(const [index,id] of ['category','subcategory-filter','type-filter'].entries()){const select=$(id),value=select.value;for(const option of [...select.options]){if(option.value&&option.value!==value&&!state.offers.some(o=>o.classification?.path?.[index]===option.value))option.remove();}}}};
function searchNavigation(){
 const ids=['category','subcategory-filter','type-filter'];crumbs.innerHTML='<button class="text-button" data-crumb="-1">Allar vörur</button>'+ids.map((id,i)=>$(id)?.value?` › <button class="text-button" data-crumb="${i}">${esc($(id).value)}</button>`:'').join('');
 const filterIds=['supplier','source-filter','brand-filter','unit-filter','review-filter',...Object.keys(specLabels).map(k=>'filter-'+k)];chips.innerHTML=filterIds.filter(id=>$(id)?.value).map(id=>`<button data-clear-filter="${id}">${esc($(id).closest('label')?.childNodes[0]?.textContent||'Sía')}: ${esc($(id).selectedOptions?.[0]?.textContent||$(id).value)} ×</button>`).join('');
 $('product-cards-view').setAttribute('aria-pressed',String(productView==='cards'));$('product-table-view').setAttribute('aria-pressed',String(productView==='table'));
}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.crumb!==undefined){const ids=['category','subcategory-filter','type-filter'];for(let i=Number(b.dataset.crumb)+1;i<ids.length;i++)$(ids[i]).value='';selectedFamilyId='';renderProducts();}if(b.dataset.clearFilter){$(b.dataset.clearFilter).value='';renderProducts();}});
const originalFamily=renderFamilyResults;renderFamilyResults=function(filtered){
 originalFamily(filtered);searchNavigation();$('family-audit')?.remove();$('search-summary').textContent='Fjölskyldur lýsa notkun; tæknilegt jafngildi er ekki sjálfkrafa staðfest.';
 if(productView==='table'){
  const cards=$('products').querySelector('.product-cards');if(cards){const list=[...cards.querySelectorAll('.product-card')];const rows=list.map(c=>{const b=c.querySelector('button');return `<tr><td>${b?.outerHTML||''}</td><td>${esc(c.querySelector('h3')?.textContent||'')}</td><td>${[...c.querySelectorAll('p')].map(p=>esc(p.textContent)).join('<br>')}</td></tr>`;}).join('');const wrap=document.createElement('div');wrap.innerHTML=table(['OPNA','HEITI','ÚTFÆRSLUR / VERÐ / EIGINLEIKAR'],rows);cards.replaceWith(wrap);}
 }
};
// Compact family cards use the existing identity and price calculation rules.
variantCard=function(g){const o=g.representative,fields=familySpecKeys(o.classification?.id||'').filter(k=>o.specifications?.[k]!=null).slice(0,3);return `<article class="card product-card"><div class="card-image">${o.image_url?`<img src="${esc(o.image_url)}" alt="${esc(o.name)}" loading="lazy" referrerpolicy="no-referrer">`:'Mynd ekki tiltæk'}</div><h3>${esc(o.name)}</h3><p>${esc(o.brand||'Framleiðandi óskráður')}${o.manufacturer_part?' · '+esc(o.manufacturer_part):''}</p><p>${fields.map(k=>esc(specLabels[k])+': '+esc(o.specifications[k])).join(' · ')||'Tæknigögn vantar'}</p><p>${new Set(g.offers.map(x=>x.supplier)).size} birgjar</p>${familyPriceText(g.offers)}<button data-detail="${o.id}">Skoða útfærslu</button></article>`;};
// Group the existing detail nodes into panels; keep async targets and form listeners intact.
const originalDetail=detail;detail=function(id){returnFocus=document.activeElement;originalDetail(id);const o=state.offers.find(x=>x.id===id);if(o)organizeDetail(o);};
function organizeDetail(o){
 const root=$('detail'),nodes=[...root.children],head=document.createElement('div');head.className='product-head';const panels={offers:pane('product-offers','',root),technical:pane('product-technical','',root),history:pane('product-history','',root),edit:pane('product-edit','',root)};root.prepend(head);
 let section='offers',headline=false;
 for(const n of nodes){
  if(n.id==='product-photo'){move(n,head);continue;}
  if(n.tagName==='H2'&&!headline){move(n,head);headline=true;continue;}
  if(n.id==='supplier-information'||n.id==='supplier-documents'){move(n,panels.technical);continue;}
  if(n.id==='classification-form'||n.querySelector('#taxonomy-form')||n.classList.contains('ai-review')){move(n,panels.edit);continue;}
  if(n.querySelector('#bom-add-product')){move(n,panels.offers);n.id='product-add-section';continue;}
  if(n.querySelector('#offer-terms-form')){move(n,panels.edit);continue;}
  if(n.id==='auto-history'){move(n,panels.history);continue;}
  if(n.tagName==='H3'){const t=n.textContent;section=/Eiginleikar/.test(t)?'technical':/saga|Reikningsmagn|Heimildir|athugana/i.test(t)?'history':'offers';}
  move(n,panels[section]);
 }
 head.insertAdjacentHTML('beforeend',`<div class="product-actions"><button class="primary" id="detail-add">Bæta á lista</button> <button id="detail-edit">Breyta / yfirfara</button> <button id="detail-chat">Spyrja Njörð</button></div>`);
 const choose=tabs(root,[['offers','Útfærslur og birgjar',panels.offers],['technical','Tæknigögn',panels.technical],['history','Saga og heimildir',panels.history]]);root.prepend(head);panels.edit.hidden=true;
 $('detail-edit').onclick=()=>{for(const p of Object.values(panels))p.hidden=true;panels.edit.hidden=false;panels.edit.querySelector('input,select,button')?.focus();};
 $('detail-add').onclick=()=>{choose('offers');$('product-add-section')?.scrollIntoView({block:'start',behavior:'smooth'});$('bom-target-quantity')?.focus();};
 $('detail-chat').onclick=()=>openAssistant();
 const target=$('bom-target');if(target){const observer=new MutationObserver(()=>{if(activeBOM&&target.querySelector('option[value="'+activeBOM.id+'"]')){target.value=String(activeBOM.id);observer.disconnect();}});observer.observe(target,{childList:true});}
 updateContext();
}
$('detail-dialog').addEventListener('close',()=>{closeAssistant();returnFocus?.focus?.();});
// Lists share one workspace; old project lists remain intact and visibly separate.
const legacy=document.createElement('details');legacy.id='legacy-lists';legacy.innerHTML='<summary>Eldri verkefnalistar · magn í pakkningum</summary>';$('bom').appendChild(legacy);move($('projects'),legacy);$('projects').hidden=false;
const newBOM=document.createElement('details');newBOM.id='bom-import-details';newBOM.innerHTML='<summary>Stofna / lesa inn nýjan efnislista</summary>';const form=$('bom-import-form');form.before(newBOM);move(form,newBOM);
const originalLoadBOM=loadBOMLists;loadBOMLists=async function(selected){await originalLoadBOM(selected);$('active-list').innerHTML=$('bom-select').innerHTML;$('active-list').value=selected?String(selected):activeBOM?String(activeBOM.id):'';};
const originalSelectBOM=selectBOM;selectBOM=async function(id){await originalSelectBOM(id);$('active-list').value=id?String(id):'';updateContext();};
$('active-list').onchange=()=>run(async()=>{await selectBOM($('active-list').value);$('bom-select').value=$('active-list').value;});
// Keep required quantities and technical approvals from the existing BOM form.
const originalPlanning=renderBOMPlanning;renderBOMPlanning=function(){originalPlanning();const p=$('bom-planning');if(!p)return;let panel=$('list-planning-fold');if(!panel){panel=document.createElement('details');panel.id='list-planning-fold';panel.innerHTML='<summary>Birgjaval, heildarkostnaður og tilboðsbeiðnir</summary>';p.before(panel);move(p,panel);}};
// Chat is a contextual side panel, including while a modal product is open.
const assistant=$('assistant');assistant.classList.add('assistant-drawer');assistant.setAttribute('aria-label','Spjalla við Njörð');assistant.insertAdjacentHTML('afterbegin','<button id="assistant-close" aria-label="Loka aðstoð">✕</button><label>Samhengi<select id="assistant-context"><option value="current">Núverandi vara / listi / birgir</option><option value="none">Almenn vöruleit</option></select></label><p id="assistant-context-label"></p><p class="pill">Lesaðstoð · engar sjálfvirkar breytingar</p><details><summary>Skjal til yfirferðar</summary><p>Veldu vinnslu. Skjalið opnast í sameiginlegu forskoðunarferli; ekkert er vistað án staðfestingar.</p><button id="chat-price-upload">Verðlisti CSV</button> <button id="chat-bom-upload">Innkaupalisti Excel / CSV</button><p>PDF og myndagreining eru ekki enn studd í þessari útgáfu.</p></details>');
function currentContext(){if($('assistant-context').value==='none')return {};if($('detail-dialog').open)return {offer_id:Number($('detail').dataset.productId)};if(workspace==='bom'&&activeBOM)return {bom_id:activeBOM.id};if($('supplier-dialog').open&&supplierEditing)return {supplier:supplierEditing.catalogue_name||supplierEditing.name};return {query:$('search').value,supplier:$('supplier').value};}
function updateContext(){if(!$('assistant-context-label'))return;const c=currentContext();const o=state.offers.find(o=>o.id===c.offer_id);$('assistant-context-label').textContent=o?'Vara: '+o.name:c.bom_id?'Listi: '+activeBOM.name:c.supplier?'Birgir: '+c.supplier:c.query?'Leit: '+c.query:'Almenn vöruleit';}
function openAssistant(){const dialog=[...document.querySelectorAll('dialog')].find(d=>d.open);move(assistant,dialog||document.body);$('purchase-cart').hidden=true;assistant.hidden=false;updateContext();$('chat-message').focus();}
function closeAssistant(){assistant.hidden=true;move(assistant,document.body);}
$('assistant-close').onclick=closeAssistant;$('assistant-context').onchange=updateContext;
function closeModals(){document.querySelectorAll('dialog').forEach(d=>{if(d.open)d.close();});closeAssistant();}
$('chat-price-upload').onclick=()=>{closeModals();openPriceImport();};$('chat-bom-upload').onclick=()=>{closeModals();$('upload-bom').click();};
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!assistant.hidden){e.preventDefault();e.stopPropagation();closeAssistant();}},true);
// Supplier overview uses the canonical profile and catalogue, not a second product search.
$('supplier-cards').before(Object.assign(document.createElement('div'),{id:'supplier-toolbar'}));$('supplier-toolbar').innerHTML='<label>Leita að birgja eða vöruflokki<input id="supplier-search" type="search"></label><button id="supplier-table">Tafla</button> <button id="supplier-grid">Spjöld</button>';
function supplierRows(){
 const q=supplierSearch.toLowerCase();
 const rows=supplierProfiles.map((s,i)=>{const name=s.catalogue_name||s.name,offers=state.offers.filter(o=>o.supplier===name),groups=[...new Set(offers.map(o=>o.classification?.path?.[0]).filter(Boolean))];const source=(state.metadata?.sync?.available_sources||[]).find(x=>x.name===name),status=state.metadata?.sync?.sources?.[source?.key]||{};return {s,i,offers,groups,status};}).filter(x=>!q||(x.s.name+' '+x.groups.join(' ')).toLowerCase().includes(supplierSearch.toLowerCase()));
 const body=rows.map(({s,i,offers,groups,status})=>{const values=[`<b>${esc(s.name)}</b><small>${groups.slice(0,3).map(esc).join(' · ')||'Flokkar óskráðir'}</small>`,`${offers.length} / ${offers.filter(o=>o.price!=null).length}`,status.last_success_at?date(status.last_success_at):'Óskráð',offers.filter(o=>o.classification?.needs_review).length+' til flokkunaryfirferðar'+(['blocked','error'].includes(status.status)?' · Uppfærsluvilla':''),`<button data-edit-supplier="${i}">Opna birgja</button> <button data-supplier-products="${i}">Vöruframboð</button>`];return supplierView==='table'?'<tr>'+values.map(v=>'<td>'+v+'</td>').join('')+'</tr>':'<article class="card">'+values.map(v=>'<p>'+v+'</p>').join('')+'</article>';}).join('');
 $('supplier-cards').className=supplierView==='table'?'':'cards';$('supplier-cards').innerHTML=supplierView==='table'?table(['BIRGIR / FLOKKAR','FÆRSLUR / MEÐ VERÐI','SÍÐAST TÓKST','YFIRFERÐ',''],body):body;
}
const originalProfiles=loadSupplierProfiles;loadSupplierProfiles=async function(){await originalProfiles();supplierRows();};
$('supplier-search').oninput=e=>{supplierSearch=e.target.value;supplierRows();};$('supplier-table').onclick=()=>{supplierView='table';supplierRows();};$('supplier-grid').onclick=()=>{supplierView='cards';supplierRows();};
function supplierProducts(s){closeModals();$('supplier').value=s.catalogue_name||s.name;showWorkspace('catalogue');renderProducts();}
document.addEventListener('click',e=>{const b=e.target.closest('[data-supplier-products]');if(b)supplierProducts(supplierProfiles[Number(b.dataset.supplierProducts)]);});
const originalSupplier=editSupplier;editSupplier=function(s={}){originalSupplier(s);organizeSupplier(s);};
function organizeSupplier(s){
 const dialog=$('supplier-dialog');for(const id of ['supplier-form','supplier-probe','supplier-discovery'])move($(id),dialog);dialog.querySelector('.supplier-workspace')?.remove();const shell=document.createElement('div');shell.className='supplier-workspace';dialog.appendChild(shell);
 const overview=pane('supplier-overview','',shell),products=pane('supplier-products-pane','',shell),docs=pane('supplier-docs-pane','',shell),updates=pane('supplier-updates-pane','',shell);
 move($('supplier-form'),overview);const discovery=$('supplier-discovery');move($('supplier-probe'),updates);move(discovery,updates);
 // Remove obsolete static explanatory siblings; all functional nodes have moved.
 for(const n of [...dialog.children])if(n!==shell&&!n.classList.contains('section-title'))n.remove();
 products.innerHTML='<p>Sameiginleg vöruleit með birgjann forvalinn.</p><button id="supplier-browse">Skoða vöruframboð</button>';$('supplier-browse').onclick=()=>supplierProducts(s);
 docs.innerHTML='<p><button id="supplier-import-price" class="primary">Lesa inn verðlista</button></p><p id="supplier-doc-list">Sæki innlestrarsögu…</p>';$('supplier-import-price').onclick=()=>{closeModals();openPriceImport(s.catalogue_name||s.name);};
 api('supplier-imports?name='+encodeURIComponent(s.catalogue_name||s.name||'')).then(rows=>{if(!$('supplier-doc-list'))return;$('supplier-doc-list').textContent=rows.length?rows.map(r=>r.source+' · '+date(r.created_at)+' · '+r.status).join('\n'):'Engin tengd innflutningssaga skráð.';}).catch(e=>{if($('supplier-doc-list'))$('supplier-doc-list').textContent=e.message;});
 updates.insertAdjacentHTML('afterbegin','<p><button id="supplier-update">Uppfæra þennan birgja</button> <button id="supplier-update-status">Skoða framvindu</button></p><p>Könnun vöruskrár finnur mögulegar tengingar; hún virkjar ekki sjálfkrafa nýjan innlesara.</p>');
 $('supplier-update-status').onclick=()=>{closeModals();showWorkspace('administration');chooseAdmin('web');};
 $('supplier-update').onclick=()=>{const source=(state.metadata?.sync?.available_sources||[]).find(x=>x.name===(s.catalogue_name||s.name));if(!source){$('supplier-discovery').textContent='Enginn sjálfvirkur innlesari er tengdur þessum birgja. Notaðu könnun eða verðlista.';return;}closeModals();showWorkspace('administration');chooseAdmin('web');document.querySelectorAll('#sync-source-options input').forEach(x=>x.checked=x.value===source.key);updateSourceCount();$('refresh-market').click();};
 tabs(shell,[['supplier-summary','Yfirlit',overview],['supplier-products','Vörur',products],['supplier-docs','Verðlistar og gögn',docs],['supplier-updates','Uppfærslur',updates]]);
}
let importSupplier='';
$('import-form').insertAdjacentHTML('afterbegin','<label>Birgir til yfirferðar<input id="import-supplier" placeholder="Birgir úr skjali"></label><p>1. Velja skjal → 2. Forskoða → 3. Yfirfara frávik → 4. Staðfesta</p>');
function openPriceImport(name=''){showWorkspace('administration');chooseAdmin('upload');importSupplier=name;$('import-supplier').value=name;$('import-dialog').showModal();}
$('import-open').onclick=()=>openPriceImport();
// Existing cart stays a draft until a named list is selected and confirmed.
$('cart-save-form').insertAdjacentHTML('afterbegin','<label>Bæta við vistaðan lista<select id="cart-target"><option value="">Stofna nýjan lista</option></select></label>');
const originalCartOpen=$('cart-open').onclick;$('cart-open').onclick=()=>{closeAssistant();originalCartOpen();$('cart-target').innerHTML='<option value="">Stofna nýjan lista</option>'+$('bom-select').innerHTML;$('cart-target').value=activeBOM?String(activeBOM.id):'';$('cart-name').required=!$('cart-target').value;};
$('cart-target').onchange=()=>$('cart-name').required=!$('cart-target').value;
const originalAddCart=addCart;addCart=function(ids){if($('detail-dialog').open)$('detail-dialog').close();originalAddCart(ids);$('cart-open').click();};
// Initialize after original asynchronous catalogue/profile loading also completes.
const originalRefresh=refresh;refresh=async function(){await originalRefresh();statusLine();supplierRows();};
loadBOMLists().catch(e=>$('status').textContent=e.message);loadSupplierProfiles();if(state.offers.length)renderProducts();statusLine();showWorkspace('catalogue');

document.addEventListener('click',e=>{const b=e.target.closest('[data-pending-import]');if(b)run(async()=>{const r=await api('import-pending?token='+encodeURIComponent(b.dataset.pendingImport));openPriceImport();showPricePreview(r);});});
