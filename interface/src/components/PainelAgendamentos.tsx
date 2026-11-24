import {
  IconCalendarEvent,
  IconCalendarTime,
  IconCircleCheck,
  IconCircleX,
  IconDeviceDesktop,
  IconPencil,
  IconPlayerPlay,
  IconPlus,
  IconRefresh,
  IconTrash,
  IconX,
} from "@tabler/icons-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import type { DiaSemana, EventoAgenda, Rotina, TarefaPc } from "@/lib/tipos";
import { cn } from "@/lib/utils";

const DIAS: { id: DiaSemana; rotulo: string }[] = [
  { id: "seg", rotulo: "S" },
  { id: "ter", rotulo: "T" },
  { id: "qua", rotulo: "Q" },
  { id: "qui", rotulo: "Q" },
  { id: "sex", rotulo: "S" },
  { id: "sab", rotulo: "S" },
  { id: "dom", rotulo: "D" },
];
const NOMES_DIAS: Record<DiaSemana, string> = { seg: "Seg", ter: "Ter", qua: "Qua", qui: "Qui", sex: "Sex", sab: "Sáb", dom: "Dom" };

function diasTexto(dias: DiaSemana[]) {
  const uteis: DiaSemana[] = ["seg", "ter", "qua", "qui", "sex"];
  if (dias.length === 5 && uteis.every((d) => dias.includes(d))) return "Seg a Sex";
  if (dias.length === 7) return "Todos os dias";
  return dias.map((d) => NOMES_DIAS[d]).join(", ");
}

const hora = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—";

const vazia = (): Rotina => ({ nome: "", pedido: "", hora: "10:00", dias: ["seg", "ter", "qua", "qui", "sex"], ativa: true });

function Secao({ icone, titulo, acao, children }: { icone: React.ReactNode; titulo: string; acao?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-wide text-texto-3">
          {icone}
          {titulo}
        </h3>
        {acao}
      </div>
      {children}
    </section>
  );
}

export function PainelAgendamentos({
  aberto,
  aoFechar,
  rotinas,
  tarefas,
  eventos,
  erroOutlook,
  erroPc,
  aoSalvar,
  aoApagar,
  aoExecutar,
  aoAtualizar,
}: {
  aberto: boolean;
  aoFechar: () => void;
  rotinas: Rotina[];
  tarefas: TarefaPc[] | null;
  eventos: EventoAgenda[] | null;
  erroOutlook: string | null;
  erroPc: string | null;
  aoSalvar: (r: Rotina) => Promise<boolean>;
  aoApagar: (r: Rotina) => void;
  aoExecutar: (r: Rotina) => void;
  aoAtualizar: () => void;
}) {
  const [edicao, setEdicao] = useState<Rotina | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [confirmarApagar, setConfirmarApagar] = useState<string | null>(null);

  useEffect(() => {
    if (!aberto) {
      setEdicao(null);
      setConfirmarApagar(null);
      return;
    }
    const esc = (e: KeyboardEvent) => e.key === "Escape" && aoFechar();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [aberto, aoFechar]);

  const salvar = async () => {
    if (!edicao) return;
    setSalvando(true);
    if (await aoSalvar(edicao)) setEdicao(null);
    setSalvando(false);
  };

  return (
    <AnimatePresence>
      {aberto && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-40 bg-black/25"
          onMouseDown={(e) => e.target === e.currentTarget && aoFechar()}
        >
          <motion.aside
            role="dialog"
            aria-label="Agendamentos"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 320, damping: 34 }}
            className="absolute inset-y-0 right-0 flex w-[460px] max-w-full flex-col border-l border-borda bg-janela shadow-[var(--sombra)]"
          >
            <header className="flex h-12 shrink-0 items-center justify-between border-b border-borda px-4">
              <h2 className="flex items-center gap-2 text-[14px] font-semibold text-texto">
                <IconCalendarTime className="h-[18px] w-[18px] text-azul" stroke={1.7} />
                Agendamentos
              </h2>
              <div className="flex items-center gap-1">
                <button type="button" onClick={aoAtualizar} aria-label="Atualizar" title="Atualizar" className="rounded-md p-1 text-texto-2 hover:bg-superficie hover:text-texto">
                  <IconRefresh className="h-4 w-4" stroke={1.8} />
                </button>
                <button type="button" onClick={aoFechar} aria-label="Fechar" className="rounded-md p-1 text-texto-2 hover:bg-superficie hover:text-texto">
                  <IconX className="h-4 w-4" stroke={1.8} />
                </button>
              </div>
            </header>

            <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto px-4 py-4">
              {/* minhas rotinas */}
              <Secao
                icone={<IconCalendarTime className="h-3.5 w-3.5" stroke={1.8} />}
                titulo="Minhas rotinas"
                acao={
                  !edicao && (
                    <button
                      type="button"
                      onClick={() => setEdicao(vazia())}
                      className="flex items-center gap-1 rounded-full bg-azul px-2.5 py-0.5 text-[12px] font-medium text-white hover:brightness-110"
                    >
                      <IconPlus className="h-3 w-3" stroke={2.2} /> Nova rotina
                    </button>
                  )
                }
              >
                {edicao && (
                  <div className="flex flex-col gap-3 rounded-xl border border-azul/40 bg-azul-suave p-3">
                    <label className="flex flex-col gap-1 text-[12px] text-texto-2">
                      Nome
                      <input
                        id="rotina-nome"
                        value={edicao.nome}
                        onChange={(e) => setEdicao({ ...edicao, nome: e.target.value })}
                        placeholder="Ex.: Chamados do dia"
                        className="rounded-lg border border-borda bg-janela px-2.5 py-1.5 text-[13px] text-texto focus:outline-none focus:ring-2 focus:ring-azul/40"
                      />
                    </label>
                    <div className="flex flex-wrap items-end gap-3">
                      <label className="flex flex-col gap-1 text-[12px] text-texto-2">
                        Hora
                        <input
                          id="rotina-hora"
                          type="time"
                          value={edicao.hora}
                          onChange={(e) => setEdicao({ ...edicao, hora: e.target.value })}
                          className="rounded-lg border border-borda bg-janela px-2 py-1 text-[13px] text-texto tabular-nums"
                        />
                      </label>
                      <div className="flex flex-col gap-1 text-[12px] text-texto-2">
                        Dias
                        <div className="flex gap-1">
                          {DIAS.map((d) => {
                            const on = edicao.dias.includes(d.id);
                            return (
                              <button
                                key={d.id}
                                type="button"
                                aria-pressed={on}
                                title={NOMES_DIAS[d.id]}
                                onClick={() =>
                                  setEdicao({ ...edicao, dias: on ? edicao.dias.filter((x) => x !== d.id) : [...edicao.dias, d.id] })
                                }
                                className={cn(
                                  "h-7 w-7 rounded-full text-[12px] font-medium",
                                  on ? "bg-azul text-white" : "border border-borda bg-janela text-texto-2",
                                )}
                              >
                                {d.rotulo}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                    <label className="flex flex-col gap-1 text-[12px] text-texto-2">
                      O que o agente faz na hora
                      <textarea
                        id="rotina-pedido"
                        rows={3}
                        value={edicao.pedido}
                        onChange={(e) => setEdicao({ ...edicao, pedido: e.target.value })}
                        placeholder="Ex.: Consulte no portal os chamados concluídos desde ontem (--dias 1) e traga a resposta do Santander."
                        className="resize-y rounded-lg border border-borda bg-janela px-2.5 py-1.5 text-[13px] leading-relaxed text-texto focus:outline-none focus:ring-2 focus:ring-azul/40"
                      />
                    </label>
                    <div className="flex justify-end gap-2">
                      <button type="button" onClick={() => setEdicao(null)} className="rounded-lg border border-borda px-3 py-1 text-[12.5px] text-texto hover:bg-superficie">
                        Cancelar
                      </button>
                      <button
                        type="button"
                        disabled={salvando || !edicao.nome.trim() || !edicao.pedido.trim() || !edicao.dias.length}
                        onClick={salvar}
                        className="rounded-lg bg-azul px-3 py-1 text-[12.5px] font-medium text-white hover:brightness-110 disabled:opacity-50"
                      >
                        {salvando ? "Salvando…" : "Salvar rotina"}
                      </button>
                    </div>
                  </div>
                )}

                {rotinas.length === 0 && !edicao && (
                  <p className="rounded-xl border border-dashed border-borda px-3 py-4 text-[12.5px] leading-relaxed text-texto-3">
                    Nenhuma rotina ainda. Crie uma com dia, hora e o pedido ao agente: na hora, aparece um aviso no sino com o
                    botão Executar. As rotinas ficam salvas no PC e só avisam com o agente aberto.
                  </p>
                )}

                <ul className="flex flex-col gap-1.5">
                  {rotinas.map((r) => (
                    <li key={r.id} className={cn("group rounded-xl border border-borda px-3 py-2", !r.ativa && "opacity-55")}>
                      <div className="flex items-start gap-3">
                        <span className="pt-0.5 text-[15px] font-semibold text-texto tabular-nums">{r.hora}</span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-[13px] font-medium text-texto">{r.nome}</p>
                          <p className="text-[11.5px] text-texto-3">
                            {diasTexto(r.dias)} · {r.ultima_execucao ? `última: ${hora(r.ultima_execucao)}` : "ainda não rodou"}
                          </p>
                          <p className="mt-0.5 line-clamp-2 text-[12px] text-texto-2">{r.pedido}</p>
                        </div>
                        <label className="relative inline-flex shrink-0 cursor-pointer items-center" title={r.ativa ? "Ativa" : "Pausada"}>
                          <input
                            type="checkbox"
                            className="peer sr-only"
                            checked={r.ativa}
                            onChange={() => aoSalvar({ ...r, ativa: !r.ativa })}
                            aria-label={`${r.ativa ? "Pausar" : "Ativar"} ${r.nome}`}
                          />
                          <span className="h-5 w-9 rounded-full bg-superficie ring-1 ring-borda transition-colors peer-checked:bg-verde" />
                          <span className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform peer-checked:translate-x-4" />
                        </label>
                      </div>
                      <div className="mt-2 flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => aoExecutar(r)}
                          className="flex items-center gap-1 rounded-full border border-borda px-2.5 py-0.5 text-[12px] text-texto hover:border-azul hover:text-azul"
                        >
                          <IconPlayerPlay className="h-3 w-3" stroke={2} /> Executar agora
                        </button>
                        <button
                          type="button"
                          onClick={() => setEdicao(r)}
                          aria-label={`Editar ${r.nome}`}
                          className="rounded-full p-1 text-texto-3 hover:bg-realce hover:text-texto"
                        >
                          <IconPencil className="h-3.5 w-3.5" stroke={1.8} />
                        </button>
                        {confirmarApagar === r.id ? (
                          <span className="ml-auto flex items-center gap-1.5 text-[12px] text-texto-2">
                            Excluir?
                            <button type="button" onClick={() => aoApagar(r)} className="rounded-full bg-vermelho px-2 py-0.5 text-[12px] text-white">
                              Sim
                            </button>
                            <button type="button" onClick={() => setConfirmarApagar(null)} className="rounded-full border border-borda px-2 py-0.5 text-[12px]">
                              Não
                            </button>
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setConfirmarApagar(r.id ?? null)}
                            aria-label={`Excluir ${r.nome}`}
                            className="ml-auto rounded-full p-1 text-texto-3 hover:bg-realce hover:text-vermelho"
                          >
                            <IconTrash className="h-3.5 w-3.5" stroke={1.8} />
                          </button>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </Secao>

              {/* Agendador do Windows */}
              <Secao icone={<IconDeviceDesktop className="h-3.5 w-3.5" stroke={1.8} />} titulo="Rotinas do PC (Agendador do Windows)">
                {erroPc && <p className="text-[12px] text-texto-3">{erroPc}</p>}
                {!erroPc && tarefas === null && <p className="text-[12px] text-texto-3">Carregando…</p>}
                {tarefas?.length === 0 && <p className="text-[12px] text-texto-3">Nenhuma tarefa AK no Agendador.</p>}
                <ul className="flex flex-col gap-1.5">
                  {tarefas?.map((t) => (
                    <li key={t.nome} className="flex items-start gap-2.5 rounded-xl border border-borda px-3 py-2">
                      {t.ok ? (
                        <IconCircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-verde" stroke={1.8} />
                      ) : (
                        <IconCircleX className="mt-0.5 h-4 w-4 shrink-0 text-vermelho" stroke={1.8} />
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[13px] font-medium text-texto">{t.nome}</p>
                        <p className="text-[11.5px] text-texto-3 tabular-nums">
                          última {hora(t.ultima_execucao)} {t.ok ? "ok" : `· erro ${t.ultimo_resultado}`} · próxima {hora(t.proxima_execucao)}
                          {!t.habilitada && " · desabilitada"}
                        </p>
                        {t.descricao && <p className="mt-0.5 line-clamp-2 text-[12px] text-texto-2">{t.descricao}</p>}
                      </div>
                    </li>
                  ))}
                </ul>
              </Secao>

              {/* Outlook */}
              <Secao icone={<IconCalendarEvent className="h-3.5 w-3.5" stroke={1.8} />} titulo="Hoje no Outlook">
                {erroOutlook && <p className="text-[12px] text-texto-3">{erroOutlook}</p>}
                {!erroOutlook && eventos === null && <p className="text-[12px] text-texto-3">Carregando…</p>}
                {eventos?.length === 0 && <p className="text-[12px] text-texto-3">Nenhum compromisso hoje.</p>}
                <ul className="flex flex-col gap-1.5">
                  {eventos?.map((e, i) => (
                    <li key={`${e.inicio}-${i}`} className="flex items-start gap-3 rounded-xl border border-borda px-3 py-2">
                      <span className="w-12 shrink-0 pt-0.5 text-[13px] font-semibold text-texto tabular-nums">{e.inicio.slice(11, 16)}</span>
                      <div className="min-w-0 flex-1">
                        {e.link ? (
                          <a href={e.link} target="_blank" rel="noopener noreferrer" className="truncate text-[13px] font-medium text-texto hover:text-azul">
                            {e.assunto}
                          </a>
                        ) : (
                          <p className="truncate text-[13px] font-medium text-texto">{e.assunto}</p>
                        )}
                        <p className="truncate text-[11.5px] text-texto-3">
                          até {e.fim.slice(11, 16)}
                          {e.local ? ` · ${e.local}` : ""}
                          {e.organizador ? ` · ${e.organizador}` : ""}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              </Secao>
            </div>
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
