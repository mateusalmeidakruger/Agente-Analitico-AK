import { IconAlertTriangle, IconCalendarSearch, IconId, IconX } from "@tabler/icons-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

// A "abinha" de Chamados do Dock: atalhos que preenchem a caixa de mensagem.
function dataMenos(dias: number) {
  const d = new Date();
  d.setDate(d.getDate() - dias);
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

export function MenuChamados({
  aberto,
  aoFechar,
  aoEscolher,
}: {
  aberto: boolean;
  aoFechar: () => void;
  aoEscolher: (texto: string) => void;
}) {
  const [dias, setDias] = useState(2);
  const escolher = (texto: string) => {
    aoEscolher(texto);
    aoFechar();
  };
  const desde = dataMenos(dias);

  return (
    <AnimatePresence>
      {aberto && (
        <motion.div
          initial={{ opacity: 0, y: 8, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 8, scale: 0.98 }}
          transition={{ duration: 0.16 }}
          role="menu"
          aria-label="Chamados"
          className="rounded-2xl border border-borda bg-janela p-2 shadow-[var(--sombra)]"
        >
          <div className="flex items-center justify-between px-2 pb-1.5 pt-1">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-texto-3">Chamados</p>
            <button type="button" onClick={aoFechar} aria-label="Fechar" className="rounded-md p-0.5 text-texto-3 hover:text-texto">
              <IconX className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="flex flex-col gap-1">
            <div className="flex flex-wrap items-center gap-2 rounded-xl px-2 py-2 hover:bg-realce">
              <IconCalendarSearch className="h-4 w-4 shrink-0 text-azul" stroke={1.7} />
              <div className="min-w-0 flex-1">
                <p className="text-[13px] text-texto">Consultar no portal</p>
                <p className="text-[11.5px] text-texto-3">
                  Em aberto + concluídos desde 00:00 de {desde} (--dias {dias})
                </p>
              </div>
              <label className="flex items-center gap-1 text-[12px] text-texto-2">
                <input
                  id="dias-portal"
                  type="number"
                  min={0}
                  max={60}
                  value={dias}
                  onChange={(e) => setDias(Math.max(0, Math.min(60, Number(e.target.value) || 0)))}
                  className="w-12 rounded-md border border-borda bg-superficie px-1.5 py-0.5 text-center text-[12px] text-texto tabular-nums"
                />
                dias
              </label>
              <button
                type="button"
                onClick={() =>
                  escolher(
                    `Consulte no portal os chamados em aberto e os concluídos desde 00:00 de ${desde} (--dias ${dias}). Separe abertos e concluídos, com CNPJ, consultor e supervisor.`,
                  )
                }
                className="rounded-full bg-azul px-3 py-1 text-[12px] font-medium text-white hover:brightness-110"
              >
                Usar
              </button>
            </div>

            <button
              type="button"
              role="menuitem"
              onClick={() => escolher("Quais contas estão fora do SLA e ainda sem chamado? Confira também a planilha de chamados.")}
              className="flex items-center gap-2 rounded-xl px-2 py-2 text-left hover:bg-realce"
            >
              <IconAlertTriangle className="h-4 w-4 shrink-0 text-amarelo" stroke={1.7} />
              <span className="text-[13px] text-texto">Contas fora do SLA e sem chamado</span>
            </button>

            <button
              type="button"
              role="menuitem"
              onClick={() => escolher("Qual a situação do chamado do CNPJ ")}
              className="flex items-center gap-2 rounded-xl px-2 py-2 text-left hover:bg-realce"
            >
              <IconId className="h-4 w-4 shrink-0 text-texto-2" stroke={1.7} />
              <span className="text-[13px] text-texto">Situação do chamado de um CNPJ</span>
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
