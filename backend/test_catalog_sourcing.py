import copy,json,tempfile,unittest
from pathlib import Path
from fastapi import HTTPException
from backend.catalog_sourcing import CatalogSourcing,public_catalog

class PrivateCatalogTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.store=CatalogSourcing(Path(self.temp.name)/'source.json')
  self.catalog={'products':[{'id':'keyboard','name':'Keyboard','price':99.99,'supplier':{'provider':'aliexpress','supplierSku':'private-listing','variantId':'private-sku','fulfillment':'manual'}},{'id':'hoodie','name':'Hoodie','price':49.99,'merch':{'provider':'printify','productId':'private-product','shopId':123,'shippingCountries':['US'],'shippingProfiles':[{'variantIds':[42],'countries':['US'],'firstItem':5,'additionalItem':1}], 'variants':[{'id':'42','providerVariantId':42,'price':49.99,'size':'M','color':'Black','enabled':True,'available':True}]}}]}
 def test_private_mapping_round_trip_preserves_current_retail_edits(self):
  refs=self.store.save(self.catalog['products']);public=public_catalog(self.catalog,refs);serialized=json.dumps(public)
  for secret in ['aliexpress','printify','private-listing','private-sku','private-product','shopId','providerVariantId']:self.assertNotIn(secret,serialized)
  public['products'][1]['merch']['variants'][0]['price']=54.99
  restored=self.store.hydrate(public);self.assertEqual(restored['products'][0]['supplier'],self.catalog['products'][0]['supplier']);self.assertEqual(restored['products'][1]['merch']['variants'][0]['providerVariantId'],42);self.assertEqual(restored['products'][1]['merch']['variants'][0]['price'],54.99)
  self.assertEqual(self.store.path.stat().st_mode&0o777,0o600)
 def test_mapping_versions_do_not_change_a_live_product_before_publication(self):
  old=self.store.save(self.catalog['products']);public=public_catalog(self.catalog,old);changed=copy.deepcopy(self.catalog);changed['products'][0]['supplier']['variantId']='new-private-sku';new=self.store.save(changed['products']);self.assertNotEqual(old['keyboard'],new['keyboard']);self.assertEqual(self.store.hydrate(public)['products'][0]['supplier']['variantId'],'private-sku')
  public['products'][0]['fulfillmentRef']='missing'
  with self.assertRaises(HTTPException):self.store.hydrate(public)
 def test_owner_only_routes_and_image_host_restriction(self):
  from fastapi.testclient import TestClient
  from backend.app import create_app
  from backend.test_checkout import FakeProvider
  from unittest.mock import patch
  from contextlib import contextmanager
  import httpx
  client=TestClient(create_app(database=Path(self.temp.name)/'test.db',private_dir=self.temp.name,manifest={},provider=FakeProvider(),catalog_loader=lambda:{'products':[]},enabled=False,worker_enabled=False))
  for path in ['/admin/catalog-sourcing','/admin/catalog-images']:
   self.assertEqual(client.post(path,json={}).status_code,401)
  response=type('Response',(),{'raise_for_status':lambda _:None,'json':lambda _:{'login':'lionsarmor'}})()
  with patch('backend.app.httpx.get',return_value=response):
   for url in ['http://127.0.0.1/secret','https://evil.example/test.jpg','https://images-api.printify.com:abc/a']:
    self.assertEqual(client.post('/admin/catalog-images',json={'url':url},headers={'authorization':'Bearer test'}).status_code,400)
   @contextmanager
   def image_response(*args,**kwargs):
    self.assertFalse(kwargs['follow_redirects']);yield httpx.Response(200,request=httpx.Request('GET','https://images-api.printify.com/test.jpg'),content=b'\xff\xd8\xfftest')
   with patch('backend.catalog_sourcing.httpx.stream',side_effect=image_response):
    copied=client.post('/admin/catalog-images',json={'url':'https://images-api.printify.com/test.jpg'},headers={'authorization':'Bearer test'});self.assertEqual(copied.status_code,200);self.assertTrue(copied.json()['image'].startswith('data:image/jpeg;base64,'))
