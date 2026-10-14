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
function exact(line,o){if(o.source_kind==='quote')return false;return identify(line,o)&&!!(line.gtin&&o.gtin&&S.validGTIN(line.gtin)&&S.validGTIN(o.gtin)||line.brand&&line.manufacturer_part&&o.brand&&o.manufacturer_part||line.supplier&&line.sku);}
function cost(line,o,currency,today){
 let reason='';
 for(const [k,v] of Object.entries(line.specifications||{})){
  if(o.specifications?.[k]==null)return {eligible:false,reason:'Tæknilegan eiginleika vantar: '+({thickness_mm:'þykkt',width_mm:'breidd',length_mm:'lengd',strength_class:'styrkleikaflokkur',treatment:'meðhöndlun',material:'efni',standard:'staðall'}[k]||k)};
  if(norm(o.specifications[k])!==norm(v))return {eligible:false,reason:'Tæknilegur eiginleiki passar ekki: '+({thickness_mm:'þykkt',width_mm:'breidd',length_mm:'lengd',strength_class:'styrkleikaflokkur',treatment:'meðhöndlun',material:'efni',standard:'staðall'}[k]||k)};
 }

 if(o.currency!==currency)reason='Annar gjaldmiðill';
 else if(o.price==null||o.net_price==null)reason='Verð eða VSK vantar';
 else if(!Number.isFinite(o.pack_quantity)||o.pack_quantity<=0)reason='Pakkastærð óstaðfest';
 else if(o.unit!==line.unit)reason='Eining passar ekki';
 else if(!Number.isFinite(Date.parse(o.observed_at))||today-Date.parse(o.observed_at)>30*86400000)reason='Verðathugun vantar eða er eldri en 30 dagar';
 else if(o.terms?.valid_until&&o.terms.valid_until<new Date(today).toISOString().slice(0,10))reason='Gildistími verðs liðinn';
 else if(/ekki (?:a lager|til)/.test(norm(o.availability)))reason='Ekki til samkvæmt birgi';
 if(reason)return {eligible:false,reason};
 const required=Math.max(line.quantity,o.terms?.min_quantity??0);
 const packs=Math.max(1,Math.ceil(Number((required/o.pack_quantity).toFixed(10)))),total=packs*o.net_price*(1-(o.terms?.discount_percent??0)/100);
 if(!Number.isFinite(total)||total<0)return {eligible:false,reason:'Ógilt verð'};
 return {eligible:true,packs,total,supplied:packs*o.pack_quantity,excess:packs*o.pack_quantity-line.quantity,unit_price:o.net_price/o.pack_quantity};
}
function quote(rows,offers,selections={},currency='ISK',today=Date.now(),settings={}){
 const market=offers.filter(o=>o.source_kind!=='purchase'&&o.source_kind!=='reference');
 const lines=rows.map(line=>{
  const reference=offers.find(o=>o.id===line.reference_offer_id);
  const candidates=market.filter(o=>(!o.bom_id||(o.bom_id===line.bom_id&&o.bom_line_id===line.line_id))).filter(o=>identify(line,o)||(o.bom_id===line.bom_id&&o.bom_line_id===line.line_id)||(reference&&S.comparable(reference,o))||(selections[line.line_id]||[]).includes(o.id)).map(o=>{
   const approved=Object.hasOwn(selections,line.line_id)?(selections[line.line_id]||[]).includes(o.id):exact(line,o);
   return {offer:o,approved,exact:exact(line,o),...cost(line,o,currency,today)};
  });
  candidates.sort((a,b)=>Number(b.eligible)-Number(a.eligible)||(a.total??Infinity)-(b.total??Infinity)||a.offer.name.localeCompare(b.offer.name));
  const accepted=candidates.filter(c=>c.approved&&c.eligible&&(!Object.hasOwn(settings.choices||{},line.line_id)||settings.choices[line.line_id]===c.offer.id));
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
// Exhaustive supplier subsets for up to 12 suppliers; larger sets are explicitly bounded.
function scenarios(q,settings={}){
 const terms=settings.suppliers||{},choices=settings.choices||{},wanted=settings.wanted_date||'';
 const lines=q.lines.map(l=>({...l,available:l.candidates.filter(c=>c.approved&&c.eligible&&(!Object.hasOwn(choices,l.line_id)||c.offer.id===choices[l.line_id]))}));
 const allNames=[...new Set(lines.flatMap(l=>l.available.map(c=>c.offer.supplier)))];
 let subsets=[];const exhaustive=allNames.length<=12;
 if(exhaustive){for(let mask=1;mask<2**allNames.length;mask++)subsets.push(new Set(allNames.filter((_,i)=>mask&(1<<i))));}
 else{subsets=allNames.map(n=>new Set([n]));subsets.push(new Set(allNames));}
 const alternatives=[];
 for(const [subset,timely] of subsets.flatMap(s=>wanted?[[s,false],[s,true]]:[[s,false]])){
  const selected=lines.map(l=>l.available.filter(c=>subset.has(c.offer.supplier)&&(!timely||(c.offer.terms?.delivery_date||terms[c.offer.supplier]?.delivery_date)&&((c.offer.terms?.delivery_date||terms[c.offer.supplier]?.delivery_date)<=wanted))).map(c=>({...c,adjusted:c.total*(1-(terms[c.offer.supplier]?.discount_percent??0)/100)})).sort((a,b)=>Number(a.offer.terms?.min_quantity==null)-Number(b.offer.terms?.min_quantity==null)||a.adjusted-b.adjusted)[0]);
  const used=[...new Set(selected.filter(Boolean).map(c=>c.offer.supplier))],missing=[];
  const subtotal=selected.reduce((s,c)=>s+(c?.adjusted||0),0);let fees=0,confirmed=true,delivery=true;
  if(selected.some(c=>!c))missing.push('Óverðlagðar eða ósamþykktar línur');
  for(const name of used){const t=terms[name]||{};
   for(const field of ['shipping','other_fees']){if(t[field]==null||t.currency!==q.currency)missing.push(name+': '+(field==='shipping'?'flutningskostnað':'önnur gjöld')+' vantar');else fees+=t[field];}
   if(t.status!=='confirmed')confirmed=false;
  }
  for(const c of selected.filter(Boolean)){
   if(c.offer.terms?.min_quantity==null)missing.push(c.offer.supplier+': lágmarkspöntun óstaðfest');
   if(c.offer.terms?.status!=='confirmed')confirmed=false;
   if(wanted){const day=c.offer.terms?.delivery_date||terms[c.offer.supplier]?.delivery_date;if(!day||day>wanted)delivery=false;}
  }
  const complete=selected.length>0&&!missing.length;
  alternatives.push({selected,used,subtotal,fees,total:complete?subtotal+fees:null,complete,confirmed,delivery:!!wanted&&delivery&&selected.every(Boolean),missing:[...new Set(missing)],coverage:selected.filter(Boolean).length});
 }
 const rank=(a,b)=>Number(b.complete)-Number(a.complete)||(a.total??Infinity)-(b.total??Infinity)||b.coverage-a.coverage;
 alternatives.sort(rank);
 const complete=alternatives.filter(a=>a.complete);
 return {exhaustive,lowest:complete[0]||alternatives[0]||null,
  fewest:[...complete].sort((a,b)=>a.used.length-b.used.length||a.total-b.total)[0]||null,
  onTime:complete.filter(a=>a.delivery)[0]||null,alternatives,wanted};
}
function scenarioRows(q,settings={}){
 const result=scenarios(q,settings),rows=[['leid','tegund','lina','heiti','magn','eining','birgir','vorunumer','pakkningar','keypt_magn','kostnadur_an_vsk','gjaldmidill','stada','heimild','verkefni','afhendingarstadur','oskadagur']];
 const append=(key,values)=>rows.push([key,...values,settings.project||'',settings.location||'',settings.wanted_date||'']);
 for(const [key,label] of [['lowest','Lægsti reiknanlegi kostnaður'],['fewest','Fæstir birgjar'],['onTime','Afhending fyrir óskadag']]){
  const s=result[key];
  q.lines.forEach((l,i)=>{const c=s?.selected[i];append(label,['vara',l.line_id,l.name,l.quantity,l.unit,c?.offer.supplier||'',c?.offer.sku||'',c?.packs??'',c?.supplied??'',c?.adjusted??'',q.currency,c?'Yfirfara afhendingu og forsendur':'Ólokið / verð vantar',c?.offer.url||'']);});
  for(const name of s?.used||[]){const t=settings.suppliers?.[name]||{};for(const f of ['shipping','other_fees'])append(label,[f,'','','','',name,'','','',t.currency===q.currency?t[f]??'':'',q.currency,t[f]==null?'Óþekkt':t.status||'estimated',t.source||'']);}
  append(label,['heild','','','','','','','','',s?.total??'',q.currency,s?.complete?(s.confirmed?'Forsendur staðfestar':'Áætlað'):'Heild óþekkt',(s?.missing||['Fullnægjandi gögn vantar']).join('; ')]);
 }
 return rows;
}
const api={identify,cost,quote,scenarios,scenarioRows};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.BOMCore=api;
})(globalThis);
