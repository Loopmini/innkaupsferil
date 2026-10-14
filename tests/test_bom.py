import io,zipfile,unittest
import bom
class BOMTest(unittest.TestCase):
 def test_icelandic_paste_and_combine(self):
  rows,_=bom.parse('heiti\tmagn\teining\tframleiðandi\nStálbor 5mm\t2,5\tstk\tTest\nStálbor 5mm\t3\tstk\tTest'.encode())
  self.assertEqual(len(rows),1);self.assertEqual(rows[0]['quantity'],5.5);self.assertEqual(rows[0]['brand'],'Test');self.assertEqual(rows[0]['source_rows'],[2,3])
 def test_leading_zero_sku_preserved(self):
  rows,_=bom.parse(b'name,quantity,unit,sku\nTest,2,stk,00123\n');self.assertEqual(rows[0]['sku'],'00123')
 def test_reject_invalid_or_missing_quantities_and_units(self):
  for value in ['NaN','-1','0','1.000,00']:
   with self.subTest(value=value),self.assertRaises(ValueError):bom.parse(f'name,quantity,unit\nTest,"{value}",stk'.encode())
  with self.assertRaises(ValueError):bom.parse(b'name,quantity\nTest,1')
  with self.assertRaises(ValueError):bom.parse(b'name,quantity,unit\nTest,1,box')
 def excel(self,formula=False):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:
   z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="BOM" r:id="rId1"/></sheets></workbook>')
   z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
   rows='<row>'+''.join(f'<c r="{c}1" t="inlineStr"><is><t>{v}</t></is></c>' for c,v in zip('ABC',['heiti','magn','eining']))+'</row>'
   rows+='<row><c r="A2" t="inlineStr"><is><t>Stálbor</t></is></c><c r="B2">'+('<f>1+1</f>' if formula else '')+'<v>2</v></c><c r="C2" t="inlineStr"><is><t>stk</t></is></c></row>'
   z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+rows+'</sheetData></worksheet>')
  return b.getvalue()
 def test_xlsx_values(self):
  rows,sheet=bom.parse(self.excel(),'bom.xlsx');self.assertEqual(rows[0]['quantity'],2);self.assertEqual(sheet,'BOM')
 def test_xlsx_formula_not_read_as_stale_value(self):
  with self.assertRaises(ValueError):bom.parse(self.excel(True),'bom.xlsx')
