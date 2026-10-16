"""Expand frozen kit BOMs into supplier order units and allocate shared lines.

Each quantity is Mouser order units per kit (a pack counts as one order unit).
Pack contents, minimums and spare parts must be resolved when authoring the BOM;
checkout never silently substitutes a part or rounds a kit's quantities.
"""
from collections import Counter
from decimal import Decimal
import re


def unit_lines(supplier):
    bom = supplier.get('bom')
    if bom is None:
        sku = supplier.get('supplierSku')
        if not isinstance(sku, str) or not sku.strip():
            raise ValueError('A Mouser part number is missing.')
        return {sku: 1}
    if supplier.get('provider') != 'mouser' or supplier.get('fulfillment') != 'automatic':
        raise ValueError('BOM kits require automatic Mouser fulfillment.')
    if not isinstance(bom, dict) or bom.get('status') != 'ready':
        raise ValueError('This kit BOM is incomplete. Finish sourcing before enabling purchases.')
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,80}', str(bom.get('revision', ''))):
        raise ValueError('The kit needs a source revision.')
    lines = bom.get('lines')
    if not isinstance(lines, list) or not 1 <= len(lines) <= 250:
        raise ValueError('The kit needs between 1 and 250 exact Mouser part lines.')
    result = {}
    for line in lines:
        if not isinstance(line, dict):
            raise ValueError('Invalid BOM line.')
        sku, qty = line.get('supplierSku'), line.get('quantity')
        if (not isinstance(sku, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9./_()+#-]{0,79}', sku)
                or sku in result or type(qty) is not int or not 1 <= qty <= 10000):
            raise ValueError('Use unique exact Mouser part numbers and positive whole order-unit quantities.')
        result[sku] = qty
    return result


def expected_lines(items):
    lines = Counter()
    for item in items:
        qty = item['qty']
        if type(qty) is not int or not 1 <= qty <= 99:
            raise ValueError('Choose between 1 and 99 kits or parts.')
        for sku, units in unit_lines(item['supplier']).items():
            lines[sku] += units * qty
    return lines


def allocated_goods(items, goods):
    """Split each aggregated supplier line in proportion to ordered units.

    Shared resistors, packs and standalone parts can occur across multiple kits.
    Decimal allocation conserves the supplier total without per-component rounding.
    """
    totals = expected_lines(items)
    if set(goods) != set(totals) or any(type(v) is not int or v < 0 for v in goods.values()):
        raise ValueError('Supplier costs do not match the exact BOM lines.')
    return [sum((Decimal(goods[sku]) * units * item['qty'] / totals[sku]
                 for sku, units in unit_lines(item['supplier']).items()), Decimal(0))
            for item in items]
