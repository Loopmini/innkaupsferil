(function(root){
'use strict';
const S=typeof module!=='undefined'&&module.exports?require('./search.js'):root.ProductSearch;
const UNKNOWN='Annað og óflokkað';
// Match product nouns, not arbitrary substrings (e.g. skrúfvél is not skrúfa).
const rules=[
 ['Leikföng og módel',/leikfang|\bmodel\b|fotstign.*traktor/],
 ['Hreinlætistæki og baðbúnaður',/badkar|badker|blondunartaek|handlaug|salerni|sturt|salernissk|vaskur|vaskar/],
 ['Stigar og vinnupallar',/\bstig[ai]r?\b|troppur|vinnupall|vinnubord|vinnubukk/],
 ['Borar og snittvörur',/\b(?:stal|tre|jarn|malm|stein|mur|flisa|gler|demants|spada|dosa|threpa)?bor(?:ar|asett)?\b|snittbakk|snittapp|snittapi|bora- og bitasett/],
 ['Skurðar- og slípivörur',/sagarblad|sagarblod|multiblad|multiblod|skurdarsk|demantsblad|slipisk|slipibel|slipibond|slipipud|fraesit(?:enn|onn)|sandpapp|sds.*fleyg|bonsvamp|bonpud|ullarpud|slipiboll/],
 ['Handverkfæri og mælitæki',/skrufjarn|skrufbit|skrufstykk|bitahald|bita hald|bitasett|bita sett|\b(?:tong|tangir|hamar|hamrar|lykill|lyklasett|hnifur|hnifar|malband|hallamal|thvinga|thvingur|toppar|blyantur|tuss)\b|maelit|maelib|maelar|laser|lyklar|skiptilykl|hex bit|handverkfaer|\bhefill\b|\bsog\b|\bsagir\b/],
 ['Vélar og rafmagnsverkfæri',/butsog|butsagir|bordsog|bordsagir|ristisog|flisasog|hjolsog|hjolsagir|sledasog|sledasagir|steinsog|steinsagir|stingsog|stingsagir|bandsog|bandsagir|sverd[s]?og|sverdsagir|borvel|skrufvel|slipirokk|slipivel|soguvel|rafmagnsverkfaer|rafmagnsverkfaeri|fraesari|fraesarar|pussari|pussarar|heftibyss|pinnabyss|naglabyss|kittisgrind|\bnagari\b|jardvegsthjopp|jarnabindingavel|skurdarvel|thykktarhefil|kaffivel|vifta|viftur|mos[s]?unarvel|\b(?:vel|velar)\b/],
 ['Suðubúnaður og suðuvörur',/suduv|sudub|suduth|sudutra|sudupist|sudubrenn|gasiq|\blogsu/],
 ['Vinnufatnaður og öryggi',/hansk|vettling|hjalm|heyrnar|oryggis|vinnufat|vinnusk|stigvel|jakk|buxur|samfest|kuldagall|fatnad|hufur|hufa|\bbelti\b|bjorgunar|fallvarn|peys|skyrt|\bbolir\b|ulpur|ulp[a-u]|andlits|ondunar|hlifd|augnhlif|su[ðd]uskerm/],
 ['Þéttingar og pakkningar',/thettisett|thettihring|pakkdos|o-hring|\boring\b|flatpakkning/],
 ['Slöngur, barkar og tengi',/slanga|slong|barki|barkar|fitting|hradtengi|samtengi|tengistykki|nippl|hosur|slonguhjol|glussatengi/],
 ['Lokar og lagnaefni',/\bloki\b|\blokar\b|kululok|pipulagn|lagnaefni|\bror\b|\bflans|gufugildr/],
 ['Drifbúnaður, dælur og legur',/\blega\b|\blegur\b|kulegur|drifbun|dael[a-u]|thrystijafn|rakaglas|motor|tjakk|loftpress|girkass|drifreim/],
 ['Efnavörur og smurefni',/\b(?:lim|kitti|fuga|thettiefni|hreinsir|hreinsiefni|olia|oliur|smur|smurefni|smurfeiti|feiti|glussi|epoxy|silicon|silikon|leysir)\b|rydhreinsi|rydloys/],
 ['Festingar og skrúfur',/\b(?:tre|stein|gifs|plat|spax)?skruf(?:a|ur|um|na|urnar)?\b|skrufusett|bolti|boltar|\bskinn(?:a|ur)\b|snitttein|hnod|hosuklemm|splitti|\bpinnar\b|\bhefti\b|reknagl|naglar|kambsaum|festing/],
 ['Rafbúnaður og lýsing',/rafbun|rafmagn|kapall|kaplar|streng|tofluvir|tengill|tenglar|\brof[ai]r?\b|lysing|ljos|rafhlod|fjoltengi|hledsl|rafstod|rafg\.stod/],
 ['Geymsla og skipulag',/taska|toskur|verkfaerakass|verkfaeratosk|geymslu|skuffusk|bakpoki|verkfaerahulst/],
 ['Rekstrarvörur og hreinlæti',/hreinlaet|hreinsivor|pappir|thurrk|sapu|ruslaf|ruslap|plastpok|plast pok|umbud|skammtar|bursti|sopur|fotur|ryksug|hreinsibun/],
 ['Hífing, keðjur og veiðarfæri',/stroff|lyftibun|hif|kedj|\btalia\b|kadal|veidarf|handfaer|bauj|\btog\b/],
 ['Véla- og kerruhlutir',/kerruhlut|beisl|yfirtengi|drifsk(?:aft|oft)|beltagrof|vinnuvel|landbuna|traktor|drykkjarker|basmott/],
 ['Málning og yfirborð',/malning|pensl|malningar.*kef|murbun|murvor/],
 ['Garður og útisvæði',/skofl|hrifur|greinaklipp|fjolorf|slattu|snyrt|gardverkfaer|multi-star|girding|staurar|\bhlid\b|udakut|udarar/],
 ['Byggingarefni',/timbur|steypu|einangr|byggingarefni|gips/]
];
const find=text=>rules.find(([,r])=>r.test(S.normalize(text)));
function explain(o){
 if(o.manual_category)return {category:o.manual_category,source:'Handvirkt val',evidence:o.manual_category};
 // A precise product noun beats a broad parent category and included accessories.
 const name=String(o.name||'').split(/\s+(?:fyrir|f\/|f\.|með|m\/|í tösku)\s*/i)[0];
 const powered=/\b(?:18v|12v|40v|\d{3,4}w)\b/.test(S.normalize(o.name));
 if(powered&&/\bsog\b|hraera|klipp|skaeri|hefill/.test(S.normalize(name)))return {category:'Vélar og rafmagnsverkfæri',source:'Vöruheiti',evidence:name};
 let hit=find(name);
 if(hit&&!/^(festing|aukahlut|fylgihlut|hlif)\b/.test(S.normalize(name)))return {category:hit[0],source:'Vöruheiti',evidence:name};
 // Descriptions may mention many unrelated applications. Use the introductory product description,
 // and leave conflicting evidence unclassified rather than choosing the first keyword anywhere.
 const lead=String(o.description||'').replace(/^VNR:\s*\S+\s*/i,'').split(/\.(?:\s|$)|[\n;]/)[0].slice(0,350).split(/\s+(?:fyrir|f\/|f\.|til notkunar)\s*/i)[0];
 const hits=rules.filter(([,r])=>r.test(S.normalize(lead)));
 if(hits.length===1)return {category:hits[0][0],source:'Lýsing birgis',evidence:lead};
 const cats=[o.category,...(o.supplier_categories||[]),...String(o.subcategory||'').split(' / ')].filter(Boolean);
 const unique=[...new Set(cats)].filter(c=>!/^\s*(aukahlutir|fylgihlutir|fylgi og varahlutir|ym[s]?ar vorur|sett|vorur|velar og taeki|\d+v|tilbod)\s*$/i.test(S.normalize(c)));
 for(const c of unique){
  if(S.normalize(c)==='onnur verkfaeri')return {category:'Handverkfæri og mælitæki',source:'Birgjaflokkur',evidence:c};
  const match=find(c);if(match)return {category:match[0],source:'Birgjaflokkur',evidence:c};
 }
 if(hit)return {category:hit[0],source:'Vöruheiti',evidence:name};
 return {category:UNKNOWN,source:hits.length>1?'Óviss lýsing':'Óflokkað',evidence:hits.length>1?'Lýsing vísar í fleiri en einn vöruflokk.':'Nægilega skýrar upplýsingar vantar.'};
}
function classify(o){return explain(o).category;}
const api={classify,explain,categories:rules.map(r=>r[0])};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ProductGroups=api;
})(globalThis);
