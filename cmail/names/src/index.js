// names worker — one name, everywhere. Same aesthetic as domainnamechecker:
// Source Code Pro, #fafafa, minimal rows, honest badges. Proxies the checker
// worker for verify+handles (keys stay server-side), merges 5-state results.
const CHECKER = 'https://domainnamechecker.tradesprior.workers.dev';
const CORS = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type' };

const LANDING = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>names — one name, everywhere</title>
  <meta name="description" content="Check a name across domains, socials, packages, app stores and ENS. Honest states, never guessed.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@300;400;500&display=swap" rel="stylesheet">
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:'Source Code Pro',monospace;background:#fafafa;color:#111;-webkit-font-smoothing:antialiased;line-height:1.6}
    a{color:#111;text-decoration:none}a:hover{text-decoration:underline}
    .wrap{max-width:800px;margin:0 auto;padding:3rem 2rem}
    h1{font-size:1rem;font-weight:500}
    .top-row{display:flex;gap:1rem;margin-top:1.5rem;align-items:stretch}
    .search{display:flex;gap:0;border:1px solid #ccc;flex:1}
    .search input{flex:1;padding:.75rem 1rem;border:none;background:transparent;font-family:'Source Code Pro',monospace;font-size:.875rem;outline:none}
    .search button{padding:.75rem 1.5rem;background:#111;color:#fff;border:none;font-family:'Source Code Pro',monospace;font-size:.75rem;font-weight:500;cursor:pointer}
    .search button:hover{background:#333}
    .status{font-size:.6875rem;color:#999;margin-top:.75rem;min-height:1.2em}
    .section{margin-top:2rem}
    .section-label{font-size:.625rem;color:#999;text-transform:uppercase;letter-spacing:.12em;margin-bottom:.75rem;font-weight:500}
    table{width:100%;border-collapse:collapse}
    td{padding:.625rem 0;border-bottom:1px solid #eee;font-size:.8125rem}
    td:first-child{font-weight:500}
    .avail{color:#166534;font-weight:500;font-size:.75rem}
    .taken{color:#999;font-size:.75rem}
    .warn{color:#b45309;font-size:.75rem}
    .note{font-size:.625rem;color:#999}
    footer{margin-top:4rem;padding-top:1rem;border-top:1px solid #eee;font-size:.625rem;color:#bbb;display:flex;justify-content:space-between}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>one name, everywhere</h1>
    <div class="top-row">
      <div class="search">
        <input type="text" id="q" placeholder="postagi — domains, socials, packages, apps, ENS">
        <button id="go">check</button>
      </div>
    </div>
    <div class="status" id="st"></div>
    <div id="out"></div>
    <footer><span>names v1.0 · states: taken / available / unclaimed? / manual</span><span>powered by domainnamechecker</span></footer>
  </div>
  <script>
    const $=s=>document.querySelector(s);
    function badge(h){
      if(h.status==='taken')return '<span class="taken">taken</span>';
      if(h.status==='available')return '<span class="avail">free</span>';
      if(h.status==='not_found')return '<span class="avail" title="'+(h.note||'')+'">unclaimed?</span>';
      if(h.status==='invalid')return '<span class="taken">n/a</span>';
      return '<span class="warn">manual</span>';
    }
    async function go(){
      const q=$('#q').value.trim();if(!q)return;
      const st=$('#st'),out=$('#out');st.textContent='checking everywhere...';out.innerHTML='';
      try{
        const r=await fetch('/api/check?name='+encodeURIComponent(q));const d=await r.json();
        st.textContent=d.summary.domains+' domains · '+d.summary.handles+' handles · '+d.summary.apps+' apps';
        let h='';
        const sec=(t,rows)=>{h+='<div class="section"><div class="section-label">'+t+'</div><table>'+rows+'</table></div>';};
        sec('domains',d.domains.map(x=>'<tr><td>'+x.domain+'</td><td>'+(x.status==='available'?'<span class="avail">free</span>':'<span class="taken">'+x.status+'</span>')+'</td><td style="text-align:right;font-size:.6875rem;color:#666">'+(x.price!=null?'$'+x.price+'/yr':'')+'</td></tr>').join('')||'<tr><td class="note">none</td></tr>');
        sec('handles · packages · web3',d.handles.map(x=>'<tr><td>'+x.label+'</td><td>'+badge(x)+'</td><td class="note">'+(x.confidence||x.reason||'')+'</td></tr>').join(''));
        sec('app stores',d.apps.map(x=>'<tr><td>'+x.label+'</td><td>'+badge(x)+'</td><td class="note">'+(x.confidence||x.reason||'')+'</td></tr>').join(''));
        if(d.claim_url)h+='<div class="section"><a class="buy" style="font-size:.6875rem;border:1px solid #ccc;padding:.375rem .75rem" href="'+d.claim_url+'" target="_blank">open claim kit →</a></div>';
        out.innerHTML=h;
      }catch(e){st.textContent='';out.innerHTML='<div style="color:#991b1b;font-size:.75rem">'+e.message+'</div>';}
    }
    $('#go').addEventListener('click',go);
    $('#q').addEventListener('keydown',e=>{if(e.key==='Enter')go()});
  </script>
</body>
</html>`;

const TLDS = ['com', 'io', 'co', 'dev', 'app', 'ai'];

async function svcFetch(env, path) {
  // Same-account service binding (no public-URL loop). Falls back to HTTPS.
  if (env && env.CHECKER_SVC) {
    const r = await env.CHECKER_SVC.fetch(new Request('https://checker' + path));
    return r.json();
  }
  const r = await fetch(CHECKER + path);
  return r.json();
}
async function checkAll(name, env) {
  const clean = String(name || '').trim().replace(/^@/, '').toLowerCase();
  if (!clean || clean.length > 60) throw new Error('name required (max 60 chars)');
  const [handlesRes, ...domainRes] = await Promise.all([
    svcFetch(env, '/api/handles/' + encodeURIComponent(clean)).catch(() => null),
    ...TLDS.map(tld =>
      svcFetch(env, '/api/verify/' + encodeURIComponent(clean + '.' + tld)).catch(() => null)),
  ]);
  const handles = (handlesRes && handlesRes.handles) || [];
  const social = handles.filter(h => !['npm_package', 'pypi_project', 'crates', 'ens', 'appstore', 'play'].includes(h.platform) && h.platform !== 'npm' && h.platform !== 'pypi');
  const apps = handles.filter(h => h.platform === 'appstore' || h.platform === 'play');
  const domains = domainRes.filter(Boolean).map(v => ({
    domain: v.domain,
    status: v.registration?.status || 'unknown',
    price: null,
  }));
  return {
    name: clean,
    domains, handles: social, apps,
    summary: {
      domains: domains.filter(d => d.status === 'available').length + '/' + domains.length + ' free',
      handles: handles.filter(h => h.status === 'available' || h.status === 'not_found').length + '/' + social.length + ' open',
      apps: apps.filter(h => h.status === 'available' || h.status === 'not_found').length + '/' + apps.length + ' open',
    },
    claim_url: CHECKER + '/#claim',
  };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === 'OPTIONS') return new Response(null, { headers: CORS });
    if (url.pathname === '/') return new Response(LANDING, { headers: { 'Content-Type': 'text/html; charset=utf-8', ...CORS } });
    if (url.pathname === '/api/health') return Response.json({ status: 'healthy', version: '1.1.0', tools: ['check_all'] }, { headers: CORS });
    if (url.pathname === '/mcp' && request.method === 'POST') {
      const body = await request.json().catch(() => ({}));
      const { method, params, id } = body;
      if (method === 'tools/list') {
        return Response.json({ jsonrpc: '2.0', id, result: { tools: [
          { name: 'check_all', description: 'One name across domains (6 TLDs), socials/packages/web3, app stores. 5-state verdicts, never guessed.', inputSchema: { type: 'object', properties: { name: { type: 'string' } }, required: ['name'] } },
        ] } }, { headers: CORS });
      }
      if (method === 'tools/call' && params && params.name === 'check_all') {
        try {
          const result = await checkAll(params.arguments && params.arguments.name, env);
          return Response.json({ jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] } }, { headers: CORS });
        } catch (e) {
          return Response.json({ jsonrpc: '2.0', id, error: { code: -32000, message: String(e && e.message || e).slice(0, 200) } }, { headers: CORS });
        }
      }
      return Response.json({ jsonrpc: '2.0', id, error: { code: -32601, message: 'Method not found' } }, { headers: CORS });
    }
    if (url.pathname === '/api/debug') {
      try {
        const r = await fetch(CHECKER + '/api/health');
        const t = await r.text();
        return Response.json({ checkerStatus: r.status, checkerBody: t.slice(0, 200) }, { headers: CORS });
      } catch (e) {
        return Response.json({ fetchError: String(e).slice(0, 300) }, { headers: CORS });
      }
    }
    if (url.pathname === '/api/check' && request.method === 'GET') {
      const name = url.searchParams.get('name');
      try {
        return Response.json(await checkAll(name, env), { headers: CORS });
      } catch (e) {
        return Response.json({ error: e.message }, { status: 400, headers: CORS });
      }
    }
    return new Response('not found', { status: 404, headers: CORS });
  },
};
