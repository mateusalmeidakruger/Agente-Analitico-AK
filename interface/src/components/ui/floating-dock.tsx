// Floating Dock (Aceternity UI), adaptado: itens são botões, podem vir desabilitados ("em breve").
import { IconLayoutNavbarCollapse } from "@tabler/icons-react";
import { AnimatePresence, type MotionValue, motion, useMotionValue, useSpring, useTransform } from "motion/react";
import { type ReactNode, useRef, useState } from "react";
import { cn } from "@/lib/utils";

export type ItemDock = {
  titulo: string;
  icone: ReactNode;
  aoClicar: () => void;
  desabilitado?: boolean;
  dica?: string;
};

export function FloatingDock({ itens, className }: { itens: ItemDock[]; className?: string }) {
  return (
    <>
      <DockDesktop itens={itens} className={className} />
      <DockCelular itens={itens} className={className} />
    </>
  );
}

function DockCelular({ itens, className }: { itens: ItemDock[]; className?: string }) {
  const [aberto, setAberto] = useState(false);
  return (
    <div className={cn("relative block md:hidden", className)}>
      <AnimatePresence>
        {aberto && (
          <motion.div layoutId="dock-celular" className="absolute inset-x-0 bottom-full mb-2 flex flex-col items-center gap-2">
            {itens.map((item, i) => (
              <motion.div
                key={item.titulo}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10, transition: { delay: i * 0.04 } }}
                transition={{ delay: (itens.length - 1 - i) * 0.04 }}
              >
                <button
                  type="button"
                  disabled={item.desabilitado}
                  onClick={() => {
                    setAberto(false);
                    item.aoClicar();
                  }}
                  className="flex h-10 items-center gap-2 rounded-full border border-borda bg-barra px-3 text-[13px] text-texto shadow-sm backdrop-blur-xl disabled:opacity-45"
                >
                  <span className="h-4 w-4">{item.icone}</span>
                  {item.titulo}
                  {item.dica && <span className="text-texto-3">· {item.dica}</span>}
                </button>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
      <button
        type="button"
        aria-label="Atalhos"
        onClick={() => setAberto(!aberto)}
        className="mx-auto flex h-10 w-10 items-center justify-center rounded-full border border-borda bg-barra backdrop-blur-xl"
      >
        <IconLayoutNavbarCollapse className="h-5 w-5 text-texto-2" />
      </button>
    </div>
  );
}

function DockDesktop({ itens, className }: { itens: ItemDock[]; className?: string }) {
  const mouseX = useMotionValue(Infinity);
  return (
    <motion.div
      onMouseMove={(e) => mouseX.set(e.pageX)}
      onMouseLeave={() => mouseX.set(Infinity)}
      className={cn(
        "mx-auto hidden h-[60px] items-end gap-3 rounded-2xl border border-borda bg-barra px-3 pb-2.5 shadow-[0_8px_30px_rgba(0,0,0,0.08)] backdrop-blur-xl md:flex",
        className,
      )}
    >
      {itens.map((item) => (
        <IconeDock mouseX={mouseX} key={item.titulo} {...item} />
      ))}
    </motion.div>
  );
}

function IconeDock({ mouseX, titulo, icone, aoClicar, desabilitado, dica }: ItemDock & { mouseX: MotionValue }) {
  const ref = useRef<HTMLButtonElement>(null);
  const distancia = useTransform(mouseX, (v) => {
    const b = ref.current?.getBoundingClientRect() ?? { x: 0, width: 0 };
    return v - b.x - b.width / 2;
  });
  const mola = { mass: 0.1, stiffness: 150, damping: 12 };
  const lado = useSpring(useTransform(distancia, [-120, 0, 120], [38, 58, 38]), mola);
  const ladoIcone = useSpring(useTransform(distancia, [-120, 0, 120], [18, 28, 18]), mola);
  const [sobre, setSobre] = useState(false);

  return (
    <motion.button
      ref={ref}
      type="button"
      aria-label={titulo}
      disabled={desabilitado}
      onClick={aoClicar}
      style={{ width: lado, height: lado }}
      onMouseEnter={() => setSobre(true)}
      onMouseLeave={() => setSobre(false)}
      className="relative flex aspect-square items-center justify-center rounded-full bg-superficie text-texto-2 transition-colors hover:text-azul disabled:cursor-default disabled:opacity-45 disabled:hover:text-texto-2"
    >
      <AnimatePresence>
        {sobre && (
          <motion.div
            initial={{ opacity: 0, y: 6, x: "-50%" }}
            animate={{ opacity: 1, y: 0, x: "-50%" }}
            exit={{ opacity: 0, y: 2, x: "-50%" }}
            className="pointer-events-none absolute -top-9 left-1/2 w-fit whitespace-pre rounded-md border border-borda bg-janela px-2 py-0.5 text-xs text-texto shadow-sm"
          >
            {titulo}
            {dica && <span className="text-texto-3"> · {dica}</span>}
          </motion.div>
        )}
      </AnimatePresence>
      <motion.div style={{ width: ladoIcone, height: ladoIcone }} className="flex items-center justify-center">
        {icone}
      </motion.div>
    </motion.button>
  );
}
