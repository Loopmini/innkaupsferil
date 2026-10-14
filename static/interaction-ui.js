'use strict';
let chatRequest=null,chatGeneration=0,chatAttachment=null,chatOpener=null;
const drawer=$('assistant'),input=$('chat-message');
$('assistant-open').textContent='✦ Spyrja Njörð';$('assistant-open').classList.add('global-assistant');
drawer.insertAdjacentHTML('afterbegin','<div class="chat-window-controls"><button id="chat-expand" aria-pressed="false">Stækka spjall</button><label>Breidd <input id="chat-width" type="range" min="360" max="850" step="10" value="480" aria-label="Breidd spjallspjalds"></label></div>');
$('chat-expand').onclick=()=>{const big=drawer.classList.toggle('chat-expanded');$('chat-expand').textContent=big?'Minnka spjall':'Stækka spjall';$('chat-expand').setAttribute('aria-pressed',String(big));input.focus();};
$('chat-width').oninput=e=>drawer.style.setProperty('--chat-width',e.target.value+'px');
$('chat-form').insertAdjacentHTML('beforeend','<p class="keyboard-hint">Enter sendir · Shift + Enter gerir línuskipti</p><button type="button" id="chat-stop" hidden>Stöðva svar</button> <button type="button" id="chat-retry" hidden>Reyna aftur</button><p class="muted" id="chat-stop-note" hidden>Stöðvun hættir við móttöku og birtingu svars. AI-vinnsla sem þegar hófst á þjóninum getur klárast og haft API-kostnað.</p>');
$('chat-form').insertAdjacentHTML('afterbegin','<div id="chat-drop"><label class="attachment-picker">Hengja við skjal<input id="chat-file" type="file" accept=".csv,.tsv,.xlsx,.txt"></label><p>Dragðu CSV eða Excel hingað. PDF og myndagreining eru enn óstudd.</p><div id="chat-attachment" role="status"></div><label id="chat-document-type-label" hidden>Skjalategund<select id="chat-document-type"><option value="">Veldu vinnslu</option><option value="price">Verðlisti (CSV)</option><option value="bom">Innkaupalisti / BOM</option></select></label></div>');
const prompts=document.createElement('div');prompts.className='chat-actions';prompts.innerHTML=['Útskýrðu muninn á þessum vörum.','Berðu saman birgjatilboðin.','Hvað vantar í þennan lista?'].map(t=>`<button type="button" data-chat-example="${t}">${t}</button>`).join('');$('chat-messages').before(prompts);
const oldOpenAssistant=openAssistant;openAssistant=function(){chatOpener=document.activeElement;oldOpenAssistant();autoSize();};
const oldCloseAssistant=closeAssistant;closeAssistant=function(){oldCloseAssistant();if(chatOpener?.isConnected)chatOpener.focus();};
// Old property handlers captured the prior function; rebind to the focus-restoring wrapper.
$('assistant-close').onclick=()=>closeAssistant();$('assistant-open').onclick=()=>openAssistant();
function autoSize(){input.style.height='auto';input.style.height=Math.min(220,Math.max(76,input.scrollHeight))+'px';}
input.addEventListener('input',autoSize);
input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();if(!aiBusy)$('chat-form').requestSubmit();}});
function setChatBusy(busy){aiBusy=busy;for(const id of ['chat-submit','chat-clear','chat-file','chat-document-type'])$(id).disabled=busy;$('chat-stop').hidden=!busy;$('chat-stop-note').hidden=!busy;}
$('chat-stop').onclick=()=>{chatGeneration++;chatRequest?.abort();chatRequest=null;setChatBusy(false);$('chat-status').textContent='Móttaka svars stöðvuð. Textinn hefur verið varðveittur.';input.focus();};
$('chat-retry').onclick=()=>{if(!aiBusy)$('chat-form').requestSubmit();};
function renderAttachment(){const box=$('chat-attachment');box.innerHTML=chatAttachment?`<b>${esc(chatAttachment.name)}</b> · ${(chatAttachment.size/1024).toFixed(0)} KB · bíður yfirferðar <button type="button" id="chat-remove-file">Fjarlægja viðhengi</button>`:'';$('chat-document-type-label').hidden=!chatAttachment;if($('chat-remove-file'))$('chat-remove-file').onclick=()=>{chatAttachment=null;$('chat-file').value='';$('chat-document-type').value='';renderAttachment();};}
async function attach(file){
 if(aiBusy)return;if(!file)return;
 if(!/\.(csv|tsv|xlsx|txt)$/i.test(file.name)){$('chat-status').textContent='Þetta skjalasnið er ekki stutt enn. Notaðu CSV eða Excel; PDF/myndir þurfa sérstakan útdrátt.';return;}
 if(file.size>3000000){$('chat-status').textContent='Viðhengi má vera mest 3 MB.';return;}
 chatAttachment=file;$('chat-document-type').value='';renderAttachment();
 if(!/\.xlsx$/i.test(file.name)){const head=(await file.slice(0,4000).text()).split(/\r?\n/)[0].toLowerCase();if(chatAttachment!==file)return;
 if(/price/.test(head)&&/supplier/.test(head))$('chat-document-type').value='price';else if(/magn|quantity/.test(head)&&/heiti|name|description/.test(head))$('chat-document-type').value='bom';}
 $('chat-status').textContent=$('chat-document-type').value?'Skjalategund greind. Yfirfarðu valið og sendu til forskoðunar.':'Veldu hvort skjalið er verðlisti eða innkaupalisti áður en þú sendir.';input.focus();
}
$('chat-file').onchange=e=>attach(e.target.files[0]);
for(const event of ['dragenter','dragover'])drawer.addEventListener(event,e=>{e.preventDefault();$('chat-drop').classList.add('drag-active');});
drawer.addEventListener('dragleave',()=>$('chat-drop').classList.remove('drag-active'));
drawer.addEventListener('drop',e=>{e.preventDefault();$('chat-drop').classList.remove('drag-active');if(e.dataTransfer.files.length!==1){$('chat-status').textContent='Veldu eitt skjal í einu.';return;}attach(e.dataTransfer.files[0]);});
async function requestChat(path,data,signal){const res=await fetch('/api/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),signal});const value=await res.json();if(!res.ok)throw Error(value.error||'Beiðni mistókst.');return value;}
function chatAnswer(message,result){
 $('chat-messages').insertAdjacentHTML('beforeend',`<article class="chat-user"><b>Þú</b><p>${esc(message)}</p></article><article class="chat-answer"><b>Njörður</b><p>${esc(result.answer)}</p>${result.questions?.length?aiList(result.questions):''}<div class="cards">${(result.products||[]).map(p=>{const o=state.offers.find(x=>x.id===p.id);return o?`<article class="card"><h3>${esc(o.name)}</h3><p>${esc(p.reason)}</p><p>${esc(o.supplier)} · ${esc(o.sku||'Vörunúmer óskráð')}</p>${priceCell(o)}<small>Verðathugun: ${date(o.observed_at)} · ${esc(o.availability||'Lagerstaða óskráð')}</small><p>${link(o)}</p><button data-detail="${o.id}" data-chat-product>Skoða vöru</button> <button data-cart-offer="${o.id}">Útbúa innkaupadrög</button></article>`:'';}).join('')}</div><p class="muted">${result.reviewed||0} vörufærslur yfirfarnar af ${result.matched||0} leitarsamsvörunum. Verð kemur úr skráðum tilboðum.</p><button type="button" data-copy-answer>Afrita svar</button></article>`);
}
$('chat-form').onsubmit=async e=>{
 e.preventDefault();if(aiBusy)return;const message=input.value.trim(),file=chatAttachment;if(!message&&!file)return;
 if(file&&!$('chat-document-type').value){$('chat-status').textContent='Veldu skjalategund. Óljóst skjal er ekki flutt inn sjálfkrafa.';return;}
 const documentType=$('chat-document-type').value,context=currentContext(),generation=++chatGeneration;
 let follow=drawer.scrollHeight-drawer.scrollTop-drawer.clientHeight<150;const controller=new AbortController();chatRequest=controller;setChatBusy(true);$('chat-retry').hidden=true;
 try{
  if(file){
   $('chat-status').textContent='Les skjal og undirbý forskoðun: '+file.name;
   let result;
   if(documentType==='price'){
    if(!/\.csv$/i.test(file.name))throw Error('Verðlistainnflutningur styður CSV. Veldu CSV-verðlista eða breyttu skjalategund.');
    const csv=await file.text();if(generation!==chatGeneration)return;
    result=await requestChat('import-preview',{csv,source:file.name,supplier:context.supplier||''},controller.signal);
   }else{
    const bytes=new Uint8Array(await file.arrayBuffer());let b='';for(let i=0;i<bytes.length;i+=8192)b+=String.fromCharCode(...bytes.subarray(i,i+8192));if(generation!==chatGeneration)return;
    result=await requestChat('bom-preview',{name:file.name.replace(/\.[^.]+$/,''),filename:file.name,base64:btoa(b)},controller.signal);
   }
   if(generation!==chatGeneration)return;
   follow=follow&&drawer.scrollHeight-drawer.scrollTop-drawer.clientHeight<150;
   const card=document.createElement('article');card.className='chat-answer';card.innerHTML=`<h3>${esc(file.name)}</h3><p>Óstaðfest vinnsludrög · ${result.rows.length} línur. ${documentType==='price'?result.possible_duplicates+' mögulegar tvítekningar.':''} Yfirfarðu og staðfestu í innlestrarferlinu.</p><button type="button">Opna forskoðun</button>`;
   card.querySelector('button').onclick=()=>{closeModals();if(documentType==='price'){openPriceImport(context.supplier||'');showPricePreview(result);}else{showWorkspace('bom');showBOMPreview(result);}};$('chat-messages').appendChild(card);
   if(chatAttachment===file){chatAttachment=null;$('chat-file').value='';renderAttachment();}
   $('chat-status').textContent='Forskoðun tilbúin. Engar vörur, verð eða listar hafa verið staðfest.';
  }else{
   $('chat-status').textContent='Leita í gögnum og útbý svar…';
   const result=await requestChat('ai-chat',{message,history:chatHistory.slice(-8),context},controller.signal);
   if(generation!==chatGeneration)return;
   follow=follow&&drawer.scrollHeight-drawer.scrollTop-drawer.clientHeight<150;
   chatHistory.push({role:'user',text:message},{role:'assistant',text:result.answer});chatHistory=chatHistory.slice(-8);chatAnswer(message,result);$('chat-status').textContent='Svar tilbúið.';
  }
  if(input.value.trim()===message)input.value='';autoSize();if(follow)drawer.scrollTo({top:drawer.scrollHeight,behavior:'auto'});
 }catch(err){if(generation!==chatGeneration)return;$('chat-status').textContent=err.name==='AbortError'?'Móttaka svars stöðvuð.':err.message+' Texti og viðhengi varðveitt.';$('chat-retry').hidden=false;}
 finally{if(generation===chatGeneration){chatRequest=null;setChatBusy(false);if(!drawer.hidden)input.focus();}}
};
function excelCell(value){const text=value.replace(/[\t\r\n]+/g,' ').trim();return /^[=+@-]/.test(text)?"'"+text:text;}
async function copyText(value,button){try{await navigator.clipboard.writeText(value);const old=button.textContent;button.textContent='Afritað';setTimeout(()=>button.textContent=old,1800);}catch{const text=document.createElement('textarea');text.value=value;text.setAttribute('aria-label','Texti til að afrita');button.after(text);text.focus();text.select();button.textContent='Ýttu á Ctrl+C í textareitnum';}}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.hasAttribute('data-copy-answer')){const clone=b.closest('.chat-answer').cloneNode(true);clone.querySelectorAll('button').forEach(x=>x.remove());copyText(clone.textContent,b);}if(b.hasAttribute('data-copy-table')){const rows=[...b.parentNode.querySelector('table').rows].map(r=>[...r.cells].map(c=>excelCell(c.textContent)));copyText(rows.map(r=>r.join('\t')).join('\n'),b);}});
const priorTable=table;table=function(headers,rows){return priorTable(headers,rows).replace('<div class="table-wrap">','<div class="table-wrap"><button type="button" class="copy-table" data-copy-table>Afrita fyrir Excel</button>');};
// A result stays inspectable while the transcript and unfinished message remain in the same drawer.
document.addEventListener('click',e=>{if(e.target.closest('[data-chat-product]')){move(drawer,$('detail-dialog'));drawer.hidden=false;updateContext();}});
// Close only the foremost draft panel and restore focus without erasing work.
let cartOpener=null;const priorCartOpen=$('cart-open').onclick;$('cart-open').onclick=()=>{cartOpener=document.activeElement;priorCartOpen();$('cart-close').focus();};
$('cart-close').onclick=()=>{$('purchase-cart').hidden=true;cartOpener?.focus?.();};
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&drawer.hidden&&!$('purchase-cart').hidden){e.preventDefault();$('cart-close').click();}},true);
// Client-only draft insertion can be undone before it is saved.
const priorAddCart=addCart;addCart=function(ids){const before=cart.map(r=>({...r}));priorAddCart(ids);$('cart-status').textContent='Bætt í innkaupadrög. ';const undo=document.createElement('button');undo.type='button';undo.textContent='Afturkalla';undo.onclick=()=>{cart=before;renderCart();$('cart-status').textContent='Viðbót afturkölluð.';};$('cart-status').appendChild(undo);};
