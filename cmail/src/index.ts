import type { Env } from "./do";
import { routeAddress, threadId, classify, canDo, screenInjection } from "./lib";
import { handleMcp } from "./mcp";
export { MailboxDO } from "./do";

// POST /admin/* requires ADMIN (call with ?actor= mailbox id; default owner).
async function actorPerms(env: Env, actor: string): Promise<string[]> {
  if (!actor || actor === "owner") return ["ADMIN"];
  try {
    const row = await env.DB.prepare("SELECT permissions FROM mailboxes WHERE id=?").bind(actor).first();
    const perms = JSON.parse((row?.permissions as string) ?? '["READ","DRAFT"]');
    return Array.isArray(perms) ? perms : ["READ", "DRAFT"];
  } catch {
    return ["READ", "DRAFT"];
  }
}

export interface InboundMsg {
  to: string; from: string; subject: string; rawText: string; raw: any;
  waitUntil: (p: Promise<any>) => void;
}

// Shared pipeline: real Email Routing messages AND /test/ingest go through here.
async function processInbound(env: Env, m: InboundMsg): Promise<string> {
  const { to, from, subject, rawText } = m;
  const { domain, localPart } = routeAddress(to);
  const snippet = rawText.replace(/<[^>]*>/g, " ").slice(0, 2000);

  const c = await classify(env, subject, snippet);
  const tid = threadId(subject);
  const msgId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  // Injection screen BEFORE anything else touches this: quarantine can only
  // downgrade (never urgent, never webhooks, never agent corpora).
  const screen = screenInjection(subject, snippet);
  if (screen.quarantined) {
    c.classification = "quarantine";
    c.needs_reply = 0;
    c.importance = Math.min(c.importance, 3);
    c.summary = `[QUARANTINED: ${screen.reasons.join("; ")}] ${c.summary}`.slice(0, 500);
  }
  const r2Key = `email/raw/${domain}/${localPart}/${Date.now()}.eml`;
  if (m.raw) await env.RAW.put(r2Key, m.raw);

  // resolve alias → mailbox
  const alias = await env.DB.prepare("SELECT target_mailbox FROM aliases WHERE alias=?").bind(to.toLowerCase()).first();
  const mailboxId = (alias?.target_mailbox as string) ?? `${localPart}@${domain}`;
  const doId = env.MAILBOX.idFromName(mailboxId);
  await env.MAILBOX.get(doId).fetch("https://do/append", {
    method: "POST",
    body: JSON.stringify({ thread_id: tid, from, subject, snippet }),
  });
  await env.DB.prepare(
    `INSERT OR IGNORE INTO messages (message_id,thread_id,domain,mailbox,sender,recipients,subject,classification,importance,needs_reply,summary,mailbox_do_id,r2_raw_key)
     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)`
  ).bind(msgId, tid, domain, mailboxId, from,
    JSON.stringify([to]), subject, c.classification, c.importance, c.needs_reply, c.summary, doId.toString(), r2Key).run();
  await env.DB.prepare("INSERT INTO audit_log (actor,action,target,detail) VALUES (?,?,?,?)")
    .bind("email-worker", "received", mailboxId, subject).run();

  // Direction 2 (webhook): important mail → stevejobless action queue.
  // Fire-and-forget; inbound mail never blocks on the bridge.
  // Quarantined mail NEVER webhooks (reviewed in place, not in the queue).
  if ((env as any).STEVE_URL && !screen.quarantined && (c.needs_reply || c.importance >= 7)) {
    const hook = fetch(`${(env as any).STEVE_URL}/api/observations/email?token=${(env as any).STEVE_BRIDGE_TOKEN ?? ""}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        message_id: msgId, thread_id: tid, domain,
        mailbox: mailboxId, sender: String(from).slice(0, 200),
        subject: subject.slice(0, 200), summary: c.summary ?? "",
        classification: c.classification, importance: c.importance,
        needs_reply: !!c.needs_reply, r2_raw_key: r2Key,
      }),
    }).catch(() => {});
    m.waitUntil(hook);
  }
  return msgId;
}

export default {
  // ---- inbound: Internet → Email Routing → Worker ----
  async email(message: any, env: Env) {
    const rawText = message.raw ? Buffer.from(await message.raw.arrayBuffer()).toString("utf-8").slice(0, 20000) : "";
    await processInbound(env, {
      to: message.to ?? "",
      from: message.from ?? "unknown",
      subject: message.headers?.get("subject") ?? "(no subject)",
      rawText,
      raw: message.raw ?? null,
      waitUntil: (p: Promise<any>) => (message as any).waitUntil?.(p),
    });
  },

  async fetch(req: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(req.url);
    // MCP is the primary agent interface
    if (url.pathname === "/mcp") return handleMcp(req, env);
    if (url.pathname === "/api/inbox") {
      const needs = url.searchParams.get("needs_reply");
      const rows = needs
        ? await env.DB.prepare("SELECT * FROM messages WHERE needs_reply=1 ORDER BY importance DESC LIMIT 100").all()
        : await env.DB.prepare("SELECT * FROM messages ORDER BY received_at DESC LIMIT 100").all();
      return Response.json(rows.results);
    }
    if (url.pathname === "/api/stats") {
      const s = await env.DB.prepare(
        `SELECT (SELECT COUNT(*) FROM messages WHERE needs_reply=1 AND status='new') AS needs_me,
                (SELECT COUNT(*) FROM messages WHERE status='new') AS total`).first();
      return Response.json(s);
    }
    // ---- admin: create address/alias (ADMIN only) ----
    if (url.pathname === "/admin/address" && req.method === "POST") {
      const b: any = await req.json();
      if (!canDo(await actorPerms(env, b.actor), "ADMIN")) return new Response("forbidden", { status: 403 });
      await env.DB.prepare("INSERT OR IGNORE INTO domains (domain) VALUES (?)").bind(b.domain).run();
      await env.DB.prepare("INSERT OR IGNORE INTO mailboxes (id,domain,local_part,address,agent,permissions) VALUES (?,?,?,?,?,?)")
        .bind(`${b.local}@${b.domain}`, b.domain, b.local, `${b.local}@${b.domain}`, b.agent ?? null, JSON.stringify(b.permissions ?? ["READ", "DRAFT"])).run();
      return Response.json({ ok: true });
    }
    if (url.pathname === "/admin/alias" && req.method === "POST") {
      const b: any = await req.json();
      if (!canDo(await actorPerms(env, b.actor), "ADMIN")) return new Response("forbidden", { status: 403 });
      await env.DB.prepare("INSERT OR REPLACE INTO aliases (alias,target_mailbox) VALUES (?,?)").bind(b.alias.toLowerCase(), b.target).run();
      return Response.json({ ok: true });
    }
    // ---- drafts queue: steve posts quote drafts; sends once Paid+SENDER ----
    if (url.pathname === "/api/drafts" && req.method === "POST") {
      const b: any = await req.json();
      if (!b.secret || b.secret !== (env as any).TEST_INGEST_SECRET) return new Response("forbidden", { status: 403 });
      if (!b.to || !b.body) return new Response("to+body required", { status: 400 });
      const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      await env.DB.prepare("INSERT INTO drafts (id,to_address,subject,body) VALUES (?,?,?,?)")
        .bind(id, String(b.to).slice(0, 200), String(b.subject ?? "").slice(0, 200), String(b.body).slice(0, 5000)).run();
      await env.DB.prepare("INSERT INTO audit_log (actor,action,target,detail) VALUES (?,?,?,?)")
        .bind("steve-bridge", "draft_queued", String(b.to).slice(0, 200), String(b.subject ?? "").slice(0, 200)).run();
      return Response.json({ ok: true, draft_id: id, status: "queued" });
    }
    if (url.pathname === "/api/drafts") {
      const rows = await env.DB.prepare("SELECT id,to_address,subject,body,status,created_at FROM drafts ORDER BY created_at DESC LIMIT 100").all();
      return Response.json(rows.results);
    }
    // ---- test ingest: same pipeline, synthetic message. Guarded by secret. ----
    if (url.pathname === "/test/ingest" && req.method === "POST") {
      const b: any = await req.json();
      if (!b.secret || b.secret !== (env as any).TEST_INGEST_SECRET) return new Response("forbidden", { status: 403 });
      const msgId = await processInbound(env, {
        to: b.to ?? "", from: b.from ?? "tester@example.com",
        subject: b.subject ?? "(test)", rawText: b.body ?? "",
        raw: null, waitUntil: (p) => ctx.waitUntil(p),
      });
      return Response.json({ ok: true, message_id: msgId });
    }
    if (url.pathname === "/") return Response.redirect("/ui/", 302);
    if (url.pathname.startsWith("/ui/")) {
      return new Response(UI, { headers: { "content-type": "text/html" } });
    }
    return new Response("cmail ok", { status: 200 });
  },
};

const UI = `<!doctype html><html><head><meta charset=utf-8><title>cmail</title>
<style>body{font-family:system-ui;max-width:720px;margin:2em auto}li{margin:.4em 0}.q{border:1px solid #ccc;padding:.5em;margin:.5em 0}.q pre{white-space:pre-wrap;font-size:.85em}</style></head><body>
<h1>cmail — needs me</h1><div id=s></div><ul id=l></ul>
<h2>drafts (queued — send on migration day)</h2><div id=d></div>
<script>fetch('/api/inbox?needs_reply=1').then(r=>r.json()).then(a=>{l.innerHTML=a.map(m=>'<li><b>'+m.subject+'</b> — '+m.sender+' <i>'+m.summary+'</i></li>').join('')||'<li>all clear</li>'});
fetch('/api/stats').then(r=>r.json()).then(s=>{document.getElementById('s').textContent='needs me: '+s.needs_me+' · total: '+s.total});
fetch('/api/drafts').then(r=>r.json()).then(a=>{document.getElementById('d').innerHTML=a.map(d=>'<div class=q><b>to '+d.to_address+'</b> — '+d.subject+' <i>('+d.status+')</i><pre>'+d.body+'</pre></div>').join('')||'<i>no drafts</i>'});</script>`;
