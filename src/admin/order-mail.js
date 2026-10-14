// Only customer-facing order fields belong in an outgoing message.
export function trackingLink(value) {
  try {const url=new URL(value);return ['https:','http:'].includes(url.protocol)&&!url.username&&!url.password?url.href:'';}catch{return '';}
}
export function customerShipments(order) {
  return (order.fulfillments || []).flatMap(f=>(f.shipments || []).map(s=>({carrier:String(s.carrier || ''),number:String(s.number || ''),url:trackingLink(s.url)}))).filter(s=>s.number);
}
export function hasCurrentMessage(order) {
  return !!order.messageContext && (order.messages || []).some(m=>m.context===order.messageContext);
}
export function thankYouDraft(order) {
  const packages=customerShipments(order),physical=(order.fulfillments || []).length>0;
  const allShipped=physical&&order.fulfillments.every(f=>['shipped','delivered','canceled'].includes(f.state));
  const subject=packages.length?`Your RODDY order is on its way — #${order.id.slice(-8).toUpperCase()}`:`Thank you for your RODDY order — #${order.id.slice(-8).toUpperCase()}`;
  const lines=[`Hi ${order.address?.first_name || 'there'},`,'','Thank you for choosing RODDY! We appreciate your order and are glad to have you here.','',`Order: RODDY-${order.id}`,...order.items.map(i=>`${i.qty || 1} × ${i.name}`),''];
  if(packages.length){
    lines.push(allShipped?'Your order is on its way. Here are your tracking details:':'Part of your order is on its way. Here are the tracking details available so far:','');
    packages.forEach((s,i)=>{if(packages.length>1)lines.push(`Package ${i+1}`);lines.push(`${s.carrier || 'Carrier'}: ${s.number}`);if(s.url)lines.push(`Track your package: ${s.url}`);lines.push('');});
    if(!allShipped)lines.push('We’ll send an update when the rest of your order ships.','');
  }else if(physical)lines.push('We’ve received your order. We’ll send your tracking details when it ships.','');
  else lines.push('Your digital items are available through your order confirmation.','');
  lines.push('Need a hand? Reply to this email or contact support@roddy.world.','','Thank you,','Roddy','RODDY · https://roddy.world');
  return {recipient:order.address?.email || '',subject,body:lines.join('\n')};
}
export function mailtoDraft({recipient,subject,body}) {
  if(!/^[^\s@?&#]+@[^\s@?&#]+\.[^\s@?&#]+$/.test(recipient) || /[\r\n]/.test(subject))return '';
  return `mailto:${encodeURIComponent(recipient)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}
