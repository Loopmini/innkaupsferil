"""Bounded BOM imports. No prices are inferred from a bill of materials."""
import csv,io,json,math,re,unicodedata,zipfile,posixpath
import xml.etree.ElementTree as ET

SPEC_FIELDS=('thickness_mm','width_mm','length_mm','strength_class','treatment','material','standard')
FIELDS=('name','quantity','unit','supplier','sku','gtin','brand','manufacturer_part')+SPEC_FIELDS
ALIASES={'name':['name','heiti','vara','lysing','vorulysing','description','item'],'quantity':['quantity','magn','qty'],'unit':['unit','eining','einingar'],'supplier':['supplier','birgir'],'sku':['sku','vorunumer','itemcode'],'gtin':['gtin','ean','strikamerki'],'brand':['brand','framleidandi'],'manufacturer_part':['manufacturerpart','framleidslunumer','mpn']}

ALIASES.update({'thickness_mm':['thicknessmm','thykktmm'],'width_mm':['widthmm','breiddmm'],'length_mm':['lengthmm','lengdmm'],'strength_class':['strengthclass','styrkleikaflokkur'],'treatment':['treatment','yfirbordsmedhondlun'],'material':['material','efni'],'standard':['standard','stadall']})

def norm(s):
 return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',str(s).replace('ð','d').replace('Ð','D').replace('þ','th').replace('Þ','Th').replace('æ','ae').replace('Æ','Ae')).encode('ascii','ignore').decode().lower().replace('ð','d'))

def xlsx_table(content):
 try:
  with zipfile.ZipFile(io.BytesIO(content)) as z:
   if len(z.infolist())>2000 or sum(i.file_size for i in z.infolist())>30_000_000:raise ValueError('Excel-skráin er of stór.')
   n={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
   shared=[]
   if 'xl/sharedStrings.xml' in z.namelist():
    shared=[''.join(si.itertext()) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',n)]
   book=ET.fromstring(z.read('xl/workbook.xml'));sheets=book.find('m:sheets',n)
   if sheets is None or not len(sheets):raise ValueError('Engin blöð í Excel-skrá.')
   sheet=sheets[0];rid=sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
   rel=next((x for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels')) if x.get('Id')==rid),None)
   if rel is None or rel.get('TargetMode')=='External':raise ValueError('Ógilt Excel-blað.')
   target=rel.get('Target','');path=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
   if not path.startswith('xl/'):raise ValueError('Ógild slóð Excel-blaðs.')
   rows=[]
   for row in ET.fromstring(z.read(path)).findall('.//m:sheetData/m:row',n):
    values={}
    for cell in row.findall('m:c',n):
     letters=re.match('[A-Z]+',cell.get('r',''))
     if not letters:continue
     col=0
     for letter in letters[0]:col=col*26+ord(letter)-64
     if col>30:continue
     if cell.find('m:f',n) is not None:raise ValueError('Excel inniheldur formúlur. Afritaðu gildin í nýtt blað og vistaðu án formúla.')
     value=cell.find('m:v',n);text=value.text if value is not None else ''
     if cell.get('t')=='s':text=shared[int(text)]
     elif cell.get('t')=='inlineStr':text=''.join(cell.find('m:is',n).itertext())
     values[col-1]=text or ''
    if values:rows.append([values.get(i,'') for i in range(max(values)+1)])
    if len(rows)>501:raise ValueError('Hámark 500 BOM-línur.')
   return rows,sheet.get('name','Fyrsta blað')
 except (zipfile.BadZipFile,ET.ParseError,KeyError,IndexError,StopIteration) as e:
  raise ValueError('Ekki tókst að lesa XLSX. Prófaðu CSV eða límdu úr Excel.') from e

def parse(content,filename='bom.csv'):
 sheet='CSV / innlímd tafla'
 if filename.lower().endswith('.xlsx'):table,sheet=xlsx_table(content)
 else:
  try:text=content.decode('utf-8-sig')
  except UnicodeDecodeError as e:raise ValueError('Vistaðu CSV sem UTF-8.') from e
  try:delimiter=csv.Sniffer().sniff(text[:4096],delimiters=',;\t').delimiter
  except csv.Error:delimiter='\t' if '\t' in text else ','
  table=list(csv.reader(io.StringIO(text),delimiter=delimiter))
 table=[r for r in table if any(str(v).strip() for v in r)]
 if len(table)<2:raise ValueError('Haus og að minnsta kosti ein vörulína þurfa að fylgja.')
 if len(table)>501:raise ValueError('Hámark 500 BOM-línur.')
 headers=[norm(h) for h in table[0]];mapping={}
 for field,aliases in ALIASES.items():
  matches=[i for i,h in enumerate(headers) if h in aliases]
  if len(matches)>1:raise ValueError(f'Tvítekinn dálkur: {field}')
  if matches:mapping[field]=matches[0]
 if not {'name','quantity','unit'}<=mapping.keys():raise ValueError('Dálka vantar: heiti, magn og eining. Notaðu sniðmátið.')
 combined={}
 for index,row in enumerate(table[1:],2):
  r={f:str(row[mapping[f]]).strip() if f in mapping and mapping[f]<len(row) else '' for f in FIELDS}
  if not r['name'] or len(r['name'])>400:raise ValueError(f'Lína {index}: heiti vantar eða er of langt.')
  try:q=float(r['quantity'].replace(',','.'))
  except ValueError:raise ValueError(f'Lína {index}: ógilt magn.')
  if not math.isfinite(q) or not 0<q<=1e9:raise ValueError(f'Lína {index}: magn þarf að vera jákvætt.')
  unit=norm(r['unit']);r['unit']={'st':'stk','pcs':'stk','ea':'stk','meter':'m','metrar':'m','litri':'l'}.get(unit,unit)
  if r['unit'] not in ('stk','m','m2','m3','kg','l'):raise ValueError(f'Lína {index}: eining þarf stk, m, m2, m3, kg eða l.')
  if any(len(r[k])>200 for k in FIELDS if k not in ('name','quantity')):raise ValueError(f'Lína {index}: gildi of langt.')
  if r['gtin'] and (not r['gtin'].isdigit() or len(r['gtin']) not in (8,12,13,14)):raise ValueError(f'Lína {index}: GTIN þarf að vera 8–14 tölustafir án bila.')
  r['quantity']=q;r['source_rows']=[index]
  key=tuple(r[k] for k in FIELDS if k!='quantity')
  if key in combined:
   combined[key]['quantity']+=q;combined[key]['source_rows'].append(index)
   if combined[key]['quantity']>1e9:raise ValueError('Samanlagt magn er of hátt.')
  else:combined[key]=r
 rows=list(combined.values())
 for i,r in enumerate(rows):
  r['line_id']=str(i+1);specs={}
  for key in SPEC_FIELDS:
   value=r.pop(key)
   if not value:continue
   if key.endswith('_mm'):
    try:value=float(value.replace(',','.'))
    except ValueError:raise ValueError('Mál í BOM þurfa tölur í mm.')
    if not math.isfinite(value) or value<=0:raise ValueError('Mál í BOM þurfa jákvæðar tölur í mm.')
   specs[key]=value
  if specs:r['specifications']=specs
 return rows,sheet
