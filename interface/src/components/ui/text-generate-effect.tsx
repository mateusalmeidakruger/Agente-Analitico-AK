// Text Generate Effect (Aceternity UI): as palavras aparecem uma a uma, saindo do desfoque.
import { motion, stagger, useAnimate } from "motion/react";
import { useEffect } from "react";
import { cn } from "@/lib/utils";

export function TextGenerateEffect({ texto, className, duracao = 0.5 }: { texto: string; className?: string; duracao?: number }) {
  const [escopo, animar] = useAnimate();
  const palavras = texto.split(" ");

  useEffect(() => {
    animar("span", { opacity: 1, filter: "blur(0px)" }, { duration: duracao, delay: stagger(0.06) });
  }, [animar, duracao, texto]);

  return (
    <div ref={escopo} className={cn(className)}>
      {palavras.map((p, i) => (
        <motion.span key={`${p}-${i}`} style={{ opacity: 0, filter: "blur(8px)" }}>
          {p}{" "}
        </motion.span>
      ))}
    </div>
  );
}
