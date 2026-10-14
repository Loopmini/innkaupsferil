/* Views over existing taxonomy leaves and source records; no destructive merging. */
(function(root){
'use strict';
const S=typeof module!=='undefined'&&module.exports?require('./search.js'):root.ProductSearch;
function families(offers){
 const map=new Map();
 for(const o of offers){const id=o.classification?.id||'other.review.unknown';if(!map.has(id))map.set(id,[]);map.get(id).push(o);}
 return [...map].map(([id,rows])=>({id,path:rows[0].classification?.path||['Óflokkað'],review:rows.some(o=>o.classification?.needs_review),offers:rows,products:S.grouped(rows),suppliers:[...new Set(rows.map(o=>o.supplier))]}));
}
function priceScope(o){return o.price_scope==='contract'?'Samningsverð First Water':o.source_kind==='market'?'Almennt vefverð':o.source_kind==='quote'?'Tilboð á BOM':o.source_kind==='purchase'?'Fyrri innkaup':'Innlesið verð · samningsstaða óskráð';}
function priceGroups(offers,today=Date.now()){
 const buckets=new Map();
 for(const o of offers){
  if(!['market','import','quote'].includes(o.source_kind)||o.price==null||!Number.isFinite(o.net_price)||o.net_price<0||!Number.isFinite(o.pack_quantity)||o.pack_quantity<=0||!o.unit||!o.currency||!Number.isFinite(Date.parse(o.observed_at))||today-Date.parse(o.observed_at)>30*86400000||o.terms?.valid_until&&o.terms.valid_until<new Date(today).toISOString().slice(0,10))continue;
  const key=[priceScope(o),o.currency,o.unit].join('|');if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push({offer:o,unitPrice:o.net_price/o.pack_quantity});
 }
 return [...buckets].map(([key,items])=>({key,scope:priceScope(items[0].offer),currency:items[0].offer.currency,unit:items[0].offer.unit,min:Math.min(...items.map(x=>x.unitPrice)),max:Math.max(...items.map(x=>x.unitPrice)),items}));
}
function audit(offers){
 const fs=families(offers),groups=S.grouped(offers),review=[],keys=new Map(),names=new Map();
 const add=(o,reason)=>review.push({id:o.id,name:o.name,supplier:o.supplier,sku:o.sku,reason});
 for(const o of offers){
  if(o.classification?.needs_review)add(o,'Vörufjölskylda óviss: '+o.classification.evidence);
  if(o.gtin&&!S.validGTIN(o.gtin))add(o,'GTIN/EAN stenst ekki lengdar- eða vartölupróf; ekki notað sem sameiginlegt auðkenni');
  if(o.specification_conflicts?.length)add(o,'Árekstur í tæknigögnum: '+o.specification_conflicts.join(', '));
  const key=S.identity(o);if(!keys.has(key))keys.set(key,[]);keys.get(key).push(o);
  const name=S.normalize(o.name).trim();if(!names.has(name))names.set(name,[]);names.get(name).push(o);
 }
 for(const rows of keys.values())if(rows.length>1&&S.grouped(rows).length>1)for(const o of rows)add(o,'Sama auðkenni en ósamræmi í útfærslu eða tæknigögnum; færslur aðskildar');
 for(const rows of names.values())if(rows.length>1&&new Set(rows.map(S.identity)).size>1)for(const o of rows)add(o,'Sama staðlaða heiti en sameiginlegt auðkenni vantar eða er ólíkt; ekki sameinað');
 const supplierCounts=[...new Set(offers.map(o=>o.supplier))].map(name=>{const rows=offers.filter(o=>o.supplier===name);return {supplier:name,records:rows.length,products:S.grouped(rows).length,families:families(rows).filter(f=>!f.review).length};});
 return {records:offers.length,products:groups.length,families:fs.filter(f=>!f.review).length,reviewBuckets:fs.filter(f=>f.review).length,combinedRecords:offers.length-groups.length,reviewRecords:new Set(review.map(r=>r.id)).size,review,supplierCounts};
}
const api={families,priceGroups,priceScope,audit};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ProductFamilies=api;
})(globalThis);
