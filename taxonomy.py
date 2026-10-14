"""Purchasing taxonomy: evidence-based paths and separately stored specifications."""
import json
import math
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).parent
TREE = json.loads((ROOT/'seeds/taxonomy.json').read_text(encoding='utf-8'))
LEAVES = {}
for top in TREE['groups']:
    for sub in top['children']:
        for leaf in sub['children']:
            LEAVES[leaf['id']] = [top['name'], sub['name'], leaf['name']]
UNKNOWN = 'other.review.unknown'
SPEC_FIELDS = {'thickness_mm':'Þykkt (mm)', 'width_mm':'Breidd (mm)', 'length_mm':'Lengd (mm)',
               'strength_class':'Styrkleikaflokkur', 'treatment':'Yfirborðsmeðhöndlun',
               'material':'Efni / viðartegund', 'standard':'Staðall', 'diameter_mm':'Þvermál (mm)', 'nominal_size':'Nafnstærð (DN)', 'pressure_class':'Þrýstiflokkur'}
NUMERIC = {'thickness_mm','width_mm','length_mm','diameter_mm'}
LEGACY = {
 'Borar og snittvörur':'tools.drilling.unspecified', 'Skurðar- og slípivörur':'tools.cutting.unspecified',
 'Handverkfæri og mælitæki':'tools.hand.unspecified', 'Vélar og rafmagnsverkfæri':'tools.power.power',
 'Suðubúnaður og suðuvörur':'tools.welding.welding','Vinnufatnaður og öryggi':'safety.review.unknown',
 'Þéttingar og pakkningar':'fasteners.seals.unspecified','Slöngur, barkar og tengi':'fluid.review.unknown',
 'Lokar og lagnaefni':'plumbing.review.unknown','Drifbúnaður, dælur og legur':'drive.review.unknown',
 'Efnavörur og smurefni':'chemicals.review.unknown','Festingar og skrúfur':'fasteners.review.unknown',
 'Rafbúnaður og lýsing':'electrical.review.unknown','Geymsla og skipulag':'storage.storage.storage',
 'Rekstrarvörur og hreinlæti':'consumables.consumables.consumables','Hífing, keðjur og veiðarfæri':'lifting.review.unknown',
 'Véla- og kerruhlutir':'drive.parts.parts','Málning og yfirborð':'chemicals.review.unknown',
 'Garður og útisvæði':'garden.garden.garden','Byggingarefni':'building.review.unknown',
 'Leikföng og módel':'toys.toys.toys','Hreinlætistæki og baðbúnaður':'plumbing.sanitary.sanitary',
 'Stigar og vinnupallar':'tools.access.access','Annað og óflokkað':UNKNOWN}
# Legacy name rules preserve coverage while canonical IDs eliminate duplicate categories.
OLD_RULES = json.loads((ROOT/'seeds/legacy-category-rules.json').read_text(encoding='utf-8'))


def norm(v):
    return ''.join(c for c in unicodedata.normalize('NFD', str(v or '').lower()) if not unicodedata.combining(c)).replace('ð','d').replace('þ','th').replace('æ','ae').replace('×','x').replace(',','.')

# Accessory/tool nouns are resolved before any material named as an application.
PRIORITY = [
 ('tools.hand.hand',r'afeinangr|steypuskaf'),
 ('tools.power.power',r'steypuvibr'),
 ('garden.garden.garden',r'einangrari|einangrar|hringeinangr|bordaeinangr'),
 ('electrical.review.unknown',r'einangrunarlimband|einangrunarband'),
 ('safety.protection.protection',r'einangrunarplastur|festipunkt'),
 ('tools.cutting.sawblades',r'sagarblad|sagarblod|multiblad|multiblod|sverdsagarblad'),
 ('tools.cutting.abrasives',r'slipisk|skurdarsk|slipiband|slipibelt|fraesitonn|fraesitenn|sandpapp'),
 ('tools.power.power',r'borvel|skrufvel|fraesari|gifsfraesar|slipivel|slipirokk|\b(?:stingsog|hjolsog|sverdsog|butsog)\b.*\d+\s*v\b'),
 ('tools.hand.hand',r'skrufbit|gifsbiti|bitasett|bitahald|kanthefill|raspur|skrufjarn'),
 ('fasteners.screws.screws',r'skruf(?:a|ur|um|na|usett)|gifss?skruf'),
 ('tools.drilling.drills',r'(?:stal|tre|stein|mur|dosa|flisa|gler|demants)?bor(?:ar|asett)?\b'),
 ('tools.drilling.taps',r'snittapp|snittbakk|snittapi'),
]
RULES = [
 ('building.timber.lvl',r'\blvl\b'),('building.timber.glulam',r'limtre|limtr[eé]'),
 ('building.timber.decking',r'pallaefni|pallabord|pallafjal|pallatim'),
 ('building.timber.cladding',r'timburklaedning|utikaedning.*tre|ut(h)?usklaedning.*(?:timbur|fura)|klaedning.*(?:fura|greni|lerki)'),
 ('building.timber.mouldings',r'fotlist|loftlist|kverklist|ger(e|a)tt|timburlist|\blistar\b.*(?:fura|greni|eik)'),
 ('building.timber.treated',r'gagnvar(?:id|inn|dar|dir).*timbur|timbur.*gagnvar'),
 ('building.timber.structural',r'burdarvirkistimbur|burdartimbur|(?:timbur|greni|fura).*\bc(?:14|16|18|20|22|24|27|30|35|40)\b'),
 ('building.timber.unspecified',r'\btimbur\b'),
 ('building.boards.plywood',r'krossvid'),('building.boards.osb',r'\bosb\b'),('building.boards.mdf',r'\bmdf\b'),
 ('building.boards.gypsum',r'gifsplat|gipsplat'),('building.boards.chipboard',r'sponaplat'),
 ('building.insulation.wool',r'steinull|glerull'),('building.insulation.foam',r'fraudplast|einangrunarplat'),
 ('building.roof.membranes',r'thakdukur|thakpapp'),('building.roof.roofing',r'thakplat|thakjarn|thakstein'),
 ('building.cladding.panels',r'klaedningarplat'),('building.openings.doors',r'\bhurd(?:ir)?\b'),
 ('building.openings.windows',r'\bglugg(?:i|ar)\b'),('building.concrete.concrete',r'\bsement\b|\bsteypa\b'),
 ('building.concrete.mortar',r'\bmurefni\b|\bmurbland'),
 ('metals.reinforcement.rebar',r'steypustyrktar|kambstal'),('metals.profiles.profiles',r'stalprofil|malmprofil|alprofil'),
 ('metals.sheets.sheets',r'stalplat|malmplat|alplat'),('metals.tubes.tubes',r'smidajarnsror|burdarror'),('metals.grating.grating',r'ristagolf'),
 ('plumbing.fittings.flanges',r'flans'),('plumbing.valves.valves',r'\blok[ai]r?\b|kululok'),
 ('plumbing.drains.drains',r'nidurfall|nidurfoll'),('plumbing.mounts.mounts',r'lagnafest|rorklemm'),
 ('plumbing.pipes.pipes',r'lagnaror|\bror\b'),('plumbing.fittings.fittings',r'lagnatengi|nippl'),
 ('fluid.pumps.pumps',r'dael[a-u]'),('fluid.couplings.couplings',r'hradtengi|slongutengi|glussatengi'),
 ('fluid.hoses.hoses',r'slanga|slong|\bbarki\b|\bbarkar\b'),('fluid.filters.filters',r'oliusia|loftsia|glussasia'),
 ('fluid.parts.parts',r'thrystijafn|loftpress|glussabun'),
 ('controls.sensors.sensors',r'skynjar'),('controls.controllers.controllers',r'\bplc\b|styring'),
 ('controls.meters.meters',r'thrystimael|rennslismael|hitamael'),('controls.connections.connections',r'styritengi'),
 ('electrical.trays.trays',r'kapalbakk'),('electrical.cables.cables',r'kapall|kaplar|streng'),
 ('electrical.sockets.sockets',r'\bteng(?:ill|lar)\b|\brof[ai]r?\b'),('electrical.panels.panels',r'toflubun|tofluvir'),
 ('electrical.lighting.lighting',r'ljos|lysing'),('electrical.power.power',r'rafhlod|aflgjaf|hledslut'),
 ('fasteners.seals.orings',r'o-hring|\boring\b'),('fasteners.seals.gaskets',r'pakkning|pakkdos|thettihring'),
 ('fasteners.bolts.bolts',r'bolti|boltar'),('fasteners.bolts.nuts',r'\braer\b|\bro\b'),
 ('fasteners.washers.washers',r'\bskinn(?:a|ur)\b'),('fasteners.anchors.anchors',r'akkeri|festing|splitti'),
 ('fasteners.nails.nails',r'naglar|hnod|hefti'),
 ('tools.hand.measure',r'malband|hallamal|maelistika|skidmal'),
 ('chemicals.paint.primer',r'grunnmalning|grunnur.*mal'),('chemicals.paint.paint',r'\bmalning\b'),
 ('chemicals.adhesives.glue',r'\blim\b|epoxy'),('chemicals.adhesives.sealants',r'kitti|fuguefni|silicon|silikon|thettiefni'),
 ('chemicals.lubricants.lubricants',r'smurefni|smurfeiti|\bolia\b|\boliur\b|\bglussi\b'),
 ('chemicals.cleaners.cleaners',r'hreinsiefni|hreinsir|rydhreinsi|rydloys'),('chemicals.accessories.accessories',r'pensl|malningarrull|malningarkef'),
 ('safety.gloves.gloves',r'hansk|vettling'),('safety.shoes.shoes',r'vinnusk|oryggissk|stigvel'),
 ('safety.helmets.helmets',r'hjalm'),('safety.fall.fall',r'fallvarn'),
 ('safety.protection.protection',r'heyrnar|ondunar|augnhlif|oryggisgler'),('safety.clothes.clothes',r'jakk|buxur|samfest|vinnufat|hufa|peys|skyrt|\bbolir\b|ulp'),
 ('lifting.slings.slings',r'stroff'),('lifting.chains.shackles',r'sjakkl'),('lifting.chains.chains',r'kedj'),
 ('lifting.carts.pallet',r'brettatjakk'),('lifting.carts.carts',r'flutningsvagn|verkfaeravagn'),('lifting.hoists.hoists',r'\btalia\b|lyftibun|hifibun'),
 ('aquaculture.nets.nets',r'eldisnet'),('aquaculture.scoops.scoops',r'\bhaf(?:ur|ar)\b'),
 ('aquaculture.tanks.tanks',r'karabunadur|eldiskar'),('aquaculture.parts.parts',r'eldiskerfi'),
 ('fishing.fishing.fishing',r'veidarf|handfaer|bauj'),('drive.drive.drive',r'\blega\b|\blegur\b|kulegur|drifreim|girkass|drifbun')]


def detect(text):
    n = norm(re.split(r'\s+(?:fyrir|f/|f\.|með|m/)\s*', str(text or ''), maxsplit=1, flags=re.I)[0])
    # Avoid treating measurements of a machine/accessory as dimensions of its material.
    for leaf, pattern in PRIORITY + RULES:
        if leaf=='building.timber.treated' and re.search(r'ogagnvar|ekki gagnvar',n):continue
        if re.search(pattern,n):return leaf
    for label, pattern in OLD_RULES:
        if label=='Byggingarefni':continue
        if re.search(pattern,n):return LEGACY[label]
    return None


def classify(o, override):
    leaf = override.get('classification_id')
    source, evidence = 'Handvirkt val', 'Staðfest af notanda'
    if not leaf:
        manual=o.get('manual_category')
        if manual:
            leaf=LEGACY.get(manual) or next((k for k,p in LEAVES.items() if ' → '.join(p)==manual),UNKNOWN)
            evidence=manual
        else:
            leaf=detect(o.get('name'));source='Vöruheiti';evidence=o.get('name','')
            if not leaf:
                desc=str(o.get('description') or '')[:600]
                intro=re.split(r'(?<=[.!?])\s|\n|\b(?:Notkun|Hentar|Applications)\b',desc,maxsplit=1)[0]
                leaf=detect(intro);source='Upphaf birgjalýsingar';evidence=intro
            if not leaf:
                cats=[o.get('category',''),o.get('subcategory',''),*(o.get('supplier_categories') or [])]
                hits={LEGACY.get(c) or detect(c) for c in cats};hits.discard(None)
                if len(hits)==1:leaf=hits.pop();source='Flokkur birgis';evidence=' → '.join(cats)
                else:leaf=UNKNOWN;source='Til yfirferðar';evidence='Flokkunarupplýsingar vantar eða eru ósamhljóða.'
    leaf=leaf if leaf in LEAVES else UNKNOWN
    review=leaf.endswith(('.unspecified','.unknown'))
    return {'id':leaf,'path':LEAVES[leaf],'source':source,'evidence':evidence[:600],
            'needs_review':review,'manual':bool(override.get('classification_id') or o.get('manual_category'))}


def specifications(o, classification, override):
    values={};evidence={};conflicts=[]
    def put(k,v,src):
        if k in conflicts:return
        if k in values and values[k]!=v:
            values.pop(k,None);evidence.pop(k,None);conflicts.append(k);return
        values[k]=v;evidence[k]=src
    if classification['id'].startswith(('building.timber.','building.boards.')):
        # Only explicit units/labels: bare 45x95 is intentionally left unknown.
        for label,raw in [('Vöruheiti',o.get('name','')),('Birgjalýsing',o.get('description',''))]:
            n=norm(raw)
            for m in re.finditer(r'(?<![\d.])(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)(?:\s*x\s*(\d+(?:\.\d+)?))?\s*mm\b',n):
                for key,v in zip(('thickness_mm','width_mm','length_mm'),m.groups()):
                    if v:put(key,float(v),label+': '+m[0]+' (þykkt × breidd × lengd)')
            for key,word in [('thickness_mm','thykkt'),('width_mm','breidd'),('length_mm','lengd')]:
                for m in re.finditer(r'\b'+word+r'\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(mm|cm|m)\b',n):
                    put(key,float(m[1])*{'mm':1,'cm':10,'m':1000}[m[2]],label+': '+m[0])
            for m in re.finditer(r'\b(?:c(?:14|16|18|20|22|24|27|30|35|40)|gl\d{2}[ch]?)\b',n):put('strength_class',m[0].upper(),label+': '+m[0])
            # Negations/alternative finishes are not silently treated as positive evidence.
            if re.search(r'\bogagnvar|ekki gagnvar|og ekki',n):
                if 'gagnvar' in n:put('treatment','Ógagnvarið',label)
            elif 'gagnvar' in n:put('treatment','Gagnvarið',label)
            for pat,value in [(r'\boheflad\b','Óheflað'),(r'\bheflad\b','Heflað'),(r'\bomalad\b','Ómálað')]:
                if re.search(pat,n):put('treatment',value,label)
            for pat,value in [(r'\bgreni\b','Greni'),(r'\bfura\b','Fura'),(r'\blerki\b','Lerki'),(r'\beik\b','Eik'),(r'\bbirki\b','Birki')]:
                if re.search(pat,n):put('material',value,label)
    if classification['id'].startswith(('plumbing.','fluid.')):
        n=norm(str(o.get('name',''))+' '+str(o.get('description','')))
        for m in re.finditer(r'\bdn\s*(\d+)\b',n):put('nominal_size','DN'+m[1],'Vöruheiti/lýsing: '+m[0])
        for m in re.finditer(r'\bpn\s*(\d+)\b',n):put('pressure_class','PN'+m[1],'Vöruheiti/lýsing: '+m[0])
        for m in re.finditer(r'thvermal\s*[:=]?\s*(\d+(?:\.\d+)?)\s*mm',n):put('diameter_mm',float(m[1]),'Vöruheiti/lýsing: '+m[0])
    for prop in (o.get('technical_properties') or [])[:50]:
        if not isinstance(prop,dict):continue
        name=norm(prop.get('name'));raw=norm(prop.get('value'));unit=norm(prop.get('unit'))
        for key,labels in [('thickness_mm',('thykkt','thickness')),('width_mm',('breidd','width')),('length_mm',('lengd','length')),('diameter_mm',('thvermal','diameter'))]:
            if not any(re.fullmatch(label+r'(?:\s*\(mm\))?',name) for label in labels):continue
            match=re.fullmatch(r'(\d+(?:\.\d+)?)\s*(mm|cm|m)?',raw)
            units=match[2] if match else None
            units=units or {'mmt':'mm','cmt':'cm','mtr':'m'}.get(unit,unit) or ('mm' if '(mm)' in name else '')
            if match and units in ('mm','cm','m'):
                put(key,float(match[1])*{'mm':1,'cm':10,'m':1000}[units],'Tæknigögn birgis: '+str(prop.get('name'))+' '+str(prop.get('value'))+' '+str(prop.get('unit')))
        for key,labels in [('strength_class',('styrkleikaflokkur','strength class')),('treatment',('yfirbordsmedhondlun','treatment')),('material',('efni','material')),('standard',('stadall','standard'))]:
            if name in labels and valid_spec(key,prop.get('value')):put(key,prop['value'],'Tæknigögn birgis: '+prop['name'])
    # Structured supplier fields are accepted only under these explicit, unit-bearing keys.
    supplied=o.get('specifications') or {}
    if isinstance(supplied,dict):
        for k,v in supplied.items():
            if k in SPEC_FIELDS and valid_spec(k,v):put(k,v,'Skráður tæknilegur eiginleiki frá birgi')
    for k,v in override.get('specifications',{}).items():
        if v is None:values.pop(k,None);evidence.pop(k,None)
        else:values[k]=v;evidence[k]='Handvirkt staðfest af notanda'
        if k in conflicts:conflicts.remove(k)
    missing=[]
    if classification['id'].startswith('building.timber.'):
        missing=[k for k in ('thickness_mm','width_mm','length_mm','strength_class','treatment') if k not in values]
    elif classification['id'].startswith('building.boards.'):
        missing=[k for k in ('thickness_mm','width_mm','length_mm') if k not in values]
    return values,evidence,conflicts,missing


def valid_spec(k,v):
    return (type(v) in (int,float) and math.isfinite(v) and 0<v<=1e7) if k in NUMERIC else (isinstance(v,str) and 0<len(v.strip())<=120)


def validate_override(data):
    leaf=data.get('classification_id','')
    if leaf and leaf not in LEAVES:raise ValueError('Veldu gildan vöruflokk, undirflokk og vörutegund.')
    specs=data.get('specifications',{})
    if not isinstance(specs,dict) or any(k not in SPEC_FIELDS or (v is not None and not valid_spec(k,v)) for k,v in specs.items()):
        raise ValueError('Ógildir eiginleikar. Mál þurfa jákvætt tölugildi í mm.')
    tags=data.get('search_tags',[])
    if not isinstance(tags,list) or len(tags)>20 or any(not isinstance(t,str) or not 0<len(t.strip())<=60 for t in tags):
        raise ValueError('Hámark 20 leitartög, 1–60 stafir hvert.')
    return {'classification_id':leaf,'specifications':specs,'search_tags':list(dict.fromkeys(t.strip() for t in tags))}


def enrich(o,override=None):
    override=override or {}
    c=classify(o,override);values,evidence,conflicts,missing=specifications(o,c,override)
    o.update(classification=c,specifications=values,specification_evidence=evidence,
             specification_conflicts=conflicts,missing_specifications=missing,
             search_tags=list(dict.fromkeys([*c['path'],*(override.get('search_tags',[]))])),
             product_enrichment=override)
    return o
