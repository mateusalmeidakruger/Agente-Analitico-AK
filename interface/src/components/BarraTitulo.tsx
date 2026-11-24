import { IconLayoutSidebar } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { Avatar } from "@/components/Avatar";
import type { StatusBase } from "@/lib/tipos";
import { cn } from "@/lib/utils";

export type EstadoPc = "verificando" | "conectado" | "desconectado";

function dataCurta(iso: string | null) {
  if (!iso) return "?";
  const [, m, d] = iso.split("-");
  return `${d}/${m}`;
}

export function BarraTitulo({
  base,
  pc,
  aoAlternarLateral,
  extra,
}: {
  base: StatusBase | null;
  pc: EstadoPc;
  aoAlternarLateral: () => void;
  extra?: ReactNode;
}) {
  const pilulaBase = base
    ? base.liberada
      ? { texto: `Base ${dataCurta(base.laudo.data)} liberada`, cor: "bg-verde" }
      : { texto: `Base ${dataCurta(base.laudo.data)} · atenção`, cor: "bg-amarelo" }
    : null;

  return (
    <header className="relative flex h-12 shrink-0 items-center gap-3 border-b border-borda bg-barra px-4 backdrop-blur-xl">
      {/* as três bolinhas do macOS: decorativas */}
      <div className="flex items-center gap-2" aria-hidden="true">
        <span className="h-3 w-3 rounded-full bg-[#ff5f57] ring-1 ring-black/10" />
        <span className="h-3 w-3 rounded-full bg-[#febc2e] ring-1 ring-black/10" />
        <span className="h-3 w-3 rounded-full bg-[#28c840] ring-1 ring-black/10" />
      </div>
      <button
        type="button"
        onClick={aoAlternarLateral}
        aria-label="Mostrar ou esconder as conversas"
        className="ml-2 rounded-md p-1 text-texto-2 hover:bg-superficie hover:text-texto"
      >
        <IconLayoutSidebar className="h-[18px] w-[18px]" stroke={1.6} />
      </button>

      <h1 className="pointer-events-none absolute left-1/2 flex -translate-x-1/2 items-center gap-2 truncate text-[13px] font-semibold text-texto max-sm:hidden">
        <Avatar tamanho={22} />
        Agente Analítico AK
      </h1>

      <div className="ml-auto flex min-w-0 items-center gap-2">
        {extra}
        {pilulaBase && (
          <span
            title={base?.aviso ?? `Laudo ${base?.laudo.arquivo ?? ""}`}
            className="flex items-center gap-1.5 truncate rounded-full border border-borda bg-janela px-2.5 py-0.5 text-xs text-texto-2"
          >
            <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", pilulaBase.cor)} />
            <span className="truncate">{pilulaBase.texto}</span>
          </span>
        )}
        <span
          title={
            pc === "conectado"
              ? "O servidor ak_local do PC está respondendo"
              : pc === "desconectado"
                ? "Abra no app desktop do Claude com o ak_local ligado"
                : "Procurando o servidor ak_local"
          }
          className="flex items-center gap-1.5 rounded-full border border-borda bg-janela px-2.5 py-0.5 text-xs text-texto-2"
        >
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              pc === "conectado" ? "bg-verde" : pc === "desconectado" ? "bg-vermelho" : "animate-pulse bg-texto-3",
            )}
          />
          <span className="max-sm:hidden">{pc === "conectado" ? "PC conectado" : pc === "desconectado" ? "PC desconectado" : "Conectando"}</span>
        </span>
      </div>
    </header>
  );
}
