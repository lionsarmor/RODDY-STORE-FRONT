export const CUSTOMER_SESSION_KEY = 'roddy:forum:session';
export const emptyAddress = () => ({first_name:'',last_name:'',email:'',phone:'',country:'US',region:'',address1:'',address2:'',city:'',zip:''});

export async function customerRequest(endpoint, path, token = '', body) {
  if (!/^https:\/\//.test(endpoint || '')) throw new Error('Accounts are temporarily unavailable. You can still shop as a guest.');
  const response = await fetch(endpoint.replace(/\/$/, '') + path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: {'content-type':'application/json', ...(token ? {authorization:`Bearer ${token}`} : {})},
    ...(body === undefined ? {} : {body:JSON.stringify(body)}),
    cache:'no-store',
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) { const error = new Error(data.error || 'Could not save your account. Please try again.'); error.status=response.status; throw error; }
  return data;
}
