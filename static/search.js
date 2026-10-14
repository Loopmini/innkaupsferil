/* Deterministic Icelandic product search; no remote service or AI credentials. */
(function(root){
  'use strict';
  function normalize(value){return String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/ð/g,'d').replace(/þ/g,'th').replace(/æ/g,'ae').replace(/(\d),(\d)/g,'$1.$2').replace(/×/g,'x');}
  const groups={steel:['stalbor','stalborar','jarnbor','jarnborar','malmbor','malmborar'],wood:['trebor','treborar','dilabor','dilaborar'],masonry:['steinbor','steinborar','murbor','murborar'],tile:['flisabor','flisaborar','glerbor','glerborar']};
  function attributes(o){
    if(o.attributes)return {...o.attributes,inferred:false};
    const name=normalize(o.name), text=name+' '+normalize(o.subcategory), words=text.split(/[^a-z0-9.]+/);
    let usage=Object.keys(groups).find(g=>groups[g].some(w=>words.includes(w)))||'';
    const drill=!!usage || words.some(w=>['bor','borar','borbit','borbitar','borasett','stalborasett','treborasett','steinborasett'].includes(w));
    if(!usage && drill){if(/\b(stal|jarn|hss|hsse|hssg|hssco)\b/.test(text))usage='steel';else if(/\btre\b/.test(text))usage='wood';}
    const isSet=/borasett|\bsett\b|threpabor/.test(name);
    // Only parse the first explicit size after a drill name. Ranges and sets need curated dimensions.
    let diameter=null;
    if(drill&&!isSet){const m=name.match(/(?:^|[^\d.])(\d+(?:\.\d+)?)\s*(?:x\s*\d+(?:\.\d+)?\s*)?mm\b/);if(m)diameter=Number(m[1]);}
    return {kind:drill?'drill':'',usage,diameter_mm:diameter,form:isSet?'set':'single',inferred:true};
  }
  function parse(query){
    let q=normalize(query);let usage='',kind='';
    for(const [group,aliases] of Object.entries(groups))for(const alias of aliases){const re=new RegExp('\\b'+alias+'\\b','g');if(re.test(q)){usage=group;kind='drill';q=q.replace(re,' ');}}
    if(/\b(bor|borar|borbit|borbitar)\b/.test(q)){kind='drill';q=q.replace(/\b(bor|borar|borbit|borbitar)\b/g,' ');}
    if(kind){for(const [pattern,val] of [[/\b(stal|jarn|malmur)\b/g,'steel'],[/\btre\b/g,'wood'],[/\b(steinn|mur)\b/g,'masonry']])if(pattern.test(q)){usage=val;q=q.replace(pattern,' ');}}
    let diameter=null;const size=q.match(/(?:^|\s)(\d+(?:\.\d+)?)\s*mm\b/);
    if(size){diameter=Number(size[1]);q=q.replace(size[0],' ');}
    return {kind,usage,diameter,terms:q.trim().split(/\s+/).filter(Boolean)};
  }
  function matches(o,query){
    const q=typeof query==='string'?parse(query):query,a=attributes(o);
    if(q.kind&&a.kind!==q.kind)return false;
    if(q.usage&&a.usage!==q.usage)return false;
    if(q.diameter!==null){
      if(q.kind){if(a.diameter_mm!==q.diameter && !(a.diameters_mm||[]).includes(q.diameter))return false;}
      else {const dimensions=[...normalize(o.name).matchAll(/(?:^|[^\d.])(\d+(?:\.\d+)?)\s*mm\b/g)].map(m=>Number(m[1]));if(!dimensions.includes(q.diameter)&&a.diameter_mm!==q.diameter)return false;}
    }
    const haystack=normalize([o.name,o.sku,o.brand,o.gtin,o.manufacturer_part,o.supplier,o.category,o.subcategory,o.description,...(o.supplier_categories||[]),...(o.search_tags||[]),...Object.values(o.specifications||{})].join(' '));
    return q.terms.every(t=>haystack.includes(t));
  }
  function same(a,b){
    const clean=v=>String(v||'').trim().toLowerCase(),digits=v=>clean(v).replace(/^0+/,'');
    if(a.gtin&&b.gtin)return digits(a.gtin)===digits(b.gtin);
    if(a.brand&&b.brand&&a.manufacturer_part&&b.manufacturer_part)return normalize(a.brand)===normalize(b.brand)&&clean(a.manufacturer_part)===clean(b.manufacturer_part);
    return !!(a.sku&&b.sku&&a.supplier&&b.supplier&&normalize(a.supplier)===normalize(b.supplier)&&clean(a.sku)===clean(b.sku));
  }
  function identity(o){
    if(o.gtin)return 'gtin:'+String(o.gtin).replace(/^0+/,'');
    if(o.brand&&o.manufacturer_part)return 'mpn:'+normalize(o.brand)+':'+String(o.manufacturer_part).trim().toLowerCase();
    if(o.supplier&&o.sku)return 'sku:'+normalize(o.supplier)+':'+String(o.sku).trim().toLowerCase();
    return 'record:'+o.id;
  }
  function grouped(offers){const map=new Map();for(const o of offers){const key=identity(o);if(!map.has(key))map.set(key,[]);map.get(key).push(o);}return [...map].map(([id,offers])=>({id,offers,representative:offers.find(o=>o.image_url)||offers[0]}));}
  function differences(a,b){
    const changes=[];for(const key of new Set([...Object.keys(a.specifications||{}),...Object.keys(b.specifications||{})])){
      const x=a.specifications?.[key],y=b.specifications?.[key];if(x==null||y==null)changes.push(key+': upplýsingar vantar');else if(normalize(x)!==normalize(y))changes.push(key+': '+x+' / '+y);
    }
    if(a.unit!==b.unit)changes.push('Ólíkar sölueiningar');if(a.pack_quantity!==b.pack_quantity)changes.push('Ólík pakkastærð');
    return changes;
  }
  function comparable(a,b){
    const c=a.classification?.id,d=b.classification?.id;
    if(a.id!==b.id&&c===d&&c?.startsWith('building.')&&!c.endsWith('.unspecified')&&!c.endsWith('.unknown')){
      const x=a.specifications||{},y=b.specifications||{};
      return ['thickness_mm','width_mm'].every(k=>x[k]!=null&&x[k]===y[k])&&Object.keys(x).every(k=>y[k]==null||x[k]===y[k]);
    }

    const x=attributes(a),y=attributes(b);
    return a.id!==b.id&&x.kind==='drill'&&y.kind==='drill'&&x.diameter_mm!==null&&x.diameter_mm===y.diameter_mm&&x.usage&&x.usage===y.usage&&x.form==='single'&&y.form==='single';
  }
  const api={normalize,attributes,parse,matches,comparable,same,identity,grouped,differences};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ProductSearch=api;
})(globalThis);
