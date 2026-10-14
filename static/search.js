/* Deterministic Icelandic product search; no remote service or AI credentials. */
(function(root){
  'use strict';
  function normalize(value){return String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/ð/g,'d').replace(/þ/g,'th').replace(/æ/g,'ae').replace(/(\d),(\d)/g,'$1.$2').replace(/×/g,'x').replace(/klaufham(?:ar|rar|ri|ra|rum)\b/g,'klaufhamar');}
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
    if(typeof query==='string'&&[o.sku,o.manufacturer_part,o.gtin].some(v=>v&&String(v).trim().toLowerCase()===query.trim().toLowerCase()))return true;
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
  function validGTIN(value){
    const s=String(value||'').trim();if(/^0+$/.test(s)||!/^(?:\d{8}|\d{12}|\d{13}|\d{14})$/.test(s))return false;
    let sum=0;for(let i=s.length-2,w=3;i>=0;i--,w=4-w)sum+=Number(s[i])*w;
    return (10-sum%10)%10===Number(s.at(-1));
  }
  function identity(o){
    if(o.product_enrichment?.keep_separate)return 'separate:'+o.id;
    if(validGTIN(o.gtin))return 'gtin:'+String(o.gtin).trim().replace(/^0+/,'');
    if(o.brand&&o.manufacturer_part)return 'mpn:'+normalize(o.brand).trim()+':'+String(o.manufacturer_part).trim().toLowerCase();
    if(o.supplier&&o.sku)return 'sku:'+normalize(o.supplier).trim()+':'+String(o.sku).trim().toLowerCase();
    return 'record:'+o.id;
  }
  function identityConflicts(a,b){
    const issues=[],x=a.specifications||{},y=b.specifications||{};
    for(const k of Object.keys(x))if(y[k]!=null&&normalize(x[k])!==normalize(y[k]))issues.push('Ósamræmi í '+k);
    if(a.gtin&&b.gtin&&String(a.gtin).replace(/^0+/,'')!==String(b.gtin).replace(/^0+/,''))issues.push('Ólík GTIN/EAN');
    if(a.brand&&b.brand&&normalize(a.brand)!==normalize(b.brand))issues.push('Ólíkir framleiðendur');
    if(a.manufacturer_part&&b.manufacturer_part&&normalize(a.manufacturer_part)!==normalize(b.manufacturer_part))issues.push('Ólík framleiðandanúmer');
    const ac=a.classification,bc=b.classification;
    if(ac?.id&&bc?.id&&!ac.needs_review&&!bc.needs_review&&ac.id!==bc.id)issues.push('Ólíkar vörutegundir');
    const hints=o=>[...normalize(o.name).matchAll(/(?:^|[^\d.])(\d+(?:\.\d+)?)\s*(mm|cm|oz|kg|gr|g|v|ah|w|kw|lm|lumens|lumen|k)\b/g)].map(m=>m[1]+m[2]).sort().join('|');
    if(hints(a)&&hints(b)&&hints(a)!==hints(b))issues.push('Ólík mál / útfærslumerki í heitum');
    return issues;
  }
  function same(a,b){
    if(a.id===b.id&&a.id!=null)return true;
    return identity(a)===identity(b)&&!identity(a).startsWith('record:')&&!identity(a).startsWith('separate:')&&!identityConflicts(a,b).length;
  }
  function grouped(offers){
    const buckets=new Map();
    for(const o of offers){const key=identity(o);if(!buckets.has(key))buckets.set(key,[]);const groups=buckets.get(key);let g=groups.find(g=>g.every(x=>same(x,o)));if(!g){g=[];groups.push(g);}g.push(o);}
    return [...buckets].flatMap(([key,groups])=>groups.map(offers=>({id:key+':'+Math.min(...offers.map(o=>o.id)),offers,representative:offers.find(o=>o.image_url)||offers[0]})));
  }
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
  const api={normalize,attributes,parse,matches,comparable,same,identity,grouped,differences,identityConflicts,validGTIN};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ProductSearch=api;
})(globalThis);
