import {
  IconChartLine,
  IconFolder,
  IconPlayerStopFilled,
  IconPlus,
  IconShieldCheck,
  IconTerminal2,
  IconTicket,
  IconUserOff,
} from "@tabler/icons-react";
import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Avatar } from "@/components/Avatar";
import { BarraLateral } from "@/components/BarraLateral";
import { BarraTitulo, type EstadoPc } from "@/components/BarraTitulo";
import { Bolha } from "@/components/Mensagens";
import { AnimatedModal } from "@/components/ui/animated-modal";
import { FloatingDock } from "@/components/ui/floating-dock";
import { MultiStepLoader } from "@/components/ui/multi-step-loader";
import { PlaceholdersAndVanishInput } from "@/components/ui/placeholders-and-vanish-input";
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import { chamarPc, comoLista, responder } from "@/lib/agente";
import { codigoErro, type Downloads, type Mcp, type Sample, usar } from "@/lib/claude";
import type { Anexo, Conversa, Mensagem, ResumoConversa, StatusBase, UsoFerramenta } from "@/lib/tipos";
import { cn } from "@/lib/utils";

const SUGESTOES = [
  "Quais contas estão fora do SLA e sem chamado?",
  "O CNPJ 59.910.525/0001-07 tem chamado aberto?",
  "Me traz a Usuarios_Atual de hoje",
  "A base de hoje foi liberada?",
  "Quais scripts você pode rodar?",
];

// status_base fora do formato esperado vira "sem informação", nunca derruba a tela
const comoBase = (v: unknown): StatusBase | null =>
  v && typeof v === "object" && "laudo" in v && (v as StatusBase).laudo ? (v as StatusBase) : null;
const agora = () => new Date().toISOString().slice(0, 19);
const conversaVazia = (): Conversa => ({ titulo: "Nova conversa", mensagens: [] });

function base64ParaBytes(b64: string) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

const COPIA_ERRO_SAMPLE: Record<string, string> = {
  not_granted: "O uso do Claude não foi permitido para esta página. Libere no aviso do app e tente de novo.",
  sampling_disabled: "O Claude não está disponível nesta conta.",
  rate_limited: "Limite de uso atingido por agora. Tente de novo em alguns minutos.",
  session_expired: "A sessão expirou. Entre de novo no Claude.",
  prompt_too_large: "A conversa ficou grande demais. Comece uma nova conversa.",
  refused: "O Claude não respondeu a esse pedido. Reformule a pergunta.",
  empty_completion: "A resposta veio vazia. Tente pedir de outro jeito.",
  tools_unavailable: "As ferramentas não estão disponíveis nesta visualização.",
};

export default function App() {
  const [sample, setSample] = useState<Sample | null>(null);
  const [mcp, setMcp] = useState<Mcp | null>(null);
  const [downloads, setDownloads] = useState<Downloads | null>(null);
  const [semClaude, setSemClaude] = useState(false);
  const [pc, setPc] = useState<EstadoPc>("verificando");
  const [base, setBase] = useState<StatusBase | null>(null);
  const [conversas, setConversas] = useState<ResumoConversa[]>([]);
  const [carregandoLista, setCarregandoLista] = useState(true);
  const [conversa, setConversa] = useState<Conversa>(conversaVazia);
  const [ocupado, setOcupado] = useState(false);
  const [escrevendo, setEscrevendo] = useState<{ texto: string; ferramentas: UsoFerramenta[]; anexos: Anexo[] } | null>(null);
  const [script, setScript] = useState<{ etapas: string[]; atual: number } | null>(null);
  const [aval, setAval] = useState<{ script: string; descricao: string; comando: string[]; decidir: (ok: boolean) => void } | null>(
    null,
  );
  const [lateralAberta, setLateralAberta] = useState(() => window.innerWidth >= 768);
  const [preencher, setPreencher] = useState<{ texto: string; n: number }>();
  const [aviso, setAviso] = useState<string | null>(null);
  const [diagnostico, setDiagnostico] = useState<string | null>(null);
  const [excluir, setExcluir] = useState<{ conversa: ResumoConversa; excluindo: boolean } | null>(null);
  const arquivos = useRef(new Map<string, string>());
  const [prontos, setProntos] = useState(new Set<string>());
  const controle = useRef<AbortController | null>(null);
  const fim = useRef<HTMLDivElement>(null);

  // liga no PC: primeiro lista os servidores que a página enxerga, depois chama o ak_local
  const conectar = useCallback(async (m: Mcp, vivo: () => boolean = () => true) => {
    setPc("verificando");
    setCarregandoLista(true);
    let servidores = "?";
    try {
      const l = await m.listTools();
      servidores = l.servers.map((s) => `${s.server} (${s.authStatus})`).join(", ") || "nenhum";
    } catch (e) {
      servidores = `listTools falhou: ${codigoErro(e)}`;
    }
    try {
      const [st, lista] = await Promise.all([chamarPc(m, "status_base"), chamarPc(m, "listar_conversas")]);
      if (!vivo()) return;
      setBase(comoBase(st));
      setConversas(comoLista<ResumoConversa>(lista));
      setPc("conectado");
      setDiagnostico(null);
    } catch (e) {
      if (!vivo()) return;
      setPc("desconectado");
      const msg = typeof e === "object" && e && "message" in e ? String((e as { message: string }).message) : String(e);
      setDiagnostico(`Erro ${codigoErro(e)}: ${msg} · Servidores visíveis: ${servidores}`);
    } finally {
      if (vivo()) setCarregandoLista(false);
    }
  }, []);

  // capabilities: o Claude (sample), o PC e o Microsoft 365 (mcp) e o botão Baixar (downloads)
  useEffect(() => {
    let vivo = true;
    (async () => {
      const [s, m, d] = await Promise.all([usar<Sample>("sample"), usar<Mcp>("mcp"), usar<Downloads>("downloads")]);
      if (!vivo) return;
      setSample(() => s); // função no setState seria executada pelo React
      setMcp(m);
      setDownloads(d);
      setSemClaude(!s);
      if (!m) {
        setPc("desconectado");
        setDiagnostico("A página não recebeu a capability mcp (claude.use(\"mcp\") voltou vazio).");
        setCarregandoLista(false);
        return;
      }
      await conectar(m, () => vivo);
    })();
    return () => {
      vivo = false;
    };
  }, []);

  useEffect(() => {
    fim.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [conversa.mensagens.length, escrevendo?.texto, escrevendo?.ferramentas.length, script]);

  const atualizarLista = useCallback(async () => {
    if (!mcp) return;
    try {
      setConversas(comoLista<ResumoConversa>(await chamarPc(mcp, "listar_conversas")));
    } catch {
      /* a lista antiga continua na tela */
    }
  }, [mcp]);

  const salvar = useCallback(
    async (c: Conversa) => {
      if (!mcp || pc !== "conectado") return c;
      try {
        const id = (await chamarPc(mcp, "salvar_conversa", { conversa: c })) as string;
        void atualizarLista();
        return { ...c, id };
      } catch {
        setAviso("Não consegui salvar a conversa no PC. Ela continua aqui na tela.");
        return c;
      }
    },
    [mcp, pc, atualizarLista],
  );

  const abrir = async (id: string) => {
    if (!mcp || ocupado) return;
    try {
      setConversa((await chamarPc(mcp, "carregar_conversa", { id })) as Conversa);
      if (window.innerWidth < 768) setLateralAberta(false);
    } catch {
      setAviso("Não consegui abrir essa conversa.");
    }
  };

  // move para dados\excluidos no PC; se for a conversa aberta, volta para uma conversa nova
  const confirmarExclusao = async () => {
    if (!mcp || !excluir) return;
    const alvo = excluir.conversa;
    setExcluir({ conversa: alvo, excluindo: true });
    try {
      await chamarPc(mcp, "apagar_conversa", { id: alvo.id });
      setConversas((lista) => lista.filter((c) => c.id !== alvo.id));
      if (conversa.id === alvo.id) setConversa(conversaVazia());
      setAviso(`"${alvo.titulo}" foi para dados\\excluidos no PC.`);
      void atualizarLista();
    } catch (e) {
      setAviso(codigoErro(e) === "cancelled" ? "Exclusão cancelada no app." : "Não consegui excluir a conversa.");
    } finally {
      setExcluir(null);
    }
  };

  const nova = () => {
    if (ocupado) return;
    setConversa(conversaVazia());
    if (window.innerWidth < 768) setLateralAberta(false);
  };

  const baixar = async (a: Anexo) => {
    const b64 = arquivos.current.get(a.caminho_copia);
    if (!b64) return;
    if (!downloads) {
      setAviso(`O download não está disponível aqui. A cópia está em ${a.caminho_copia}`);
      return;
    }
    try {
      await downloads.save({ filename: a.nome_arquivo, data: base64ParaBytes(b64) });
    } catch (e) {
      const c = codigoErro(e);
      if (c !== "declined") setAviso(`Não deu para baixar (${c}). A cópia está em ${a.caminho_copia}`);
    }
  };

  const enviar = async (texto: string) => {
    if (!sample || ocupado) return;
    setAviso(null);
    const pergunta: Mensagem = { papel: "usuario", texto, hora: agora() };
    const historico = conversa.mensagens;
    let atual: Conversa = {
      ...conversa,
      titulo: conversa.mensagens.length ? conversa.titulo : texto.slice(0, 60),
      base_do_dia: base?.laudo.data ?? null,
      mensagens: [...historico, pergunta],
    };
    setConversa(atual);
    setOcupado(true);
    const usos: UsoFerramenta[] = [];
    const anexos: Anexo[] = [];
    setEscrevendo({ texto: "", ferramentas: usos, anexos });
    controle.current = new AbortController();

    let resposta: Mensagem;
    try {
      const final = await responder(
        sample,
        pc === "conectado" ? mcp : null,
        historico,
        texto,
        {
          aoEscrever: (t) => setEscrevendo((e) => (e ? { ...e, texto: t } : e)),
          aoUsarFerramenta: (u) => {
            usos.push(u);
            setEscrevendo((e) => (e ? { ...e, ferramentas: [...usos] } : e));
            if (u.nome === "status_base" && !u.erro && mcp)
              chamarPc(mcp, "status_base").then((s) => setBase(comoBase(s)), () => {});
          },
          aoReceberArquivo: (a, b64) => {
            anexos.push(a);
            if (b64) {
              arquivos.current.set(a.caminho_copia, b64);
              setProntos(new Set(arquivos.current.keys()));
            }
            setEscrevendo((e) => (e ? { ...e, anexos: [...anexos] } : e));
          },
          pedirAval: (p) => new Promise((decidir) => setAval({ ...p, decidir })),
          aoRodarScript: setScript,
        },
        controle.current.signal,
      );
      resposta = { papel: "agente", texto: final, hora: agora(), ferramentas: usos, anexos };
    } catch (e) {
      const c = codigoErro(e);
      const parcial = typeof e === "object" && e && "text" in e ? String((e as { text?: string }).text ?? "") : "";
      const detalhe = typeof e === "object" && e && "message" in e ? String((e as { message: string }).message).slice(0, 300) : String(e);
      resposta = {
        papel: "agente",
        texto: c === "refused" ? "" : parcial,
        hora: agora(),
        ferramentas: usos,
        anexos,
        erro: c === "cancelled" ? "Resposta interrompida." : `${COPIA_ERRO_SAMPLE[c] ?? "A resposta falhou."} (${c}: ${detalhe})`,
      };
    }
    atual = { ...atual, mensagens: [...atual.mensagens, resposta] };
    setEscrevendo(null);
    setScript(null);
    setOcupado(false);
    setConversa(await salvar(atual));
  };

  const preencherCaixa = (texto: string) => setPreencher({ texto, n: Date.now() });

  const dock = [
    { titulo: "Nova conversa", icone: <IconPlus className="h-full w-full" stroke={1.8} />, aoClicar: nova },
    {
      titulo: "Chamados",
      icone: <IconTicket className="h-full w-full" stroke={1.6} />,
      aoClicar: () => preencherCaixa("Quais contas estão fora do SLA e ainda sem chamado? Confira também a planilha de chamados."),
    },
    {
      titulo: "Arquivos",
      icone: <IconFolder className="h-full w-full" stroke={1.6} />,
      aoClicar: () => preencherCaixa("Quais arquivos do dia você pode me trazer?"),
    },
    {
      titulo: "Scripts",
      icone: <IconTerminal2 className="h-full w-full" stroke={1.6} />,
      aoClicar: () => preencherCaixa("Quais scripts você pode rodar?"),
    },
    {
      titulo: "Base do dia",
      icone: <IconShieldCheck className="h-full w-full" stroke={1.6} />,
      aoClicar: () => preencherCaixa("A base de hoje foi liberada?"),
    },
    { titulo: "Zerados", dica: "em breve", desabilitado: true, icone: <IconUserOff className="h-full w-full" stroke={1.6} />, aoClicar: () => {} },
    { titulo: "Projeção", dica: "em breve", desabilitado: true, icone: <IconChartLine className="h-full w-full" stroke={1.6} />, aoClicar: () => {} },
  ];

  const vazia = conversa.mensagens.length === 0 && !escrevendo;

  return (
    <div className="flex h-full items-stretch justify-center md:p-5">
      <div className="relative flex h-full w-full max-w-[1280px] flex-col overflow-hidden bg-janela md:rounded-xl md:border md:border-borda md:shadow-[var(--sombra)]">
        <BarraTitulo base={base} pc={pc} aoAlternarLateral={() => setLateralAberta((a) => !a)} />

        <div className="relative flex min-h-0 flex-1">
          <AnimatePresence initial={false}>
            {lateralAberta && (
              <motion.aside
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: 260, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                transition={{ duration: 0.22, ease: "easeOut" }}
                className="z-20 shrink-0 overflow-hidden border-r border-borda max-md:absolute max-md:inset-y-0 max-md:left-0 max-md:shadow-[var(--sombra)]"
              >
                <div className="h-full w-[260px]">
                  <BarraLateral
                    conversas={conversas}
                    atual={conversa.id}
                    carregando={carregandoLista}
                    semPc={pc === "desconectado"}
                    aoAbrir={abrir}
                    aoNova={nova}
                    aoExcluir={(c) => !ocupado && setExcluir({ conversa: c, excluindo: false })}
                  />
                </div>
              </motion.aside>
            )}
          </AnimatePresence>

          <main className="flex min-w-0 flex-1 flex-col">
            <div className="min-h-0 flex-1 overflow-y-auto">
              <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6">
                {semClaude && (
                  <p className="rounded-xl border border-borda bg-superficie px-4 py-3 text-[13px] text-texto-2">
                    Esta página só conversa dentro do Claude. Abra o link no app desktop do Claude.
                  </p>
                )}
                {pc === "desconectado" && !semClaude && (
                  <p className="rounded-xl border border-borda bg-superficie px-4 py-3 text-[13px] leading-relaxed text-texto-2">
                    O PC não respondeu. O chat funciona, mas sem a base, os chamados, os arquivos e os scripts. Para ligar,
                    abra o agente no app desktop do Claude com o servidor <span className="font-mono text-[12px]">ak_local</span> em
                    execução (Configurações → Desenvolvedor).
                    {diagnostico && (
                      <span className="mt-2 block break-words font-mono text-[11.5px] text-texto-3">{diagnostico}</span>
                    )}
                    {mcp && (
                      <button
                        type="button"
                        onClick={() => conectar(mcp)}
                        className="mt-2 block rounded-full border border-borda bg-janela px-3 py-1 text-[12px] text-texto hover:border-azul hover:text-azul"
                      >
                        Tentar conectar de novo
                      </button>
                    )}
                  </p>
                )}

                {vazia && (
                  <section className="flex flex-col gap-5 pt-[8vh]">
                    <Avatar tamanho={64} />
                    <TextGenerateEffect
                      texto="Pergunte sobre a base do dia, os chamados ou os arquivos do RPA."
                      className="max-w-xl text-[26px] font-semibold leading-tight tracking-tight text-texto"
                    />
                    <p className="max-w-xl text-[14px] leading-relaxed text-texto-2">
                      O agente lê a base validada da Central, os chamados do robô e da planilha ABERTURA DE CHAMADOS, entrega
                      cópias dos arquivos e roda os scripts liberados. Zerados, projeção, constância e destaques estão em
                      construção.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {SUGESTOES.slice(0, 4).map((s) => (
                        <button
                          key={s}
                          type="button"
                          disabled={!sample}
                          onClick={() => enviar(s)}
                          className="rounded-full border border-borda bg-janela px-3 py-1.5 text-left text-[13px] text-texto hover:border-azul hover:text-azul disabled:opacity-50"
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  </section>
                )}

                {conversa.mensagens.map((m, i) => (
                  <Bolha key={`${m.hora}-${i}`} m={m} arquivosProntos={prontos} aoBaixar={baixar} />
                ))}

                {escrevendo && (
                  <div className="flex flex-col gap-3">
                    <Bolha
                      m={{ papel: "agente", texto: escrevendo.texto, hora: "", ferramentas: escrevendo.ferramentas, anexos: escrevendo.anexos }}
                      escrevendo
                      arquivosProntos={prontos}
                      aoBaixar={baixar}
                    />
                    <MultiStepLoader etapas={script?.etapas ?? []} atual={script?.atual ?? 0} visivel={script !== null} />
                  </div>
                )}
                <div ref={fim} />
              </div>
            </div>

            <div className="shrink-0 border-t border-borda bg-barra px-4 pb-[calc(12px+env(safe-area-inset-bottom,0px))] pt-3 backdrop-blur-xl sm:px-6">
              <div className="mx-auto flex w-full max-w-3xl flex-col gap-3">
                {aviso && (
                  <p role="status" className="flex items-center justify-between gap-3 text-[12px] text-amarelo">
                    {aviso}
                    <button type="button" onClick={() => setAviso(null)} className="shrink-0 text-texto-3 hover:text-texto">
                      Fechar
                    </button>
                  </p>
                )}
                <div className="flex items-center gap-2">
                  <div className="min-w-0 flex-1">
                    <PlaceholdersAndVanishInput sugestoes={SUGESTOES} aoEnviar={enviar} ocupado={ocupado || !sample} valorExterno={preencher} />
                  </div>
                  {ocupado && (
                    <button
                      type="button"
                      onClick={() => controle.current?.abort()}
                      aria-label="Parar a resposta"
                      title="Parar"
                      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-borda bg-janela text-texto-2 hover:text-vermelho"
                    >
                      <IconPlayerStopFilled className="h-4 w-4" />
                    </button>
                  )}
                </div>
                <FloatingDock itens={dock} className={cn(ocupado && "pointer-events-none opacity-60")} />
              </div>
            </div>
          </main>
        </div>
      </div>

      <AnimatedModal
        aberto={aval !== null}
        aoFechar={() => {
          aval?.decidir(false);
          setAval(null);
        }}
      >
        {aval && (
          <div className="flex flex-col gap-4 p-5">
            <div className="flex flex-col gap-1">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-amarelo">Ação externa · precisa do seu aval</p>
              <h2 className="text-[17px] font-semibold text-texto">Rodar {aval.script}?</h2>
              {aval.descricao && <p className="text-[13px] leading-relaxed text-texto-2">{aval.descricao}</p>}
            </div>
            <pre className="overflow-x-auto rounded-lg border border-borda bg-superficie px-3 py-2 font-mono text-[12px] text-texto">
              {aval.comando.map((c) => (/\s/.test(c) ? `"${c}"` : c)).join(" ")}
            </pre>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  aval.decidir(false);
                  setAval(null);
                }}
                className="rounded-lg border border-borda px-3.5 py-1.5 text-[13px] text-texto hover:bg-superficie"
              >
                Não rodar
              </button>
              <button
                type="button"
                onClick={() => {
                  aval.decidir(true);
                  setAval(null);
                }}
                className="rounded-lg bg-azul px-3.5 py-1.5 text-[13px] font-medium text-white hover:brightness-110"
              >
                Rodar agora
              </button>
            </div>
          </div>
        )}
      </AnimatedModal>
      <AnimatedModal aberto={excluir !== null} aoFechar={() => !excluir?.excluindo && setExcluir(null)}>
        {excluir && (
          <div className="flex flex-col gap-4 p-5">
            <div className="flex flex-col gap-1">
              <h2 className="text-[17px] font-semibold text-texto">Excluir esta conversa?</h2>
              <p className="truncate text-[13px] font-medium text-texto">{excluir.conversa.titulo}</p>
              <p className="text-[13px] leading-relaxed text-texto-2">
                Ela sai da lista e vai para a pasta <span className="font-mono text-[12px]">dados\excluidos</span> no PC. Para
                recuperar, é só mover o arquivo de volta para <span className="font-mono text-[12px]">dados\conversas</span>.
              </p>
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                disabled={excluir.excluindo}
                onClick={() => setExcluir(null)}
                className="rounded-lg border border-borda px-3.5 py-1.5 text-[13px] text-texto hover:bg-superficie disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={excluir.excluindo}
                onClick={confirmarExclusao}
                className="rounded-lg bg-vermelho px-3.5 py-1.5 text-[13px] font-medium text-white hover:brightness-110 disabled:opacity-60"
              >
                {excluir.excluindo ? "Excluindo…" : "Excluir"}
              </button>
            </div>
          </div>
        )}
      </AnimatedModal>
    </div>
  );
}
