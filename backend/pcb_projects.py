"""Owner-only electronics manufacturing packages. No supplier requests or payment."""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import threading
import time
from uuid import UUID,uuid4
import zipfile
from fastapi import HTTPException,Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

MAX_FILE=20*1024*1024
MAX_PROJECT=128*1024*1024
SLOTS={
 'gerber':{'label':'Board manufacturing ZIP','extensions':['.zip']},
 'bom':{'label':'Parts list (BOM)','extensions':['.csv','.xls','.xlsx']},
 'placement':{'label':'Component positions','extensions':['.csv','.txt','.pos','.xls','.xlsx','.zip']},
 'drawing':{'label':'Assembly drawing / instructions','extensions':['.pdf','.txt','.zip','.png','.jpg','.jpeg']},
 'firmware':{'label':'Firmware / test files','extensions':['.bin','.hex','.uf2','.zip','.pdf','.txt']},
 'enclosure':{'label':'Enclosure / box build','extensions':['.step','.stp','.stl','.zip','.pdf']},
}

def text(value,maximum=120,required=False,multiline=False):
 if not isinstance(value,str) or len(value)>maximum or any(ord(c)<32 and not (multiline and c in "\n\t") for c in value):raise HTTPException(400,'Check the project fields.')
 value=value.strip()
 if required and not value:raise HTTPException(400,'Give the project a name.')
 return value

def address(value):
 if not isinstance(value,dict):raise HTTPException(400,'Enter your prototype delivery address.')
 result={k:text(value.get(k,''),254 if k=='email' else 150) for k in ['name','email','phone','address1','address2','city','region','zip','country']}
 if not all(result[k] for k in ['name','email','address1','city','zip','country']) or not re.fullmatch(r'[A-Z]{2}',result['country']) or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',result['email']):raise HTTPException(400,'Complete your name, email, street, city, postal code and two-letter country code.')
 return result

def metadata(body):
 if not isinstance(body,dict):raise HTTPException(400,'Enter the project details.')
 value={'name':text(body.get('name',''),120,True),'revision':text(body.get('revision','1'),40,True),'productId':text(body.get('productId',''),100),'notes':text(body.get('notes',''),4000,multiline=True),'shippingNotes':text(body.get('shippingNotes',''),2000,multiline=True)}
 for field,choices,default in [('build',['diy','assembled'],'assembled'),('assemblyType',['smt','tht','mixed'],'mixed'),('componentSupply',['turnkey','partial','consigned'],'turnkey'),('shipMode',['prototype','customer'],'prototype')]:
  selected=body.get(field,default)
  if selected not in choices:raise HTTPException(400,'Choose a build and shipping option.')
  value[field]=selected
 for field,default,minimum,maximum in [('quantity',5,1,10000),('layers',2,1,32)]:
  n=body.get(field,default)
  if type(n) is not int or not minimum<=n<=maximum:raise HTTPException(400,'Check board quantity and layers.')
  value[field]=n
 for field in ['widthMm','heightMm','thicknessMm']:
  n=body.get(field,None)
  if n is not None and (type(n) not in {int,float} or not 0<n<=1000):raise HTTPException(400,'Board dimensions must be positive millimetres, or left blank.')
  value[field]=n
 value['prototypeAddress']=address(body.get('prototypeAddress')) if body.get('prototypeAddress') else None
 return value


class PcbProjects:
 def __init__(self,directory):
  self.root=Path(directory);self.root.mkdir(parents=True,exist_ok=True,mode=0o700);self.lock=threading.RLock()
 def folder(self,ident):
  try:
   if str(UUID(ident))!=ident:raise ValueError()
  except (ValueError,TypeError,AttributeError):raise HTTPException(404,'Project not found.') from None
  return self.root/ident
 def write(self,path,data):
  temp=path.with_name('.saving-'+secrets.token_hex(16))
  try:
   with open(temp,'x',encoding='utf-8') as f:
    os.chmod(temp,0o600);json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
   os.replace(temp,path)
  finally:temp.unlink(missing_ok=True)
 def read(self,ident):
  try:return json.loads((self.folder(ident)/'project.json').read_text())
  except (OSError,ValueError):raise HTTPException(404,'Project not found.') from None
 def state(self,project):
  files=project['files'];missing=[]
  if not files.get('gerber'):missing.append('Board manufacturing ZIP')
  if project['build']=='assembled':
   if not files.get('bom'):missing.append('Parts list (BOM)')
   if project['assemblyType']!='tht' and not files.get('placement'):missing.append('Component positions')
  if project['shipMode']=='prototype' and not project.get('prototypeAddress'):missing.append('Your prototype delivery address')
  return {**project,'missing':missing,'ready':not missing,'status':'Ready for engineering review' if not missing else 'Draft'}
 def listing(self):
  with self.lock:
   projects=[self.state(json.loads(p.read_text())) for p in self.root.glob('*/project.json')]
   settings=self.root/'prototype-address.json'
   return {'projects':sorted(projects,key=lambda p:p['updated'],reverse=True),'prototypeAddress':json.loads(settings.read_text()) if settings.exists() else None,'slots':SLOTS,'maxFileBytes':MAX_FILE,'integration':{'provider':'pcbway','connected':False,'submissionEnabled':False,'paymentEnabled':False}}
 def save(self,body,ident=None):
  data=metadata(body)
  with self.lock:
   if ident:
    old=self.read(ident);data.update(id=ident,created=old['created'],files=old['files'])
   else:
    ident=str(uuid4());self.folder(ident).mkdir(mode=0o700);data.update(id=ident,created=int(time.time()),files={})
   data['updated']=int(time.time());self.write(self.folder(ident)/'project.json',data)
   return self.state(data)
 async def upload(self,ident,slot,name,request):
  folder=self.folder(ident);self.read(ident)
  if slot not in SLOTS or not re.fullmatch(r'[\w .()+-]{1,150}',name,re.ASCII) or name.startswith('.') or Path(name).suffix.lower() not in SLOTS[slot]['extensions']:raise HTTPException(400,'Choose a supported file with a simple filename.')
  temporary=folder/('.upload-'+secrets.token_hex(16));size=0;digest=hashlib.sha256()
  try:
   with open(temporary,'xb') as output:
    os.chmod(temporary,0o600)
    async for chunk in request.stream():
     size+=len(chunk)
     if size>MAX_FILE:raise HTTPException(413,'Each file must be 20 MB or smaller.')
     digest.update(chunk);output.write(chunk)
    output.flush();os.fsync(output.fileno())
   if not size:raise HTTPException(400,'That file is empty.')
   if Path(name).suffix.lower() in {'.zip','.xlsx'}:
    try:
     with zipfile.ZipFile(temporary) as z:
      if not z.infolist() or len(z.infolist())>5000 or sum(i.file_size for i in z.infolist())>MAX_PROJECT or any(i.flag_bits&1 or i.filename.startswith(('/', '\\')) or '..' in i.filename.replace('\\','/').split('/') for i in z.infolist()):raise ValueError()
    except (zipfile.BadZipFile,ValueError):raise HTTPException(400,'Use a valid, unencrypted ZIP/Excel file without unsafe paths (maximum expanded size 128 MB).') from None
   with self.lock:
    project=self.read(ident)
    if sum(v['size'] for k,v in project['files'].items() if k!=slot)+size>MAX_PROJECT:raise HTTPException(413,'This project is too large. Keep its files below 128 MB total.')
    filename=secrets.token_hex(16)+Path(name).suffix.lower();destination=folder/filename;os.replace(temporary,destination)
    previous=project['files'].get(slot);project['files'][slot]={'name':name,'stored':filename,'size':size,'sha256':digest.hexdigest(),'uploaded':int(time.time())};project['updated']=int(time.time())
    try:self.write(folder/'project.json',project)
    except Exception:destination.unlink(missing_ok=True);raise
    if previous:(folder/previous['stored']).unlink(missing_ok=True)
   return self.state(project)
  finally:temporary.unlink(missing_ok=True)
 def export(self,ident):
  with self.lock:
   project=self.state(self.read(ident))
   if not project['ready']:raise HTTPException(409,'Still needed: '+', '.join(project['missing']))
   output=self.root/('.packet-'+secrets.token_hex(16)+'.zip')
   manifest={'schemaVersion':1,'supplier':'pcbway','project':{k:v for k,v in project.items() if k not in {'files','prototypeAddress'}},'assembly':{'requested':project['build']=='assembled','componentSupply':project['componentSupply'] if project['build']=='assembled' else None,'style':project['assemblyType'] if project['build']=='assembled' else None},'files':{},'fulfillment':{'mode':project['shipMode'],'address':project['prototypeAddress'] if project['shipMode']=='prototype' else None,'customerAddressSource':'verified-paid-order' if project['shipMode']=='customer' else None},'automation':{'submit':False,'pay':False},'instructions':'Engineering review package only. Confirm files, assembly scope, quote, shipping and billing before manufacturing. Customer dispatch must use the verified paid order address.'}
   try:
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as z:
     os.chmod(output,0o600)
     for slot,info in project['files'].items():
      source=self.folder(ident)/info['stored']
      if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=info['sha256']:raise HTTPException(409,'A project file is missing or changed. Upload it again.')
      filename=slot+'/'+info['name'];z.write(source,filename);manifest['files'][slot]={k:v for k,v in info.items() if k!='stored'};manifest['files'][slot]['path']=filename
     z.writestr('PROJECT_MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
   except Exception:output.unlink(missing_ok=True);raise
   return output


def register_pcb_projects(app,require_admin,directory):
 projects=PcbProjects(directory)
 @app.get('/admin/pcb/projects')
 def listing(request:Request):
  require_admin(request);return projects.listing()
 @app.post('/admin/pcb/projects')
 def create(request:Request,body:dict):
  require_admin(request);return projects.save(body)
 @app.post('/admin/pcb/prototype-address')
 def save_address(request:Request,body:dict):
  require_admin(request);data=address(body)
  with projects.lock:projects.write(projects.root/'prototype-address.json',data)
  return {'saved':True}
 @app.post('/admin/pcb/projects/{ident}')
 def save(ident:str,request:Request,body:dict):
  require_admin(request);return projects.save(body,ident)
 @app.post('/admin/pcb/projects/{ident}/files/{slot}')
 async def upload(ident:str,slot:str,request:Request,name:str=''):
  require_admin(request);return await projects.upload(ident,slot,name,request)
 @app.post('/admin/pcb/projects/{ident}/export')
 def export(ident:str,request:Request):
  require_admin(request);path=projects.export(ident)
  return FileResponse(path,media_type='application/zip',filename='RODDY-PCB-'+ident+'.zip',background=BackgroundTask(path.unlink,missing_ok=True))
 return projects
