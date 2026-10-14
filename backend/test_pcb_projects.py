import io,json,os,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.test_checkout import FakeProvider
from backend.pcb_projects import MAX_FILE

ADDRESS={'name':'Test Owner','email':'owner@example.com','phone':'2025550100','address1':'123 Example Street','address2':'','city':'New York','region':'NY','zip':'10001','country':'US'}
def gerber():
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w') as z:z.writestr('board.gtl','G04 Synthetic test fixture*');z.writestr('board.drl','M48')
 return b.getvalue()
class PcbWizardTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.client=TestClient(create_app(database=self.root/'orders.db',private_dir=self.root,manifest={},provider=FakeProvider(),catalog_loader=lambda:{'products':[]},enabled=False,worker_enabled=False))
 def request(self,method,path,body=None,content=None,login='lionsarmor'):
  response=type('Response',(),{'raise_for_status':lambda _:None,'json':lambda _:{'login':login}})()
  with patch('backend.app.httpx.get',return_value=response):return self.client.request(method,'/admin/pcb'+path,json=body,content=content,headers={'authorization':'Bearer test-owner'})
 def create(self,**changes):
  response=self.request('POST','/projects',{'name':'Prototype','revision':'a','quantity':5,'build':'assembled','assemblyType':'smt','shipMode':'prototype','prototypeAddress':ADDRESS,**changes});self.assertEqual(response.status_code,200,response.text);return response.json()
 def upload(self,p,slot,name,content):return self.request('POST','/projects/'+p['id']+'/files/'+slot+'?name='+name,content=content)
 def test_owner_only_durable_uploads_and_private_export(self):
  self.assertEqual(self.client.get('/admin/pcb/projects').status_code,401)
  self.assertEqual(self.request('GET','/projects',login='other').status_code,403)
  p=self.create();self.assertFalse(p['ready']);self.assertEqual(self.request('POST','/projects/'+p['id']+'/export',{}).status_code,409)
  uploaded_gerber=gerber()
  for slot,name,data in [('gerber','board.zip',uploaded_gerber),('bom','bom.csv',b'Reference,MPN,Quantity\nR1,TEST,1'),('placement','parts.pos',b'Ref X Y Rotation Side\nR1 1 2 0 top')]:
   r=self.upload(p,slot,name,data);self.assertEqual(r.status_code,200,r.text)
  p=r.json();self.assertTrue(p['ready']);folder=self.root/'pcb-projects'/p['id'];self.assertEqual(folder.stat().st_mode&0o777,0o700)
  for f in folder.iterdir():self.assertEqual(f.stat().st_mode&0o777,0o600)
  packet=self.request('POST','/projects/'+p['id']+'/export',{});self.assertEqual(packet.status_code,200);self.assertEqual(packet.headers['cache-control'],'no-store')
  with zipfile.ZipFile(io.BytesIO(packet.content)) as z:
   m=json.loads(z.read('PROJECT_MANIFEST.json'));self.assertEqual(m['fulfillment']['address'],ADDRESS);self.assertEqual(m['automation'],{'submit':False,'pay':False});self.assertEqual(z.read('gerber/board.zip'),uploaded_gerber);self.assertNotIn('stored',json.dumps(m))
  self.assertFalse(list((self.root/'pcb-projects').glob('.packet-*')))
  self.assertEqual(len(self.request('GET','/projects').json()['projects']),1)
 def test_diy_and_through_hole_only_require_the_correct_files(self):
  p=self.create(build='diy',shipMode='customer',prototypeAddress=None);r=self.upload(p,'gerber','board.zip',gerber());self.assertTrue(r.json()['ready']);self.assertEqual(r.json()['missing'],[])
  with zipfile.ZipFile(io.BytesIO(self.request('POST','/projects/'+p['id']+'/export',{}).content)) as z:
   m=json.loads(z.read('PROJECT_MANIFEST.json'));self.assertFalse(m['assembly']['requested']);self.assertIsNone(m['assembly']['componentSupply']);self.assertNotIn('prototypeAddress',m['project']);self.assertIsNone(m['fulfillment']['address']);self.assertEqual(m['fulfillment']['customerAddressSource'],'verified-paid-order')
  p=self.create(assemblyType='tht');self.upload(p,'gerber','board.zip',gerber());r=self.upload(p,'bom','bom.csv',b'Reference,MPN\nR1,TEST');self.assertTrue(r.json()['ready'])
 def test_bad_uploads_paths_sizes_and_replacements(self):
  p=self.create(build='diy');self.assertEqual(self.upload(p,'gerber','board.zip',b'not a zip').status_code,400)
  self.assertEqual(self.upload(p,'gerber','..%2Fboard.zip',gerber()).status_code,400)
  self.assertEqual(self.upload(p,'unknown','board.zip',gerber()).status_code,400)
  self.assertEqual(self.upload(p,'gerber','board.zip',b'x'*(MAX_FILE+1)).status_code,413)
  self.assertFalse(list((self.root/'pcb-projects'/p['id']).glob('.upload-*')))
  first=self.upload(p,'gerber','board.zip',gerber()).json()['files']['gerber']['stored'];self.upload(p,'gerber','new-board.zip',gerber());self.assertFalse((self.root/'pcb-projects'/p['id']/first).exists())
  self.assertEqual(self.request('POST','/projects/not-a-project/files/gerber?name=board.zip',content=gerber()).status_code,404)
 def test_prototype_address_and_multiline_notes_are_private(self):
  self.assertEqual(self.request('POST','/prototype-address',ADDRESS).status_code,200)
  self.assertEqual(self.request('GET','/projects').json()['prototypeAddress'],ADDRESS)
  self.assertEqual((self.root/'pcb-projects/prototype-address.json').stat().st_mode&0o777,0o600)
  p=self.create(notes='Flash firmware.\nTest USB.',prototypeAddress=None);self.assertIn('Your prototype delivery address',p['missing']);self.assertIn('\n',p['notes'])
