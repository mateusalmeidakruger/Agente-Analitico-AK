// Outlook pelo conector Microsoft 365 (só leitura: Mail.Read, Calendars.Read).
// A busca devolve UM bloco de texto JSON por item e, no fim, um bloco com nextOffset.
import type { Mcp } from "./claude";
import type { EmailResumo, EventoAgenda } from "./tipos";

export const M365 = "Microsoft 365";

function blocosJson(r: { content: { type: string; text?: string }[] }): Record<string, unknown>[] {
  const itens: Record<string, unknown>[] = [];
  for (const c of r.content ?? []) {
    if (c.type !== "text" || !c.text) continue;
    try {
      const v = JSON.parse(c.text);
      if (v && typeof v === "object" && !Array.isArray(v) && !("nextOffset" in v) && !("moreResults" in v)) itens.push(v);
    } catch {
      /* bloco que não é JSON: ignora */
    }
  }
  return itens;
}

const texto = (v: unknown) => (typeof v === "string" ? v : "");

function paraEmail(e: Record<string, unknown>): EmailResumo {
  return {
    id: texto(e.id),
    uri: texto(e.uri),
    assunto: texto(e.subject) || "(sem assunto)",
    remetente: texto(e.senderName) || texto(e.sender),
    email_remetente: texto(e.sender),
    recebido: texto(e.receivedDateTime),
    resumo: texto(e.summary).replace(/\s+/g, " ").slice(0, 280),
    lido: Boolean(e.isRead),
    importante: e.importance === "high",
    anexos: Boolean(e.hasAttachments),
    link: texto(e.webLink).startsWith("https://") ? texto(e.webLink) : "",
  };
}

export async function emailsDesde(mcp: Mcp, desdeIso: string, limite = 25, signal?: AbortSignal) {
  const r = await mcp.callTool(M365, "outlook_email_search", { order: "newest", afterDateTime: desdeIso, limit: limite }, { cache: false, signal });
  return blocosJson(r).map(paraEmail).filter((e) => e.recebido > desdeIso);
}

export async function buscarEmails(mcp: Mcp, filtros: Record<string, unknown>, signal?: AbortSignal) {
  const entrada: Record<string, unknown> = { limit: 15 };
  for (const k of ["query", "sender", "afterDateTime", "beforeDateTime", "folderName"]) if (filtros[k]) entrada[k] = filtros[k];
  if (!entrada.query && !entrada.sender && !entrada.afterDateTime && !entrada.beforeDateTime) entrada.order = "newest";
  const r = await mcp.callTool(M365, "outlook_email_search", entrada, { cache: false, signal });
  return blocosJson(r).map(paraEmail);
}

export async function lerEmail(mcp: Mcp, uri: string, signal?: AbortSignal) {
  if (!uri.startsWith("mail:///")) throw new Error("uri de e-mail inválida");
  const r = await mcp.callTool(M365, "read_resource", { uri }, { cache: false, signal });
  const t = typeof r.payload === "string" ? r.payload : JSON.stringify(r.payload ?? r.content);
  return t.length > 12_000 ? `${t.slice(0, 12_000)}\n…(cortado)` : t;
}

export async function agenda(mcp: Mcp, de: Date, ate: Date, signal?: AbortSignal): Promise<EventoAgenda[]> {
  const r = await mcp.callTool(
    M365,
    "outlook_calendar_search",
    { query: "*", afterDateTime: de.toISOString(), beforeDateTime: ate.toISOString(), order: "oldest", limit: 25 },
    { cache: false, signal },
  );
  return blocosJson(r).map((e) => {
    const ini = (e.start ?? {}) as { dateTime?: string; timeZone?: string };
    const fim = (e.end ?? {}) as { dateTime?: string };
    const local = (e.location ?? {}) as { displayName?: string };
    return {
      assunto: texto(e.subject) || "(sem título)",
      inicio: ini.dateTime ?? "",
      fim: fim.dateTime ?? "",
      fuso: ini.timeZone ?? "",
      local: local.displayName ?? (typeof e.location === "string" ? e.location : ""),
      organizador: texto((e.organizer as { emailAddress?: { name?: string } } | undefined)?.emailAddress?.name),
      link: texto(e.webLink).startsWith("https://") ? texto(e.webLink) : "",
    };
  });
}

export async function buscarPessoa(mcp: Mcp, consulta: string, signal?: AbortSignal) {
  const r = await mcp.callTool(M365, "search_people", { query: consulta, limit: 5 }, { cache: false, signal });
  const itens = blocosJson(r);
  const lista = itens.length ? itens : Array.isArray(r.payload) ? (r.payload as Record<string, unknown>[]) : [];
  return lista.map((p) => ({ nome: texto(p.displayName), email: texto(p.mail) || texto(p.userPrincipalName), cargo: texto(p.jobTitle) }));
}

/** Início e fim do dia local, para a agenda de hoje. */
export function hojeIntervalo(): [Date, Date] {
  const ini = new Date();
  ini.setHours(0, 0, 0, 0);
  const fim = new Date(ini);
  fim.setDate(fim.getDate() + 1);
  return [ini, fim];
}
