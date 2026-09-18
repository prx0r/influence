// DomainNameChecker V4.0 — Domain Availability Oracle
// One engine. Three interfaces: Web, REST, MCP.

// Environment vars
const CF_TOKEN = globalThis.CF_AI_TOKEN || '';
const CF_ACCOUNT = globalThis.CF_ACCOUNT_ID || '';

// STATUS enum
const STATUS = Object.freeze({
  AVAILABLE: 'AVAILABLE',
  TAKEN: 'TAKEN',
  PREMIUM: 'PREMIUM',
  UNAVAILABLE: 'UNAVAILABLE',
  UNSUPPORTED: 'UNSUPPORTED',
  UNVERIFIED: 'UNVERIFIED',
});

// REGISTRARS — check links, not buy links
const REGISTRARS = [
  { id: 'porkbun', name: 'Porkbun', url: function(d) { return 'https://porkbun.com/products/domains?search=' + encodeURIComponent(d); } },
  { id: 'namecheap', name: 'Namecheap', url: function(d) { return 'https://www.namecheap.com/domains/registration/results.aspx?domain=' + encodeURIComponent(d); } },
  { id: 'dynadot', name: 'Dynadot', url: function(d) { return 'https://www.dynadot.com/domain/search?domain=' + encodeURIComponent(d); } },
  { id: 'cloudflare', name: 'Cloudflare', url: function(d) { return 'https://domains.cloudflare.com/?query=' + encodeURIComponent(d); } },
];

// === HELPERS ===

function validateDomain(domain) {
  if (!domain || typeof domain !== 'string') return false;
  var d = domain.toLowerCase().trim();
  if (d.length < 3 || d.length > 253) return false;
  if (!d.includes('.')) return false;
  return /^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z]{2,})+$/.test(d);
}

function normalizeDomain(domain) {
  return domain.toLowerCase().trim();
}

// === RDAP BOOTSTRAP ===

var RDAP_BOOTSTRAP = {
  com: 'https://rdap.verisign.com/com/v1/domain/',
  net: 'https://rdap.verisign.com/net/v1/domain/',
  org: 'https://rdap.publicinterestregistry.org/rdap/domain/',
  io: 'https://rdap.identitydigital.services/rdap/domain/',
  dev: 'https://pubapi.registry.google/rdap/domain/',
  app: 'https://pubapi.registry.google/rdap/domain/',
  xyz: 'https://rdap.centralnic.com/xyz/domain/',
  ai: 'https://rdap.identitydigital.services/rdap/domain/',
  co: 'https://rdap.nic.co/domain/',
  sh: 'https://rdap.identitydigital.services/rdap/domain/',
  me: 'https://rdap.afilias-srs.net/rdap/domain/',
  us: 'https://rdap.nidirect.us/rdap/domain/',
  uk: 'https://rdap.nic.uk/rdap/domain/',
  de: 'https://rdap.denic.de/rdap/domain/',
  fr: 'https://rdap.fr/rdap/domain/',
  nl: 'https://rdap.sidn.nl/rdap/domain/',
  be: 'https://rdap.afrinic.net/rdap/domain/',
  at: 'https://rdap.nic.at/rdap/domain/',
  ch: 'https://rdap.nic.ch/rdap/domain/',
  eu: 'https://rdap.eu/rdap/domain/',
  ca: 'https://rdap.cira.ca/rdap/domain/',
  au: 'https://rdap.auda.org.au/rdap/domain/',
  jp: 'https://rdap.jprs.jp/rdap/domain/',
  ru: 'https://rdap.tcinet.ru/rdap/domain/',
  br: 'https://rdap.registro.br/domain/',
  in: 'https://rdap.inregistry.in/rdap/domain/',
  se: 'https://rdap.iis.se/rdap/domain/',
  no: 'https://rdap.norid.no/rdap/domain/',
  dk: 'https://rdap.punktforsyningen.dk/rdap/domain/',
  pl: 'https://rdap.dns.pl/rdap/domain/',
  cz: 'https://rdap.nic.cz/rdap/domain/',
  sk: 'https://rdap.sk-nic.sk/rdap/domain/',
  ie: 'https://rdap.weare.ie/rdap/domain/',
  nz: 'https://rdap.srs.net.nz/rdap/domain/',
  za: 'https://rdap.registry.net.za/rdap/domain/',
  mx: 'https://rdap.nic.mx/rdap/domain/',
  cl: 'https://rdap.nic.cl/rdap/domain/',
  ar: 'https://rdap.nic.ar/rdap/domain/',
  pt: 'https://rdap.dns.pt/rdap/domain/',
  it: 'https://rdap.nic.it/rdap/domain/',
  es: 'https://rdap.nic.es/rdap/domain/',
  tk: 'https://rdap.nic.tk/rdap/domain/',
  ml: 'https://rdap.nic.ml/rdap/domain/',
  ga: 'https://rdap.nic.ga/rdap/domain/',
  pw: 'https://rdap.nic.pw/rdap/domain/',
  tv: 'https://rdap.nic.tv/rdap/domain/',
  cc: 'https://rdap.nic.cc/rdap/domain/',
  ws: 'https://rdap.nic.ws/rdap/domain/',
};

// === CORE ENGINE ===

function cfRegistryCheck(domains) {
  if (!CF_TOKEN || !CF_ACCOUNT) return Promise.resolve([]);
  var batches = [];
  for (var i = 0; i < domains.length; i += 20) {
    batches.push(domains.slice(i, i + 20));
  }
  var allResults = [];
  var chain = Promise.resolve();
  batches.forEach(function(batch) {
    chain = chain.then(function() {
      var domainList = batch.map(function(d) { return d.split('.')[0]; }).join(',');
      var extensions = Array.from(new Set(batch.map(function(d) { return d.split('.').pop(); }))).join(',');
      return fetch('https://api.cloudflare.com/client/v4/accounts/' + CF_ACCOUNT + '/registrar/domain-check', {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer ' + CF_TOKEN,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ domain: domainList, extensions: extensions }),
      })
      .then(function(resp) {
        if (!resp.ok) {
          batch.forEach(function(d) {
            allResults.push({ domain: d, status: STATUS.UNVERIFIED, proof: { source: 'cloudflare_registry', authoritative: false, error: 'API error ' + resp.status } });
          });
          return;
        }
        return resp.json().then(function(data) {
          if (!data.success || !data.result) {
            batch.forEach(function(d) {
              allResults.push({ domain: d, status: STATUS.UNVERIFIED, proof: { source: 'cloudflare_registry', authoritative: false, error: 'unexpected response' } });
            });
            return;
          }
          var results = data.result || [];
          batch.forEach(function(d) {
            var parts = d.split('.');
            var tld = parts.pop();
            var name = parts.join('.');
            var match = results.find(function(r) {
              return (r.domain === name && r.extension === tld);
            });
            if (!match) {
              allResults.push({ domain: d, status: STATUS.UNVERIFIED, proof: { source: 'cloudflare_registry', authoritative: false, error: 'no match in response' } });
              return;
            }
            if (match.registrable === true) {
              allResults.push({ domain: d, status: STATUS.AVAILABLE, proof: { source: 'cloudflare_registry', authoritative: true, registrable: true } });
            } else if (match.reason === 'domain_unavailable') {
              allResults.push({ domain: d, status: STATUS.TAKEN, proof: { source: 'cloudflare_registry', authoritative: true, reason: 'domain_unavailable' } });
            } else if (match.reason === 'domain_premium') {
              allResults.push({ domain: d, status: STATUS.PREMIUM, proof: { source: 'cloudflare_registry', authoritative: true, reason: 'domain_premium' } });
            } else if (match.reason === 'extension_disallows_registration') {
              allResults.push({ domain: d, status: STATUS.UNAVAILABLE, proof: { source: 'cloudflare_registry', authoritative: true, reason: 'extension_disallows_registration' } });
            } else {
              allResults.push({ domain: d, status: STATUS.UNVERIFIED, proof: { source: 'cloudflare_registry', authoritative: false, reason: match.reason || 'unknown' } });
            }
          });
        });
      })
      .catch(function(err) {
        batch.forEach(function(d) {
          allResults.push({ domain: d, status: STATUS.UNVERIFIED, proof: { source: 'cloudflare_registry', authoritative: false, error: err.message } });
        });
      });
    });
  });
  return chain.then(function() { return allResults; });
}

function rdapCheck(domain) {
  var tld = domain.split('.').pop();
  var base = RDAP_BOOTSTRAP[tld];
  if (!base) return Promise.resolve({ domain: domain, status: STATUS.UNSUPPORTED, proof: { source: 'rdap', authoritative: false, error: 'No RDAP server for .' + tld } });
  var controller = new AbortController();
  var timer = setTimeout(function() { controller.abort(); }, 5000);
  return fetch(base + domain, { signal: controller.signal })
    .then(function(resp) {
      clearTimeout(timer);
      if (resp.status === 200) {
        return resp.json().then(function(data) {
          var hasStatus = data.status && data.status.length > 0;
          if (hasStatus) {
            return { domain: domain, status: STATUS.TAKEN, proof: { source: 'rdap', authoritative: true, registered: true, statuses: data.status } };
          }
          return { domain: domain, status: STATUS.UNVERIFIED, proof: { source: 'rdap', authoritative: true, registered: null, note: 'null registered state' } };
        });
      }
      if (resp.status === 404) {
        return { domain: domain, status: STATUS.AVAILABLE, proof: { source: 'rdap', authoritative: true, registered: false } };
      }
      return { domain: domain, status: STATUS.UNVERIFIED, proof: { source: 'rdap', authoritative: false, error: 'HTTP ' + resp.status } };
    })
    .catch(function(err) {
      clearTimeout(timer);
      if (err.name === 'AbortError') {
        return { domain: domain, status: STATUS.UNVERIFIED, proof: { source: 'rdap', authoritative: false, error: 'timeout' } };
      }
      return { domain: domain, status: STATUS.UNVERIFIED, proof: { source: 'rdap', authoritative: false, error: err.message } };
    });
}

function checkDomains(domains) {
  domains = domains.map(normalizeDomain);
  var valid = domains.filter(validateDomain);
  var invalid = domains.filter(function(d) { return !validateDomain(d); });
  var results = invalid.map(function(d) {
    return { domain: d, status: STATUS.UNSUPPORTED, proof: { source: 'validation', authoritative: false, error: 'invalid domain format' } };
  });
  return cfRegistryCheck(valid).then(function(cfResults) {
    results = results.concat(cfResults);
    var unanswered = cfResults.filter(function(r) { return r.status === STATUS.UNVERIFIED; }).map(function(r) { return r.domain; });
    if (unanswered.length === 0) return results;
    var rdapPromises = unanswered.map(function(d) { return rdapCheck(d); });
    return Promise.all(rdapPromises).then(function(rdapResults) {
      rdapResults.forEach(function(rr) {
        var idx = results.findIndex(function(r) { return r.domain === rr.domain; });
        if (idx !== -1 && results[idx].status === STATUS.UNVERIFIED) {
          if (rr.status !== STATUS.UNVERIFIED) {
            results[idx] = rr;
          } else {
            results[idx].proof.note = 'Registry lookup unavailable. No availability claim was made.';
          }
        }
      });
      return results;
    });
  });
}

function makeResult(domain, status, proof) {
  return {
    domain: domain,
    status: status,
    proof: Object.assign({
      source: proof.source || 'unknown',
      authoritative: proof.authoritative || false,
      checked_at: new Date().toISOString(),
    }, proof),
    registrar_links: REGISTRARS.map(function(r) {
      return { name: r.name, url: r.url(domain) };
    }),
  };
}

// === MCP HANDLER ===

function handleMcp(body) {
  var method = body.method;
  var params = body.params || {};
  var id = body.id;

  if (method === 'tools/list') {
    return {
      jsonrpc: '2.0',
      id: id,
      result: {
        tools: [{
          name: 'verify_domain',
          description: 'Check domain availability via Cloudflare registry + RDAP fallback',
          inputSchema: {
            type: 'object',
            properties: {
              domain: { type: 'string', description: 'Full domain to check (e.g. example.com)' }
            },
            required: ['domain']
          }
        }]
      }
    };
  }

  if (method === 'tools/call') {
    var toolName = params.name;
    var args = params.arguments || {};

    if (toolName === 'verify_domain') {
      var domain = normalizeDomain(args.domain || '');
      if (!validateDomain(domain)) {
        return { jsonrpc: '2.0', id: id, error: { code: -32602, message: 'Invalid domain format' } };
      }
      return checkDomains([domain]).then(function(results) {
        var r = results[0];
        var result = makeResult(r.domain, r.status, r.proof);
        return { jsonrpc: '2.0', id: id, result: { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] } };
      });
    }

    return { jsonrpc: '2.0', id: id, error: { code: -32601, message: 'Tool not found: ' + toolName } };
  }

  return { jsonrpc: '2.0', id: id, error: { code: -32601, message: 'Method not found: ' + method } };
}

var LANDING_PAGE = [
'<!DOCTYPE html>',
'<html lang="en">',
'<head>',
'  <meta charset="UTF-8">',
'  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
'  <title>Domain Availability Oracle</title>',
'  <link rel="canonical" href="https://domainnamechecker.dev/">',
'  <link href="https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@300;400;500&display=swap" rel="stylesheet">',
'  <style>',
'    *{margin:0;padding:0;box-sizing:border-box}',
'    body{font-family:"Source Code Pro",monospace;background:#fafafa;color:#111;line-height:1.6}',
'    .wrap{max-width:900px;margin:0 auto;padding:3rem 2rem}',
'    h1{font-size:1rem;font-weight:500}',
'    .sub{font-size:.75rem;color:#999;margin-top:.25rem}',
'    .top{display:flex;gap:1rem;margin-top:1.5rem}',
'    .search{display:flex;flex:1;border:1px solid #ccc}',
'    .search input{flex:1;padding:.75rem 1rem;border:none;background:transparent;font-family:inherit;font-size:.875rem;outline:none}',
'    .search button{padding:.75rem 1.5rem;background:#111;color:#fff;border:none;font-family:inherit;font-size:.75rem;font-weight:500;cursor:pointer}',
'    .st{font-size:.6875rem;color:#999;margin-top:.75rem;min-height:1.2em}',
'    .cols{display:flex;gap:2rem;margin-top:2rem}',
'    .col{flex:1;min-width:0}',
'    .sl{font-size:.625rem;color:#999;text-transform:uppercase;letter-spacing:.12em;margin-bottom:.75rem;font-weight:500}',
'    .card{border:1px solid #eee;padding:1rem;margin-bottom:.75rem;background:#fff}',
'    .card:hover{border-color:#ccc}',
'    .dn{font-weight:500;font-size:.875rem}',
'    .ds{font-size:.75rem;margin-top:.375rem}',
'    .ds-a{color:#166534;font-weight:500}',
'    .ds-t{color:#991b1b;font-weight:500}',
'    .ds-p{color:#c2410c;font-weight:500}',
'    .ds-u{color:#6b7280;font-weight:500}',
'    .ds-x{color:#92400e;font-weight:500}',
'    .dsub{font-size:.625rem;color:#999;margin-top:.125rem}',
'    .rbtn{display:inline-block;margin-top:.5rem;padding:.25rem .75rem;border:1px solid #ccc;background:transparent;font-family:inherit;font-size:.625rem;cursor:pointer;color:#111}',
'    .pt{font-size:.625rem;color:#999;cursor:pointer;margin-top:.5rem}',
'    .pt:hover{color:#111}',
'    .pd{display:none;margin-top:.5rem;padding:.75rem;background:#f9f9f9;border:1px solid #eee;font-size:.625rem;white-space:pre-wrap;line-height:1.8}',
'    .pd.open{display:block}',
'    .rr{margin-top:.625rem;display:flex;flex-wrap:wrap;gap:.5rem}',
'    .rl{display:inline-block;padding:.25rem .625rem;border:1px solid #ccc;font-size:.625rem;font-family:inherit;color:#111;background:transparent;cursor:pointer;text-decoration:none}',
'    .rl:hover{border-color:#111;background:#f5f5f5}',
'    .err{color:#991b1b;font-size:.75rem;padding:1rem 0}',
'    .empty{color:#999;font-size:.75rem;padding:1rem 0}',
'    footer{margin-top:4rem;padding-top:1rem;border-top:1px solid #eee;font-size:.625rem;color:#bbb;display:flex;justify-content:space-between}',
'    footer a{color:#999}',
'  </style>',
'</head>',
'<body>',
'  <div class="wrap">',
'    <h1>domain availability oracle</h1>',
'    <div class="sub">v4.0.0 \u2014 Cloudflare registry + RDAP fallback</div>',
'    <div class="top">',
'      <div class="search">',
'        <input type="text" id="q" placeholder="example.com">',
'        <button id="go">CHECK</button>',
'      </div>',
'    </div>',
'    <div class="st" id="st"></div>',
'    <div id="out"></div>',
'    <footer>',
'      <span>v4.0.0</span>',
'      <span><a href="/llms.txt">llms.txt</a></span>',
'    </footer>',
'  </div>',
'  <script>',
'function isDomain(s){s=s.trim().toLowerCase();if(!s.includes("."))return false;return /^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\\.[a-z]{2,})+$/.test(s)}',
'function esc(s){return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}',
'function sc(s){if(s==="AVAILABLE")return"ds-a";if(s==="TAKEN")return"ds-t";if(s==="PREMIUM")return"ds-p";if(s==="UNAVAILABLE"||s==="UNSUPPORTED")return"ds-u";return"ds-x"}',
'function sl(s){return s==="AVAILABLE"?"AVAILABLE \u2713":s}',
'function ss(s){if(s==="AVAILABLE")return"Registry-confirmed available";if(s==="TAKEN")return"Registry-confirmed taken";if(s==="PREMIUM")return"Premium \u2014 check registrar";if(s==="UNAVAILABLE")return"TLD does not allow registration";if(s==="UNSUPPORTED")return"Unsupported TLD";return"Lookup failed. No claim made."}',
'function rp(p){var L=[];L.push("source: "+esc(p.source||"?"));L.push("authoritative: "+p.authoritative);if(p.checked_at)L.push("checked_at: "+p.checked_at);if(p.latency_ms!=null)L.push("latency_ms: "+p.latency_ms);if(p.error)L.push("error: "+esc(p.error));if(p.reason)L.push("reason: "+esc(p.reason));return L.join("\\n")}',
'var _tid=0;function rc(r){var id="p"+(_tid++);var h="<div class=card><div class=dn>"+esc(r.domain)+"</div><div class=ds "+sc(r.status)+">"+sl(r.status)+"</div><div class=dsub>"+ss(r.status)+"</div>";if(r.status==="UNVERIFIED")h+="<button class=rbtn data-d="+esc(r.domain)+">RETRY</button>";h+="<div class=pt data-t="+id+">proof \u25be</div><pre class=pd id="+id+">"+esc(rp(r.proof))+"</pre>";if(r.registrar_links&&r.registrar_links.length){h+="<div class=rr>";for(var i=0;i<r.registrar_links.length;i++){var rl=r.registrar_links[i];h+="<a class=rl href="+esc(rl.url)+" target=_blank>CHECK AT "+esc(rl.name)+" \u2192</a>"}h+="</div>"}return h+"</div>"}',
'async function doCheck(){var q=document.getElementById("q").value.trim();if(!q)return;var st=document.getElementById("st"),out=document.getElementById("out");st.textContent="checking...";out.innerHTML="";if(!isDomain(q)){st.textContent="";out.innerHTML="<div class=err>Invalid domain format</div>";return}try{var r=await fetch("/api/check/"+encodeURIComponent(q));var d=await r.json();st.textContent="";if(d.error){out.innerHTML="<div class=err>"+esc(d.error.message)+"</div>";return}out.innerHTML=rc(d)}catch(e){st.textContent="";out.innerHTML="<div class=err>"+esc(e.message)+"</div>"}}',
'document.getElementById("go").onclick=doCheck;',
'document.getElementById("q").onkeydown=function(e){if(e.key==="Enter")doCheck()};',
'document.getElementById("out").onclick=function(e){var t=e.target;if(t.classList.contains("rbtn")){document.getElementById("q").value=t.getAttribute("data-d");doCheck()}if(t.classList.contains("pt")){var el=document.getElementById(t.getAttribute("data-t"));if(el)el.classList.toggle("open")}};',
'  </script>',
'</body>',
'</html>'
].join('\n');

// === LLMS_TXT ===

var LLMS_TXT = '# Domain Availability Oracle v4.0\n'
+ '\n'
+ '> Check domain availability via Cloudflare registry API and RDAP fallback.\n'
+ '> One engine. Three interfaces: Web, REST, MCP.\n'
+ '\n'
+ '## Statuses\n'
+ '\n'
+ '- AVAILABLE - domain is registrable (registry-confirmed)\n'
+ '- TAKEN - domain is registered (registry-confirmed)\n'
+ '- PREMIUM - domain is premium-priced (check registrar)\n'
+ '- UNAVAILABLE - TLD disallows registration\n'
+ '- UNSUPPORTED - TLD not in RDAP bootstrap map\n'
+ '- UNVERIFIED - all lookups failed; no availability claim made\n'
+ '\n'
+ '## API\n'
+ '\n'
+ '- GET /api/health - version, engine, endpoints\n'
+ '- GET /api/check/:domain - check single domain (JSON with status + proof)\n'
+ '- POST /api/check - bulk check up to 20 domains\n'
+ '  Body: { "domains": ["a.com", "b.com"] }\n'
+ '- POST /mcp - MCP endpoint (tools: verify_domain)\n'
+ '\n'
+ '## MCP Tools\n'
+ '\n'
+ '- verify_domain - Check domain availability via Cloudflare registry + RDAP\n'
+ '  Input: { "domain": "example.com" }\n'
+ '  Returns: { domain, status, proof, registrar_links }\n'
+ '\n'
+ '## Proof Object\n'
+ '\n'
+ 'Each result includes a proof receipt:\n'
+ '- source: cloudflare_registry | rdap | validation\n'
+ '- authoritative: true/false\n'
+ '- checked_at: ISO timestamp\n'
+ '- latency_ms: response time\n'
+ '- Additional fields: reason, error, registered, note\n'
+ '\n'
+ '## Links\n'
+ '\n'
+ '- GitHub: https://github.com/prx0r/domainnamechecker\n'
+ '- Live: https://domainnamechecker.dev/';

// === HTTP HANDLER ===

var corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

function handleRequest(request) {
  var url = new URL(request.url);
  var path = url.pathname;

  if (request.method === 'OPTIONS') return new Response(null, { headers: corsHeaders });

  // Health
  if (path === '/api/health') {
    var healthObj = {
      version: '4.0.0',
      engine: 'domain-availability-oracle',
      status: 'healthy',
      endpoints: [
        'GET /api/health',
        'GET /api/check/:domain',
        'POST /api/check',
        'POST /mcp',
        'GET /llms.txt',
      ]
    };
    return new Response(JSON.stringify(healthObj), { headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders) });
  }

  // Single domain check
  if (path.startsWith('/api/check/') && request.method === 'GET') {
    var domain = decodeURIComponent(path.slice('/api/check/'.length));
    domain = normalizeDomain(domain);
    if (!validateDomain(domain)) {
      return new Response(JSON.stringify({ error: { code: 'INVALID_DOMAIN', message: 'Invalid domain format' } }), { status: 400, headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders) });
    }
    var t0 = Date.now();
    return checkDomains([domain]).then(function(results) {
      var elapsed = Date.now() - t0;
      var r = results[0];
      var result = makeResult(r.domain, r.status, r.proof);
      result.latency_ms = elapsed;
      return new Response(JSON.stringify(result), { headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders) });
    });
  }

  // Bulk check
  if (path === '/api/check' && request.method === 'POST') {
    return request.json().then(function(body) {
      var domains = body.domains || [];
      if (!Array.isArray(domains) || domains.length === 0) {
        return new Response(JSON.stringify({ error: { code: 'INVALID_INPUT', message: 'domains must be a non-empty array' } }), { status: 400, headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders) });
      }
      if (domains.length > 20) {
        return new Response(JSON.stringify({ error: { code: 'LIMIT_EXCEEDED', message: 'max 20 domains per request' } }), { status: 400, headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders) });
      }
      var t0 = Date.now();
      return checkDomains(domains).then(function(results) {
        var elapsed = Date.now() - t0;
        var mapped = results.map(function(r) {
          return makeResult(r.domain, r.status, r.proof);
        });
        return new Response(JSON.stringify({
          results: mapped,
          metadata: { total: mapped.length, latency_ms: elapsed, checked_at: new Date().toISOString() }
        }), { headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders) });
      });
    });
  }

  // MCP
  if (path === '/mcp' && request.method === 'POST') {
    return request.json().then(function(body) {
      return handleMcp(body).then(function(resp) {
        return new Response(JSON.stringify(resp), { headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders) });
      });
    });
  }

  // Static files
  if (path === '/llms.txt') return new Response(LLMS_TXT, { headers: Object.assign({ 'Content-Type': 'text/plain' }, corsHeaders) });
  if (path === '/robots.txt') return new Response('User-agent: *\nAllow: /\nSitemap: https://domainnamechecker.dev/sitemap.xml', { headers: Object.assign({ 'Content-Type': 'text/plain' }, corsHeaders) });
  if (path === '/sitemap.xml') return new Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://domainnamechecker.dev/</loc><changefreq>weekly</changefreq><priority>1</priority></url></urlset>', { headers: Object.assign({ 'Content-Type': 'application/xml' }, corsHeaders) });

  // Landing page
  if (path === '/') {
    return new Response(LANDING_PAGE, { headers: Object.assign({ 'Content-Type': 'text/html; charset=utf-8' }, corsHeaders) });
  }

  return new Response(JSON.stringify({ error: { code: 'NOT_FOUND', message: 'Not found' } }), { status: 404, headers: Object.assign({ 'Content-Type': 'application/json' }, corsHeaders) });
}

addEventListener('fetch', function(event) { event.respondWith(handleRequest(event.request)); });
