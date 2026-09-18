// Domain Intelligence Engine — Cloudflare Worker v3
// Full pipeline: generate → verify → score → compare → track

// Env vars (set via wrangler secret put CF_AI_TOKEN / CF_ACCOUNT_ID)
const CF_AI_TOKEN = globalThis.CF_AI_TOKEN || '';
const CF_ACCOUNT_ID = globalThis.CF_ACCOUNT_ID || '';

// === VERIFICATION PIPELINE ===

async function verifyDomain(domain) {
  const evidence = [];
  
  // Stage 1: DNS probe (cheap heuristic)
  const dns = await dnsProbe(domain);
  evidence.push({ source: 'dns', status: dns.has_records ? 'records_found' : 'no_records' });
  
  // Stage 2: RDAP (authoritative registration evidence)
  const rdap = await rdapCheck(domain);
  evidence.push({ source: 'rdap', status: rdap.registered ? 'registered' : 'not_registered', details: rdap });
  
  // Stage 3: Determine final status with cross-verification
  let status = 'unknown';
  let confidence = 0.5;
  let sources = [];

  // RDAP is authoritative
  if (rdap.registered === false) {
    // RDAP says not registered — but double-check with DNS
    if (dns.has_records) {
      // DNS has records but RDAP says not registered - suspicious, may be reserved or parked
      status = 'unknown';
      confidence = 0.6;
      sources.push('rdap_not_found_but_dns_exists');
    } else {
      status = 'available';
      confidence = 0.95;
      sources.push('rdap_not_found');
    }
  } else if (rdap.registered === true) {
    status = 'taken';
    confidence = 0.99;
    sources.push('rdap_confirmed');
  } else {
    // RDAP failed, fall back to DNS
    if (dns.has_records) {
      status = 'taken';
      confidence = 0.85;
      sources.push('dns_records_found');
    } else {
      status = 'unknown';
      confidence = 0.5;
      sources.push('rdap_failed_no_dns');
    }
  }
  
  return {
    domain,
    registration: { status, confidence, authoritative: rdap.registered !== null, verified_at: new Date().toISOString() },
    evidence,
    sources,
    dns: dns,
    rdap: rdap,
    schema_version: '3.0.0'
  };
}

async function dnsProbe(domain) {
  const recordTypes = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME'];
  const records = {};
  let hasRecords = false;
  
  for (const type of recordTypes) {
    try {
      const response = await fetch(`https://cloudflare-dns.com/dns-query?name=${domain}&type=${type}`, { headers: { 'Accept': 'application/dns-json' } });
      const data = await response.json();
      if (data.Answer && data.Answer.length > 0) {
        hasRecords = true;
        records[type] = data.Answer.map(a => a.data);
      }
    } catch (e) {}
  }
  
  return { has_records: hasRecords, records };
}

async function rdapCheck(domain) {
  const tld = domain.split('.').pop();
  // RDAP servers per TLD (from IANA bootstrap)
  const RDAP = {
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
  };
  const base = RDAP[tld];
  if (!base) return { registered: null, error: 'No RDAP server for .' + tld };

  try {
    const response = await fetch(base + domain);
    if (response.status === 200) {
      const data = await response.json();
      return {
        registered: true,
        name: data.ldhName,
        status: data.status,
        events: data.events?.map(e => ({ action: e.eventAction, date: e.eventDate })) || [],
      };
    }
    if (response.status === 404) return { registered: false };
    return { registered: null, error: 'RDAP status: ' + response.status };
  } catch (e) {
    return { registered: null, error: e.message };
  }
}

// === INPUT VALIDATION ===

function validateDomain(domain) {
  if (!domain || typeof domain !== 'string') return false;
  const d = domain.toLowerCase().trim();
  if (d.length > 253) return false;
  return /^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z]{2,})+$/.test(d);
}

// === DOMAIN GENERATION ===

function generateCandidates(concept, tlds = ['com']) {
  const candidates = [];
  const clean = concept.toLowerCase().replace(/[^a-z0-9-]/g, '');
  
  // Exact match (preserves hyphens if present)
  if (clean.length >= 2) {
    for (const t of tlds) candidates.push(`${clean}.${t}`);
  }
  
  // Non-hyphenated version
  const noHyphen = clean.replace(/-/g, '');
  if (noHyphen !== clean && noHyphen.length >= 2) {
    for (const t of tlds) candidates.push(`${noHyphen}.${t}`);
  }
  
  // Split variants from the full concept
  for (let i = 2; i < clean.length; i++) {
    if (clean[i - 1] === '-') continue; // don't split at existing hyphens
    for (const t of tlds) candidates.push(`${clean.slice(0, i)}-${clean.slice(i)}.${t}`);
  }
  
  // Compounds with the non-hyphenated base
  const suffixes = ['api', 'tool', 'util', 'ops', 'fn', 'run', 'hub', 'lab', 'kit', 'pro', 'go', 'now', 'io', 'net', 'dev', 'cap', 'cmd', 'do'];
  for (const s of suffixes) {
    for (const t of tlds) {
      candidates.push(`${noHyphen}${s}.${t}`);
      candidates.push(`${noHyphen}-${s}.${t}`);
    }
  }
  
  // HTTP status codes
  const codes = ['200', '204', '206', '301', '404', '418', '42', '64', '101'];
  for (const c of codes) { for (const t of tlds) candidates.push(`${noHyphen}${c}.${t}`); }
  
  return [...new Set(candidates)];
}

// === VARIANT PACKS ===

const VARIANT_PACKS = {
  default: {
    name: 'Default',
    description: 'Compounds, suffixes, and HTTP codes',
    generate: (concept, tlds) => generateCandidates(concept, tlds),
  },
  sanskrit: {
    name: 'Sanskrit',
    description: 'Sanskrit translations via LLM',
    translate: async (concept, tlds) => {
      const candidates = [];
      try {
        const resp = await fetch(
          `https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/ai/run/@cf/meta/llama-3.1-8b-instruct`,
          {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + CF_AI_TOKEN, 'Content-Type': 'application/json' },
            body: JSON.stringify({
              messages: [{
                role: 'system',
                content: `You are a Sanskrit linguist. Given an English concept, return 5 Sanskrit words (transliterated to Latin script, lowercase, no diacritics) that capture its meaning. Focus on short, pronounceable words suitable for domain names. Return ONLY a JSON array of strings, no explanation.`
              }, { role: 'user', content: concept }],
              max_tokens: 100,
              temperature: 0.3,
            }),
          }
        );
        const data = await resp.json();
        const content = data.result?.choices?.[0]?.message?.content || '';
        const match = content.match(/\[[\s\S]*?\]/);
        if (match) {
          const words = JSON.parse(match[0]);
          for (const w of words) {
            const clean = w.toLowerCase().replace(/[^a-z]/g, '');
            if (clean.length >= 3 && clean.length <= 12) {
              for (const t of tlds) candidates.push(`${clean}.${t}`);
            }
          }
        }
      } catch (e) {}
      return candidates;
    },
    generate: (concept, tlds) => {
      // Synchronous fallback - return empty, async version will be used
      return [];
    },
  },
  tech: {
    name: 'Tech',
    description: 'Developer-focused compounds',
    generate: (concept, tlds) => {
      const candidates = [];
      const clean = concept.toLowerCase().replace(/[^a-z0-9]/g, '');
      const prefixes = ['dev', 'get', 'my', 'use', 'try', 'ask', 'raw', 'dry', 'pro', 'zen'];
      const suffixes = ['dev', 'api', 'io', 'lab', 'hub', 'kit', 'app', 'run', 'now', 'sh', 'ai', 'dev'];
      const dots = ['dev', 'io', 'ai', 'sh', 'app', 'xyz'];
      
      // Base + suffix
      for (const s of suffixes) {
        for (const t of tlds) {
          candidates.push(`${clean}${s}.${t}`);
          candidates.push(`${clean}-${s}.${t}`);
        }
      }
      
      // Prefix + base
      for (const p of prefixes) {
        for (const t of tlds) {
          candidates.push(`${p}${clean}.${t}`);
          candidates.push(`${p}-${clean}.${t}`);
        }
      }
      
      // Tech TLDs
      for (const d of dots) {
        if (!tlds.includes(d)) {
          for (const t of [d]) candidates.push(`${clean}.${t}`);
        }
      }
      
      return [...new Set(candidates)].slice(0, 50);
    },
  },
  animals: {
    name: 'Animals',
    description: 'Animal name variants',
    animals: ['owl', 'fox', 'hawk', 'ant', 'bee', 'mole', 'raven', 'wolf', 'bear', 'deer', 'lynx', 'hare', 'moth', 'crane', 'dove', 'wren', 'pike', 'ray', 'elk', 'ape'],
    generate: (concept, tlds) => {
      const candidates = [];
      const clean = concept.toLowerCase().replace(/[^a-z0-9]/g, '');
      const animals = VARIANT_PACKS.animals.animals;
      
      // Animal + concept
      for (const a of animals) {
        for (const t of tlds) {
          candidates.push(`${a}${clean}.${t}`);
          candidates.push(`${a}-${clean}.${t}`);
          candidates.push(`${clean}${a}.${t}`);
          candidates.push(`${clean}-${a}.${t}`);
        }
      }
      
      return [...new Set(candidates)].slice(0, 50);
    },
  },
  nature: {
    name: 'Nature',
    description: 'Nature-inspired names',
    nature: ['moss', 'fern', 'fig', 'plum', 'oak', 'elm', 'ash', 'yew', 'fir', 'cedar', 'pine', 'palm', 'reed', 'sage', 'mint', 'bloom', 'vale', 'dale', 'glen', 'peak'],
    generate: (concept, tlds) => {
      const candidates = [];
      const clean = concept.toLowerCase().replace(/[^a-z0-9]/g, '');
      const nature = VARIANT_PACKS.nature.nature;
      
      // Nature + concept
      for (const n of nature) {
        for (const t of tlds) {
          candidates.push(`${n}${clean}.${t}`);
          candidates.push(`${n}-${clean}.${t}`);
          candidates.push(`${clean}${n}.${t}`);
          candidates.push(`${clean}-${n}.${t}`);
        }
      }
      
      return [...new Set(candidates)].slice(0, 50);
    },
  },
};

function getVariantCandidates(concept, tlds, pack = 'default') {
  const variantPack = VARIANT_PACKS[pack] || VARIANT_PACKS.default;
  return variantPack.generate(concept, tlds);
}

// === SCORING ===

function scoreDomain(domain, intent) {
  const name = domain.split('.')[0];
  const tld = domain.split('.')[1];
  let score = 0;
  
  // Length (max 4)
  if (name.length <= 3) score += 4; else if (name.length <= 4) score += 3; else if (name.length <= 6) score += 2; else if (name.length <= 8) score += 1;
  
  // Hyphens (max 3)
  const hyphens = (name.match(/-/g) || []).length;
  if (hyphens === 0) score += 3; else if (hyphens === 1) score += 2; else if (hyphens === 2) score += 1;
  
  // TLD (max 3)
  if (tld === 'com') score += 3; else if (tld === 'xyz') score += 2; else if (tld === 'dev') score += 2; else if (tld === 'site') score += 1;
  
  // Semantic match (max 3)
  if (name === intent) score += 3; else if (name.startsWith(intent)) score += 2; else if (name.includes(intent)) score += 1;
  
  // Meaning strength (max 4)
  const meaning = getMeaning(domain);
  if (meaning.strength === 'strong') score += 4; else if (meaning.strength === 'medium') score += 2; else if (meaning.strength === 'weak') score += 1;
  
  // Developer/agent relevance (max 3)
  if (meaning.developerNative) score += 2;
  if (meaning.agentNative) score += 1;
  
  return { score, meaning };
}

function getMeaning(domain) {
  const name = domain.split('.')[0].replace(/-/g, '');
  const meanings = {
    'get200': { meaning: 'GET something successfully (HTTP 200 OK)', strength: 'strong', developerNative: true, agentNative: true },
    'get204': { meaning: 'GET succeeded with no content (HTTP 204)', strength: 'medium', developerNative: true, agentNative: false },
    'getfn': { meaning: 'GET function', strength: 'strong', developerNative: true, agentNative: true },
    'getapi': { meaning: 'GET an API', strength: 'strong', developerNative: true, agentNative: true },
    'gettool': { meaning: 'GET a tool', strength: 'strong', developerNative: true, agentNative: true },
    'getutil': { meaning: 'GET a utility', strength: 'medium', developerNative: true, agentNative: true },
    'getops': { meaning: 'GET operations', strength: 'medium', developerNative: true, agentNative: true },
    'getrun': { meaning: 'GET and run', strength: 'medium', developerNative: true, agentNative: true },
    'getcap': { meaning: 'GET capabilities', strength: 'strong', developerNative: true, agentNative: true },
  };
  return meanings[name] || { meaning: name, strength: 'weak', developerNative: false, agentNative: false };
}

function tldPricingKeys(tlds) {
  return [...new Set((tlds || ['com']).map(t => t.replace('.', '').toLowerCase()))];
}

// === LLM INTENT PARSER ===

async function parseIntent(query) {
  const q = query.trim().toLowerCase();

  // Quick heuristic — no LLM needed
  if (/^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z]{2,})+$/.test(q)) {
    return { type: 'verify', domain: q };
  }
  if (q.split(/\s+/).length <= 2 && /^[a-z0-9-]+$/.test(q)) {
    return { type: 'mine', concept: q, context: null };
  }

  // Use LLM to UNDERSTAND the query, not just extract
  try {
    const resp = await fetch(
      `https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/ai/run/@cf/meta/llama-3.1-8b-instruct`,
      {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + CF_AI_TOKEN, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{
            role: 'system',
            content: `You are a domain name intelligence assistant. Analyze the user's query and return a JSON object with:
- "concept": a SHORT domain name (lowercase, no spaces, max 12 chars). CRITICAL: If the user mentions a style (animal, nature, metaphor), the concept MUST reflect that style. E.g. "animal domain for seo" -> "hawkseo" or "foxseo", NOT "agentseo". "nature name for tools" -> "mosstool" or "fernapi". "need a domain for agent seo" -> "agentseo".
- "context": what the user is building (1 sentence)
- "style": "suggestive"|"descriptive"|"animal"|"metaphor"|"invented"

Return ONLY valid JSON, no explanation.`
          }, {
            role: 'user',
            content: query
          }],
          max_tokens: 200,
          temperature: 0,
        }),
      }
    );
    const data = await resp.json();
    const content = data.result?.choices?.[0]?.message?.content || '';
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]);
      if (parsed.concept) {
        return {
          type: 'mine',
          concept: parsed.concept.toLowerCase().replace(/[^a-z0-9-]/g, '').slice(0, 15),
          context: parsed.context || null,
          style: parsed.style || 'suggestive',
        };
      }
    }
  } catch (e) { /* fall through */ }

  return { type: 'mine', concept: q.replace(/[^a-z0-9-]/g, '').slice(0, 15), context: null, style: 'suggestive' };
}

// Name analysis — what does this name suggest?
function analyzeName(domain) {
  const name = domain.split('.')[0].replace(/-/g, '');
  const meanings = {
    'get': { meaning: 'retrieve/call', strength: 'strong', archetype: 'action' },
    'fetch': { meaning: 'retrieve', strength: 'strong', archetype: 'action' },
    'tool': { meaning: 'utility', strength: 'strong', archetype: 'object' },
    'util': { meaning: 'utility', strength: 'medium', archetype: 'object' },
    'ops': { meaning: 'operations', strength: 'medium', archetype: 'action' },
    'fn': { meaning: 'function', strength: 'strong', archetype: 'code' },
    'api': { meaning: 'interface', strength: 'strong', archetype: 'code' },
    'hub': { meaning: 'center', strength: 'medium', archetype: 'place' },
    'lab': { meaning: 'experiment', strength: 'medium', archetype: 'place' },
    'kit': { meaning: 'toolkit', strength: 'medium', archetype: 'object' },
    'pro': { meaning: 'professional', strength: 'medium', archetype: 'quality' },
    'go': { meaning: 'action', strength: 'medium', archetype: 'action' },
    'run': { meaning: 'execute', strength: 'medium', archetype: 'action' },
    'now': { meaning: 'immediate', strength: 'medium', archetype: 'time' },
    'tiny': { meaning: 'small/simple', strength: 'strong', archetype: 'size' },
    'mini': { meaning: 'small', strength: 'strong', archetype: 'size' },
    'micro': { meaning: 'very small', strength: 'strong', archetype: 'size' },
    'nano': { meaning: 'atomic', strength: 'strong', archetype: 'size' },
    'owl': { meaning: 'wisdom/search', strength: 'strong', archetype: 'animal' },
    'fox': { meaning: 'cleverness', strength: 'strong', archetype: 'animal' },
    'hawk': { meaning: 'vision/speed', strength: 'strong', archetype: 'animal' },
    'ant': { meaning: 'tiny work', strength: 'medium', archetype: 'animal' },
    'bee': { meaning: 'distributed', strength: 'medium', archetype: 'animal' },
    'mole': { meaning: 'digging/finding', strength: 'medium', archetype: 'animal' },
    'raven': { meaning: 'intelligence', strength: 'medium', archetype: 'animal' },
    'moss': { meaning: 'natural/organic', strength: 'weak', archetype: 'nature' },
    'fern': { meaning: 'natural', strength: 'weak', archetype: 'nature' },
    'fig': { meaning: 'fruit/sweet', strength: 'weak', archetype: 'nature' },
    'plum': { meaning: 'fruit', strength: 'weak', archetype: 'nature' },
    'radar': { meaning: 'detection', strength: 'strong', archetype: 'tool' },
    'probe': { meaning: 'investigation', strength: 'strong', archetype: 'tool' },
    'relay': { meaning: 'pass-through', strength: 'medium', archetype: 'tool' },
    'lens': { meaning: 'focus/vision', strength: 'medium', archetype: 'tool' },
  };

  // Check compound words
  for (const [key, val] of Object.entries(meanings)) {
    if (name === key) return val;
    if (name.startsWith(key) && name.length > key.length) {
      const rest = name.slice(key.length);
      const restMeaning = meanings[rest];
      if (restMeaning) {
        return { meaning: val.meaning + ' + ' + restMeaning.meaning, strength: 'strong', archetype: val.archetype + '+' + restMeaning.archetype };
      }
      return { ...val, meaning: val.meaning + ' + ' + rest };
    }
    if (name.endsWith(key) && name.length > key.length) {
      const prefix = name.slice(0, -key.length);
      const prefixMeaning = meanings[prefix];
      if (prefixMeaning) {
        return { meaning: prefixMeaning.meaning + ' + ' + val.meaning, strength: 'strong', archetype: prefixMeaning.archetype + '+' + val.archetype };
      }
      return { ...val, meaning: prefix + ' + ' + val.meaning };
    }
  }

  return { meaning: name, strength: 'weak', archetype: 'unknown' };
}

// Research-backed recommendation
function getRecommendation(concept, context, availableDomains) {
  const avail = availableDomains.filter(d => d.status === 'available');
  const taken = availableDomains.filter(d => d.status === 'taken');

  let rec = '';
  if (avail.length === 0) {
    rec = 'All exact domains are taken. Try adding a suffix or prefix.';
  } else {
    const cheapest = avail.sort((a, b) => (a.registration || 999) - (b.registration || 999))[0];
    const cheapestTld = cheapest.domain.split('.').pop();
    rec = cheapest.domain + ' is available at $' + (cheapest.registration || 0).toFixed(2) + '/yr — the cheapest option.';
    if (cheapestTld !== 'com') {
      rec += ' .com is taken.';
    }
  }
  return rec;
}
// === TLD PRICING CACHE ===
// Based on real registrar pricing (updated 2026-08-21)
// Source: TLD-List, Cloudflare, Porkbun, Dynadot, Namecheap
// Only .com pricing is authoritative; others are approximate market rates.

const TLD_PRICING = {
  com: {
    porkbun:    { registration: 11.08, renewal: 11.08, transfer: 11.08, privacy: 0, promo: null, updated: '2026-08-21' },
    cloudflare: { registration: 10.44, renewal: 10.44, transfer: 10.44, privacy: 0, promo: null, updated: '2026-08-21' },
    namecheap:  { registration: 9.58,  renewal: 13.98, transfer: 9.58,  privacy: 2.88, promo: null, updated: '2026-08-21' },
    dynadot:    { registration: 9.99,  renewal: 9.99,  transfer: 9.99,  privacy: 0, promo: null, updated: '2026-08-21' },
  },
  dev: {
    porkbun:    { registration: 14.99, renewal: 14.99, transfer: 14.99, privacy: 0, promo: null, updated: '2026-08-21' },
    cloudflare: { registration: 12.00, renewal: 12.00, transfer: 12.00, privacy: 0, promo: null, updated: '2026-08-21' },
    namecheap:  { registration: 14.98, renewal: 14.98, transfer: 14.98, privacy: 0, promo: null, updated: '2026-08-21' },
    dynadot:    { registration: 13.99, renewal: 13.99, transfer: 13.99, privacy: 0, promo: null, updated: '2026-08-21' },
  },
  io: {
    porkbun:    { registration: 44.99, renewal: 44.99, transfer: 44.99, privacy: 0, promo: null, updated: '2026-08-21' },
    cloudflare: { registration: 44.00, renewal: 44.00, transfer: 44.00, privacy: 0, promo: null, updated: '2026-08-21' },
    namecheap:  { registration: 32.98, renewal: 32.98, transfer: 32.98, privacy: 0, promo: null, updated: '2026-08-21' },
    dynadot:    { registration: 42.99, renewal: 42.99, transfer: 42.99, privacy: 0, promo: null, updated: '2026-08-21' },
  },
  ai: {
    porkbun:    { registration: 89.99, renewal: 89.99, transfer: 89.99, privacy: 0, promo: null, updated: '2026-08-21' },
    cloudflare: { registration: 84.00, renewal: 84.00, transfer: 84.00, privacy: 0, promo: null, updated: '2026-08-21' },
    namecheap:  { registration: 74.98, renewal: 74.98, transfer: 74.98, privacy: 0, promo: null, updated: '2026-08-21' },
    dynadot:    { registration: 79.99, renewal: 79.99, transfer: 79.99, privacy: 0, promo: null, updated: '2026-08-21' },
  },
  xyz: {
    porkbun:    { registration: 1.15,  renewal: 11.99, transfer: 11.99, privacy: 0, promo: 'first year $1.15', updated: '2026-08-21' },
    cloudflare: { registration: 12.00, renewal: 12.00, transfer: 12.00, privacy: 0, promo: null, updated: '2026-08-21' },
    namecheap:  { registration: 1.98,  renewal: 12.98, transfer: 12.98, privacy: 0, promo: 'first year $1.98', updated: '2026-08-21' },
    dynadot:    { registration: 12.99, renewal: 12.99, transfer: 12.99, privacy: 0, promo: null, updated: '2026-08-21' },
  },
  co: {
    porkbun:    { registration: 29.99, renewal: 29.99, transfer: 29.99, privacy: 0, promo: null, updated: '2026-08-21' },
    cloudflare: { registration: 30.00, renewal: 30.00, transfer: 30.00, privacy: 0, promo: null, updated: '2026-08-21' },
    namecheap:  { registration: 9.98,  renewal: 29.98, transfer: 29.98, privacy: 0, promo: null, updated: '2026-08-21' },
    dynadot:    { registration: 27.99, renewal: 27.99, transfer: 27.99, privacy: 0, promo: null, updated: '2026-08-21' },
  },
  app: {
    porkbun:    { registration: 14.99, renewal: 14.99, transfer: 14.99, privacy: 0, promo: null, updated: '2026-08-21' },
    cloudflare: { registration: 12.00, renewal: 12.00, transfer: 12.00, privacy: 0, promo: null, updated: '2026-08-21' },
    namecheap:  { registration: 14.98, renewal: 14.98, transfer: 14.98, privacy: 0, promo: null, updated: '2026-08-21' },
    dynadot:    { registration: 13.99, renewal: 13.99, transfer: 13.99, privacy: 0, promo: null, updated: '2026-08-21' },
  },
  net: {
    porkbun:    { registration: 11.49, renewal: 11.49, transfer: 11.49, privacy: 0, promo: null, updated: '2026-08-21' },
    cloudflare: { registration: 10.44, renewal: 10.44, transfer: 10.44, privacy: 0, promo: null, updated: '2026-08-21' },
    namecheap:  { registration: 11.98, renewal: 14.98, transfer: 11.98, privacy: 0, promo: null, updated: '2026-08-21' },
    dynadot:    { registration: 10.99, renewal: 10.99, transfer: 10.99, privacy: 0, promo: null, updated: '2026-08-21' },
  },
  org: {
    porkbun:    { registration: 11.49, renewal: 11.49, transfer: 11.49, privacy: 0, promo: null, updated: '2026-08-21' },
    cloudflare: { registration: 10.44, renewal: 10.44, transfer: 10.44, privacy: 0, promo: null, updated: '2026-08-21' },
    namecheap:  { registration: 9.98,  renewal: 13.98, transfer: 9.98,  privacy: 0, promo: null, updated: '2026-08-21' },
    dynadot:    { registration: 10.49, renewal: 10.49, transfer: 10.49, privacy: 0, promo: null, updated: '2026-08-21' },
  },
  sh: {
    porkbun:    { registration: 39.99, renewal: 39.99, transfer: 39.99, privacy: 0, promo: null, updated: '2026-08-21' },
    cloudflare: { registration: 39.00, renewal: 39.00, transfer: 39.00, privacy: 0, promo: null, updated: '2026-08-21' },
    namecheap:  { registration: 39.98, renewal: 39.98, transfer: 39.98, privacy: 0, promo: null, updated: '2026-08-21' },
    dynadot:    { registration: 38.99, renewal: 38.99, transfer: 38.99, privacy: 0, promo: null, updated: '2026-08-21' },
  },
};

// Buy links for each registrar
const BUY_LINK = {
  porkbun:    d => 'https://porkbun.com/products/domains?search=' + encodeURIComponent(d),
  cloudflare: d => 'https://www.cloudflare.com/products/registrar/',
  namecheap:  d => 'https://www.namecheap.com/domains/registration/results.aspx?domain=' + encodeURIComponent(d),
  dynadot:    d => 'https://www.dynadot.com/domain/search?domain=' + encodeURIComponent(d),
};

const REGISTRAR_NAMES = { porkbun: 'Porkbun', cloudflare: 'Cloudflare', namecheap: 'Namecheap', dynadot: 'Dynadot' };

// === REGISTRAR COMPARISON ===

async function compareRegistrars(domain) {
  const tld = domain.split('.').pop();
  const pricing = TLD_PRICING[tld];
  if (!pricing) return { domain, quotes: [], best_year_1: null, best_5_year: null };

  const quotes = Object.entries(pricing).map(([reg, p]) => {
    const year_1 = p.registration + p.privacy;
    const year_2_5 = p.renewal * 4;
    return {
      registrar: reg,
      registrar_name: REGISTRAR_NAMES[reg] || reg,
      domain,
      registration: p.registration,
      renewal: p.renewal,
      transfer: p.transfer,
      privacy: p.privacy,
      promo: p.promo,
      currency: 'USD',
      year_1_cost: year_1,
      year_2_5_cost: year_2_5,
      total_5_year: year_1 + year_2_5,
      buy_url: BUY_LINK[reg] ? BUY_LINK[reg](domain) : null,
      updated: p.updated,
    };
  });

  quotes.sort((a, b) => a.total_5_year - b.total_5_year);

  return {
    domain,
    tld,
    pricing_freshness: pricing[Object.keys(pricing)[0]]?.updated || 'unknown',
    quotes,
    best_year_1: quotes[0],
    best_5_year: quotes[0],
    checked_at: new Date().toISOString(),
  };
}

// === DOMAIN INTELLIGENCE RECORD ===

function createIntelligenceRecord(domain, verification, scoring, registrar) {
  return {
    domain,
    identity: {
      tokens: domain.split('.')[0].split(/[-]/),
      length: domain.split('.')[0].length,
      tld: domain.split('.')[1]
    },
    meaning: scoring.meaning,
    scores: {
      total: scoring.score,
      agent_native: scoring.meaning.agentNative,
      developer_native: scoring.meaning.developerNative
    },
    availability: {
      status: verification.registration.status,
      confidence: verification.registration.confidence,
      authoritative: verification.registration.authoritative,
      verified_at: verification.registration.verified_at
    },
    cost: registrar ? {
      best_year_1: registrar.best_year_1,
      best_5_year: registrar.best_5_year,
      quotes: registrar.quotes
    } : null,
    history: {
      first_checked: new Date().toISOString(),
      availability_changes: []
    },
    demand: {
      search_appearances: 0,
      favorites: 0,
      registrar_clicks: 0
    }
  };
}

// === SEARCH ANALYTICS ===

const searchStore = new Map();
const clickStore = new Map();

function trackSearch(query, results) {
  const id = `search-${Date.now()}`;
  searchStore.set(id, { query, results: results.length, timestamp: new Date().toISOString() });
  return id;
}

function trackClick(searchId, domain) {
  const clicks = clickStore.get(domain) || 0;
  clickStore.set(domain, clicks + 1);
  return { domain, total_clicks: clicks + 1 };
}

function getAnalytics() {
  return {
    total_searches: searchStore.size,
    total_clicks: [...clickStore.values()].reduce((a, b) => a + b, 0),
    top_domains: [...clickStore.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10)
  };
}

// === MCP HANDLER ===

async function handleMcp(body) {
  const { method, params, id } = body;
  
  if (method === 'tools/list') {
    return { jsonrpc: '2.0', id, result: { tools: [
      { name: 'verify_domain', description: 'Full verification pipeline: DNS + RDAP + status', inputSchema: { type: 'object', properties: { domain: { type: 'string' } }, required: ['domain'] } },
      { name: 'generate_domains', description: 'Generate domain candidates from concept. Packs: default, sanskrit, tech, animals, nature', inputSchema: { type: 'object', properties: { concept: { type: 'string' }, tlds: { type: 'array', items: { type: 'string' } }, pack: { type: 'string', enum: ['default', 'sanskrit', 'tech', 'animals', 'nature'] } }, required: ['concept'] } },
      { name: 'score_domain', description: 'Score domain with semantic meaning', inputSchema: { type: 'object', properties: { domain: { type: 'string' }, intent: { type: 'string' } }, required: ['domain', 'intent'] } },
      { name: 'compare_registrars', description: 'Compare domain prices across registrars', inputSchema: { type: 'object', properties: { domain: { type: 'string' } }, required: ['domain'] } },
      { name: 'mine_domains', description: 'Full pipeline: generate + verify + score + compare. Packs: default, sanskrit, tech, animals, nature', inputSchema: { type: 'object', properties: { concept: { type: 'string' }, intent: { type: 'string' }, tlds: { type: 'array', items: { type: 'string' } }, pack: { type: 'string', enum: ['default', 'sanskrit', 'tech', 'animals', 'nature'] } }, required: ['concept', 'intent'] } },
      { name: 'get_analytics', description: 'Get search and click analytics', inputSchema: { type: 'object', properties: {} } }
    ]}};
  }
  
  if (method === 'tools/call') {
    const { name, arguments: args } = params;
    
    if (name === 'verify_domain') {
      const result = await verifyDomain(args.domain);
      return { jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] } };
    }
    
    if (name === 'generate_domains') {
      const candidates = getVariantCandidates(args.concept, args.tlds, args.pack);
      return { jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: JSON.stringify({ concept: args.concept, pack: args.pack || 'default', candidates, count: candidates.length }, null, 2) }] } };
    }
    
    if (name === 'score_domain') {
      const { score, meaning } = scoreDomain(args.domain, args.intent);
      return { jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: JSON.stringify({ domain: args.domain, intent: args.intent, score, meaning }, null, 2) }] } };
    }
    
    if (name === 'compare_registrars') {
      const result = await compareRegistrars(args.domain);
      return { jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] } };
    }
    
    if (name === 'mine_domains') {
      const candidates = getVariantCandidates(args.concept, args.tlds, args.pack);
      const verified = [];
      for (const c of candidates.slice(0, 20)) {
        const v = await verifyDomain(c);
        if (v.registration.status === 'available') {
          const { score, meaning } = scoreDomain(c, args.intent);
          const registrar = await compareRegistrars(c);
          verified.push({ ...v, score, meaning, registrar: registrar.best_5_year });
        }
      }
      verified.sort((a, b) => b.score - a.score);
      const searchId = trackSearch(args.concept, verified);
      return { jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: JSON.stringify({ concept: args.concept, intent: args.intent, pack: args.pack || 'default', total_candidates: candidates.length, available: verified.length, search_id: searchId, results: verified.slice(0, 10) }, null, 2) }] } };
    }
    
    if (name === 'get_analytics') {
      return { jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: JSON.stringify(getAnalytics(), null, 2) }] } };
    }
  }
  
  return { jsonrpc: '2.0', id, error: { code: -32601, message: 'Method not found' } };
}

// === LANDING PAGE ===

const LLMS_TXT = `# Domain Intelligence Engine

> Verify domain availability via DNS + RDAP, generate candidates, compare registrar prices.

## MCP Tools

- verify_domain — Full verification pipeline: DNS probe + RDAP registration check
- generate_domains — Generate domain candidates from a concept + TLDs
- score_domain — Score a domain by semantic meaning, length, TLD
- compare_registrars — Compare domain prices across registrars
- mine_domains — Full pipeline: generate + verify + score + compare
- get_analytics — Search and click analytics

## API

GET /api/verify/:domain — Verify domain (DNS + RDAP)
GET /api/registrar/:domain — Compare registrar prices
POST /api/mine — Mine domains (full pipeline)
GET /api/health — Health check
POST /mcp — MCP endpoint (JSON-RPC)

## Links

- GitHub: https://github.com/prx0r/domainnamechecker
- API Docs: /docs/api
- MCP Docs: /docs/mcp`;

const LANDING_PAGE = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Domain Intelligence Engine</title>
  <meta name="description" content="Check domain availability via DNS + RDAP, generate candidates, compare registrar prices.">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://domainnamechecker.dev/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@300;400;500&display=swap" rel="stylesheet">
  <script type="application/ld+json">{"@context":"https://schema.org","@type":"SoftwareApplication","name":"Domain Intelligence Engine","url":"https://domainnamechecker.tradesprior.workers.dev","applicationCategory":"DeveloperApplication","operatingSystem":"Web","description":"Check domain availability via DNS + RDAP, generate candidates, compare registrar prices","offers":{"@type":"Offer","price":"0","priceCurrency":"USD"}}</script>
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
    .curr{border:1px solid #ccc;padding:.75rem .5rem;background:transparent;font-family:'Source Code Pro',monospace;font-size:.75rem;cursor:pointer;outline:none;min-width:70px}
    .status{font-size:.6875rem;color:#999;margin-top:.75rem;min-height:1.2em}
    .section{margin-top:2rem}
    .section-label{font-size:.625rem;color:#999;text-transform:uppercase;letter-spacing:.12em;margin-bottom:.75rem;font-weight:500}
    table{width:100%;border-collapse:collapse}
    tr.row{cursor:pointer;transition:background .1s}
    tr.row:hover{background:#f0f0f0}
    td{padding:.625rem 0;border-bottom:1px solid #eee;font-size:.8125rem}
    td:first-child{font-weight:500}
    .avail{color:#166534;font-weight:500;font-size:.75rem}
    .taken{color:#999;font-size:.75rem}
    .verified{font-size:.625rem;color:#166534;font-weight:500;margin-left:.3rem}
    .unverified{font-size:.625rem;color:#92400e;margin-left:.3rem}
    .price-col{text-align:right;color:#666;font-size:.75rem}
    .buy{font-size:.6875rem;color:#111;border:1px solid #ccc;padding:.25rem .625rem;display:inline-block}
    .buy:hover{border-color:#111;text-decoration:none}
    .expand{display:none}
    .expand.open{display:table-row}
    .taken-row td:first-child{color:#999}
    .expand td{padding:.5rem 0 .75rem 0;border-bottom:1px solid #eee}
    .reg-card{padding:.5rem 0}
    .reg-card+.reg-card{border-top:1px solid #f5f5f5}
    .reg-top{display:flex;justify-content:space-between;align-items:center}
    .reg-name{font-weight:500;font-size:.8125rem}
    .reg-prices{font-size:.75rem;color:#666;margin-top:.25rem}
    .reg-meta{font-size:.625rem;color:#999;margin-top:.25rem;display:flex;gap:1rem;flex-wrap:wrap}
    .promo{color:#166534;font-weight:500}
    .tag{font-size:.625rem;padding:.125rem .375rem;border:1px solid #eee;display:inline-block}
    .tag.privacy{border-color:#166534;color:#166534}
    .toggle{font-size:.6875rem;color:#999;cursor:pointer;border:1px solid #ccc;padding:.375rem .75rem;background:transparent;font-family:'Source Code Pro',monospace;margin-top:1.5rem;display:inline-block}
    .toggle:hover{border-color:#111;color:#111}
    .toggle.on{background:#111;color:#fff;border-color:#111}
    .empty{color:#999;font-size:.75rem;padding:1rem 0}
    .error{color:#991b1b;font-size:.75rem;padding:1rem 0}
    .sep{margin-top:1.5rem;border-top:1px solid #eee;padding-top:1.5rem}
    footer{margin-top:4rem;padding-top:1rem;border-top:1px solid #eee;font-size:.625rem;color:#bbb;display:flex;justify-content:space-between}
    footer a{color:#999}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>domain search</h1>
    <div class="top-row">
      <div class="search">
        <input type="text" id="q" placeholder="is agentseo available? or search for tools">
        <button id="go">search</button>
      </div>
      <select class="curr" id="cur">
        <option value="USD">$ USD</option>
        <option value="GBP">£ GBP</option>
        <option value="EUR">€ EUR</option>
        <option value="AUD">A$ AUD</option>
        <option value="CAD">C$ CAD</option>
        <option value="JPY">¥ JPY</option>
      </select>
      <select class="curr" id="pack" title="variant pack">
        <option value="default">default</option>
        <option value="sanskrit">sanskrit</option>
        <option value="tech">tech</option>
        <option value="animals">animals</option>
        <option value="nature">nature</option>
      </select>
    </div>
    <div class="status" id="st"></div>
    <div id="out"></div>
    <footer>
      <span>v3.2.0</span>
      <span><a href="/llms.txt">llms.txt</a> · <a href="/docs/api">api</a> · <a href="/docs/mcp">mcp</a></span>
    </footer>
  </div>
  <script>
    const $=s=>document.querySelector(s);
    const RATES={USD:1,GBP:0.79,EUR:0.92,AUD:1.53,CAD:1.36,JPY:149.5};
    const SYM={USD:'$',GBP:'£',EUR:'€',AUD:'A$',CAD:'C$',JPY:'¥'};
    function isDomain(s){s=s.trim().toLowerCase();return /^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\\.[a-z]{2,})+$/.test(s)&&s.includes('.')&&s.split('.').pop().length>=2}
    function pv(v){if(v==null)return'—';const c=$('#cur').value;const conv=v*RATES[c];return SYM[c]+(conv>=100?Math.round(conv):conv.toFixed(2))}

    async function loadPricing(domain,td){
      if(td.dataset.loaded)return;td.dataset.loaded='1';
      td.innerHTML='<span style="color:#999;font-size:.625rem">loading...</span>';
      try{
        const r=await fetch('/api/registrar/'+encodeURIComponent(domain));
        const p=await r.json();
        if(!p.quotes||!p.quotes.length){td.innerHTML='<span style="color:#999;font-size:.6875rem">no pricing</span>';return;}
        let h='';
        for(const q of p.quotes){
          h+='<div class="reg-card"><div class="reg-top"><span class="reg-name">'+q.registrar_name+'</span><span>'+pv(q.registration)+' 1st yr</span></div>';
          h+='<div class="reg-prices">renewal '+pv(q.renewal)+'/yr · transfer '+pv(q.transfer)+'</div>';
          h+='<div class="reg-meta">';
          if(q.privacy>0)h+='<span class="tag">privacy '+pv(q.privacy)+'</span>';
          else h+='<span class="tag privacy">free privacy</span>';
          h+='<span>5yr total '+pv(q.total_5_year)+'</span>';
          if(q.promo)h+='<span class="promo">'+q.promo+'</span>';
          h+='</div>';
          h+='<div style="margin-top:.375rem">'+(q.buy_url?'<a href="'+q.buy_url+'" target="_blank" class="buy">buy at '+q.registrar_name+' →</a>':'')+'</div></div>';
        }
        td.innerHTML=h;
      }catch(e){td.innerHTML='<span style="color:#991b1b;font-size:.6875rem">'+e.message+'</span>';}
    }

    function makeRows(rows,showScore){
      let h='';
      for(const r of rows){
        const id=r.domain.replace(/\\./g,'-');
        h+='<tr class="row" onclick="toggle(\\''+id+'\\',\\''+r.domain+'\\')">';
        h+='<td>'+r.domain+'</td>';
        h+='<td>'+(r.status==='available'?'<span class="avail">available</span>':'<span class="taken">taken</span>')+'</td>';
        if(showScore)h+='<td style="color:#999;font-size:.75rem">'+(r.score||'')+'</td>';
        h+='<td class="price-col">from '+pv(r.registration)+'/yr</td>';
        h+='<td>'+(r.buy_url&&r.status==='available'?'<a href="'+r.buy_url+'" target="_blank" class="buy" onclick="event.stopPropagation()">buy →</a>':'')+'</td>';
        h+='</tr>';
        h+='<tr class="expand" id="'+id+'"><td colspan="'+(showScore?5:4)+'"><div id="p-'+id+'"></div></td></tr>';
      }
      return h;
    }
    window.toggle=function(id,domain){
      const el=document.getElementById(id);if(!el)return;
      el.classList.toggle('open');
      if(el.classList.contains('open'))loadPricing(domain,document.getElementById('p-'+id));
    };

    let showV=true,exactD=[],varD=[];
    function renderAll(q){
      const av=exactD.filter(r=>r.status==='available');
      const tk=exactD.filter(r=>r.status!=='available');
      let h='<div class="section">';
      h+='<div class="section-label">'+q+' — available</div>';
      h+=av.length?'<table>'+makeRows(av,false)+'</table>':'<div class="empty">none available</div>';
      h+='<div class="sep"></div>';
      h+='<div class="section-label">'+q+' — taken</div>';
      h+=tk.length?'<table>'+makeRows(tk,false)+'</table>':'<div class="empty">all available!</div>';
      h+='</div>';
      h+='<button class="toggle'+(showV?' on':'')+'" onclick="toggleV()">'+(showV?'hide variants':'show variants')+'</button>';
      if(showV&&varD.length){
        const va=varD.filter(r=>r.status==='available');
        h+='<div class="section" style="margin-top:1rem"><div class="section-label">variants — '+va.length+' available</div>';
        h+='<table>'+makeRows(varD,true)+'</table></div>';
      }
      out.innerHTML=h;
    }
    window.toggleV=function(){showV=!showV;renderAll($('#q').value.trim());};
    let searchCount=parseInt(localStorage.getItem('dn searches')||'0');
    function trackSearch(q){searchCount++;localStorage.setItem('dn searches',searchCount);const el=document.getElementById('analytics');if(el)el.textContent=searchCount+' searches';}
    window.addEventListener('load',()=>{const el=document.getElementById('analytics');if(el&&searchCount)el.textContent=searchCount+' searches';});

    async function search(){
      const q=$('#q').value.trim();if(!q)return;
      const st=$('#st'),out=$('#out');
      exactD=[];varD=[];showV=false;out.innerHTML='';
      if(isDomain(q)){
        st.textContent='checking...';
        try{
          const r=await fetch('/api/check/'+encodeURIComponent(q));
          const d=await r.json();
          st.textContent='';
          const isAvail=d.status==='AVAILABLE';
          let h='<div class="section"><span style="font-weight:500">'+d.domain+'</span> '+(isAvail?'<span class="avail">available</span>':'<span class="taken">taken</span>');
          h+='<div style="font-size:.6875rem;color:#999;margin-top:.25rem">source: '+d.proof.source+(d.proof.authoritative?' (authoritative)':'')+'</div>';
          if(d.registrar_links&&d.registrar_links.length){
            h+='<div style="margin-top:1rem"><div class="section-label">check at</div>';
            h+='<div style="display:flex;flex-wrap:wrap;gap:.5rem">';
            for(const rl of d.registrar_links){h+='<a href="'+rl.url+'" target="_blank" style="font-size:.6875rem;color:#111;border:1px solid #ccc;padding:.25rem .625rem;text-decoration:none">'+rl.name+' →</a>'}
            h+='</div></div>'}
          h+='</div>';out.innerHTML=h;
        }catch(err){st.textContent='';out.innerHTML='<div class="error">'+err.message+'</div>'}
      }
    }
    $('#go').addEventListener('click',search);
    $('#q').addEventListener('keydown',e=>{if(e.key==='Enter')search()});
    $('#cur').addEventListener('change',()=>{if($('#q').value.trim())search()});
  </script>
</body>
</html>`;

// === V4 ENGINE (additive) ===
const STATUS={AVAILABLE:'AVAILABLE',TAKEN:'TAKEN',PREMIUM:'PREMIUM',UNAVAILABLE:'UNAVAILABLE',UNSUPPORTED:'UNSUPPORTED',UNVERIFIED:'UNVERIFIED'};
function normalizeDomain(d){return d.toLowerCase().trim()}
const RDAP={com:'https://rdap.verisign.com/com/v1/domain/',net:'https://rdap.verisign.com/net/v1/domain/',org:'https://rdap.publicinterestregistry.org/rdap/domain/',io:'https://rdap.identitydigital.services/rdap/domain/',dev:'https://pubapi.registry.google/rdap/domain/',app:'https://pubapi.registry.google/rdap/domain/',xyz:'https://rdap.centralnic.com/xyz/domain/',ai:'https://rdap.identitydigital.services/rdap/domain/',co:'https://rdap.nic.co/domain/',sh:'https://rdap.identitydigital.services/rdap/domain/'};
function v4CfCheck(domains){if(!CF_AI_TOKEN||!CF_ACCOUNT_ID)return Promise.resolve([]);const all=[];let chain=Promise.resolve();for(let i=0;i<domains.length;i+=20){const batch=domains.slice(i,i+20);chain=chain.then(()=>fetch('https://api.cloudflare.com/client/v4/accounts/'+CF_ACCOUNT_ID+'/registrar/domain-check',{method:'POST',headers:{'Authorization':'Bearer '+CF_AI_TOKEN,'Content-Type':'application/json'},body:JSON.stringify({domains:batch})}).then(r=>{if(!r.ok){batch.forEach(d=>all.push({domain:d,status:STATUS.UNVERIFIED,proof:{source:'cf_registry',authoritative:false,error:'API '+r.status}}));return}return r.json()}).then(data=>{if(!data.success||!data.result||!data.result.domains){batch.forEach(d=>all.push({domain:d,status:STATUS.UNVERIFIED,proof:{source:'cf_registry',authoritative:false,error:'bad response'}}));return}data.result.domains.forEach(item=>{if(item.registrable)all.push({domain:item.name,status:STATUS.AVAILABLE,proof:{source:'cf_registry',authoritative:true}});else if(item.reason==='domain_unavailable')all.push({domain:item.name,status:STATUS.TAKEN,proof:{source:'cf_registry',authoritative:true,reason:item.reason}});else if(item.reason==='domain_premium')all.push({domain:item.name,status:STATUS.PREMIUM,proof:{source:'cf_registry',authoritative:true,reason:item.reason}});else if(item.reason==='extension_disallows_registration')all.push({domain:item.name,status:STATUS.UNAVAILABLE,proof:{source:'cf_registry',authoritative:true,reason:item.reason}});else all.push({domain:item.name,status:STATUS.UNVERIFIED,proof:{source:'cf_registry',authoritative:false,reason:item.reason||'unknown'}})})}).catch(e=>{batch.forEach(d=>all.push({domain:d,status:STATUS.UNVERIFIED,proof:{source:'cf_registry',authoritative:false,error:e.message}}))}))}return chain.then(()=>all)}
function v4RdapCheck(domain){const tld=domain.split('.').pop();const base=RDAP[tld];if(!base)return Promise.resolve({domain,status:STATUS.UNSUPPORTED,proof:{source:'rdap',error:'No RDAP for .'+tld}});const c=new AbortController();const t=setTimeout(()=>c.abort(),5000);return fetch(base+domain,{signal:c.signal}).then(r=>{clearTimeout(t);if(r.status===200)return r.json().then(d=>({domain,status:d.status&&d.status.length>0?STATUS.TAKEN:STATUS.UNVERIFIED,proof:{source:'rdap',authoritative:true,registered:d.status&&d.status.length>0?true:null}}));if(r.status===404)return{domain,status:STATUS.AVAILABLE,proof:{source:'rdap',authoritative:true,registered:false}};return{domain,status:STATUS.UNVERIFIED,proof:{source:'rdap',error:'HTTP '+r.status}}}).catch(e=>{clearTimeout(t);return{domain,status:STATUS.UNVERIFIED,proof:{source:'rdap',error:e.name==='AbortError'?'timeout':e.message}}})}
function v4CheckDomains(domains){domains=domains.map(normalizeDomain);const valid=domains.filter(validateDomain);const invalid=domains.filter(d=>!validateDomain(d));const results=invalid.map(d=>({domain:d,status:STATUS.UNSUPPORTED,proof:{source:'validation',error:'invalid format'}}));return v4CfCheck(valid).then(cf=>{results.push(...cf);const un=cf.filter(r=>r.status===STATUS.UNVERIFIED).map(r=>r.domain);if(!un.length)return results;return Promise.all(un.map(v4RdapCheck)).then(rr=>{rr.forEach(r=>{const i=results.findIndex(x=>x.domain===r.domain);if(i!==-1&&results[i].status===STATUS.UNVERIFIED){if(r.status!==STATUS.UNVERIFIED)results[i]=r;else results[i].proof.note='No claim made.'}});return results})})}
function v4MakeResult(d,s,p){return{domain:d,status:s,proof:{source:p.source||'unknown',authoritative:p.authoritative||false,checked_at:new Date().toISOString(),...p},registrar_links:[{name:'Porkbun',url:'https://porkbun.com/products/domains?search='+encodeURIComponent(d)},{name:'Namecheap',url:'https://www.namecheap.com/domains/registration/results.aspx?domain='+encodeURIComponent(d)},{name:'Dynadot',url:'https://www.dynadot.com/domain/search?domain='+encodeURIComponent(d)},{name:'Cloudflare',url:'https://domains.cloudflare.com/?query='+encodeURIComponent(d)}]}}

// === HTTP HANDLER ===

const corsHeaders = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type' };

async function handleRequest(request) {
  const url = new URL(request.url);
  const path = url.pathname;
  
  if (request.method === 'OPTIONS') return new Response(null, { headers: corsHeaders });
  
  // Health
  if (path === '/api/health') return Response.json({ status: 'healthy', version: '4.0.0', endpoints: ['GET /api/verify/:domain', 'GET /api/check/:domain', 'POST /api/check', 'GET /api/health'] }, { headers: corsHeaders });

  // V4 check
  if (path.startsWith('/api/check/') && request.method === 'GET') {
    const domain = normalizeDomain(decodeURIComponent(path.split('/api/check/')[1]));
    if (!validateDomain(domain)) return Response.json({ error: { code: 'INVALID_DOMAIN', message: 'Invalid domain format' } }, { status: 400, headers: corsHeaders });
    const t0 = Date.now();
    const results = await v4CheckDomains([domain]);
    const r = results[0];
    const result = v4MakeResult(r.domain, r.status, r.proof);
    result.latency_ms = Date.now() - t0;
    return Response.json(result, { headers: corsHeaders });
  }

  // V4 bulk check
  if (path === '/api/check' && request.method === 'POST') {
    const { domains } = await request.json();
    if (!Array.isArray(domains) || domains.length === 0) return Response.json({ error: { code: 'INVALID_INPUT', message: 'domains must be a non-empty array' } }, { status: 400, headers: corsHeaders });
    if (domains.length > 20) return Response.json({ error: { code: 'LIMIT_EXCEEDED', message: 'max 20 domains' } }, { status: 400, headers: corsHeaders });
    const norm = domains.map(normalizeDomain);
    const inv = norm.filter(d => !validateDomain(d));
    if (inv.length > 0) return Response.json({ error: { code: 'INVALID_DOMAIN', message: 'invalid: ' + inv.join(', ') } }, { status: 400, headers: corsHeaders });
    const t0 = Date.now();
    const results = await v4CheckDomains(norm);
    const mapped = results.map(r => v4MakeResult(r.domain, r.status, r.proof));
    return Response.json({ results: mapped, metadata: { total: domains.length, latency_ms: Date.now() - t0 } }, { headers: corsHeaders });
  }
  
  // Verify endpoint
  if (path.startsWith('/api/verify/') && request.method === 'GET') {
    const domain = decodeURIComponent(path.split('/api/verify/')[1]);
    if (!validateDomain(domain)) {
      return Response.json({ error: { code: 'INVALID_DOMAIN', message: 'Invalid domain format' } }, { status: 400, headers: corsHeaders });
    }
    return Response.json(await verifyDomain(domain), { headers: corsHeaders });
  }
  
  // Registrar comparison
  if (path.startsWith('/api/registrar/') && request.method === 'GET') {
    const domain = decodeURIComponent(path.split('/api/registrar/')[1]);
    if (!validateDomain(domain)) {
      return Response.json({ error: { code: 'INVALID_DOMAIN', message: 'Invalid domain format' } }, { status: 400, headers: corsHeaders });
    }
    return Response.json(await compareRegistrars(domain), { headers: corsHeaders });
  }
  
  // Mine endpoint — exact domain first, then variants
  if (path === '/api/mine' && request.method === 'POST') {
    const { concept, intent, tlds, pack } = await request.json();
          const name = concept.toLowerCase().replace(/[^a-z0-9-]/g, '');

    // 1. Check exact domain across all TLDs
    const allTlds = ['com', 'org', 'net', 'dev', 'io', 'ai', 'xyz', 'co', 'app', 'sh'];
    const exactChecks = allTlds.map(t => name + '.' + t);
    const exactResults = [];
    for (let i = 0; i < exactChecks.length; i += 10) {
      const chunk = exactChecks.slice(i, i + 10);
      const v = await Promise.all(chunk.map(c => verifyDomain(c)));
      exactResults.push(...chunk.map((c, j) => ({ domain: c, v: v[j] })));
    }
    const exact = exactResults.map(({ domain: d, v }) => {
      const tld = d.split('.').pop();
      const p = TLD_PRICING[tld]?.cloudflare;
      return {
        domain: d,
        status: v.registration.status,
        confidence: v.registration.confidence,
        registrar: 'cloudflare',
        registration: p?.registration || null,
        renewal: p?.renewal || null,
        total_5_year: p ? (p.registration + p.privacy) + p.renewal * 4 : null,
        buy_url: BUY_LINK.cloudflare(d),
      };
    });

    // 2. Generate variant candidates
    const candidates = getVariantCandidates(concept, tlds, pack);
    const variantBatch = candidates.filter(c => !exactChecks.includes(c)).slice(0, 30);
    const verified = [];
    for (let i = 0; i < variantBatch.length; i += 10) {
      const chunk = variantBatch.slice(i, i + 10);
      const v = await Promise.all(chunk.map(c => verifyDomain(c)));
      verified.push(...chunk.map((c, j) => ({ domain: c, v: v[j] })));
    }
    const variants = verified.map(({ domain: d, v }) => {
      const { score, meaning } = scoreDomain(d, intent);
      const tld = d.split('.').pop();
      const p = TLD_PRICING[tld]?.cloudflare;
      return {
        domain: d,
        status: v.registration.status,
        confidence: v.registration.confidence,
        score,
        meaning,
        registration: p?.registration || null,
        renewal: p?.renewal || null,
        total_5_year: p ? (p.registration + p.privacy) + p.renewal * 4 : null,
        buy_url: BUY_LINK.cloudflare(d),
      };
    });
    variants.sort((a, b) => {
      if (a.status === 'available' && b.status !== 'available') return -1;
      if (a.status !== 'available' && b.status === 'available') return 1;
      return b.score - a.score;
    });

    return Response.json({
      concept, intent,
      exact,
      variants,
      total_exact: exact.length,
      exact_available: exact.filter(r => r.status === 'available').length,
      total_variants: variants.length,
      variants_available: variants.filter(r => r.status === 'available').length,
    }, { headers: corsHeaders });
  }
  
  // Bulk verify endpoint
  if (path === '/api/bulk-verify' && request.method === 'POST') {
    const { domains } = await request.json();
    if (!Array.isArray(domains) || domains.length === 0) {
      return Response.json({ error: { code: 'INVALID_INPUT', message: 'domains must be a non-empty array' } }, { status: 400, headers: corsHeaders });
    }
    if (domains.length > 50) {
      return Response.json({ error: { code: 'LIMIT_EXCEEDED', message: 'max 50 domains per request' } }, { status: 400, headers: corsHeaders });
    }
    const results = [];
    for (const domain of domains) {
      if (!validateDomain(domain)) {
        results.push({ domain, error: 'invalid domain format' });
        continue;
      }
      const v = await verifyDomain(domain);
      const p = await compareRegistrars(domain);
      results.push({ ...v, pricing: p });
    }
    return Response.json({
      results,
      metadata: { total: domains.length, verified: results.filter(r => !r.error).length, timestamp: new Date().toISOString() }
    }, { headers: corsHeaders });
  }
  
  // MCP
  if (path === '/mcp' && request.method === 'POST') {
    const body = await request.json();
    return Response.json(await handleMcp(body), { headers: corsHeaders });
  }
  
  // Streaming search endpoint — SSE
  if (path === '/api/search' && request.method === 'POST') {
    const { q, pack } = await request.json();
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        const send = (event, data) => {
          controller.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`));
        };

        // Parse intent with LLM
        const intent = await parseIntent(q);
        send('intent', { type: intent.type, query: q });

        if (intent.type === 'verify') {
          const domain = intent.domain;
          send('status', { msg: 'verifying ' + domain });
          const [v, p] = await Promise.all([
            verifyDomain(domain),
            compareRegistrars(domain)
          ]);
          send('domain', { type: 'verify', verification: v, pricing: p });

        } else {
          // Mine
          const concept = intent.concept || q;
    const name = concept.toLowerCase().replace(/[^a-z0-9-]/g, '');
          const tlds = ['com', 'net', 'org', 'io', 'dev', 'co', 'ai', 'xyz', 'app', 'sh'];

          // Stream context if LLM provided it
          if (intent.context) {
            send('context', { text: intent.context });
          }

          send('status', { msg: 'checking ' + name + '.*' });
          const exactResults = [];
          for (const tld of tlds) {
            const domain = name + '.' + tld;
            const v = await verifyDomain(domain);
            const p = TLD_PRICING[tld]?.cloudflare;
            const analysis = analyzeName(domain);
            const entry = {
              domain,
              status: v.registration.status,
              confidence: v.registration.confidence,
              registration: p?.registration || null,
              renewal: p?.renewal || null,
              total_5_year: p ? (p.registration + p.privacy) + p.renewal * 4 : null,
              buy_url: BUY_LINK.cloudflare(domain),
              meaning: analysis.meaning,
              archetype: analysis.archetype,
            };
            exactResults.push(entry);
            send('exact', entry);
          }

          // Send recommendation after exacts
          const rec = getRecommendation(concept, intent.context, exactResults);
          send('recommendation', { text: rec });

          send('status', { msg: 'generating variants' });
          const candidates = getVariantCandidates(concept, ['com'], pack);
          const batch = candidates.filter(c => !tlds.some(t => c === name + '.' + t)).slice(0, 25);
          for (let i = 0; i < batch.length; i += 5) {
            const chunk = batch.slice(i, i + 5);
            const results = await Promise.all(chunk.map(async c => {
              const v = await verifyDomain(c);
              const { score } = scoreDomain(c, 'get');
              const tld = c.split('.').pop();
              const p = TLD_PRICING[tld]?.cloudflare;
              const analysis = analyzeName(c);
              return {
                domain: c,
                status: v.registration.status,
                score,
                registration: p?.registration || null,
                renewal: p?.renewal || null,
                total_5_year: p ? (p.registration + p.privacy) + p.renewal * 4 : null,
                buy_url: BUY_LINK.cloudflare(c),
                meaning: analysis.meaning,
                archetype: analysis.archetype,
              };
            }));
            send('variants', results);
          }
        }
        send('done', {});
        controller.close();
      }
    });
    return new Response(stream, {
      headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', ...corsHeaders },
    });
  }
  
  // Static files
  if (path === '/llms.txt') return new Response(LLMS_TXT, { headers: { 'Content-Type': 'text/plain', ...corsHeaders } });
  if (path === '/robots.txt') return new Response('User-agent: *\nAllow: /\nSitemap: https://domainnamechecker.tradesprior.workers.dev/sitemap.xml', { headers: { 'Content-Type': 'text/plain', ...corsHeaders } });
  if (path === '/sitemap.xml') return new Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://domainnamechecker.tradesprior.workers.dev/</loc><changefreq>weekly</changefreq><priority>1</priority></url></urlset>', { headers: { 'Content-Type': 'application/xml', ...corsHeaders } });
  
  // Landing page
  if (path === '/') {
    return new Response(LANDING_PAGE, { headers: { 'Content-Type': 'text/html; charset=utf-8', ...corsHeaders } });
  }
  
  return Response.json({ error: { code: 'NOT_FOUND', message: 'Not found' } }, { status: 404, headers: corsHeaders });
}

addEventListener('fetch', event => { event.respondWith(handleRequest(event.request)); });
