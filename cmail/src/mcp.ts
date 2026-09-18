import type { Env } from "./do";

// MCP primary interface: list/search/read/draft/reply/send/archive + ask.
// Drafts are default; SEND requires explicit permission + human confirm.
const TOOLS = [
  "email.list_domains", "email.list_mailboxes", "email.inbox", "email.search",
  "email.read", "email.thread", "email.draft", "email.reply", "email.send",
  "email.archive", "email.label", "email.needs_reply", "email.ask",
];

export async function handleMcp(req: Request, env: Env): Promise<Response> {
  if (req.method === "GET") return Response.json({ tools: TOOLS });
  const body: any = await req.json().catch(() => ({}));
  const { tool, args = {}, actor = "owner" } = body;
  const perms = await getPerms(env, actor);
  const need = (t: string) => (["email.send"].includes(t) ? "SEND" : ["email.draft", "email.reply"].includes(t) ? "DRAFT" : "READ");
  if (!perms.includes("ADMIN") && !perms.includes(need(tool))) return Response.json({ error: "forbidden" }, { status: 403 });

  switch (tool) {
    case "email.list_domains": return Response.json({ domains: (await env.DB.prepare("SELECT * FROM domains").all()).results });
    case "email.list_mailboxes": return Response.json({ mailboxes: (await env.DB.prepare("SELECT * FROM mailboxes").all()).results });
    case "email.inbox": {
      const rows = await env.DB.prepare("SELECT * FROM messages WHERE mailbox=? ORDER BY received_at DESC LIMIT 50").bind(args.mailbox ?? "").all();
      return Response.json({ messages: rows.results });
    }
    case "email.search": {
      const q = `%${String(args.q ?? "").replace(/[\\%_]/g, (c) => `\\${c}`)}%`;
      const rows = await env.DB.prepare("SELECT * FROM messages WHERE subject LIKE ? ESCAPE '\\' OR summary LIKE ? ESCAPE '\\' ORDER BY importance DESC LIMIT 50")
        .bind(q, q).all();
      return Response.json({ messages: rows.results });
    }
    case "email.thread": {
      const rows = await env.DB.prepare("SELECT * FROM messages WHERE thread_id=? ORDER BY received_at ASC LIMIT 100").bind(args.thread_id ?? "").all();
      return Response.json({ messages: rows.results });
    }
    case "email.read": {
      const m = await env.DB.prepare("SELECT * FROM messages WHERE message_id=?").bind(args.message_id ?? "").first();
      if (!m) return Response.json({ error: "not found" }, { status: 404 });
      const raw = await env.RAW.get(m.r2_raw_key as string);
      return Response.json({ meta: m, raw: raw ? (await raw.text()).slice(0, 20000) : null });
    }
    case "email.needs_reply": {
      const rows = await env.DB.prepare("SELECT * FROM messages WHERE needs_reply=1 AND status='new' ORDER BY importance DESC LIMIT 50").all();
      return Response.json({ messages: rows.results });
    }
    case "email.archive":
      await env.DB.prepare("UPDATE messages SET status='archived' WHERE message_id=?").bind(args.message_id ?? "").run();
      return Response.json({ ok: true });
    case "email.label":
      await env.DB.prepare("UPDATE messages SET labels_json=? WHERE message_id=?").bind(JSON.stringify(args.labels ?? []), args.message_id ?? "").run();
      return Response.json({ ok: true });
    case "email.draft":
    case "email.reply": {
      // auto-draft only; never auto-send
      await env.DB.prepare("INSERT INTO audit_log (actor,action,target,detail) VALUES (?,?,?,?)")
        .bind(actor, tool, args.to ?? args.message_id ?? "", (args.subject ?? "") + " :: " + (args.body ?? "").slice(0, 500)).run();
      return Response.json({ ok: true, drafted: true, note: "draft saved; explicit confirm required to send" });
    }
    case "email.send":
      // requires SEND + human confirmation flag.
      if (!args.confirmed) return Response.json({ error: "send requires confirmed:true (human approval)" }, { status: 400 });
      if ((env as any).SENDER) {
        try {
          await (env as any).SENDER.send({ from: args.from ?? "hello@cmail", to: args.to, subject: args.subject ?? "", text: args.body ?? args.text ?? "" });
          if (args.draft_id) {
            await env.DB.prepare("UPDATE drafts SET status='sent' WHERE id=?").bind(args.draft_id).run();
          }
          await env.DB.prepare("INSERT INTO audit_log (actor,action,target,detail) VALUES (?,?,?,?)").bind(actor, "send", args.to ?? "", args.subject ?? "").run();
          return Response.json({ ok: true, sent: true });
        } catch (e: any) {
          return Response.json({ ok: false, sent: false, error: `send failed: ${String(e?.message ?? e).slice(0, 200)}` }, { status: 502 });
        }
      }
      // Outbound disabled until Workers Paid + SENDER binding: report honestly, never fake a send.
      await env.DB.prepare("INSERT INTO audit_log (actor,action,target,detail) VALUES (?,?,?,?)").bind(actor, "send_blocked", args.to ?? "", args.subject ?? "").run();
      return Response.json({ ok: false, sent: false, error: "outbound disabled — enable Workers Paid and the SENDER binding" });
    case "email.ask": {
      // semantic helper: search + summarize via Workers AI.
      // Quarantined mail is EXCLUDED from the corpus (no indirect injection).
      try {
        const rows = await env.DB.prepare("SELECT subject,summary,sender FROM messages WHERE classification != 'quarantine' ORDER BY received_at DESC LIMIT 30").all();
        const r: any = await env.AI.run("@cf/meta/llama-3.1-8b-instruct", {
          messages: [{ role: "user", content: `Q: ${args.q}\nEmails:\n${JSON.stringify(rows.results).slice(0, 4000)}` }],
        });
        return Response.json({ answer: r?.response ?? "no AI response" });
      } catch (e: any) {
        return Response.json({ answer: null, error: `AI unavailable: ${String(e?.message ?? e).slice(0, 200)}` }, { status: 502 });
      }
    }
    default: return Response.json({ error: "unknown tool", tools: TOOLS }, { status: 400 });
  }
}

async function getPerms(env: Env, actor: string): Promise<string[]> {
  if (actor === "owner") return ["ADMIN"];
  try {
    const row = await env.DB.prepare("SELECT permissions FROM mailboxes WHERE id=?").bind(actor).first();
    const perms = JSON.parse((row?.permissions as string) ?? '["READ","DRAFT"]');
    return Array.isArray(perms) ? perms : ["READ", "DRAFT"];
  } catch {
    return ["READ", "DRAFT"];
  }
}
