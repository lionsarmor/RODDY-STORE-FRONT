import copy
import io
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
import zipfile

from backend import test_commerce as commerce_tests
from backend.keycaps import snapshot, packet, MARKS, ARROWS, NUMBER_ROWS, label, PALETTE, PALETTE_DOCUMENT, validate_colors


class KeycapOrderTests(unittest.TestCase):
    quote = commerce_tests.MixedCheckoutTests.quote
    checkout = commerce_tests.MixedCheckoutTests.checkout
    order = commerce_tests.MixedCheckoutTests.order
    tick = commerce_tests.MixedCheckoutTests.tick
    admin = commerce_tests.MixedCheckoutTests.admin

    def setUp(self):
        commerce_tests.MixedCheckoutTests.setUp(self)
        self.templates = self.root/'test-keycap-templates'
        self.templates.mkdir()
        def layer(path, color='GR001'):
            return {'id':'test-layer','colorId':color,'x':0,'y':0,'vectDef':path,'vectScale':100,'vectViewbox':'0 0 1250 1000'}
        keys = {'test-commander':{'colorId':'BL003','layers':[layer('M100 100H200V200H100Z')]},
                'test-arrow':{'colorId':'BL003','layers':[layer('M150 100L200 200H100Z')]},
                'test-number':{'colorId':'GR002','layers':[layer('M100 100H150V250H100Z'),layer('M100 400H200V500H100Z','OG019')]}}
        self.template = {'id':'x16-v06-cherry-tkl','revision':'fixture-1','compatibility':'Synthetic test fixture; not a manufacturing design.',
                         'base':{'name':'Test','keys':keys,'layoutKeys':[{'id':k} for k in keys]},
                         'meta':{'test-commander':{'group':'accents','sourceKey':'COMMANDER','keyId':'commander','autoLegendLayers':[]},'test-arrow':{'group':'accents','sourceKey':'UP','keyId':'up','autoLegendLayers':[]},'test-number':{'group':'alpha','sourceKey':'1','keyId':'1','autoLegendLayers':[0]}},
                         'numberRowText':{'test-number':[layer('M100 100H150V250H100Z'),layer('M100 400H300V450H100Z')]},
                         'marks':{name:[layer('M100 100H200V200H100Z')] for name in MARKS},
                         'paletteVersion':PALETTE_DOCUMENT['version'], 'arrows':{'test-arrow':[layer('M100 100H300V300H100Z','GR002')]}}
        (self.templates/'x16-v06-cherry-tkl.json').write_text(json.dumps(self.template))
        template_patch = patch('backend.keycaps.TEMPLATES', self.templates)
        template_patch.start()
        self.addCleanup(template_patch.stop)
        self.profile = {'id':'x16-compatible','name':'X16 compatible','revision':'v06.1','templateId':'x16-v06-cherry-tkl',
                        'marks':list(MARKS),'arrows':list(ARROWS),'numberRows':list(NUMBER_ROWS)}
        self.catalog['keycapProfiles'] = [self.profile]
        self.product = {'id':'custom-keys','name':'Custom keys','price':99.99,'type':'physical','active':True,
                        'status':'available','trackStock':False,'keycaps':{'profileId':'x16-compatible'},
                        'officeShipping':{'US':{'firstItem':10,'additionalItem':3}}}
        self.catalog['products'].append(self.product)
        self.design = {'profileId':'x16-compatible','revision':'v06.1','alpha':'GR002','modifiers':'GR009',
                       'accents':'BL003','mark':'roddy-r','arrows':'small-black','numberRow':'swatches','keyColors':{}}
        self.items = [{'id':'custom-keys','qty':1,'design':copy.deepcopy(self.design)}]
        self.packets = self.app.state.order_packets

    def paid_order(self):
        q = self.quote(); self.assertEqual(q.status_code,200,q.text)
        result = self.checkout(q.json()); self.assertEqual(result.status_code,200,result.text)
        self.provider.is_paid = True
        self.tick()
        return result.json()

    def test_private_template_generates_frozen_order_snapshots(self):
        template = self.template
        frozen = snapshot(self.catalog,self.product,self.design)
        self.assertTrue(frozen['json']['keys'] == template['base']['keys'])
        self.assertTrue(frozen['json']['layoutKeys'] == template['base']['layoutKeys'])
        self.profile['name'] = 'Changed later'
        self.assertEqual(frozen['profile']['name'],'X16 compatible')

    def test_every_available_mark_and_arrow_style_is_frozen_into_manufacturing_json(self):
        from backend.keycaps import ARROWS
        for mark in MARKS:
            for arrows in ARROWS:
                with self.subTest(mark=mark, arrows=arrows):
                    design={**self.design,'mark':mark,'arrows':arrows}
                    frozen=snapshot(self.catalog,self.product,design)
                    self.assertEqual(frozen['selection'],design)
                    self.assertEqual(frozen['json']['keys']['test-commander']['layers'],self.template['marks'][mark])
                    source=self.template['arrows']['test-arrow'] if arrows.startswith('bold-') else self.template['base']['keys']['test-arrow']['layers']
                    actual=frozen['json']['keys']['test-arrow']['layers']
                    self.assertEqual([l['vectDef'] for l in actual],[l['vectDef'] for l in source])
                    self.assertEqual({l['colorId'] for l in actual},{'GR002' if arrows.endswith('-white') else 'GR001'})
                    self.assertIn(ARROWS[arrows],label(design))
                    self.assertIn(MARKS[mark],label(design))
        self.assertEqual(json.loads((self.templates/'x16-v06-cherry-tkl.json').read_text()),self.template)

    def test_two_designs_share_shipping_group_and_paid_packet_has_both_jsons(self):
        self.items.append({'id':'custom-keys','qty':2,'design':{**self.design,'mark':'otter-x','arrows':'bold-white'}})
        q = self.quote(); self.assertEqual(q.status_code,200,q.text)
        self.assertEqual(q.json()['subtotal'],29997); self.assertEqual(q.json()['shipping'],1600)
        result = self.paid_order(); order = self.order(result['sessionId'])
        details, files = packet(order)
        self.assertEqual(len(files),3);self.assertEqual(details['delivery'],commerce_tests.ADDRESS)
        self.assertEqual({i['selection']['mark']:i['quantity'] for i in details['items']},{'roddy-r':1,'otter-x':2})
        self.assertEqual(details['squareOrderId'],'provider-order')
        self.assertEqual(self.supplier.submitted,[])
        self.assertNotIn('custom-keys',[i['id'] for i in self.app.state.commerce.inventory()])
        self.assertEqual(self.packets.info(result['sessionId'])['state'],'ready')
        directory = self.packets.directory/('RODDY-'+order['request_id'])
        self.assertEqual(directory.stat().st_mode & 0o777,0o700)
        for name, content in files:
            self.assertEqual((directory/name).read_bytes(),content)
            self.assertEqual((directory/name).stat().st_mode & 0o777,0o600)
        before = {p.name:p.stat().st_mtime_ns for p in directory.iterdir()}
        self.tick();self.assertEqual({p.name:p.stat().st_mtime_ns for p in directory.iterdir()},before)

    def test_unpaid_and_refunded_orders_do_not_generate_new_packets(self):
        q = self.quote().json();result = self.checkout(q).json()
        self.tick();self.assertIsNone(self.packets.info(result['sessionId']));self.assertEqual(list(self.packets.directory.iterdir()),[])
        self.provider.is_paid = True;self.tick()
        self.assertEqual(self.packets.info(result['sessionId'])['state'],'ready')
        self.provider.is_paid = False;self.tick()
        self.assertEqual(self.admin('POST','/admin/keycaps/packets',{}).status_code,409)
        self.assertEqual(len(list(self.packets.directory.iterdir())),1)  # Preserve the owner's historical record.

    def test_frozen_packet_survives_catalog_changes_and_requires_owner_and_payment(self):
        result = self.paid_order();order = self.order(result['sessionId']);original = packet(order)
        self.profile['name']='Later';self.profile['revision']='v07';self.product['price']=100
        path='/admin/orders/'+order['request_id']+'/keycaps'
        self.assertEqual(self.client.post(path,json={'action':'download'}).status_code,401)
        downloaded=self.admin('POST',path,{'action':'download'});self.assertEqual(downloaded.status_code,200,downloaded.text[:100])
        self.assertEqual(downloaded.headers['cache-control'],'no-store')
        with zipfile.ZipFile(io.BytesIO(downloaded.content)) as archive:
            for name,content in original[1]:self.assertEqual(archive.read(name),content)
        self.provider.is_paid=False
        self.assertEqual(self.admin('POST',path,{'action':'download'}).status_code,409)

    def test_tampered_stale_missing_or_foreign_designs_are_rejected(self):
        for changes in [{'numberRow':'unknown'},{'mark':'plain-x'},{'arrows':'secret'},{'accents':'#000'},{'revision':'old'},{'profileId':'other'},{'price':.01}]:
            items=[{'id':'custom-keys','qty':1,'design':{**self.design,**changes}}]
            self.assertIn(self.quote(items).status_code,[400,409])
        self.assertEqual(self.quote([{'id':'custom-keys','qty':1}]).status_code,400)
        self.assertEqual(self.quote([{'id':'office','qty':1,'design':self.design}]).status_code,400)
        self.assertEqual(self.quote(self.items*2).status_code,400)
        self.assertEqual(self.provider.created,[])

    def test_disabled_mark_is_rejected_even_when_an_old_catalog_allows_it(self):
        for mark in ['roddy-x','pixel-rainbow-x']:
            self.profile['marks'].append(mark)
            self.items[0]['design']['mark']=mark
            self.assertEqual(self.quote().status_code,400)
        self.assertEqual(self.provider.created,[])

    def test_shipping_must_be_configured_and_changed_quote_cannot_buy_another_design(self):
        self.product['officeShipping']={};self.assertEqual(self.quote().status_code,409)
        self.product['officeShipping']={'US':{'firstItem':10,'additionalItem':3}}
        q=self.quote().json();self.items[0]['design']['mark']='otter-x'
        self.assertEqual(self.checkout(q).status_code,409)
        self.items[0]['design']['mark']='roddy-r';self.profile['revision']='next'
        self.assertEqual(self.checkout(q).status_code,409)
        self.assertEqual(self.provider.created,[])

    def test_disk_failure_retries_and_admin_zip_still_works(self):
        q=self.quote().json();result=self.checkout(q).json();self.provider.is_paid=True
        with patch('backend.order_packets.Path.rename',side_effect=OSError('disk full')):self.tick()
        self.assertEqual(self.packets.info(result['sessionId'])['state'],'queued')
        self.assertEqual(list(self.packets.directory.iterdir()),[])
        order=self.order(result['sessionId'])
        self.assertEqual(self.admin('POST','/admin/orders/'+order['request_id']+'/keycaps',{'action':'download'}).status_code,200)
        self.tick();self.assertEqual(self.packets.info(result['sessionId'])['state'],'ready')

    def test_batch_queue_download_does_not_check_off_orders_and_submission_is_reversible(self):
        result=self.paid_order();order=self.order(result['sessionId']);path='/admin/orders/'+order['request_id']
        self.assertEqual(self.client.post('/admin/keycaps/packets',json={}).status_code,401)
        downloaded=self.admin('POST','/admin/keycaps/packets',{});self.assertEqual(downloaded.status_code,200)
        with zipfile.ZipFile(io.BytesIO(downloaded.content)) as archive:
            self.assertEqual(len(archive.namelist()),2)
            self.assertTrue(all(n.startswith('RODDY-'+order['request_id']+'/') for n in archive.namelist()))
        self.assertEqual(self.app.state.commerce.fulfillments(result['sessionId'])[0]['state'],'awaiting-submission')
        self.assertEqual(self.admin('POST',path+'/keycaps',{'action':'submitted','supplierReference':'YUZU-123'}).status_code,200)
        self.assertEqual(self.admin('POST','/admin/keycaps/packets',{}).status_code,409)
        self.assertEqual(self.admin('POST',path+'/keycaps',{'action':'pending'}).status_code,200)
        self.assertEqual(self.admin('POST','/admin/keycaps/packets',{}).status_code,200)
        self.assertEqual(self.admin('POST',path+'/shipment',{'kind':'keycaps','carrier':'UPS','number':'123','url':'https://ups.com/test'}).status_code,200)
        status=self.client.post('/order',json={'sessionId':result['sessionId']}).json()
        self.assertEqual(status['fulfillments'][0]['kind'],'keycaps');self.assertEqual(status['fulfillments'][0]['state'],'shipped')
        self.assertEqual(status['items'][0]['design'],self.design)
        self.assertNotIn('buyer@example.com',json.dumps(status))
        self.assertNotIn('keycap_packets',json.dumps(status))

    def test_sale_notifications_are_owner_only_and_emit_once_for_verified_payment(self):
        self.assertEqual(self.client.get('/admin/sales').status_code,401)
        first=self.admin('GET','/admin/sales').json();self.assertEqual(first['sales'],[]);self.assertEqual(first['cursor'],0)
        q=self.quote().json();result=self.checkout(q).json();self.tick()
        self.assertEqual(self.admin('GET','/admin/sales?after=0').json()['sales'],[])
        self.provider.is_paid=True;self.tick();self.tick()
        events=self.admin('GET','/admin/sales?after=0').json()
        self.assertEqual(len(events['sales']),1);self.assertEqual(events['pendingKeycaps'],1)
        self.assertEqual(events['sales'][0]['amountCents'],10999)
        self.assertNotIn('buyer@example.com',json.dumps(events))
        self.assertNotIn(result['sessionId'],json.dumps(events))
        self.assertEqual(self.admin('GET','/admin/sales?after='+str(events['cursor'])).json()['sales'],[])
        self.assertEqual(len(self.admin('GET','/admin/orders?view=keycaps').json()['data']),1)
        order=self.order(result['sessionId'])
        self.admin('POST','/admin/orders/'+order['request_id']+'/keycaps',{'action':'submitted'})
        self.assertEqual(self.admin('GET','/admin/sales?after='+str(events['cursor'])).json()['pendingKeycaps'],0)
        self.assertEqual(self.admin('GET','/admin/orders?view=keycaps').json()['data'],[])

    def test_individual_colors_survive_payment_and_owner_packet(self):
        self.items[0]['design']['keyColors']={'up':'RD003','commander':'YW026'}
        result=self.paid_order();order=self.order(result['sessionId']);summary,files=packet(order)
        design=json.loads(files[0][1]);self.assertEqual(design['keys']['test-arrow']['colorId'],'RD003')
        self.assertEqual(design['keys']['test-commander']['colorId'],'YW026')
        self.assertEqual(summary['items'][0]['selection']['keyColors'],{'up':'RD003','commander':'YW026'})
        self.assertIn('RD003',summary['items'][0]['palette']);self.assertEqual(summary['items'][0]['palette']['RD003']['hex'],PALETTE['RD003']['hex'])
        self.assertTrue(validate_colors(design))

    def test_unknown_raw_hex_foreign_keys_and_malformed_overrides_fail_before_checkout(self):
        for changes in [{'alpha':'#FAF7F0'},{'accents':'ZZ999'},{'keyColors':{'up':'#262626'}},
                        {'keyColors':{'other-layout-key':'GR001'}},{'keyColors':[]},{'keyColors':None},
                        {'keyColors':{'up':False}},{'keyColors':{'__proto__':'GR001'}}]:
            with self.subTest(changes=changes):
                self.items[0]['design']={**self.design,**changes};self.assertEqual(self.quote().status_code,400)
        self.assertEqual(self.provider.created,[])

    def test_per_key_color_changes_invalidate_a_payment_quote(self):
        self.items[0]['design']['keyColors']={'up':'RD003'}
        quoted=self.quote().json();self.items[0]['design']['keyColors']['up']='OG001'
        self.assertEqual(self.checkout(quoted).status_code,409);self.assertEqual(self.provider.created,[])

    def test_unapproved_legend_color_in_private_artwork_is_rejected(self):
        self.template['marks']['roddy-r'][0]['colorId']='#000000'
        (self.templates/'x16-v06-cherry-tkl.json').write_text(json.dumps(self.template))
        self.assertEqual(self.quote().status_code,409);self.assertEqual(self.provider.created,[])

    def test_profile_unchecking_hides_butterfly_and_api_rejects_saved_selection(self):
        design={**self.design,'mark':'commander-x16'}
        self.assertEqual(snapshot(self.catalog,self.product,design)['selection']['mark'],'commander-x16')
        self.profile['marks'].remove('commander-x16')
        self.assertEqual(self.quote([{'id':'custom-keys','qty':1,'design':design}]).status_code,409)

    def test_text_number_row_uses_contrast_and_freezes_the_order_choice(self):
        self.items[0]['design'].update(numberRow='text',keyColors={'1':'GR001'})
        original=copy.deepcopy(self.template)
        result=self.paid_order();order=self.order(result['sessionId']);summary,files=packet(order)
        document=json.loads(files[0][1]);layers=document['keys']['test-number']['layers']
        self.assertEqual([l['vectDef'] for l in layers],[l['vectDef'] for l in self.template['numberRowText']['test-number']])
        self.assertEqual({l['colorId'] for l in layers},{'GR002'})
        self.assertEqual(summary['items'][0]['selection']['numberRow'],'text')
        self.assertEqual(self.template,original)
        self.profile['defaults']={'numberRow':'swatches'};self.profile['numberRows']=['swatches']
        self.assertEqual(packet(order)[1],files)
        self.assertEqual(self.quote().status_code,409)
