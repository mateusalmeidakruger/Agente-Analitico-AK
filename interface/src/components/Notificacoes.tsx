import { IconBell, IconCalendarTime, IconExternalLink, IconMail, IconPaperclip, IconPlayerPlay, IconX } from "@tabler/icons-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef } from "react";
import type { EmailResumo, Notificacao, Rotina } from "@/lib/tipos";
import { cn } from "@/lib/utils";

function quando(iso: string) {
  const d = new Date(iso);
  const hoje = new Date();
  const mesmoDia = d.toDateString() === hoje.toDateString();
  return mesmoDia
    ? d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export function Notificacoes({
  aberto,
  aoAlternar,
  itens,
  naoLidas,
  semOutlook,
  aoResumirEmail,
  aoExecutarRotina,
  aoDispensarRotina,
  aoAbrirAgendamentos,
}: {
  aberto: boolean;
  aoAlternar: (aberto: boolean) => void;
  itens: Notificacao[];
  naoLidas: number;
  semOutlook: string | null;
  aoResumirEmail: (e: EmailResumo) => void;
  aoExecutarRotina: (r: Rotina) => void;
  aoDispensarRotina: (r: Rotina) => void;
  aoAbrirAgendamentos: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!aberto) return;
    const fora = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && aoAlternar(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && aoAlternar(false);
    document.addEventListener("mousedown", fora);
    window.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", fora);
      window.removeEventListener("keydown", esc);
    };
  }, [aberto, aoAlternar]);

  const rotinas = itens.filter((n) => n.tipo === "rotina");
  const emails = itens.filter((n) => n.tipo === "email");

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => aoAlternar(!aberto)}
        aria-label={naoLidas ? `Notificações, ${naoLidas} novas` : "Notificações"}
        title="Notificações"
        className="relative flex h-7 w-7 items-center justify-center rounded-md text-texto-2 hover:bg-superficie hover:text-texto"
      >
        <IconBell className="h-[18px] w-[18px]" stroke={1.6} />
        {naoLidas > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-vermelho px-1 text-[10px] font-semibold leading-none text-white tabular-nums">
            {naoLidas > 99 ? "99+" : naoLidas}
          </span>
        )}
      </button>

      <AnimatePresence>
        {aberto && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-[calc(100%+8px)] z-40 flex max-h-[70vh] w-[380px] max-w-[calc(100vw-24px)] flex-col overflow-hidden rounded-2xl border border-borda bg-janela shadow-[var(--sombra)]"
          >
            <div className="flex items-center justify-between border-b border-borda px-4 py-2.5">
              <p className="text-[13px] font-semibold text-texto">Notificações</p>
              <button
                type="button"
                onClick={aoAbrirAgendamentos}
                className="flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[12px] text-azul hover:bg-azul-suave"
              >
                <IconCalendarTime className="h-3.5 w-3.5" stroke={1.8} />
                Agendamentos
              </button>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto">
              {rotinas.length > 0 && (
                <section className="border-b border-borda px-2 py-2">
                  <h3 className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-texto-3">Rotinas na hora</h3>
                  <ul className="flex flex-col gap-1">
                    {rotinas.map((n) =>
                      n.tipo === "rotina" ? (
                        <li key={n.id} className="flex items-start gap-2.5 rounded-xl bg-azul-suave px-2.5 py-2">
                          <IconCalendarTime className="mt-0.5 h-4 w-4 shrink-0 text-azul" stroke={1.7} />
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-[13px] font-medium text-texto">{n.rotina.nome}</p>
                            <p className="line-clamp-2 text-[12px] text-texto-2">{n.rotina.pedido}</p>
                            <div className="mt-1.5 flex gap-1.5">
                              <button
                                type="button"
                                onClick={() => aoExecutarRotina(n.rotina)}
                                className="flex items-center gap-1 rounded-full bg-azul px-2.5 py-0.5 text-[12px] font-medium text-white hover:brightness-110"
                              >
                                <IconPlayerPlay className="h-3 w-3" stroke={2} />
                                Executar
                              </button>
                              <button
                                type="button"
                                onClick={() => aoDispensarRotina(n.rotina)}
                                className="rounded-full border border-borda px-2.5 py-0.5 text-[12px] text-texto-2 hover:text-texto"
                              >
                                Hoje não
                              </button>
                            </div>
                          </div>
                          <span className="shrink-0 text-[11px] text-texto-3 tabular-nums">{n.rotina.hora}</span>
                        </li>
                      ) : null,
                    )}
                  </ul>
                </section>
              )}

              <section className="px-2 py-2">
                <h3 className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-texto-3">E-mails novos</h3>
                {semOutlook && <p className="px-2 py-2 text-[12px] leading-relaxed text-texto-3">{semOutlook}</p>}
                {!semOutlook && emails.length === 0 && (
                  <p className="px-2 py-2 text-[12px] text-texto-3">Nenhum e-mail novo. O agente confere a caixa de entrada a cada minuto.</p>
                )}
                <ul className="flex flex-col">
                  {emails.map((n) =>
                    n.tipo === "email" ? (
                      <li key={n.id} className="group flex items-start gap-2.5 rounded-xl px-2.5 py-2 hover:bg-realce">
                        <IconMail className={cn("mt-0.5 h-4 w-4 shrink-0", n.email.importante ? "text-vermelho" : "text-texto-3")} stroke={1.7} />
                        <button type="button" onClick={() => aoResumirEmail(n.email)} className="min-w-0 flex-1 text-left" title="Pedir resumo ao agente">
                          <p className="flex items-center gap-1 truncate text-[13px] font-medium text-texto">
                            <span className="truncate">{n.email.remetente}</span>
                            {n.email.anexos && <IconPaperclip className="h-3 w-3 shrink-0 text-texto-3" />}
                          </p>
                          <p className="truncate text-[12.5px] text-texto">{n.email.assunto}</p>
                          <p className="line-clamp-1 text-[12px] text-texto-3">{n.email.resumo}</p>
                        </button>
                        <div className="flex shrink-0 flex-col items-end gap-1">
                          <span className="text-[11px] text-texto-3 tabular-nums">{quando(n.email.recebido)}</span>
                          {n.email.link && (
                            <a
                              href={n.email.link}
                              target="_blank"
                              rel="noopener noreferrer"
                              aria-label="Abrir no Outlook"
                              title="Abrir no Outlook"
                              className="rounded p-0.5 text-texto-3 opacity-100 hover:text-azul md:opacity-0 md:group-hover:opacity-100"
                            >
                              <IconExternalLink className="h-3.5 w-3.5" />
                            </a>
                          )}
                        </div>
                      </li>
                    ) : null,
                  )}
                </ul>
              </section>
            </div>
            <button
              type="button"
              onClick={() => aoAlternar(false)}
              className="flex items-center justify-center gap-1 border-t border-borda py-2 text-[12px] text-texto-3 hover:text-texto md:hidden"
            >
              <IconX className="h-3.5 w-3.5" /> Fechar
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
