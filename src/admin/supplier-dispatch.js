export function dispatchRequest(supplier, reference = '') {
  const s = supplier.settings;
  return [
    `RODDY dispatch request${reference ? ` — RODDY-${reference}` : ''}`,
    `Supplier: ${supplier.name}`,
    `Packaging agreement: ${s.agreementStatus}`,
    s.agreementEvidence ? `Agreement record: ${s.agreementEvidence}` : 'Obtain supplier confirmation before relying on these requests.',
    `Packaging requested: ${s.packaging}`,
    `Omit retail price receipts: ${s.omitPriceReceipts ? 'Yes' : 'No request'}`,
    `Omit promotional inserts: ${s.omitPromotions ? 'Yes' : 'No request'}`,
    `Dispatch preference: ${s.dispatch === 'self' ? 'To RODDY for inspection / repacking; confirm the owner address separately.' : s.dispatch === 'customer' ? 'Direct to the customer where agreed.' : 'Confirm the delivery arrangement for this order.'}`,
    s.instructions,
    'Keep mandatory customs, safety, warranty and product identification documents accurate.',
  ].filter(Boolean).join('\n');
}
