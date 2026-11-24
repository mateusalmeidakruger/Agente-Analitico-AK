import { IconMessage2, IconPlus, IconSearch, IconTrash } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import type { ResumoConversa } from "@/lib/tipos";
import { cn } from "@/lib/utils";

function grupo(iso: string): string {
  const d = new Date(iso);
  const hoje = new Date();
  const zero = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const dias = Math.round((zero(hoje) - zero(d)) / 86_400_000);
  if (dias <= 0) return "Hoje";
  if (dias === 1) return "Ontem";
  if (dias < 7) return "Últimos 7 dias";
  return "Anteriores";
}

export function BarraLateral({
  conversas,
  atual,
  carregando,
  semPc,
  aoAbrir,
  aoNova,
  aoExcluir,
}: {
  conversas: ResumoConversa[];
  atual: string | undefined;
  carregando: boolean;
  semPc: boolean;
  aoAbrir: (id: string) => void;
  aoNova: () => void;
  aoExcluir: (c: ResumoConversa) => void;
}) {
  const [busca, setBusca] = useState("");
  const grupos = useMemo(() => {
    const filtradas = conversas.filter((c) => c.titulo.toLowerCase().includes(busca.toLowerCase()));
    const mapa = new Map<string, ResumoConversa[]>();
    for (const c of filtradas) {
      const g = grupo(c.atualizada ?? c.criada);
      mapa.set(g, [...(mapa.get(g) ?? []), c]);
    }
    return [...mapa.entries()];
  }, [conversas, busca]);

  return (
    <nav aria-label="Conversas" className="flex h-full w-full flex-col gap-3 bg-lateral px-3 pb-3 pt-3 backdrop-blur-2xl">
      <div className="flex items-center gap-2">
        <label className="flex h-8 min-w-0 flex-1 items-center gap-1.5 rounded-lg bg-realce px-2 text-texto-3">
          <IconSearch className="h-3.5 w-3.5 shrink-0" stroke={1.8} />
          <input
            id="busca-conversas"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar"
            className="w-full min-w-0 bg-transparent text-[13px] text-texto placeholder:text-texto-3 focus:outline-none"
          />
        </label>
        <button
          type="button"
          onClick={aoNova}
          aria-label="Nova conversa"
          title="Nova conversa"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-texto-2 hover:bg-realce hover:text-texto"
        >
          <IconPlus className="h-4 w-4" stroke={2} />
        </button>
      </div>

      <div className="-mx-1 min-h-0 flex-1 overflow-y-auto px-1">
        {semPc && (
          <p className="px-2 py-3 text-[12px] leading-relaxed text-texto-3">
            As conversas ficam salvas no PC. Abra o agente no app desktop do Claude, com o ak_local ligado, para vê-las.
          </p>
        )}
        {!semPc && carregando && <p className="px-2 py-3 text-[12px] text-texto-3">Carregando conversas…</p>}
        {!semPc && !carregando && conversas.length === 0 && (
          <p className="px-2 py-3 text-[12px] leading-relaxed text-texto-3">
            Nenhuma conversa salva ainda. Cada conversa vira um arquivo em dados\conversas no PC.
          </p>
        )}
        {grupos.map(([nome, itens]) => (
          <section key={nome} className="mb-3">
            <h2 className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-texto-3">{nome}</h2>
            <ul className="flex flex-col gap-0.5">
              {itens.map((c) => (
                <li key={c.id} className="group relative">
                  <button
                    type="button"
                    onClick={() => aoAbrir(c.id)}
                    className={cn(
                      "flex w-full items-center gap-2 rounded-lg py-1.5 pl-2 pr-8 text-left text-[13px]",
                      c.id === atual ? "bg-azul text-white" : "text-texto hover:bg-realce",
                    )}
                  >
                    <IconMessage2 className={cn("h-4 w-4 shrink-0", c.id === atual ? "text-white" : "text-texto-3")} stroke={1.6} />
                    <span className="truncate">{c.titulo}</span>
                  </button>
                  {/* aparece ao passar o mouse ou focar; no celular fica sempre visível */}
                  <button
                    type="button"
                    onClick={() => aoExcluir(c)}
                    aria-label={`Excluir a conversa ${c.titulo}`}
                    title="Excluir conversa"
                    className={cn(
                      "absolute right-1 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md opacity-100 transition-opacity focus:opacity-100 md:opacity-0 md:group-hover:opacity-100",
                      c.id === atual ? "text-white/80 hover:bg-white/15 hover:text-white" : "text-texto-3 hover:bg-realce hover:text-vermelho",
                    )}
                  >
                    <IconTrash className="h-3.5 w-3.5" stroke={1.8} />
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </nav>
  );
}
