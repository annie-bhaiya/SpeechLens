export async function api<T>(url:string,options?:RequestInit):Promise<T>{
  const response=await fetch(url,options);
  if(!response.ok){const body=await response.json().catch(()=>({detail:response.statusText}));throw new Error(typeof body.detail==='string'?body.detail:JSON.stringify(body.detail));}
  return response.status===204?undefined as T:response.json();
}
export const number=(value:number|null|undefined,digits=1)=>value==null?'—':value.toFixed(digits);
