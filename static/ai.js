'use strict';
let aiBusy=false;
async function aiStatus(){
 try{const s=await api('ai-status');$('ai-status').textContent=s.configured?`Lykill skráður · ${s.model} · tenging verður prófuð við fyrstu beiðni.`:'Óvirk þar til API-lykli er bætt við. Kerfið virkar áfram án AI.';}
 catch{$('ai-status').textContent='Ekki tókst að lesa AI-stillingar.';}
}
const aiList=items=>items.length?'<ul>'+items.map(x=>`<li>${esc(x)}</li>`).join('')+'</ul>':'<p>Engar frekari athugasemdir.</p>';
document.addEventListener('click',async event=>{
 const b=event.target.closest('button');if(!b)return;
 if(b.dataset.aiReview){
  const id=Number(b.dataset.aiReview),box=$('ai-product-result');
  if(aiBusy){box.textContent='Önnur AI-beiðni er í gangi.';return;}
  aiBusy=true;b.disabled=true;box.textContent='Yfirferð í gangi…';
  try{
   const r=await api('ai-review',{id,categories:state.metadata?.taxonomy?taxLeaves().map(l=>l.path.join(' → ')):[...ProductGroups.categories,'Annað og óflokkað']});
   if(!box.isConnected||$('detail').dataset.productId!==String(id))return;
   box.innerHTML=`<p><b>Tillaga: ${esc(r.category)}</b></p><p>${esc(r.reason)}</p>${aiList(r.issues)}<button type="button" id="ai-use-category">Setja tillögu í flokkunarreit</button><p class="muted">Yfirfarðu síðan og vistaðu flokkun í forminu hér fyrir neðan. Engin breyting hefur verið vistuð.</p>`;
   $('ai-use-category').onclick=()=>{if($('taxonomy-form')){const leaf=taxLeaves().find(l=>l.path.join(' → ')===r.category);if(!leaf)return;$('edit-top').value=leaf.id.split('.')[0];$('edit-top').onchange();$('edit-sub').value=leaf.id.split('.').slice(0,2).join('.');$('edit-sub').onchange();$('edit-type').value=leaf.id;$('edit-type').focus();}else{$('product-category').value=r.category;$('product-category').focus();}};
  }catch(e){if(box.isConnected)box.textContent=e.message;}
  finally{aiBusy=false;b.disabled=false;}
 }
 if(b.dataset.aiLine){
  const line=bomQuote?.lines.find(l=>l.line_id===b.dataset.aiLine),box=b.closest('details').querySelector('.ai-bom-result');
  if(!line||!activeBOM)return;
  if(aiBusy){box.textContent='Önnur AI-beiðni er í gangi.';return;}
  aiBusy=true;b.disabled=true;box.textContent='Met vörutillögur…';
  const candidates=line.candidates.slice(0,40);
  try{
   const r=await api('ai-bom',{id:activeBOM.id,line_id:line.line_id,candidates:candidates.map(c=>c.offer.id)});
   if(!box.isConnected)return;
   box.innerHTML=`<p>${esc(r.summary)}</p><p class="muted">${candidates.length} tillögur metnar. Yfirfarðu kröfurnar og merktu sjálfur við viðeigandi vörur hér að ofan.</p>`+r.suggestions.map(s=>{const o=candidates.find(c=>c.offer.id===s.id).offer;return `<div class="card"><b>${esc(o.name)} · ${esc(o.supplier)} · ${esc(o.sku||'')}</b><p>${esc(s.reason)}</p>${aiList(s.checks)}<button type="button" data-detail="${o.id}">Skoða vöruspjald</button></div>`;}).join('');
  }catch(e){if(box.isConnected)box.textContent=e.message;}
  finally{aiBusy=false;b.disabled=false;}
 }
});
aiStatus();
