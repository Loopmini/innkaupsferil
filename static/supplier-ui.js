'use strict';
let supplierProfiles=[],supplierEditing=null,supplierLoading=false;
const supplierFields={name:'Nafn birgja',website:'Vefslóð',registration_number:'Kennitala / fyrirtækjanúmer',address:'Heimilisfang',postal_code:'Póstnúmer',city:'Bær / borg',country:'Land',phone:'Sími',email:'Netfang',notes:'Athugasemdir'};
$('supplier-fields').innerHTML=Object.entries(supplierFields).map(([k,label])=>`<label>${label}${k==='notes'?`<textarea id="supplier-${k}" maxlength="3000"></textarea>`:`<input id="supplier-${k}" ${k==='name'?'required':''} type="${k==='email'?'email':'text'}" maxlength="${k==='website'?2000:k==='email'?254:300}">`}</label>`).join('');
function supplierDiscovery(d){
 if(!d)return '<p>Vefur hefur ekki verið kannaður. Vistaðu slóð og veldu „Kanna vöruskrá“.</p>';
 const labels={possible:'Möguleg vörutenging fannst',unknown:'Engin staðfest vörutenging fannst',blocked:'Aðgangi hafnað',error:'Könnun mistókst'};
 return `<h3>${esc(labels[d.status]||'Niðurstaða könnunar')}</h3><p>${esc(d.note||'')}</p><p class="muted">Athugað ${esc(new Date(d.checked_at).toLocaleString('is-IS'))}. Þetta virkjar ekki sjálfvirkan innlestur.</p>`+(d.findings||[]).map(f=>`<p><b>${esc(f.kind==='api'?'Vöruviðmót':f.kind==='sitemap'?'Síðukort':f.kind==='file'?'Skjalatengill':'Vefur')}</b> · ${esc(f.detail)}<br><a href="${esc(f.url)}" target="_blank" rel="noopener noreferrer">Skoða heimild ↗</a></p>`).join('');
}
async function loadSupplierProfiles(){
 if(supplierLoading)return;supplierLoading=true;
 try{supplierProfiles=await api('supplier-profiles');$('supplier-cards').innerHTML=supplierProfiles.map((s,i)=>{
  const canonical=s.catalogue_name||s.name,rows=state.offers.filter(o=>o.supplier===canonical),c=state.metadata?.connections?.suppliers?.find(x=>x.supplier===canonical);
  return `<article class="card"><h3>${esc(s.name)}</h3><p>${[s.address,s.postal_code,s.city,s.country].filter(Boolean).map(esc).join(' · ')||'Heimilisfang óskráð'}</p><p>${s.registration_number?'Kt. '+esc(s.registration_number)+' · ':''}${esc(s.phone||'Sími óskráður')}<br>${esc(s.email||'Netfang óskráð')}</p><p>${rows.length} vörufærslur · ${(s.contacts||[]).length} tengiliðir</p>${s.website?`<p><a href="${esc(s.website)}" target="_blank" rel="noopener noreferrer">Vefur birgis ↗</a></p>`:''}${c?`<p class="muted">${esc(c.finding)}</p>`:''}<button data-edit-supplier="${i}">Upplýsingar og tengiliðir</button></article>`;
 }).join('');if(typeof supplierRows==='function')supplierRows();$('supplier-list-status').textContent='';}catch(e){$('supplier-list-status').textContent='Ekki tókst að lesa birgjaskrá: '+e.message;}finally{supplierLoading=false;}
}
function addSupplierContact(c={}){
 const row=document.createElement('fieldset');row.className='supplier-contact';
 row.innerHTML='<legend>Tengiliður</legend>'+Object.entries({name:'Nafn',role:'Starfsheiti / hlutverk',phone:'Sími',email:'Netfang',notes:'Athugasemdir'}).map(([key,label])=>`<label>${label}<input data-contact-field="${key}" value="${esc(c[key]||'')}" ${key==='name'?'required':''} type="${key==='email'?'email':'text'}" maxlength="${key==='notes'?1000:254}"></label>`).join('')+'<button type="button" data-remove-contact>Fjarlægja tengilið úr eyðublaði</button>';
 $('supplier-contacts').appendChild(row);
}
function editSupplier(s={}){
 supplierEditing=s;$('supplier-dialog-title').textContent=s.name?'Birgir: '+s.name:'Bæta við birgja';
 for(const key of Object.keys(supplierFields))$('supplier-'+key).value=s[key]||'';
 $('supplier-contacts').innerHTML='';(s.contacts||[]).forEach(addSupplierContact);
 $('supplier-save-status').textContent='';$('supplier-probe').disabled=!s.id||!s.website;
 $('supplier-discovery').innerHTML=supplierDiscovery(s.discovery);$('supplier-dialog').showModal();
}
$('supplier-new').onclick=()=>editSupplier();
$('supplier-contact-add').onclick=()=>addSupplierContact();
$('supplier-reload').onclick=loadSupplierProfiles;
document.addEventListener('click',e=>{
 const edit=e.target.closest('[data-edit-supplier]');if(edit)editSupplier(supplierProfiles[Number(edit.dataset.editSupplier)]);
 const remove=e.target.closest('[data-remove-contact]');if(remove)remove.closest('fieldset').remove();
});
$('supplier-form').onsubmit=async e=>{
 e.preventDefault();$('supplier-save').disabled=true;
 try{
  const supplier={id:supplierEditing?.id,catalogue_name:supplierEditing?.catalogue_name||''};
  for(const key of Object.keys(supplierFields))supplier[key]=$('supplier-'+key).value;
  supplier.contacts=[...document.querySelectorAll('#supplier-contacts fieldset')].map(f=>Object.fromEntries([...f.querySelectorAll('[data-contact-field]')].map(x=>[x.dataset.contactField,x.value])));
  supplierEditing=await api('supplier-save',{supplier});$('supplier-probe').disabled=!supplierEditing.website;
  $('supplier-website').value=supplierEditing.website;$('supplier-discovery').innerHTML=supplierDiscovery(supplierEditing.discovery);
  $('supplier-save-status').textContent='Birgi og tengiliðum hefur verið vistað.';await loadSupplierProfiles();
 }catch(err){$('supplier-save-status').textContent=err.message;}finally{$('supplier-save').disabled=false;}
};
$('supplier-website').oninput=()=>{$('supplier-probe').disabled=true;$('supplier-save-status').textContent='Vistaðu breytta slóð áður en hún er könnuð.';};
$('supplier-probe').onclick=async()=>{
 if(!supplierEditing?.id)return;
 const id=supplierEditing.id;$('supplier-probe').disabled=true;$('supplier-save').disabled=true;
 $('supplier-discovery').textContent='Kanna aðgangsreglur, vef og mögulegar vöruskrár. Þetta getur tekið um eina mínútu; engar vörur eru fluttar inn.';
 try{const result=await api('supplier-probe',{id});if(supplierEditing?.id===id){supplierEditing.discovery=result;$('supplier-discovery').innerHTML=supplierDiscovery(result);}await loadSupplierProfiles();}
 catch(e){if(supplierEditing?.id===id)$('supplier-discovery').textContent=e.message;}
 finally{$('supplier-save').disabled=false;$('supplier-probe').disabled=!supplierEditing?.id||!supplierEditing?.website;}
};
loadSupplierProfiles();
