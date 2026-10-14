'use strict';
let activeBOM=null,bomQuote=null,bomSaving=false;
async function loadBOMLists(selected){
 const rows=await api('boms');$('bom-select').innerHTML='<option value="">Veldu vistaðan efnislista</option>'+rows.map(r=>`<option value="${r.id}">${esc(r.name)}</option>`).join('');
 if(selected)$('bom-select').value=String(selected);
}
async function selectBOM(id){
 if(!id){activeBOM=null;$('bom-results').innerHTML='';if($('bom-planning'))$('bom-planning').innerHTML='';return;}
 activeBOM=await api('bom?id='+encodeURIComponent(id));if(activeBOM.settings?.currency)$('bom-currency').value=activeBOM.settings.currency;if(!state.offers.length)await refresh();renderBOM();
}
function renderBOM(){
 if(!activeBOM)return;
 const open=new Set([...document.querySelectorAll('#bom-results details[open]')].map(e=>e.dataset.line));
 bomQuote=BOMCore.quote(activeBOM.rows.map(r=>({...r,bom_id:activeBOM.id})),state.offers,activeBOM.selections,$('bom-currency').value,Date.now(),activeBOM.settings||{});
 if(typeof renderBOMPlanning==='function')renderBOMPlanning();
 const q=bomQuote,complete=q.complete;
 const split=Object.entries(q.split).map(([s,n])=>`<div class="bom-supplier-total">${esc(s)}: <b>${money(n,q.currency)}</b></div>`).join('');
 $('bom-results').innerHTML=`<div class="section-title"><h2>${esc(activeBOM.name)}</h2><button id="bom-export">Sækja línuverð CSV (án birgjagjalda)</button></div><p class="muted">${esc(activeBOM.sheet)} · ${q.lines.length} línur eftir sameiningu alveg eins lína.</p><div class="notice"><b>${q.covered} af ${q.lines.length} línum með samþykktri vöru og reiknanlegu verði.</b><p>${complete?'Vörukostnaður valinna lína (án birgjagjalda)':'Hlutakostnaður — heildarverð listans er óþekkt'}: <strong>${money(q.subtotal,q.currency)}</strong> án VSK.</p>${split}<p>Heilar pakkningar · án flutnings og óþekktra afslátta. Samanburður nær aðeins til innlesinna og samþykktra vara. Óstaðfest lagerstaða er ekki afhendingarloforð.</p></div>`;
 $('bom-results').innerHTML+='<h3>Vörukostnaður hjá einum birgi (án birgjagjalda)</h3>'+table(['BIRGIR','VERÐLAGÐAR LÍNUR','KOSTNAÐUR ÁN VSK'],q.suppliers.map(s=>`<tr><td>${esc(s.supplier)}</td><td>${s.coverage} / ${q.lines.length} ${s.complete?'<span class="pill">Allar línur</span>':'<span class="pill warn">Ófullkomið</span>'}</td><td>${s.complete?money(s.total,q.currency):'Heild óþekkt'+(s.coverage?' · hlutakostnaður '+money(s.total,q.currency):'')}</td></tr>`).join(''));
 if(!q.suppliers.length)$('bom-results').innerHTML+='<p>Enginn birgir passar við línurnar í núverandi gögnum.</p>';
 $('bom-results').innerHTML+='<h3>Yfirferð efnislista</h3><p class="muted">Merktu við þær tillögur sem uppfylla kröfurnar. Athugaðu efni, stærð, lengd, festingu og staðla. Aðeins samþykktar vörur með staðfestum verðgrunni fara í kostnaðarsamanburð.</p>'+q.lines.map(l=>{
 const result=l.best?`<span class="bom-price">${esc(l.best.offer.supplier)} · ${money(l.best.total,q.currency)}</span><small>${l.best.packs} pakkningar · ${l.best.supplied} ${esc(l.unit)} keypt · umframmagn ${Number(l.best.excess.toFixed(8))} ${esc(l.unit)}</small>`:l.suggestion?`<span class="bom-issues">Ódýrasta reiknanlega tillaga: ${money(l.suggestion.total,q.currency)} hjá ${esc(l.suggestion.offer.supplier)} — staðfesta þarf vöruna.</span>`:l.candidates.length?'<span class="bom-issues">Vörur fundust; samanburðarhæft verð vantar.</span>':'<span class="bom-issues">Engin samsvörun fannst.</span>';
 return `<details class="bom-line" data-line="${esc(l.line_id)}" ${open.has(l.line_id)?'open':''}><summary><b>${esc(l.name)}</b> · ${l.quantity} ${esc(l.unit)}<small>${l.candidates.length} mögulegar vörufærslur</small>${result}</summary><p>${esc(l.supplier)} ${esc(l.sku)} ${l.gtin?'· GTIN '+esc(l.gtin):''}</p><p class="muted">${Object.entries(l.specifications||{}).map(([k,v])=>esc((typeof specLabels==='object'?specLabels[k]:k)||k)+': '+esc(v)).join(' · ')}</p>`+table(['SAMÞYKKJA','VARA / BIRGIR','MAGN OG KOSTNAÐUR','STAÐA / HEIMILD'],l.candidates.slice(0,50).map(c=>`<tr><td><label class="bom-approve"><input type="checkbox" data-bom-line="${esc(l.line_id)}" data-bom-offer="${c.offer.id}" ${c.approved?'checked':''} ${bomSaving?'disabled':''} aria-label="Samþykkja ${esc(c.offer.name)} hjá ${esc(c.offer.supplier)}"><span>${c.exact?'Sama auðkenni':'Staðganga / yfirfara'}</span></label></td><td><b>${esc(c.offer.name)}</b><small>${esc(c.offer.supplier)} · ${esc(c.offer.sku||'Vörunúmer vantar')}</small></td><td>${c.eligible?`<b>${money(c.total,q.currency)}</b><small>${c.packs} pakkningar × ${c.offer.pack_quantity} ${esc(c.offer.unit)}</small><small>${c.supplied} ${esc(l.unit)} keypt</small>`:`<span class="bom-issues">${esc(c.reason)}</span>`}</td><td>${link(c.offer)}<small>${esc(c.offer.availability||'Lagerstaða óstaðfest')}</small><small>Verðathugun: ${date(c.offer.observed_at)}</small></td></tr>`).join(''))+(l.candidates.length>50?'<p class="muted">Fyrstu 50 niðurstöður sýndar. Þrengdu lýsingu eða bættu vörunúmeri í innlestrarskrána ef þarf.</p>':'')+`<p><button type="button" data-ai-line="${esc(l.line_id)}">AI-aðstoð við þessa línu</button></p><p class="muted">Sendir línuna og allt að 40 vörutillögur til OpenAI. Samþykktu vörur með reitunum hér að ofan.</p><div class="ai-bom-result" role="status"></div></details>`;
 }).join('');
}
$('bom-import-form').onsubmit=async event=>{
 event.preventDefault();$('bom-import-submit').disabled=true;$('bom-status').textContent='Les lista og leita að vörum…';
 try{
  const f=$('bom-file').files[0],text=$('bom-text').value;
  if(f&&text.trim())throw Error('Veldu annaðhvort skrá eða innlímdan texta. Hreinsaðu hitt svæðið.');
  if(!f&&!text.trim())throw Error('Veldu skrá eða límdu inn töflu.');
  const payload={name:$('bom-name').value,text};
  if(f){if(f.size>3000000)throw Error('Hámark 3 MB.');payload.filename=f.name;delete payload.text;const bytes=new Uint8Array(await f.arrayBuffer());let b='';for(let i=0;i<bytes.length;i+=8192)b+=String.fromCharCode(...bytes.subarray(i,i+8192));payload.base64=btoa(b);}
  const result=await api('bom-preview',payload);showBOMPreview(result);
 }catch(e){$('bom-status').textContent=e.message;}finally{$('bom-import-submit').disabled=false;}
};
$('bom-select').onchange=()=>run(async()=>{await selectBOM($('bom-select').value);$('bom-status').textContent='';});
$('bom-currency').onchange=renderBOM;
$('bom-recalculate').onclick=()=>run(async()=>{await refresh();renderBOM();$('bom-status').textContent='Samanburður endurreiknaður með nýjustu innlesnu verði.';});
$('bom-results').addEventListener('change',async event=>{
 const input=event.target;if(!input.dataset.bomLine||!activeBOM||bomSaving)return;
 const id=input.dataset.bomLine,offer=Number(input.dataset.bomOffer),line=bomQuote.lines.find(l=>l.line_id===id);
 const before=JSON.parse(JSON.stringify(activeBOM.selections));
 const accepted=line.candidates.filter(c=>c.approved).map(c=>c.offer.id);
 activeBOM.selections[id]=input.checked?[...new Set([...accepted,offer])]:accepted.filter(x=>x!==offer);
 bomSaving=true;renderBOM();
 try{await api('bom-selection',{id:activeBOM.id,selections:activeBOM.selections});$('bom-status').textContent='Vöruval vistað.';}
 catch(e){activeBOM.selections=before;$('bom-status').textContent=e.message;}
 finally{bomSaving=false;renderBOM();}
});
$('bom-results').addEventListener('click',e=>{
 if(e.target.id!=='bom-export'||!bomQuote)return;
 const safe=v=>'"'+String(v??'').replace(/^[=+@-]/,"'$&").replace(/"/g,'""')+'"';
 const rows=[['heiti','magn','eining','birgir','vorunumer','pakkningar','kostnadur_an_vsk','gjaldmidill','stada','slod'],...bomQuote.lines.map(l=>[l.name,l.quantity,l.unit,l.best?.offer.supplier||'',l.best?.offer.sku||'',l.best?.packs??'',l.best?.total?.toFixed(2)??'',bomQuote.currency,l.best?'Samþykkt vara; athuga afhendingu':'Ólokið / verð vantar',l.best?.offer.url||''])];
 const url=URL.createObjectURL(new Blob(['\ufeff'+rows.map(r=>r.map(safe).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='bom-samanburdur.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
run(()=>loadBOMLists());
