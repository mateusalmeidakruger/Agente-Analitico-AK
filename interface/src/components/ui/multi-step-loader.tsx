// Multi Step Loader (Aceternity UI), adaptado: mostra as etapas reais de um script rodando
// no PC, dentro de um cartão (não cobre a tela inteira).
import { AnimatePresence, motion } from "motion/react";
import { cn } from "@/lib/utils";

function IconeCheck({ feito, className }: { feito?: boolean; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.6} stroke="currentColor" className={cn("h-5 w-5", className)}>
      {feito ? (
        <path
          fillRule="evenodd"
          fill="currentColor"
          stroke="none"
          d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Zm13.36-1.814a.75.75 0 1 0-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.094l3.75-5.25Z"
          clipRule="evenodd"
        />
      ) : (
        <path d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" strokeLinecap="round" strokeLinejoin="round" />
      )}
    </svg>
  );
}

export function MultiStepLoader({ etapas, atual, visivel }: { etapas: string[]; atual: number; visivel: boolean }) {
  return (
    <AnimatePresence mode="wait">
      {visivel && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className="relative overflow-hidden rounded-xl border border-borda bg-superficie px-4 py-3"
          role="status"
          aria-live="polite"
        >
          <div className="flex flex-col gap-2">
            {etapas.map((etapa, i) => {
              const distancia = Math.abs(i - atual);
              const opacidade = Math.max(1 - distancia * 0.25, 0.35);
              return (
                <motion.div
                  key={etapa}
                  className="flex items-center gap-2 text-[13px]"
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: opacidade, y: 0 }}
                  transition={{ duration: 0.4 }}
                >
                  <IconeCheck
                    feito={i < atual}
                    className={cn(i < atual ? "text-verde" : i === atual ? "text-azul" : "text-texto-3")}
                  />
                  <span className={cn(i === atual ? "font-medium text-texto" : "text-texto-2")}>{etapa}</span>
                  {i === atual && (
                    <motion.span
                      className="ml-1 h-1.5 w-1.5 rounded-full bg-azul"
                      animate={{ opacity: [0.2, 1, 0.2] }}
                      transition={{ repeat: Infinity, duration: 1.2 }}
                    />
                  )}
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
