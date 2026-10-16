import copy
import json
from decimal import Decimal
from backend.test_mouser_orders import MouserAutomaticTests
from backend.mouser_bom import allocated_goods, expected_lines, unit_lines


class KitTests(MouserAutomaticTests):
    def kit(self):
        self.product.update(price=99.99, prototypeWarning='Testing not complete; firmware not supplied.')
        self.product['supplier']['bom'] = {'revision': 'H-v1', 'status': 'ready', 'lines': [
            {'supplierSku': '123-RESISTOR', 'quantity': 2},
            {'supplierSku': '456-PACK', 'quantity': 1, 'note': 'One pack contains ten switches; nine required.'}]}
        return self.product

    def test_two_kits_and_standalone_shared_part_allocate_cost_once(self):
        self.kit()
        second = copy.deepcopy(self.product)
        second.update(id='second-kit')
        second['supplier']['supplierSku'] = 'kit-second'
        second['supplier']['bom']['lines'] = [{'supplierSku': '123-RESISTOR', 'quantity': 3}]
        self.catalog['products'].append(second)
        self.items = [{'id': self.product['id'], 'qty': 2}, {'id': second['id'], 'qty': 1}]
        p = self.app.state.commerce.pricing
        p.save({**p.settings(), 'enabled': True, 'round99': False, 'feeFixed': 0})
        q = self.quote(); self.assertEqual(q.status_code, 200, q.text)
        lines = self.transport.carts[next(iter(self.transport.carts))]
        self.assertEqual({l['MouserPartNumber']: l['Quantity'] for l in lines}, {'123-RESISTOR': 7, '456-PACK': 2})
        items, _ = self.app.state.commerce.price(json.dumps([{'id': i['id'], 'qty': i['qty'], 'variantId': ''} for i in self.items]))
        costs = allocated_goods(items, {'123-RESISTOR': 3500, '456-PACK': 1000})
        self.assertEqual(costs, [Decimal(3000), Decimal(1500)])
        self.assertEqual(sum(costs), 4500)
        total = q.json()['amountTotal']
        self.assertGreater(total, 5350)
        self.assertLess(total, 7400, 'The shared resistor line must not be charged twice')

    def test_paid_kit_keeps_original_revision_and_has_red_warning_without_sales_block(self):
        self.kit()
        order = self.paid_order()
        self.product['supplier']['bom']['revision'] = 'H-v2'
        self.product['supplier']['bom']['lines'][0]['quantity'] = 9
        self.tick()
        lines = self.transport.orders['7001']['OrderLines']
        self.assertEqual(next(l['Quantity'] for l in lines if l['ProductInfo']['MouserPartNumber'] == '123-RESISTOR'), 2)
        frozen = json.loads(self.order(order['session'])['items'])[0]
        self.assertEqual(frozen['supplier']['bom']['revision'], 'H-v1')
        self.assertEqual(self.transport.submissions, 1)

    def test_incomplete_bom_and_bad_quantities_fail_before_supplier_calls(self):
        self.kit()
        for change in [lambda b: b.update(status='draft'), lambda b: b.update(lines=[]),
                       lambda b: b['lines'][0].update(quantity=True),
                       lambda b: b['lines'].append(copy.deepcopy(b['lines'][0]))]:
            original = copy.deepcopy(self.product['supplier']['bom'])
            change(self.product['supplier']['bom'])
            self.assertEqual(self.quote().status_code, 409)
            self.assertEqual(self.transport.calls, [])
            self.product['supplier']['bom'] = original

    def test_cart_templates_are_private_fresh_and_never_submit(self):
        self.kit()
        self.assertEqual(self.client.get('/admin/kit-carts').status_code, 401)
        self.assertEqual(self.client.post('/admin/kit-carts', json={}).status_code, 401)
        body = {'productId': self.product['id'], 'quantity': 2, 'country': 'US'}
        first = self.admin('POST', '/admin/kit-carts', body)
        second = self.admin('POST', '/admin/kit-carts', body)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertNotEqual(first.json()['cart']['cart'], second.json()['cart']['cart'])
        self.assertEqual(first.json()['cart']['lines'], {'123-RESISTOR': 4, '456-PACK': 2})
        self.assertEqual(len(self.admin('GET', '/admin/kit-carts').json()['carts']), 2)
        self.assertEqual(self.transport.submissions, 0)
        self.assertTrue(all(c[1] == 'cart/items/insert' for c in self.transport.calls))
        self.assertNotIn(first.json()['cart']['cart'], self.client.get('/inventory').text)

    def test_kit_price_overrun_suspends_product_before_purchase(self):
        self.kit(); order = self.paid_order()
        self.transport.cost = 50; self.tick()
        self.assertEqual(self.transport.submissions, 0)
        self.assertIn(self.product['id'], self.client.get('/inventory').json()['suspendedProducts'])
        self.assertEqual(self.app.state.commerce.fulfillments(order['session'])[0]['state'], 'review')

    def test_kit_and_roddy_board_produce_separate_fulfillments(self):
        self.kit()
        board = next(p for p in self.catalog['products'] if p.get('trackStock') and p.get('type') == 'physical')
        self.items = [{'id': self.product['id'], 'qty': 1}, {'id': board['id'], 'qty': 1}]
        order = self.paid_order(); self.tick()
        self.assertEqual({f['kind'] for f in self.app.state.commerce.fulfillments(order['session'])}, {'office', 'mouser'})
        self.assertEqual(len(self.transport.orders['7001']['OrderLines']), 2)

    def test_cost_allocation_including_a_standalone_part(self):
        supplier = self.kit()['supplier']
        items = [{'supplier': supplier, 'qty': 2}, {'supplier': {'supplierSku': '123-RESISTOR'}, 'qty': 1}]
        self.assertEqual(expected_lines(items), {'123-RESISTOR': 5, '456-PACK': 2})
        self.assertEqual(allocated_goods(items, {'123-RESISTOR': 501, '456-PACK': 200}), [Decimal('600.8'), Decimal('100.2')])
        with self.assertRaises(ValueError): allocated_goods(items, {'123-RESISTOR': 501})

