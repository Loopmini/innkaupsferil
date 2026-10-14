# Innkaupsferil

Leitanlegur vörugrunnur og verðsamanburður fyrir innkaup. Fyrsta keyranlega útgáfa; íslenskt viðmót, Python 3.11+ og SQLite. Engar utanaðkomandi keyrsluháðar pakkningar.

## Keyra

```sh
git clone https://github.com/Loopmini/innkaupsferil.git
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

Grunnurinn er tómur við fyrstu ræsingu. Engin sýniverð eru látin líta út fyrir að vera raunveruleg verð. Birgjalistinn er upphafslisti; nýjir birgjar geta komið inn með CSV.

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

Úttakið er **drög til yfirferðar**, ekki staðfest verðlistagögn. VSK, eining, pakkastærð og flokkun eru skilin auð og verður að staðfesta þau áður en CSV er lesið inn. Tólið giskar ekki á upplýsingar og notar ekki `lowPrice` úr verðbili sem einstakt vöruverð. Sjálfvirk söfnun er ekki virk í vefviðmótinu og engin tímastýrð verðvakt hefur verið sett upp.

## Prófanir

```sh
python -m unittest discover -s tests -v
node --check static/app.js
```

## Takmarkanir og áframhald

Þetta er staðbundið forrit fyrir einn notanda. Engin notendainnskráning eða fjölnotendaheimildir eru tilbúnar; þjónustan bindur aðeins á 127.0.0.1. Ekki opna hana beint á internetið. Opinbera GitHub-safnið á aðeins að innihalda kóða, aldrei reikninga, samningsverð eða gagnagrunn.

Ekki hefur verið safnað öllum vörum/verðum allra birgja. Næstu verk eru staðfest tenging fyrir hvern birgjavef, sitemaps/API þar sem í boði, yfirferð staðgönguvara, tímasettar uppfærslur og auðkennd hýsing. Frakt, samningsafslættir, lágmarkspantanir og lagerstaða eru ekki í útreikningi. Innkaupalistar eru áætlanir byggðar á nýjustu innlesnu verðum, ekki verðtilboð eða pantanir.

Heitið tengir þetta við Innkaupsferil-verkefnið. Engin tæknileg tenging við fyrri Sites-útgáfu eða ChatGPT-verkefnisgögn hefur verið sett upp; til þess þarf aðgang að þeim gögnum og skilgreint gagnaviðmót.
