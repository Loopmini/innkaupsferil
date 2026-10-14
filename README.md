# Innkaupsferil

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
