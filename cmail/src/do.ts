// cmail — studio-wide communication bus.
// Mailbox DO = canonical per-mailbox state. D1 = global index. R2 = raw .eml.

export interface Env {
  DB: D1Database;
  RAW: R2Bucket;
  SESSION: KVNamespace;
  AI: Ai;
  MAILBOX: DurableObjectNamespace;
  // SENDER: SendEmail; // uncomment after Workers Paid enabled
}

export class MailboxDO {
  state: DurableObjectState;
  env: Env;
  constructor(state: DurableObjectState, env: Env) {
    this.state = state;
    this.env = env;
  }
  async fetch(req: Request): Promise<Response> {
    const url = new URL(req.url);
    if (url.pathname === "/append" && req.method === "POST") {
      const msg = await req.json();
      const threads: Record<string, any[]> = (await this.state.storage.get("threads")) ?? {};
      const t = String((msg as any).thread_id ?? "misc").slice(0, 80);
      const arr = (threads[t] ??= []);
      arr.push(msg);
      if (arr.length > 200) threads[t] = arr.slice(-200); // cap: DO is hot state, D1/R2 hold history
      await this.state.storage.put("threads", threads);
      return Response.json({ ok: true, thread: t });
    }
    if (url.pathname === "/threads") {
      return Response.json((await this.state.storage.get("threads")) ?? {});
    }
    return new Response("not found", { status: 404 });
  }
}
