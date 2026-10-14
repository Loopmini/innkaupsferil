(function(root){
'use strict';
const S=typeof module!=='undefined'&&module.exports?require('./search.js'):root.ProductSearch;
const norm=S.normalize, canonical=v=>String(v||'').trim().toLowerCase();
const gtin=v=>String(v||'').replace(/^0+/,'');
function identify(line,o){
 if(line.supplier&&norm(line.supplier)!==norm(o.supplier))return false;
 if(line.gtin)return !!o.gtin&&gtin(line.gtin)===gtin(o.gtin);
 if(line.brand&&line.manufacturer_part)return norm(line.brand)===norm(o.brand)&&canonical(line.manufacturer_part)===canonical(o.manufacturer_part);
 if(line.sku)return canonical(line.sku)===canonical(o.sku);
 return S.matches(o,line.name);
}
function exact(line,o){return !!(line.gtin&&o.gtin||line.brand&&line.manufacturer_part&&o.brand&&o.manufacturer_part||line.supplier&&line.sku);}
function cost(line,o,currency,today){
 let reason='';
 if(o.currency!==currency)reason='Annar gjaldmiðill';
 else if(o.price==null||o.net_price==null)reason='Verð eða VSK vantar';
 else if(!Number.isFinite(o.pack_quantity)||o.pack_quantity<=0)reason='Pakkastærð óstaðfest';
 else if(o.unit!==line.unit)reason='Eining passar ekki';
 else if(!Number.isFinite(Date.parse(o.observed_at))||today-Date.parse(o.observed_at)>30*86400000)reason='Verðathugun vantar eða er eldri en 30 dagar';
 else if(/ekki (?:a lager|til)/.test(norm(o.availability)))reason='Ekki til samkvæmt birgi';
 if(reason)return {eligible:false,reason};
 const packs=Math.max(1,Math.ceil(Number((line.quantity/o.pack_quantity).toFixed(10)))),total=packs*o.net_price;
 if(!Number.isFinite(total)||total<0)return {eligible:false,reason:'Ógilt verð'};
 return {eligible:true,packs,total,supplied:packs*o.pack_quantity,excess:packs*o.pack_quantity-line.quantity,unit_price:o.net_price/o.pack_quantity};
}
function quote(rows,offers,selections={},currency='ISK',today=Date.now()){
 const market=offers.filter(o=>o.source_kind!=='purchase'&&o.source_kind!=='reference');
 const lines=rows.map(line=>{
  const candidates=market.filter(o=>identify(line,o)).map(o=>{
   const approved=Object.hasOwn(selections,line.line_id)?(selections[line.line_id]||[]).includes(o.id):exact(line,o);
   return {offer:o,approved,exact:exact(line,o),...cost(line,o,currency,today)};
  });
  candidates.sort((a,b)=>Number(b.eligible)-Number(a.eligible)||(a.total??Infinity)-(b.total??Infinity)||a.offer.name.localeCompare(b.offer.name));
  const accepted=candidates.filter(c=>c.approved&&c.eligible);
  return {...line,candidates,best:accepted[0]||null,suggestion:candidates.find(c=>c.eligible)||null};
 });
 const chosen=lines.filter(l=>l.best),subtotal=chosen.reduce((sum,l)=>sum+l.best.total,0);
 const names=[...new Set(lines.flatMap(l=>l.candidates.map(c=>c.offer.supplier)))];
 const suppliers=names.map(supplier=>{
  const priced=lines.map(l=>l.candidates.filter(c=>c.offer.supplier===supplier&&c.approved&&c.eligible).sort((a,b)=>a.total-b.total)[0]);
  return {supplier,coverage:priced.filter(Boolean).length,total:priced.reduce((s,c)=>s+(c?.total||0),0),complete:priced.every(Boolean)};
 }).sort((a,b)=>Number(b.complete)-Number(a.complete)||b.coverage-a.coverage||a.total-b.total);
 const split={};for(const l of chosen){const name=l.best.offer.supplier;split[name]=(split[name]||0)+l.best.total;}
 return {lines,currency,subtotal,covered:chosen.length,complete:chosen.length===lines.length&&lines.length>0,split,suppliers};
}
const api={identify,cost,quote};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.BOMCore=api;
})(globalThis);
