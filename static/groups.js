(function(root){
'use strict';
const S=typeof module!=='undefined'&&module.exports?require('./search.js'):root.ProductSearch;
const rules=[
 ['Skurðar- og slípivörur',/sagarblad|sagarblod|multiblad|multiblod|skurdarski|slipiski|slipibel|slipibond|slipipud|fresitenn|sandpapp|sds.*fleyg/],
 ['Véla- og kerruhlutir',/kerruhlut|beisl|yfirtengi|drifsk[aö]ft|drifsk[aö]ft|beltagrof|vinnuvel|landbuna|rafg\.stod|glussatengi/],
 ['Geymsla og skipulag',/taska|toskur|verkfaerakass|verkfaerat[oö]sk|geymslu|skuffusk/],
 ['Málning og yfirborð',/malning|pensl|malningar.*kef|murbun|murvor/],
 ['Garður og útisvæði',/skofl|hrifur|greinaklipp|fjolorf|slattu|snyrt|gir[ðd]ing|staurar|\bhli[ðd]\b/],
 ['Borar og snittvörur',/\b(bor|borar|borasett|stalbor|trebor|jarnbor|flisabor|murbor|glerbor|demantsbor|snittbakki|snittbakkar|snittapi|snittappar|spadaborar|dosaborar|dosabor|spadabor)\b/],
 ['Efnavörur og smurefni',/\b(lim|kitti|fuga|threttiefni|thettiefni|hreinsir|hreinsiefni|olia|oliur|smur|smurefni|smurfeiti|feiti|glussi|epoxy|silicon|silikon|leysir)\b|rydhreinsi|rydl[oö]ys/],
 ['Festingar og skrúfur',/skruf|bolti|boltar|skinna|skinnur|snitttein|hnod|festing|hosuklemm|splitti|pinnar|\bhefti\b/],
 ['Slöngur, barkar og tengi',/slanga|slong|barki|barkar|fitting|hradtengi|tengistykki|nippl|hosur|slonguhjol/],
 ['Lokar og lagnaefni',/loki|lokar|kululok|pipulagn|lagnaefni|\bror\b|\bflans/],
 ['Rafbúnaður og lýsing',/rafbun|rafmagn|kapall|kaplar|streng|tofluvir|tengill|tenglar|rof[ai]|lysing|ljos|rafhlod|fjoltengi|hle[ðd]sl/],
 ['Vinnufatnaður og öryggi',/hansk|vettling|hjalm|heyrn|hlifar|oryggis|vinnufat|vinnusk|stigvel|jakki|buxur|samfest|kuldagall|fatnad|hufur|hufa|belti|bjorgunar|fallvarn/],
 ['Vélar og rafmagnsverkfæri',/borvel|skrufvel|slipirokk|slipivel|soguvel|rafmagnsverkfaer|velar|\bvel\b/],
 ['Handverkfæri og mælitæki',/verkfaer|t[oö]ng|tangir|hamar|hamrar|skrufjar|lykill|lyklasett|hnif|maeli|malband|hallamal|hefil|sog|sagir|thving|\btoppar\b|blyant|tuss|laser|hex bit/],
 ['Drifbúnaður, dælur og legur',/lega|legur|drifbun|daela|daelur|motor|tjakk|loftpress/],
 ['Rekstrarvörur og hreinlæti',/hreinlaet|pappir|thurrk|sapu|ruslaf|ruslap|plastpok|umbud|skammtar|bursti|sopur|fotur/],
 ['Hífing, keðjur og veiðarfæri',/stroff|lyftibun|hif|kedj|tal[ií]|ka[ðd]al|veidarf|handfaer|bauj|\btog\b/],
 ['Byggingarefni',/timbur|steypu|einangr|byggingarefni|gips/]
];
function classify(o){if(o.manual_category)return o.manual_category;const name=S.normalize(o.name);let hit=rules.find(([,r])=>r.test(name));if(!hit)hit=rules.find(([,r])=>r.test(S.normalize([...(o.supplier_categories||[]),o.category,o.subcategory].join(' '))));if(!hit)hit=rules.find(([,r])=>r.test(S.normalize(o.description||'')));return hit?hit[0]:'Annað og óflokkað';}
const api={classify,categories:rules.map(r=>r[0])};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ProductGroups=api;
})(globalThis);
