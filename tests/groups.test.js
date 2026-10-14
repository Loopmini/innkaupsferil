const assert=require('node:assert/strict'),g=require('../static/groups.js');
const cases=[
 [{name:'2 tommur',supplier_categories:['Glussa','Hraðtengi'],description:'VNR: 123 Lykill fyrir ROFLEX tengi.'},'Handverkfæri og mælitæki'],
 [{name:'1 tomma',supplier_categories:['Hraðtengi'],description:'Þéttisett fyrir ROFLEX tengi.'},'Þéttingar og pakkningar'],
 [{name:'MAKITA Skrúfvél 18V',category:'18V'},'Vélar og rafmagnsverkfæri'],
 [{name:'MAKITA Borvél í tösku með rafhlöðu og hleðslutæki'},'Vélar og rafmagnsverkfæri'],
 [{name:'Skrúfjárn Torx T20'},'Handverkfæri og mælitæki'],
 [{name:'Skrúfbiti T15 50mm'},'Handverkfæri og mælitæki'],
 [{name:'HECO tréskrúfa 4,5x50'},'Festingar og skrúfur'],
 [{name:'Fræsitönn Bein 8mm'},'Skurðar- og slípivörur'],
 [{name:'MAKITA Steinbor SDS+ 6mm',category:'18V'},'Borar og snittvörur'],
 [{name:'BOR SPAÐABOR 17MM',category:'rafmagns-hledsluverkfaeri-aukahlutir'},'Borar og snittvörur'],
 [{name:'Loftslanga á hjóli',category:'Aukahlutir f. loftpressur'},'Slöngur, barkar og tengi'],
 [{name:'Brunndæla 750XC',category:'Vélar og tæki'},'Drifbúnaður, dælur og legur'],
 [{name:'1 1/2"',description:'VNR: 35-30-100024 Hraðtengi m/ró og BSP gengjum. Þrýstiþol 300 bör.'},'Slöngur, barkar og tengi'],
 [{name:'1 1/2"',supplier_categories:['Glussa','Hraðtengi','ROFLEX']},'Slöngur, barkar og tengi'],
 [{name:'Tegund XYZ',description:'Hreinsiefni fyrir vélar og verkfæri. Inniheldur ekki olíu.'},'Efnavörur og smurefni'],
 [{name:'ABC',description:'Vara til margra nota. Hentar fyrir dælur, slöngur og borvélar.'},'Annað og óflokkað'],
 [{name:'Skrúfvél',manual_category:'Minn flokkur',description:'Loki'},'Minn flokkur'],
 [{name:'Óþekkt vara',category:'Aukahlutir'},'Annað og óflokkað'],
 [{name:'Ryksugupokar 5 stk'},'Rekstrarvörur og hreinlæti'],
 [{name:'Baðkar MEZZO'},'Hreinlætistæki og baðbúnaður'],
 [{name:'Hjólsög 18V'},'Vélar og rafmagnsverkfæri'],
 [{name:'Vara X',category:'Peysur, Skyrtur og Bolir'},'Vinnufatnaður og öryggi']
];
for(const [o,want] of cases)assert.equal(g.classify(o),want,JSON.stringify(o));
assert.equal(g.explain({name:'X',description:'Hraðtengi úr stáli.'}).source,'Lýsing birgis');
console.log('Classification passed: '+cases.length+' cases; manual priority, supplier evidence, descriptions and ambiguous products.');
