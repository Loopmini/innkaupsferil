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
    const haystack=normalize([o.name,o.sku,o.brand,o.gtin,o.manufacturer_part,o.supplier,o.category,o.subcategory].join(' '));
    return q.terms.every(t=>haystack.includes(t));
  }
  function comparable(a,b){
    const x=attributes(a),y=attributes(b);
    return a.id!==b.id&&x.kind==='drill'&&y.kind==='drill'&&x.diameter_mm!==null&&x.diameter_mm===y.diameter_mm&&x.usage&&x.usage===y.usage&&x.form==='single'&&y.form==='single';
  }
  const api={normalize,attributes,parse,matches,comparable};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ProductSearch=api;
})(globalThis);
