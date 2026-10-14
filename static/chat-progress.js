'use strict';
let chatHistory=[];
const clock=v=>v?new Date(v).toLocaleTimeString('is-IS',{hour:'2-digit',minute:'2-digit',second:'2-digit'}):'Óþekkt';
const duration=seconds=>seconds<60?Math.ceil(seconds)+' sek.':seconds<3600?Math.ceil(seconds/60)+' mín.':(seconds/3600).toFixed(1)+' klst.';
function supplierTimer(runtime,phase,fullCount,fullRunning){
 if(phase==='blocked')return 'Aðgangi hafnað · ekkert í niðurhali';
 if(['error','not_connected','interrupted'].includes(phase))return 'Engin tímaáætlun · þarf yfirferð';
 if(phase==='queued')return 'Í bið · upphafstími óþekktur';
 if(phase!=='running')return 'Lota ekki í gangi';
 const elapsed=(Date.now()-Date.parse(runtime?.started_at))/1000;
 if(!Number.isFinite(elapsed))return 'Tími óþekktur';
 const prefix='Liðið í lotu: '+duration(Math.max(0,elapsed));
 const done=runtime.work_done,total=runtime.work_total,stamp=Date.parse(runtime.updated_at);
 if(!(done>=3&&total>=done))return prefix+' · mæli hraða; tími eftir óþekktur';
 if(Date.now()-stamp>60000)return prefix+' · bið lengist; áætlun óviss';
 const measured=(stamp-Date.parse(runtime.started_at))/1000;
 const per=measured/done,remaining=Math.max(0,(total-done)*per-(Date.now()-stamp)/1000);
 if(remaining===0&&done<total)return prefix+' · áætlun liðin; bíð eftir nýrri mælingu';
 let result=prefix+' · áætlað eftir í lotu: '+duration(remaining);
 if(fullRunning&&runtime.scan_total&&runtime.scan_done){
  const left=Math.max(0,runtime.scan_total-(fullCount?.scanned||0)-runtime.scan_done);
  result+=' · gróf áætlun fyrir birgi: '+duration(left*measured/runtime.scan_done)+' (án biðar eftir öðrum birgjum)';
 }
 return result+' · miðað við mældan meðalhraða';
}
function renderImportProgress(info){
 const box=$('import-progress-body');if(!box)return;
 const f=info.full,full=!!(f?.running||f?.finished_at&&f.finished_at>=(info.finished_at||info.started_at||''));
 const selected=full?(f.selected||[]):(info.selected||[]),completed=full?(f.completed||[]):(info.completed||[]),failed=full?Object.keys(f.failed||{}):selected.filter(k=>['error','blocked','not_connected'].includes(info.sources?.[k]?.status));
 const done=full?completed.length+failed.length:completed.length,total=selected.length;
 const names=Object.fromEntries((info.available_sources||[]).map(s=>[s.key,s.name]));
 const active=info.running?Object.entries(info.runtime||{}).filter(([,s])=>s.phase==='running').map(([k])=>names[k]||k):[];
 const stateLabel=info.phase==='error'?'Villa við keyrslu / vistun':info.phase==='interrupted'||full&&f?.status==='interrupted'?'Keyrsla rofnaði':info.stop_requested?'Stöðvun beðin — virkar lotur klárast fyrst':info.running?(info.phase==='saving'?'Vista gögn…':'Innlestri haldið áfram'):full&&f.status==='stopped'?'Heildarlestur stöðvaður':'Enginn innlestur í gangi';
 const start=full?f.started_at:info.started_at;
 const elapsed=start?Math.max(0,Math.round(((info.running?Date.now():Date.parse(full?f.finished_at:info.finished_at)||Date.now())-Date.parse(start))/60000)):0;
 const counts=full?(f.counts||{}):(info.runtime||{});
 const added=Object.values(counts).reduce((n,v)=>n+(v.new_products||0),0),changed=Object.values(counts).reduce((n,v)=>n+(v.changed_products||0),0);
 box.innerHTML=`<p><b>${esc(stateLabel)}</b>${active.length?' · Nú: '+active.map(esc).join(' og '):''}</p>${total?`<progress max="${total}" value="${Math.min(done,total)}" aria-label="Birgjar afgreiddir"></progress><p>${done} af ${total} birgjum afgreiddir · ${failed.length} með villu/aðgangshöfnun · ${elapsed} mínútur</p>`:'<p>Veldu birgja hér að ofan og ræstu uppfærslu eða heildarlestur.</p>'}<p>${full?'Þessi heildarumferð':'Núverandi / síðasta lota'}: <b>${added} nýjar</b> · <b>${changed} breyttar færslur</b>${full?' · '+(f.batches||0)+' lotur':''}.</p><p class="muted">${info.running?'Framvindan er sótt á 3 sekúndna fresti.':'Síðasta vistun: '+clock(info.finished_at)+'.'} Birgjaframvinda telur afgreidda birgja, ekki hlutfall allra vara á markaði. Breytingateljari telur breytingar milli lota; sama vara getur breyst aftur.</p>${info.error?`<p class="bom-issues">${esc(info.error)}</p>`:''}`;
 const phases={queued:'Í bið',running:'Í lestri',ok:'Lota lesin',partial:'Hluti lesinn',blocked:'Aðgangi hafnað',error:'Villa',not_connected:'Tenging ólokið'};
 $('import-source-progress').innerHTML=table(['BIRGIR','STAÐA / FRAMVINDA','FÆRSLUR / ÚRVAL','TÍMI','SÍÐASTA MERKI'],(info.available_sources||[]).map(({key,name})=>{
  const runtime=info.runtime?.[key],s=info.sources?.[key]||{},pending=full&&f.pending?.includes(key);
  let phase=info.running&&runtime?.phase==='running'?'running':info.running&&pending?'queued':runtime?.phase||s.status||'unknown';
  if(!info.running&&['running','queued'].includes(phase))phase='interrupted';
  const stage=phase==='running'?runtime.stage:pending?'Bíður næstu lotu':s.index_check||s.scope||'';
  const stamp=runtime?.updated_at||s.checked_at;
  const age=stamp?Math.max(0,Math.round((Date.now()-Date.parse(stamp))/1000)):null;
  return `<tr><td>${esc(name)}</td><td><span class="pill ${['blocked','error','not_connected','interrupted'].includes(phase)?'warn':''}">${esc(phases[phase]||({interrupted:'Rofnaði',unknown:'Ekki lesið'})[phase]||phase)}</span><small>${esc(stage)}</small>${s.error?`<small class="bom-issues">${esc(s.error)}</small>`:''}${s.errors?.length?`<small>${s.errors.length} skráðar síður með villu</small>`:''}</td><td>${runtime?.loaded??s.loaded??0} vörufærslur${s.expected||runtime?.expected?`<small>${s.expected||runtime.expected} viðmið úr birgjagögnum (vörur eða slóðir)</small>`:''}${s.index?`<small>Síðukort ${date(s.index.checked_at)}: ${s.index.total} slóðir · ${s.index.baseline?'fyrsta mæling; samanburður bíður næstu skoðunar':s.index.added+' nýjar · '+s.index.missing+' vantar frá síðustu skoðun'}</small><small>Horfin slóð staðfestir ekki að vara sé hætt. Eldri vöruspjöld varðveitt.</small>`:''}</td><td>${esc(supplierTimer(runtime,phase,f?.counts?.[key],full&&f?.running))}</td><td>${esc(clock(stamp))}${phase==='running'&&age>60?`<small>${age} sek. án nýs framvindumerkis; beiðni getur enn verið í gangi.</small>`:''}</td></tr>`;
 }).join(''));
}
$('chat-form').onsubmit=async e=>{
 e.preventDefault();if(aiBusy){$('chat-status').textContent='Önnur AI-beiðni er í gangi.';return;}
 const message=$('chat-message').value.trim();if(!message)return;
 aiBusy=true;$('chat-submit').disabled=true;$('chat-clear').disabled=true;$('chat-status').textContent='Njörður leitar í vörugrunni og metur tillögur…';
 try{
  await refresh();
  const result=await api('ai-chat',{message,history:chatHistory.slice(-8)});
  chatHistory.push({role:'user',text:message},{role:'assistant',text:result.answer});chatHistory=chatHistory.slice(-8);
  $('chat-messages').insertAdjacentHTML('beforeend',`<article class="chat-user"><b>Þú</b><p>${esc(message)}</p></article><article class="chat-answer"><b>Njörður</b><p>${esc(result.answer)}</p>${result.questions.length?'<h3>Til að þrengja valið</h3>'+aiList(result.questions):''}${result.products.length?`<p><button type="button" data-cart-suggestions="${result.products.map(p=>p.id).join(',')}">Útbúa drög úr þessum tillögum</button></p>`:''}<div class="cards">${result.products.map(p=>{const o=state.offers.find(o=>o.id===p.id);return o?`<div class="card"><h3>${esc(o.name)}</h3><p>${esc(o.supplier)} · ${esc(o.sku||'Vörunúmer vantar')}</p><p>${esc(p.reason)}</p>${priceCell(o)}<p class="muted">Verðathugun: ${date(o.observed_at)} · ${esc(o.availability||'Lagerstaða óstaðfest')}</p><p>${link(o)}</p><button type="button" data-detail="${o.id}">Skoða vöruspjald</button> <button type="button" data-cart-offer="${o.id}">Í innkaupadrög</button></div>`:'';}).join('')}</div><p class="muted">Leitað að: ${result.queries.map(esc).join(' · ')||'Beiðni þarf nánari lýsingu'}. ${result.matched} færslur pössuðu við leitina; AI fékk ${result.reviewed} til yfirferðar. Ekki tæmandi markaðsleit. Verð kemur úr vörugrunni.</p></article>`);
  $('chat-message').value='';$('chat-status').textContent='Svar tilbúið. Þú getur spurt áfram eða opnað vöruspjald.';
 }catch(err){$('chat-status').textContent=err.message;}
 finally{aiBusy=false;$('chat-submit').disabled=false;$('chat-clear').disabled=false;}
};
$('chat-clear').onclick=()=>{chatHistory=[];$('chat-messages').innerHTML='';$('chat-status').textContent='Nýtt spjall.';};
document.addEventListener('click',e=>{const b=e.target.closest('[data-chat-example]');if(b){$('chat-message').value=b.dataset.chatExample;$('chat-message').focus();}});
if(state.metadata?.sync)renderImportProgress(state.metadata.sync);
