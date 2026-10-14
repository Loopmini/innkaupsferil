'use strict';
let selectedFamilyId='',familyQuery='';
const numericSpec=k=>k.endsWith('_mm')||['head_weight_g','weight_g','voltage_v','current_a','power_w'].includes(k);
function familySpecKeys(id){
 const config=state.metadata?.taxonomy?.comparison_fields||{};
 const keys=Object.keys(config).filter(k=>id===k||id.startsWith(k+'.')||k.startsWith(id+'.'));
 const longest=keys.filter(k=>!keys.some(other=>other!==k&&other.startsWith(k+'.')));
 return [...new Set(longest.flatMap(k=>config[k]).concat(['material','standard']))];
}
function familyPriceText(offers){
 const ranges=ProductFamilies.priceGroups(offers);
 if(!ranges.length)return '<p class="muted">Samanburðarhæft verð vantar eða er úrelt.</p>';
 return ranges.map(r=>`<p><b>${money(r.min,r.currency)}${r.max!==r.min?' – '+money(r.max,r.currency):''} / ${esc(r.unit)}</b> án VSK<small>${esc(r.scope)} · ${r.items.length} verðfærslur með staðfestan grunn</small></p>`).join('');
}
function variantSpecs(o){
 return familySpecKeys(o.classification?.id||'').map(k=>`<span><b>${esc(specLabels[k]||k)}:</b> ${esc(o.specifications?.[k]??'Óskráð')}</span>`).join(' · ');
}
function variantCard(g){
 const o=g.representative;
 return `<article class="card product-card">${o.image_url?`<img src="${esc(o.image_url)}" alt="${esc(o.name)}" loading="lazy" referrerpolicy="no-referrer">`:'<div class="card-image">Mynd ekki tiltæk</div>'}<h3>${esc(o.name)}</h3><p>${esc(o.brand||'Framleiðandi óskráður')} · MPN ${esc(o.manufacturer_part||'Óskráð')} · EAN ${esc(o.gtin||'Óskráð')}</p><p>${variantSpecs(o)}</p><p>${esc((o.description||'Lýsing óskráð').slice(0,240))}</p><p>${new Set(g.offers.map(x=>x.supplier)).size} birgjar · ${g.offers.length} birgjafærslur</p><p>${g.offers.map(x=>esc(x.supplier)+' · '+esc(x.sku||'Vörunúmer óskráð')).join('<br>')}</p>${familyPriceText(g.offers)}<p><button data-detail="${o.id}">Skoða útfærslu og birgjatilboð</button></p><small>Veldu ákveðna vöru, birgja og magn á vöruspjaldinu.</small></article>`;
}
function renderFamilyResults(filtered){
 const q=$('search').value.trim();if(q!==familyQuery){selectedFamilyId='';familyQuery=q;}
 const fs=ProductFamilies.families(filtered).sort((a,b)=>a.path.join().localeCompare(b.path.join(),'is'));
 const exact=!!q&&filtered.some(o=>[o.sku,o.manufacturer_part,o.gtin].some(v=>v&&String(v).trim().toLowerCase()===q.toLowerCase()));
 const chosen=fs.find(f=>f.id===selectedFamilyId)||($('type-filter').value&&fs.length===1?fs[0]:null);
 const products=ProductSearch.grouped(filtered);
 $('result-count').textContent=`${fs.filter(f=>!f.review).length} vörufjölskyldur · ${products.length} vörur/útfærslur · ${filtered.length} birgjafærslur`;
 $('catalogue-title').textContent=chosen?chosen.path.join(' → '):'Vörufjölskyldur';
 $('search-summary').textContent='Vörufjölskylda er yfirlit um notkun, ekki staðfesting á tæknilegu jafngildi. Óviss auðkenni og flokkun eru merkt til yfirferðar.';
 let html='<p><button id="tax-reset">Hreinsa allar síur</button> <button id="family-audit">Yfirferð alls vörusafns</button></p>';
 if(chosen||exact){
  html+='<p><button id="family-back">← Allar vörufjölskyldur</button></p>';
  if(chosen?.review)html+='<p class="pill warn">Ótilgreind vörutegund · þarf yfirferð</p>';
  const rows=chosen?chosen.products:products;
  if(chosen){const fields=familySpecKeys(chosen.id);html+='<details class="card"><summary>Samanburðartafla útfærslna · ekki jafngildisstaðfesting</summary>'+table(['ÚTFÆRSLA','FRAMLEIÐANDI / MPN',...fields.map(k=>specLabels[k]||k),'BIRGJAR'],rows.slice(0,pageLimit).map(g=>{const o=g.representative;return `<tr><td><button data-detail="${o.id}">${esc(o.name)}</button></td><td>${esc(o.brand||'Óskráð')} · ${esc(o.manufacturer_part||'Óskráð')}</td>${fields.map(k=>`<td>${esc(o.specifications?.[k]??'Óskráð')}</td>`).join('')}<td>${g.offers.map(x=>esc(x.supplier)).join(', ')}</td></tr>`;}).join(''))+'</details>';}
  html+='<p>Veldu útfærslu til að sjá tilboð, heimildir, gagnablöð og bæta ákveðnu birgjavali á BOM.</p><div class="cards product-cards">'+rows.slice(0,pageLimit).map(variantCard).join('')+'</div>'+(rows.length>pageLimit?'<button id="show-more">Sýna fleiri</button>':'');
 }else{
  html+='<div class="cards product-cards">'+fs.map(f=>{
   const leaf=taxLeaves().find(l=>l.id===f.id),photo=f.offers.find(o=>o.image_url);
   const fields=familySpecKeys(f.id).filter(k=>f.offers.some(o=>o.specifications?.[k]!=null));
   return `<article class="card product-card">${photo?`<img src="${esc(photo.image_url)}" alt="Dæmi: ${esc(photo.name)}" loading="lazy" referrerpolicy="no-referrer"><small>Dæmismynd úr úrvali · ${esc(photo.supplier)}</small>`:'<div class="card-image">Mynd ekki tiltæk</div>'}<h3>${esc(f.path.at(-1))}</h3><p>${esc(leaf?.description||'')}</p>${f.review?'<span class="pill warn">Vörutegund óviss · þarf yfirferð</span>':''}<p><b>${f.products.length} vörur/útfærslur</b> · ${f.suppliers.length} birgjar</p>${familyPriceText(f.offers)}<button data-family="${esc(f.id)}">Skoða allt úrvalið</button></article>`;
  }).join('')+'</div>';
 }
 if(!fs.length)html+='<p>Engar vörur passa við valdar síur.</p>';
 $('products').innerHTML=html;
 $('products').querySelectorAll('img').forEach(img=>img.addEventListener('error',()=>{img.replaceWith(document.createTextNode('Mynd frá birgi ekki tiltæk.'));}));
}
function showFamilyAudit(){
 const a=ProductFamilies.audit(state.offers);
 $('family-audit-content').innerHTML=`<p>${a.records} upprunafærslur · ${a.products} vörur/útfærslur · ${a.families} vörufjölskyldur · ${a.reviewBuckets} flokkunarhópar til yfirferðar.</p><p>${a.combinedRecords} færslur falla undir sameiginleg vöruauðkenni í viðmótinu. Engum upprunafærslum er eytt. ${a.reviewRecords} færslur þarfnast yfirferðar.</p><p>Talning fylgir sömu reglum eftir endurhleðslu og innlestur. Slóðavöktun er sér mæling og jafngildir ekki vörufjölda. Fjöldi aðskildra útfærslna miðast við tiltæk auðkenni; fleiri tvítekningar geta falist í færslum sem vantar auðkenni.</p>`+table(['BIRGIR','FJÖLSKYLDUR','VÖRUR / ÚTFÆRSLUR','BIRGJAFÆRSLUR'],a.supplierCounts.map(r=>`<tr><td>${esc(r.supplier)}</td><td>${r.families}</td><td>${r.products}</td><td>${r.records}</td></tr>`).join(''))+'<p><button id="family-review-export">Sækja allan yfirferðarlista CSV</button></p>'+table(['VARA / BIRGIR','ÁSTÆÐA',''],a.review.slice(0,200).map(r=>`<tr><td>${esc(r.name)}<small>${esc(r.supplier)} · ${esc(r.sku||'')}</small></td><td>${esc(r.reason)}</td><td><button data-audit-detail="${r.id}">Yfirfara</button></td></tr>`).join(''))+`<p>Fyrstu ${Math.min(200,a.review.length)} af ${a.review.length} athugasemdum sýndar; allar fylgja CSV.</p>`;
 $('family-audit-dialog').showModal();
 $('family-review-export').onclick=()=>{
  const rows=[['id','upprunalegt_heiti','birgir','vorunumer','astaeda'],...a.review.map(r=>[r.id,r.name,r.supplier,r.sku,r.reason])],safe=v=>'"'+String(v??'').replace(/^[=+@-]/,"'$&").replace(/"/g,'""')+'"';
  const url=URL.createObjectURL(new Blob(['\ufeff'+rows.map(r=>r.map(safe).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'})),link=document.createElement('a');link.href=url;link.download='vorusafn-yfirferd.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 };
}
document.addEventListener('click',e=>{
 const b=e.target.closest('button');if(!b)return;
 if(b.dataset.family){selectedFamilyId=b.dataset.family;familyQuery=$('search').value.trim();const leaf=taxLeaves().find(l=>l.id===selectedFamilyId);if(leaf){$('category').value=leaf.path[0];taxonomyFilters();$('subcategory-filter').value=leaf.path[1];taxonomyFilters();$('type-filter').value=leaf.path[2];}pageLimit=60;renderProducts();}
 if(b.id==='family-back'||b.id==='tax-reset'){selectedFamilyId='';$('type-filter').value='';renderProducts();}
 if(b.id==='family-audit')showFamilyAudit();
 if(b.dataset.auditDetail){$('family-audit-dialog').close();detail(Number(b.dataset.auditDetail));}
});
