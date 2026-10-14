# Innkaupsferil

Leitanlegur vörugrunnur og verðsamanburður fyrir innkaup. Fyrsta keyranlega útgáfa; íslenskt viðmót, Python 3.11+ og SQLite. Engar utanaðkomandi keyrsluháðar pakkningar.

## Keyra

```sh
git clone --branch feature/procurement-catalogue https://github.com/Loopmini/innkaupsferil.git
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

BYKO, Sindri, Fossberg og Ísól eru prófuð en fá ekki tilbúna tengingu ef robots.txt, aðgangur eða sértækur vörulestur bregst. Aðrir birgjar eru enn ótengdir. Aðgangshöfnun 401/403 eða 429 er ekki sniðgengin. Engin innskráning eða leynilyklar eru notuð.

Nýjar athuganir vistast í `data/market-live.json`, stöður í `data/market-status.json` og breytingasaga opinberra verðs/lagers í `data/market-history.sqlite`. Fyrri gögn eru varðveitt ef tenging mistekst. Stakar vörur sem hverfa úr heilli Þór-API-keyrslu falla út úr nýjasta listanum; eldri athuganir haldast í verðsögu. Handfærðar upphafsathuganir geta enn birst með eigin eldri dagsetningu. VSK og einingamagn eru áfram ekki giskuð; óstaðfest nettóverð er ekki notað í verðreiknuðum innkaupalistum.

Appið uppfærir sjálfvirkt ef 24 klst. eru liðnar frá síðustu keyrslu og meðan Python-forritið keyrir. Þetta er ekki þjónusta sem keyrir áfram þegar tölvan eða forritið er slökkt. Slökkva má á sjálfvirkninni með `INNKAUP_AUTO_REFRESH=0`. Hnappurinn **Uppfæra markaðsverð** ræsir söfnun í bakgrunni. Í **Birgjar** sést árangur og takmarkanir hverrar tengingar. `Uppfaera-markad.bat` keyrir einnig uppfærslu án þess að opna vefappið.

Opinberar tækniskýringar: https://developer.woocommerce.com/docs/apis/store-api/resources-endpoints/products/
