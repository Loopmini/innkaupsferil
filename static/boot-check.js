'use strict';
// Independent of app.js: expose partial upgrades instead of silently showing an old UI.
window.addEventListener('load',async()=>{
 const note=document.createElement('p');note.id='installation-status';note.setAttribute('role','status');document.querySelector('aside').appendChild(note);
 const issue=message=>{note.setAttribute('role','alert');note.className='installation-error';note.textContent=message;};
 try{
  const response=await fetch('/api/version',{cache:'no-store'});if(!response.ok)throw Error('Eldri bakendi svarar; lokaðu eldri keyrslu og ræstu úr uppfærðu möppunni.');
  const v=await response.json();
  const theme=getComputedStyle(document.documentElement).getPropertyValue('--njord-theme-build').trim();
  if(v.version!=='0.18'||theme!=='compact-018'||!window.njordThemeReady||!window.njordEvidenceReady){issue('Ófullkomin uppfærsla: bakendi '+v.version+', útlit '+(theme||'vantar')+'. Afritaðu allan uppfærslupakkann og endurræstu.');return;}
  note.textContent='v0.18 · nýtt viðmót virkt';note.title='Keyrir úr: '+v.folder;
  const details=document.createElement('details');details.innerHTML='<summary>Uppsetning og útgáfa</summary>';const text=document.createElement('p');text.textContent='Njörður v'+v.version+' · Forrit: '+v.folder+' · Gögn: '+v.database;details.appendChild(text);document.getElementById('admin-settings')?.appendChild(details);
 }catch(err){issue('Ekki tókst að staðfesta útgáfu: '+err.message);}
});
