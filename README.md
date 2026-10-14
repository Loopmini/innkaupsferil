# Njörður

Leitanlegur vörugrunnur og verðsamanburður fyrir innkaup. Fyrsta keyranlega útgáfa; íslenskt viðmót, Python 3.11+ og SQLite. Engar utanaðkomandi keyrsluháðar pakkningar.

## Keyra

```sh
git clone --branch feature/supplier-directories https://github.com/Loopmini/innkaupsferil.git
cd innkaupsferil
python app.py
```

Opnaðu **http://127.0.0.1:8000**. Á Windows má nota `py app.py`. Gagnagrunnur stofnast sjálfkrafa í `data/catalog.sqlite`. Hann er ekki í Git. Taktu afrit af allri `data/` möppunni þegar forritið er stöðvað. `INNKAUP_DB` getur vísað á aðra staðsetningu.

## Það sem virkar

- Leit eftir heiti, vörunúmeri, framleiðanda, GTIN og birgi; síur eftir flokki og birgi.
- Innlestur CSV með villuprófun allra lína áður en breytingar eru vistaðar. Eldri athuganir yfirskrifa ekki nýrri verð.
- Verðsamanburður án VSK, leiðréttur fyrir pakkastærð; gjaldmiðlar og einingar eru aðskilin.
- Vörutenging eftir GTIN (með vartöluprófun) eða framleiðanda + framleiðslunúmeri. Vörur með aðeins svipuð heiti eru ekki sjálfkrafa taldar jafngildar.
- Verðsaga með pakkastærð, VSK og einingu hverrar athugunar. Endurtekinn innlestur sömu athugunar tvítekur ekki verðsöguna.
- Verkefni og innkaupalistar, fjöldi pakkninga og vörukostnaður eftir birgja/gjaldmiðli.
- Bein tenging á innlesna vöruslóð og merking verðheimilda eldri en 30 daga.
- Birgjayfirlit sýnir þekju innlesinna gagna.

Grunnurinn heldur litlu opinberu upphafsúrtaki frá útgáfu 0.2 í `seeds/public-market.json`: sex 5 mm borafærslur, þar af þrjár með birtu verði. Þetta er ekki heildarskrá allra birgja. Upprunaslóð, athugunardagur, pakkastærð og staða verðs fylgja færslum. Verð vantar þar sem það náðist ekki; frá-verð fjölstærðavara er aldrei notað sem verð á 5 mm afbrigði. VSK-óstaðfest verð er sýnt sem birt pakkningarverð og útilokað frá nettósamanburði.

### Gögn úr fyrra verkefni

Ef `data/legacy-project.json` er til staðar les appið upprunalegt `fw-procurement-v1` JSON-úttak úr fyrri vefútgáfu. Innkaupalínur, magneiningar, birgjar, vörunúmer, flokkunarstaða og upprunareikningar varðveitast. Magn er reikningsmagn, ekki staðfest raunnotkun. Verð sem vantar er `null`, aldrei núll eða áætlað kaupverð. Einkagögn eru ekki í GitHub-safninu; þau fylgja aðeins einkaprófunarpakka þegar hann er afhentur sérstaklega. API sýnir þessi gögn aðeins á staðbundinni þjónustu.

### Merkingarbær vöruleit

Leita má að `5mm bor`, `5 mm bor`, `5,0mm stálbor` eða `5mm járnbor`. Stærð og notkun eru túlkuð sérstaklega. 5,5 mm, 15 mm, 5 Ah borvélar og borasett með óstaðfestum stærðum blandast ekki í 5 mm niðurstöður. Almenn textaleit notar öll leitarorð og styður íslenska stafi með eða án brodda.

Greining úr vörulýsingu er merkt sem slík. Sambærilegir borar eru aðeins tillögur með sama þvermáli og notkun, ekki tæknilega staðfest jafngildi. Lengd, leggur, húðun, HSS-G/HSS-Co og pakkning þurfa áfram yfirferð.

Á Windows má tvísmella á `Starta-Windows.bat`. Python þarf að vera uppsett. Vafrinn opnast sjálfkrafa og skipanaglugginn þarf að vera opinn.

## Verðlistar

Sæktu sniðmát í viðmótinu. Notaðu UTF-8 CSV með kommum milli dálka og tugabrotspunkti í tölum. CSV-gildi með kommu þurfa gæsalappir. Eftirfarandi dálkar eru í sniðmátinu:

| Dálkur | Merking |
|---|---|
| supplier, sku, name | Birgir, vörunúmer hjá birgi, vöruheiti; nauðsynlegt |
| category | Flokkur; tómt birtist sem Óflokkað |
| brand, manufacturer_part | Framleiðandi og vörunúmer hans; aðeins fylla með staðfestum upplýsingum |
| gtin | Strikamerki sem texti; ekki tapa núllum í Excel |
| price, currency | Verð pakkningar og gjaldmiðill, t.d. ISK |
| vat_included, vat_rate | true/false og VSK-prósenta, t.d. 24; ekki álykta VSK |
| pack_quantity, unit | Magn í pakkningu og eining: stk, m, m2, m3, kg eða l |
| url | Bein vöruslóð; má vera tómt fyrir verðlista án vefsíðu |
| observed_at | Dagsetning verðheimildar á ISO-sniði, t.d. 2026-10-14; ekki framtíðardagsetning |

Einingaverð án VSK = verð / (1 + VSK/100) / magn í pakkningu þegar VSK er innifalinn. Ekki flytja inn rúlluverð sem metraverð nema lengd rúllu sé staðfest. Verðlista þarf að samræma handvirkt áður en þeir eru lesnir inn.

## Fyrsta verðsöfnunartólið

`collect.py` les opinber Product/Offer JSON-LD verð af skýrum vöruslóðum. Það skríður ekki yfir heila verslun. Takmarkaður leyfislisti hýsilheita er í kóðanum (BYKO, Húsasmiðjan, Würth, Sindri og Fossberg); **þessi listi merkir ekki að viðkomandi vefur hafi verið sannreyndur sem samhæfur**. Vefir sem þurfa JavaScript eða sértæka framsetningu þurfa eigin tengingu.

```sh
python collect.py --supplier BYKO --urls data/product-urls.txt --output data/price-review.csv
```

Slóðaskráin hefur eina HTTPS-vöruslóð í hverri línu (hámark 100). Tólið athugar robots.txt, virðir biðreglur og skilar villum ef gögn eru ekki aðgengileg. Engin innskráning eða framhjáhlaup aðgangstakmarkana. Athuga þarf notkunarskilmála birgis áður en það er notað reglulega. Villur vistast við hlið CSV í `.errors.json`.

Úttakið er **drög til yfirferðar**, ekki staðfest verðlistagögn. VSK, eining, pakkastærð og flokkun eru skilin auð og verður að staðfesta þau áður en CSV er lesið inn. Tólið giskar ekki á upplýsingar og notar ekki `lowPrice` úr verðbili sem einstakt vöruverð. Þetta eldra yfirferðartól er aðskilið frá nýju sjálfvirku tengingunum í market_sync.py, sjá útgáfu 0.3 neðar.

## Prófanir

```sh
python -m unittest discover -s tests -v
node --check static/app.js
node tests/search.test.js
```

## Takmarkanir og áframhald

Þetta er staðbundið forrit fyrir einn notanda. Engin notendainnskráning eða fjölnotendaheimildir eru tilbúnar; þjónustan bindur aðeins á 127.0.0.1. Ekki opna hana beint á internetið. Opinbera GitHub-safnið á aðeins að innihalda kóða, aldrei reikninga, samningsverð eða gagnagrunn.

Ekki hefur verið safnað öllum vörum/verðum allra birgja. Næstu verk eru fleiri birgjatengingar, aukin þekja stórra síðukorta, yfirferð staðgönguvara og auðkennd hýsing. Frakt, samningsafslættir, lágmarkspantanir og lagerstaða eru ekki í útreikningi. Innkaupalistar eru áætlanir byggðar á nýjustu innlesnu verðum, ekki verðtilboð eða pantanir.

Fyrri verkefnisgögn tengjast nú með staðbundnu JSON-úttaki. Það er afrit á tilteknum tíma, ekki lifandi tenging við ChatGPT eða Sites. Skipta má um `data/legacy-project.json` með nýrra úttaki sama sniðs þegar forritið er stöðvað. SQLite-innkaupalistar og innlesin verð varðveitast sérstaklega.

## Útgáfa 0.3 – sjálfvirkar gagnatengingar

`python market_sync.py` sækir Þór í öllum síðum opinbers WooCommerce Store API. Talan í birgjayfirliti sýnir hvort öll API-færslugögn náðust. Afbrigðavörur geta þurft stærðarval; lægsta verð þeirra er ekki notað sem verð hverrar stærðar. API-verð er leiðrétt eftir currency_minor_unit.

Húsasmiðjan er lesin úr opinberu síðukorti í endurkeyranlegum lotum, 100 slóðir í hverri sjálfgefinni keyrslu. Borar eru fremst í fyrstu umferð. Í næstu keyrslum eru jafnframt endurskoðaðar allt að 50 elstu athuganir sem eru eldri en sólarhringur; ekki hvert verð daglega. `--husa-limit 500` stækkar lotuna. Bendill vistast í `data/market-status.json`. Síðukort telur slóðir, ekki staðfestar vörur. Flokkasíður án aðalvörunúmers eru ekki fluttar inn. Vörusíður án verðs haldast með óþekktu verði.

BYKO, Sindri, Fossberg og Ísól eru prófuð en fá ekki tilbúna tengingu ef robots.txt, aðgangur eða sértækur vörulestur bregst. Fleiri vöruskrártengingar bættust við í útgáfu 0.4, sjá neðar. Aðgangshöfnun 401/403 eða 429 er ekki sniðgengin. Engin innskráning eða leynilyklar eru notuð.

Nýjar athuganir vistast í `data/market-live.json`, stöður í `data/market-status.json` og breytingasaga opinberra verðs/lagers í `data/market-history.sqlite`. Fyrri gögn eru varðveitt ef tenging mistekst. Stakar vörur sem hverfa úr heilli Þór-API-keyrslu falla út úr nýjasta listanum; eldri athuganir haldast í verðsögu. Handfærðar upphafsathuganir geta enn birst með eigin eldri dagsetningu. VSK og einingamagn eru áfram ekki giskuð; óstaðfest nettóverð er ekki notað í verðreiknuðum innkaupalistum.

Appið uppfærir sjálfvirkt ef 24 klst. eru liðnar frá síðustu keyrslu og meðan Python-forritið keyrir. Þetta er ekki þjónusta sem keyrir áfram þegar tölvan eða forritið er slökkt. Slökkva má á sjálfvirkninni með `INNKAUP_AUTO_REFRESH=0`. Hnappurinn **Uppfæra markaðsverð** ræsir söfnun í bakgrunni. Í **Birgjar** sést árangur og takmarkanir hverrar tengingar. `Uppfaera-markad.bat` keyrir einnig uppfærslu án þess að opna vefappið.

Opinberar tækniskýringar: https://developer.woocommerce.com/docs/apis/store-api/resources-endpoints/products/


## Útgáfa 0.4 – vöruskrár án verðs og könnun allra birgja

Vörur án verðs eru leitanlegar og tengdar heimild, með `price: null`. Ekkert verð eða lagerstaða er áætlað. Færslur geta verið vörufjölskyldur; vörunúmer afbrigða sem vantar eru ekki búin til. Vörufjölskyldunúmer með X-stöfum hjá Barka eru ekki pöntunarnúmer.

`python market_sync.py --sources rubix landvelar isfell barki wurth iskraft hampidjan` keyrir nýju tengingarnar. Rúbix, Ísfell, Barki og Würth eru lesin í 25 slóða lotum úr opinberum síðukortum. Ískraft hefur aðeins eina staðfesta vöruslóð í fyrstu tengingu; síðukortið reyndist ekki innihalda vörulista. Hampiðjan er lesin í 20 vöru lotum úr vörulista. Landvélar eru lesnar í 100 færslu lotum úr opinberu Store API. Bendill varðveitist og hringir aftur þegar enda er náð; það þýðir EKKI að hver vara verði uppfærð daglega. Hlutaþekja er sýnd allan tímann. Fjöldi slóða er ekki alltaf fjöldi sérgreindra afbrigða.

Rúbix-tengingin les nákvæmt verð úr aðalverðreit; frá-verð afbrigða er ekki notað. Hinar nýju síðukortstengingarnar lesa vörur án verðvinnslu. Landvéla-API getur skilað verði, en núllverð eru talin óþekkt, aldrei ókeypis. Verðlausar vörur eru ekki settar í verðreiknaða innkaupalista.

### Könnun 14. október 2026

| Birgir | Niðurstaða / leið |
|---|---|
| Rúbix | Opinber vöruskrá og verð. Rubix-samstæðan lýsir PunchOut/EDI; ekki staðfest fyrir íslenska aðganginn. |
| Vatnsvirkinn | Nýr JavaScript-vefur; engin staðfest vörugagnatenging enn. Óska eftir vöruskrárútflutningi. |
| Vatn og veitur, Rönning | Opinberir vefir en sjálfvirkt aðgangspróf fékk 403. Kanna gagnaskipti við Fagkaup. |
| Sindri, Fossberg | Fyrri 403 niðurstaða stendur; ekki prófað framhjá aðgangstakmörkun. Kanna Fagkaup-útflutning. |
| Ískraft | Opinber heiti og vörunúmer; verð krefjast sérstakrar leiðar. Aðeins ein staðfest vöruslóð; heildarvörutenging ólokið. |
| Reykjafell | robots.txt útilokar /products og /vorur. Óska eftir samþykktri tengingu eða útflutningi. |
| Hampiðjan | Opinber vörulisti, vörunúmer og lýsingar; innskráning til pöntunar. |
| Ísfell | Opinberar vörusíður og bæklingar. Vörusíður lesnar; PDF-afbrigði ekki enn sundurliðuð. |
| Landvélar | Opinbert Store API svarar; sum verð vantar/núll. |
| Barki | Opinber vöruskrá, fjölskyldur og tækniblöð; engin staðfest verðtenging. |
| Würth | Opinber vöruskrá; fyrirtækjaverð krefjast innskráningar. |
| BYKO | Opinber PDF-verðlistaleið til staðar; PDF-innlestur ekki sjálfvirkur enn. |
| Ísól | Vefverslun; fyrri 403 niðurstaða. Óska eftir samþykktri tengingu eða útflutningi. |

Heimildir: https://rubix.is/ · https://solution.rubix.com/service/e-procurement/ · https://vatnsvirkinn.is/ · https://www.vatnogveitur.is/ · https://www.ronning.is/ · https://iskraft.husa.is/ · https://www.reykjafell.is/robots.txt · https://verslun.hampidjan.is/vorur · https://isfell.is/vorulistar/ · https://landvelar.is/vorur/ · https://www.barki.is/ · https://wurth.is/ · https://byko.is/serlausnir/verdlistar

Könnun er einnig í `seeds/supplier-connections.json` og birgjakortum viðmótsins. Opinber vefverslun sannar hvorki API-aðgang né heimild til að sækja samningsverð. Enginn póstur eða aðgangsumsókn hefur verið send.

## Útgáfa 0.5 – flokkayfirlit og BOM

Vörugrunnurinn opnast með flokkakortum í stað alls vörulistans. Leit virkar áfram yfir grunninn, og flokkaval opnar vörurnar. Flokkun yfirlitsins er reglubundin greining úr heitum og birgjaflokkum; hún breytir ekki upprunalegu reikningsflokkuninni. Óvissar vörur haldast í „Annað og óflokkað“.

**BOM-samanburður** tekur við UTF-8 CSV/TSV, töflu límdri úr Excel og XLSX (fyrsta blað, haus í fyrstu línu, engar formúlur). Hámark er 500 línur og 3 MB. Skyldudálkar eru `heiti,magn,eining`; valfrjálst `birgir,vorunumer,gtin,framleidandi,mpn`. Ensk dálkaheiti eru einnig studd. Einingar: `stk,m,m2,m3,kg,l`. Vörunúmer og strikamerki verða að vera texti í Excel til að varðveita núll. Alveg eins línur eru sameinaðar fyrir pakkareikning.

Vöruleit í BOM notar sama stærðar-/efnisgrunn og almenn leitarvirkni. Beint GTIN, framleiðandi + MPN eða birgir + vörunúmer er sjálfvirk samsvörun. Textaleit er tillaga, ekki sjálfkrafa staðfest jafngildi; notandi samþykkir vörufærslurnar áður en þær fara í heildartölur. Listar og samþykktar vörur vistast í SQLite og eru einkagögn.

Kostnaður = heilar pakkningar sem þarf × verð pakkningar án VSK. Samanburður krefst þekkts verðs, VSK, pakkamagns, sömu einingar/gjaldmiðils og athugunar innan 30 daga. Vörur merktar ekki á lager eru ekki valdar. Óstaðfest lagerstaða er sýnd og er ekki afhendingarloforð. Núll er aldrei staðgengill fyrir óþekkt verð.

Niðurstöður sýna lægsta reiknanlega kostnað **á hverri línu**, skiptingu milli birgja og kostnað/þekju fyrir kaup hjá einum birgi. Ófullkomin körfa sýnir aðeins hlutakostnað, aldrei lægsta heildarverð. Þetta er ekki heildarbestun yfir frakt, magni háða afslætti eða lágmarkspantanir. Engin gengisumbreyting eða pöntunarsending. CSV-útflutningur inniheldur vöruval og kostnað þar sem hann er reiknanlegur.

Prófanir: `python -m unittest discover -s tests`, `node tests/search.test.js` og `node tests/bom.test.js`. BOM-prófin ná yfir pakkarúnnun, ófullkomnar körfur, samþykki, gjaldmiðla, einingar, ferskleika og XLSX-formúluvarnir.


## Fleiri vörur og birgjar – 14. október 2026

Dynjandi og Tengi eru nú tengdir með opinberu Store API í 100 færslu lotum, sömu varfærnu verðtúlkun og Landvélar. Núllverð og verðbil verða ekki samanburðarverð. Keyra má `python market_sync.py --sources dynjandi` til að sækja næstu lotu. Sjálfgefin uppfærsla nær einnig til Dynjanda og Tengis.

Birgjayfirlit sýnir nú líka kannaða birgja sem hafa engar vörur í grunni:
- [Dynjandi](https://www.dynjandi.is/): öryggisbúnaður, persónuhlífar og iðnaðarvörur; tengdur.
- [Tengi](https://www.tengi.is/): lagnaefni, fittings og ryðfríir lokar og hreinlætistæki; tengdur, hlutaþekja.
- [Tandur](https://www.tandur.is/): hreinlætisefni, þrifaáhöld og rekstrarvörur; opinber listaverð með VSK, vörutenging ólokið.
- [Vélasalan](https://velasalan.is/): dælur, vélar og varahlutir fyrir sjó og iðnað; vörutenging ólokið.

Þetta eru mögulegir viðbótarbirgjar, ekki staðfest tæknileg jafngildi eða tæmandi markaðsyfirlit. Skoða þarf efnisgæði, mál, vottanir og pakkningar áður en vörur eru samþykktar í BOM.


## Vörumyndir og handvirk flokkun

Vöruspjaldið sýnir mynd frá birgja þegar myndaslóð fylgir vöruviðmóti eða opinber vörusíða birtir myndalýsigögn. Fyrir eldri færslur er mynd sótt þegar spjaldið er opnað. Engin mynd er giskuð út frá heiti eða óstaðfestum flokkatengli. Myndaleysi eða aðgangshöfnun birtist í spjaldinu; mynd getur táknað vörufjölskyldu, svo staðfesta þarf afbrigði. Myndir eru hlaðnar frá birgja með referrerpolicy=no-referrer.

Í „Skoða“ → „Breyta flokkun“ má velja eða skrifa flokk, einnig fyrir óflokkaðar vörur. Flokkurinn gildir fyrir þessa vörufærslu, fer fram yfir sjálfvirka flokkun og vistast í data/catalog.sqlite. Upprunaleg birgjaflokkun er varðveitt. „Nota sjálfvirka flokkun“ eyðir eigin leiðréttingu. Verð og vörunúmer eru ekki breytt með þessari aðgerð. Varðveittu data/catalog.sqlite við uppfærslu uppsetningar.


## Njörður v0.6 – myndir, birgjalýsingar og heildarlestur

Nýtt heiti og sjávarþema. Fyrri gagnagrunnur og auðkenni haldast; engin gögn þurfa að flytjast vegna nafnabreytingar.

Myndavillan var í Content-Security-Policy: ytri HTTPS-myndir eru nú leyfðar sem myndir, en JavaScript er áfram aðeins frá forritinu. Vörulýsing og birgjaflokkar eru sótt úr opinberum vörulýsigögnum; Wix-vöruflokkar eru tengdir nákvæmri vöruslóð. Barki 35-30-100024 er viðmiðunarpróf: mynd, hraðtengislýsing, þrýstiþol/flæði og flokkar. Innfelld viðmiðunar-/staðgengilsverð eru ekki lesin inn sem kaupverð. Lýsingar birtast sem texti og nýtast í leit og sjálfvirkri flokkun. Eigin flokkun hefur alltaf forgang.

„Lesa alla birgja“ fer heila umferð í lotum yfir tengdar vöruskrár, frá vistuðum bendli. Nýjar vörur og breytt verð/framboð vistast eftir hverja lotu. Birgjum er skipt á milli lota; lokaður eða bilaður birgir er merktur og kemur ekki í veg fyrir hina. Ótengdir birgjar verða ekki sjálfkrafa tengdir. Heildarstaða, loknir birgjar og villur eru í data/full-sync.json. „Stöðva eftir lotu“ bíður eftir vistun núverandi lotu. Eftir lokun forrits má hefja nýja umferð frá vistuðum stöðum; birgjar sem voru áður yfirfarnir eru þá skoðaðir aftur. Forritið þarf að vera í gangi og stórar skrár geta tekið marga klukkutíma eða lengur. Þetta tryggir ekki tæmandi þekju allra afbrigða, innskráningarverða eða lokaðra vefja.

Venjulegur uppfærsluhnappur og dagleg staðbundin keyrsla taka áfram eina lotu frá hverjum birgi. Heildarlestur er val notanda og er ekki ræstur sjálfkrafa við opnun.


## Birgjaval og samtímis innlestur

Opnaðu „Velja birgja fyrir innlestur“, veldu einn eða fleiri, eða notaðu „Velja alla“/„Hreinsa val“. „Uppfæra valda birgja“ tekur eina lotu hjá hverjum völdum birgi. „Heildarlestur valinna birgja“ tekur heila umferð í lotum. Dagleg sjálfvirk uppfærsla nær áfram til allra skráðra tenginga; birgjaval í viðmóti gildir um handvirku keyrsluna.

Báðar leiðir vinna með allt að tvo birgja samtímis. Heildarlestur afgreiðir tvær birgjalotur í einu; ein samræmd vistun kemur í veg fyrir að tveir þræðir yfirskrifi gögn hvors annars. Bið milli beiðna og robots-reglur hvers birgis haldast. Stöðvun bíður eftir báðum virkum lotum. Óvaldir birgjar varðveitast og enginn tómur vallisti er túlkaður sem „allir“. Birgjaval læsist meðan innlestur stendur yfir.

Prófað: 43 Python-próf, Node-leitar/BOM-próf og DOM-próf fyrir birgjaval, rétt beiðnigögn, myndir og flokkun. Samtímapróf notar tvo þræði með samstillingarhindrun og sannreynir jafnframt varðveislu óvalinna birgja.


## Yfirferð flokkunar með birgjalýsingum

Sjálfvirk flokkun notar nú nákvæm vöruheiti, upphaf vörulýsingar og birgjaflokka. Lýsingar um notkun og meðfylgjandi fylgihluti fá ekki að yfirgnæfa sjálfa vörutegundina. Skrúfur, skrúfbitar og skrúfvélar eru aðgreindar; beygingar og samsett orð eins og tréskrúfa, steinbor og fræsitönn hafa sérstakar reglur. Leikföng/módel, suðuvörur, baðbúnaður, vinnupallar og þéttingar hafa eigin flokka.

Vöruspjaldið sýnir flokkunargrundvöll og textann sem styður hana. Handvirkar leiðréttingar hafa alltaf forgang. Ófullnægjandi eða mótsagnakennd lýsing getur áfram skilað Annað og óflokkað; þetta er reglubundin tillaga, ekki staðfest bókhaldsflokkun eða tæknilegt jafngildi. Upprunaleg heiti, birgjaflokkar og verð breytast ekki.

Nýju reglurnar gilda sjálfkrafa um fyrirliggjandi og ný gögn þegar forritið er endurhlaðið. Lýsingar sem eru aðeins vistaðar í annarri uppsetningu eru ekki aðgengilegar við þessa yfirferð, en sömu reglur gilda um þær þar. Prófanir: `node tests/groups.test.js` (22 tilvik) auk fyrri Python-, leitar-, BOM- og viðmótsprófa.


## Gagnablöð frá birgja

Vöruspjaldið sýnir „Gagnablöð og skjöl frá birgi“ með PDF-tenglum sem fundust á vörusíðunni eða í lýsingu vöruviðmóts. Opinber Wix-skjöl eru lesin úr tæknigögnum nákvæmrar vöru; einkamerkt skjöl eru ekki birt. Tenglar eru aðeins HTTPS, afrit eru sameinuð og þekkt persónuverndar-/skilmálaskjöl útilokuð. Skjal getur átt við vörufjölskyldu og þarf að yfirfara stærð/gerð hjá birgi. Engin fullyrðing um tæmandi skjalaþekju eða yfirferð á PDF-innihaldi.

Eldri lýsigagnavistun er endurnýjuð þegar spjaldið opnast, svo skjöl geti bæst við. Barki 35-30-100024 er staðfest dæmi: RoflexDatasheet.pdf svaraði með application/pdf og PDF-skráarhaus. 45 Python-próf og fyrri DOM-próf standast. Gervigreindartenging er ekki virkjuð í þessari breytingu.

## AI-aðstoð tilbúin til virkjunar · v0.7

Enginn API-lykill fylgir. Forritið virkar áfram án AI. Á Windows: opnaðu `Stilla-AI-Windows.bat`, límdu þinn lykil á eftir `OPENAI_API_KEY=` í textaskránni sem opnast og vistaðu. Skráin heitir `.env` og er í sömu möppu og `app.py`; hjálparskráin yfirskrifar ekki fyrirliggjandi stillingar. Á öðrum kerfum: afrita `.env.example` í `.env` og breyta henni. Endurhlaða vefsíðunni; stillingar eru lesnar við hverja beiðni. Umhverfisbreytur hafa forgang. Ekki senda lykilinn í spjall, setja hann í GitHub eða deila `.env`.

Vöruspjald: „Yfirfara og leggja til flokk“ metur vöruheiti, lýsingu, auðkenni, einingar og hvort mynd/gagnablað/verð sé skráð. Tillaga og annmarkar birtast. „Setja tillögu í flokkunarreit“ fyllir reitinn; síðan þarf að velja „Vista flokkun“. Handvirkt val breytist ekki án vistunar.

BOM: opna línu og velja „AI-aðstoð við þessa línu“. Aðstoðin metur fyrstu 40 tillögur núverandi leitarkerfis, skilar allt að fimm mögulegum vörum og atriðum sem þarf að athuga. Hún leitar ekki á öllum netinu og finnur ekki vörur utan þess úrtaks. Þú samþykkir viðeigandi vörur sjálfur með reitunum í samanburðinum. Kostnaður er áfram reiknaður úr skráðum verðum, VSK, magni og pakkastærðum, aldrei úr AI-svari.

Við smell eru viðkomandi vöruupplýsingar eða ein BOM-lína og afmarkaðar tillögur sendar til OpenAI. Ekki sendir reikningar, upprunaskrár, einkaglósur, kaupverð eða allur gagnagrunnurinn. Engin sjálfvirk AI-keyrsla, skjalalestur eða heildaryfirferð allra vara. Engin pöntun er send. AI getur gert mistök; tæknilegt jafngildi þarf yfirferð.

Sjálfgefið líkan: `gpt-5-mini`, breytanlegt með `OPENAI_MODEL`. Python-staðalsafn, Responses API, structured outputs, `store:false`, ein beiðni samtímis, 90 sekúndna netbið og 4.000 úttakstákn að hámarki. Engar sjálfvirkar endurtilraunir. API-notkun fer á þinn OpenAI-reikning. Stöðumerkingin „Lykill skráður“ staðfestir aðeins að gildi sé til staðar; fyrsta aðgerð prófar aðganginn. Villur um lykil, kvóta, líkan og nettengingu birtast án þess að lykill eða hrátt API-svar sé sýnt.

Staðfest með hermdum API-svörum; raunverulegt API-kall bíður lykils. Keyra próf með `python3 -m unittest discover -s tests` og Node-prófin í `tests/`.

## Vöruflokkun fyrir innkaup · v0.8

Flokkunin er fyrir vöruleit, birgjasamanburð og BOM, ekki bókhald. `seeds/taxonomy.json` skilgreinir eina samræmda leið fyrir hverja vörutegund: yfirflokkur → undirflokkur → vörutegund. Núverandi flokkar eru færðir í þessa uppbyggingu við lestur; upprunalegar færslur og birgjaflokkar varðveitast. Tómar greinar sjást og eru merktar „Bíður vörugagna“.

| Fyrri flokkar | Nýr aðalstaður |
| --- | --- |
| Borar og snittvörur; handverkfæri; rafmagnsverkfæri; skurðar-/slípivörur; suðuvörur; stigar | Verkfæri og fylgihlutir, aðgreindir undirflokkar |
| Festingar og skrúfur; þéttingar og pakkningar | Festingar og þéttingar |
| Slöngur og tengi; dælur | Dælur, slöngur og vökvabúnaður |
| Lokar og lagnaefni; hreinlætistæki | Lagnir og tengihlutir |
| Rafbúnaður og lýsing | Rafmagn og lýsing; sérhæfð stýring/mæling fær eigin yfirflokk |
| Málning; efnavörur og smurefni | Málning, lím og efnavörur |
| Vinnufatnaður og öryggi | Vinnuvernd og vinnufatnaður |
| Hífing, keðjur og veiðarfæri | Lyfti- og flutningsbúnaður eða Veiðarfæri eftir gögnum |
| Drifbúnaður og vélahlutir; geymsla; rekstrarvörur; garður; leikföng | Varðveittir aðskildir yfirflokkar |

Byggingarefni hefur Timbur (burðarvirki, gagnvarið, timburklæðningar, pallaefni, límtré, LVL, listar), Plötuefni (krossviður, OSB, MDF, gifs, spónaplötur), Einangrun, Þakefni, aðrar klæðningar, Hurðir og glugga, Steypu og múrvörur. Timburklæðningar eru aðeins undir Timbri. Stál og málmar og Eldisbúnaður hafa einnig eigin greinar; almenn net eru ekki sjálfkrafa flokkuð sem eldisnet.

Stærð, efni/viðartegund, styrkleikaflokkur, yfirborðsmeðhöndlun og staðall eru aðskilin frá flokkun. Leit og síur styðja þau, auk framleiðanda, birgis og sölueiningar. Fyrir timbur/plötur eru aðeins tekin mál með skýrum einingum eða merktum tæknigögnum. `45x95 mm` er túlkað sem þykkt × breidd, `45x95x4200 mm` sem þykkt × breidd × lengd, og sú túlkun er sýnd við reitinn. Ómerkt `45x95` gefur engin staðfest mál. Árekstur milli gilda skilur reit eftir óþekktan og merkir til yfirferðar. Lengd í metrum eða cm má normalísera í mm vegna skýrrar einingar; það er ekki umreikningur sölueininga eða verðgrunns.

Vöruheiti, upphaf lýsingar, birgjaflokkar og merkt JSON-LD `additionalProperty` tæknigögn styðja flokkun/eiginleika. Tæki, skrúfur eða sagarblöð sem nefna timbur/gifs/MDF sem notkunarefni fara ekki sjálfkrafa í byggingarefni. Gagnablöð eru áfram tengd á vöruspjaldi; PDF-innihald er ekki lesið sjálfvirkt. Ný birgjagögn sjást við enduropnun spjalds/endurhleðslu.

Á vöruspjaldi má velja öll þrjú flokkunarþrep, leiðrétta eiginleika og bæta leitartögum. Ein aðalflokkun, mörg leitartög. Handvirk gildi eru vistuð í nýrri SQLite-töflu `product_enrichment` og yfirskrifast ekki við innlestur birgja. Eldri handvirkar flokkunarbreytingar varðveitast og eru samræmdar þegar hægt er; óþekktur eldri sérflokkur er merktur til yfirferðar. „Fjarlægja þessar handvirku breytingar“ endurheimtir fyrirliggjandi birgjagögn/eldri flokkun. Flokkunaróvissa og vöntun eiginleika eru aðskildar síur.

Sama vara miðast við GTIN, framleiðanda + framleiðandanúmer eða birgi + vörunúmer. Sambærileg lýsing er aðeins möguleg staðganga. Timbur-/plötustaðgöngur þurfa sömu vörutegund og skráða þykkt/breidd; þekktir eiginleikar mega ekki stangast á. Það staðfestir ekki útskiptanleika og vantar hugsanlega lengd, styrk, meðhöndlun eða staðla. Vöruspjaldið sýnir birgi, birgjanúmer, MPN, verðgrunn, einingu, VSK, pakkastærð og tengil. Engin umreikningur milli stk., m, m² og kg án staðfestra gagna.

Bæta má vöru og magni beint á nýjan eða vistaðan BOM-lista. Skráðir eiginleikar fylgja sem kröfur. BOM úr CSV/XLSX getur líka borið valfrjálsu dálkana `thykkt_mm`, `breidd_mm`, `lengd_mm`, `styrkleikaflokkur`, `yfirbordsmedhondlun`, `efni`, `stadall`. Línur með ólíkar kröfur eru ekki sameinaðar. Sama auðkenni og mögulegar staðgöngur eru aðgreindar. Staðgöngur þarf að samþykkja; vantar verð, einingar eða áskilinn tæknieiginleika telst línan ekki fullverðlögð. Ófullkomin tilboð sýna þekju og hlutakostnað, ekki villandi heildarverð.

AI-uppsetning úr v0.7 fylgir áfram, nú með samræmdum flokkunarstígum og tæknikröfum. Lykill fylgir ekki. Prófanir nota tilbúin tímabundin dæmi; þeim er ekki bætt í vörugrunninn. 67 Python-próf, Node-próf fyrir leit/flokkun/BOM og DOM-próf fyrir flokkunarslóðir, síur, vistun, AI-tillögur og vörur á BOM staðfest.

### Það sem bíður gagna

Flokkunartréð býr ekki sjálft til vöruúrval. Ef timbur, málmar eða aðrir flokkar eru tómir þarf staðfestar birgjafærslur. Verð eitt nægir ekki til samanburðar þegar eining, pakkastærð eða VSK er óþekkt. Óstaðfest gildi eru ekki fyllt sjálfvirkt. Engin full sjálfvirk yfirferð tæknilegs jafngildis, lagerstöðu eða afhendingar hefur verið gerð. Yfirlit yfir umfang gagna í einkapakkanum fylgir í `GAGNASTADA.txt`; einkagögnin eru ekki í GitHub.

## Spjall og innlestrarvakt · v0.9

Veldu **Spjalla við Njörð** í vinstri valmynd. Lýstu þörfinni, t.d. „Mig vantar 20 stk. af 5 mm stálborum“, og spurðu áfram til að þrengja valið. Spjallið notar fyrirliggjandi OpenAI-tengingu og sama `.env` lykil. Án lykils birtast leiðbeiningar um virkjun. Enginn nýr lykill fylgir.

Spjallið myndar allt að fimm leitarorðasambönd, leitar í innlesnum markaðs-/verðlistavörum og gefur AI allt að 40 samsvaranir. Allt að átta vöruspjöld birtast með verði úr gagnagrunni, birgja, vörunúmeri, athugunardegi og tengli. Auðkenni svara eru sannreynd gegn vörunum sem voru sendar. Opnaðu vöruspjald til að bæta á BOM með eigin magni. AI sendir hvorki pöntun né vistar sjálft breytingar. Spjallið er ekki tæmandi vefleit eða tæknileg jafngildisstaðfesting.

Tvö afmörkuð API-köll eru gerð á hverju svari. Skilaboðin þín, síðustu átta spjallskilaboð og afmarkaðar vöruupplýsingar fara til OpenAI. Einkareikningar og eldri innkaupalínur eru útilokuð úr vöruleit spjallsins. Spjallsaga er aðeins í minni vafrans, hverfur við endurhleðslu og má hreinsa með „Nýtt spjall“.

Innlestrarvakt sést fyrir ofan vörugrunninn. Hún sýnir bið, virkan lestur, síðasta framvindumerki, aðgangshöfnun/villur, vistun, birgja afgreidda, tíma sem liðinn er og nýjar/breyttar færslur. „Staða hvers birgis“ opnar nánari yfirlit. Meðan lestur er í gangi er staða sótt á þriggja sekúndna fresti, annars á 15 sekúndna fresti. Hægur birgir felur ekki lengur niðurstöðu þess sem lýkur fyrr.

Framvindustikan telur afgreidda birgja, ekki vörur eða öruggt hlutfall af öllum markaði. Vöru-/slóðafjöldi úr birgjagögnum er merktur sem viðmið. Engin ágiskuð lokatímaspá. Breytingateljarar undanskilja breytingu á athugunardegi einum og sér; í heildarumferð geta þeir talið sömu vöru aftur ef hún breytist milli lota. Ný gögn vistast þegar lotu lýkur. Við stöðvun klárast virkar lotur fyrst; þögn frá birgi birtist sem tími frá síðasta merki, ekki sjálfkrafa sem bilun.

Windows UTF-8 viðgerðin fylgir. Prófanir: 72 Python-próf, Node-próf fyrir leit/BOM/flokkun og DOM-próf fyrir spjall, framhaldsspurningar, vöruspjöld og innlestrarstöðu. Raunveruleg AI-köll bíða lykils í keyrsluumhverfi notanda; prófað hér með hermdum API-svörum.


## Áfangauppfærsla · v0.10

Þessi útgáfa byggir á núverandi SQLite-gögnum, birgjatengingum og flokkun. Engin endurstilling eða eyðing vörugagna er hluti uppfærslunnar. Windows-villan sem gat falið allar vörur var hleðsluvilla: íslensk JSON-flokkanöfn voru lesin með cp1252 í stað UTF-8. Það er leiðrétt. Nýjar hleðsluvillur birtast sem villur, ekki sem tómur grunnur.

### Uppfærsla núverandi uppsetningar

1. Lokaðu keyrandi Njörði (Ctrl+C í ræsingarglugganum) og taktu afrit af allri núverandi möppu.
2. Afþjappaðu `Njordur_v010_uppfaersla.zip`. Afritaðu innihald `Innkaupsferil` yfir sömu forritsmöppu og leyfðu yfirskrift kóðaskráa. Ekki búa til nýja tóma uppsetningu.
3. Uppfærslupakkinn hefur hvorki `data/` né `.env`; núverandi gögn og lykill haldast. Ræstu `Starta-Windows.bat` aftur og endurhlaðaðu síðunni með Ctrl+F5.
4. Skoðaðu vörufjölda og vistaða lista. Undir „Gagnavarsla, afrit og innflutningssaga“ má taka og sækja ZIP-afrit.

### Áfangi 1 — gagnavarsla og innlestur

SQLite-afrit eru tekin með backup API, einnig við ræsingu og fyrir birgjainnlestrarumferð. Afrit geyma vörugrunn, lista og markaðsskrár en aldrei `.env`. Endurheimt sannreynir skráarheiti, SHA-256, JSON og SQLite áður en hún tekur björgunarafrit og skrifar gögn. Skrár sem vantar í gamalt afrit eru ekki fjarlægðar. Afrit eru á sama diski, engin sjálfvirk grisjun: sækja þarf afrit og geyma annars staðar.

Verðlista-CSV, BOM og tilboðssvör hafa forskoðun og sérstaka staðfestingu. Verðlisti sýnir nýjar, breyttar, óbreyttar og mögulega tvíteknar færslur. Sama birgir/vörunúmer uppfærist; sama BOM-innflutningur með sama heiti opnar fyrri lista. Svör uppfæra sömu birgja/línu. Heimild og innflutningsdagur varðveitast. Innflutningssaga býður afturköllun þegar síðari breytingar eða notkun vörunnar gera hana ekki óörugga. Annars þarf að afturkalla nýrri breytingar fyrst eða nota afrit.

Vefinnlestur sýnir raunveruleg stig og fjölda, en notar enn fyrra sjálfvirka vistunarferli eftir lotu. **Forskoðun og samþykki einstakra vefbreytinga er enn óútfært.** Fyrir slíkar lotur er afrit til endurheimtar; sértæk afturköllun einnar birgjalotu bíður.

### Áfangi 2 — vöruspjöld og samanburður

Leit birtir eitt spjald fyrir sama þekkta GTIN eða framleiðanda+MPN, annars birgi+vörunúmer. Upprunafærslur eru varðveittar. Heiti eitt sameinar ekki vörur. Vöruspjald sýnir tilboð, tengla, heimildir og mögulegar staðgöngur með mismun/óþekktum eiginleikum. Ófullkomin auðkenni geta því enn valdið fleiri en einu spjaldi fyrir raunverulega sömu vöru.

Skrá má staðfest/áætlað lágmarksmagn, viðbótarafslátt, gildistíma og afhendingardag á vöru. BOM námundar upp í heilar pakkningar og virðir MOQ. Óþekkt verð, VSK, eining eða pakkning hindrar línusamanburð; óþekkt MOQ eða birgjagjöld hindra fulla heildartölu. Engin óstaðfest eininga- eða gengisumbreyting.

### Áfangi 3 — vistaðir listar og birgjaval

Listi geymir verkefni, afhendingarstað, óskadag, gjaldmiðil, birgjaskilmála og handvirkt val hverrar línu. Reiknaðar eru leiðir fyrir lægsta þekkta kostnað, fæsta birgja og afhendingu fyrir dag. Gjöld eru föst fyrir hverja birgjapöntun, án VSK. Allar birgjasamsetningar eru skoðaðar upp að 12 birgjum; yfir því er samanburður afmarkaður og merktur.

„Sækja innkaupaleiðir og heildarkostnað CSV“ flytur út línur með birgjaafslætti, pakkafjölda, keyptu magni, gjöldum, heild og stöðu hvers valkosts. Óþekkt heild er tóm og merkt, aldrei núll. Eldri línuverðsútflutningur er áfram aðskilinn og merktur án birgjagjalda.

Óútfært: magnþrepaverð, flutningsverð eftir þyngd/magni, samnýting pakkninga milli ólíkra BOM-lína og breyting magnreita á þegar vistuðum línum. Magn má velja í drögum/innflutningi; til að breyta heildarlista er hægt að lesa inn endurskoðaðan lista með nýju heiti.

### Áfangi 4 — leit, innkaupadrög og spjall

Forsíða hefur vöruspjöld, flokka og nýlega lista. Flokkasíur sýna viðeigandi mál fyrir timbur/plötur eða þvermál, DN og PN fyrir lagnir. Hliðarspjald safnar vörum úr leit eða spjalli, sameinar sama auðkenni og biður notanda um magn/einingar áður en hann samþykkir vistaðan lista. Óvistuð drög og spjall eru aðeins í minni vafrans.

Spjall nýtir fyrirliggjandi OpenAI-stillingar og raunverulegar innlesnar vörur; enginn nýr lykill þarf að vera settur í BAT-skrá. Einkainnkaup og BOM-tilboðssvör fara ekki í almenna vöruleit spjallsins. AI-texti er tillaga, ekki staðfesting tæknilegs jafngildis. Verð á spjöldum og útreikningar koma úr gögnum. API-prófanir hér eru hermdar; lifandi kall og útlitsprófun í Windows-vafra bíða keyrslu notanda.

### Áfangi 5 — tilboðsbeiðnir og svör

CSV-tilboðsbeiðni inniheldur stöðug lista-/línuauðkenni, magn/einingar, lýsingu, tæknikröfur og afhendingarupplýsingar. Sama skrá er svarssniðmát. Innlestur svara sannreynir línutengingar og hefur forskoðun. Svör eru ekki sjálfkrafa samþykkt sem tæknilega jafngild; kröfur úr beiðni verða ekki sjálfkrafa að staðfestum eiginleikum svars.

Enginn sendingarhnappur eða tölvupóststenging er virk; notandi sækir skjalið og sendir sjálfur. Sjálfvirkur lestur óstaðlaðra PDF-/tölvupóstsvara bíður. Gagnablöð haldast sem tenglar, PDF-innihald er ekki túlkað sjálfvirkt.

### Staðfesting og gögn sem vantar

81 Python-próf og 5 Node-prófasöfn: vistun/enduropnun í nýju ferli, endurtekinn innflutningur, örugg afturköllun, skemmd afrit, svör á sömu línu, pakkningar, MOQ, óþekkt gjöld, handvirkt val, afhending, flokkun og leit. DOM-próf ná yfir spjall/framvindu og leið frá innkaupadrögum yfir í vistaðan lista/birgjaval. Engin raunveruleg pöntun, sending eða API-kall var gert.

Nýju eiginleikarnir fylla ekki upp vantaðar birgjaupplýsingar. Timbur/málmar og aðrir tómir flokkar bíða staðfestra vörufærslna. Pakkningar, VSK, flutningur, MOQ og afhending þurfa staðfestar heimildir áður en viðkomandi tilboð fær fulla heildartölu.
