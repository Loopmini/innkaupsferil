'use strict';
// Presentation only: reuse existing data, forms, detail builders and dialogs.
document.body.insertAdjacentHTML('afterbegin','<a class="skip-link" href="#main-content">Fara í efni</a>');
main.id='main-content';main.tabIndex=-1;
$('search').placeholder='Leita að vöru, vörunúmeri, birgja eða eiginleikum…';
const panelReturn=new Map();
for(const id of ['detail-dialog','supplier-dialog']){
 const d=$(id),bar=d.querySelector('.section-title'),close=bar.querySelector('[data-close]');
 const expand=document.createElement('button');expand.type='button';expand.textContent='Stækka';expand.setAttribute('aria-pressed','false');expand.setAttribute('aria-label','Stækka '+(id==='detail-dialog'?'vöruspjald':'birgjaspjald'));
 expand.onclick=()=>{const expanded=d.classList.toggle('expanded-panel');expand.textContent=expanded?'Minnka':'Stækka';expand.setAttribute('aria-pressed',String(expanded));};bar.insertBefore(expand,close);
 close.textContent='Loka ×';close.setAttribute('aria-label','Loka '+(id==='detail-dialog'?'vöruspjaldi':'birgjaspjaldi')+' og fara til baka');
 const title=bar.querySelector('h2');if(!title.id)title.id=id+'-title';d.setAttribute('aria-labelledby',title.id);
 d.addEventListener('close',()=>{const saved=panelReturn.get(id);if(saved){window.scrollTo(0,saved.y);if(saved.focus?.isConnected)saved.focus.focus();}panelReturn.delete(id);});
}
const themeDetail=detail;detail=function(id){if(!$('detail-dialog').open)panelReturn.set('detail-dialog',{focus:document.activeElement,y:window.scrollY});themeDetail(id);$('detail-dialog').querySelector('[data-close]').focus();};
const themeSupplier=editSupplier;editSupplier=function(s={}){if(!$('supplier-dialog').open)panelReturn.set('supplier-dialog',{focus:document.activeElement,y:window.scrollY});themeSupplier(s);$('supplier-dialog').querySelector('[data-close]').focus();};
// A family opens inline; keep its heading visible without resetting search or filters.
document.addEventListener('click',e=>{if(e.target.closest('[data-family]')){$('products').scrollIntoView({block:'start',behavior:'auto'});const heading=$('products').querySelector('h2,h3');if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true});}}});
document.addEventListener('keydown',e=>{if(e.key==='/'&&!e.ctrlKey&&!e.altKey&&!e.metaKey&&!document.querySelector('dialog[open]')&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)&&!document.activeElement?.isContentEditable){e.preventDefault();showWorkspace('catalogue');$('search').focus();}});

window.njordThemeReady=true;
