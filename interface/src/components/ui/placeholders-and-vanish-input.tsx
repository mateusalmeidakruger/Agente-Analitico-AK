// Placeholders and Vanish Input (Aceternity UI), adaptado: sugestões girando e o texto
// se desfaz em partículas ao enviar. Fica bloqueado enquanto o agente responde.
import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

type Particula = { x: number; y: number; r: number; cor: string };

export function PlaceholdersAndVanishInput({
  sugestoes,
  aoEnviar,
  ocupado,
  valorExterno,
}: {
  sugestoes: string[];
  aoEnviar: (texto: string) => void;
  ocupado?: boolean;
  valorExterno?: { texto: string; n: number };
}) {
  const [atual, setAtual] = useState(0);
  const [valor, setValor] = useState("");
  const [sumindo, setSumindo] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const particulas = useRef<Particula[]>([]);
  const intervalo = useRef<number | null>(null);

  // sugestões trocam a cada 3,5 s, pausando com a aba escondida
  useEffect(() => {
    const iniciar = () => {
      intervalo.current = window.setInterval(() => setAtual((a) => (a + 1) % sugestoes.length), 3500);
    };
    const visibilidade = () => {
      if (document.visibilityState !== "visible" && intervalo.current) {
        clearInterval(intervalo.current);
        intervalo.current = null;
      } else if (document.visibilityState === "visible" && !intervalo.current) iniciar();
    };
    iniciar();
    document.addEventListener("visibilitychange", visibilidade);
    return () => {
      if (intervalo.current) clearInterval(intervalo.current);
      document.removeEventListener("visibilitychange", visibilidade);
    };
  }, [sugestoes.length]);

  // um atalho do Dock pode preencher a caixa
  useEffect(() => {
    if (valorExterno) {
      setValor(valorExterno.texto);
      inputRef.current?.focus();
    }
  }, [valorExterno]);

  const desenhar = useCallback(() => {
    const input = inputRef.current;
    const canvas = canvasRef.current;
    if (!input || !canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    canvas.width = 800;
    canvas.height = 800;
    ctx.clearRect(0, 0, 800, 800);
    const estilo = getComputedStyle(input);
    const tamanho = parseFloat(estilo.getPropertyValue("font-size"));
    ctx.font = `${tamanho * 2}px ${estilo.fontFamily}`;
    ctx.fillStyle = estilo.color;
    ctx.fillText(valor, 16, 40);
    const dados = ctx.getImageData(0, 0, 800, 800).data;
    const novas: Particula[] = [];
    for (let y = 0; y < 800; y++) {
      const linha = 4 * y * 800;
      for (let x = 0; x < 800; x++) {
        const i = linha + 4 * x;
        if (dados[i + 3] > 0) {
          novas.push({ x, y, r: 1, cor: `rgba(${dados[i]}, ${dados[i + 1]}, ${dados[i + 2]}, ${dados[i + 3] / 255})` });
        }
      }
    }
    particulas.current = novas;
  }, [valor]);

  const animar = (inicio: number) => {
    const passo = (pos = 0) => {
      requestAnimationFrame(() => {
        const vivas: Particula[] = [];
        for (const p of particulas.current) {
          if (p.x < pos) vivas.push(p);
          else {
            if (p.r <= 0) continue;
            p.x += Math.random() > 0.5 ? 1 : -1;
            p.y += Math.random() > 0.5 ? 1 : -1;
            p.r -= 0.05 * Math.random();
            vivas.push(p);
          }
        }
        particulas.current = vivas;
        const ctx = canvasRef.current?.getContext("2d");
        if (ctx) {
          ctx.clearRect(pos, 0, 800, 800);
          for (const p of particulas.current) {
            if (p.x > pos) {
              ctx.beginPath();
              ctx.rect(p.x, p.y, p.r, p.r);
              ctx.fillStyle = p.cor;
              ctx.fill();
            }
          }
        }
        if (particulas.current.length > 0) passo(pos - 8);
        else {
          setValor("");
          setSumindo(false);
        }
      });
    };
    passo(inicio);
  };

  const enviar = () => {
    const texto = valor.trim();
    if (!texto || ocupado || sumindo) return;
    aoEnviar(texto);
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setValor("");
      return;
    }
    setSumindo(true);
    desenhar();
    const maxX = particulas.current.reduce((m, p) => (p.x > m ? p.x : m), 0);
    animar(maxX);
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        enviar();
      }}
      className={cn(
        "relative mx-auto h-12 w-full overflow-hidden rounded-full border border-borda bg-janela shadow-[0_2px_10px_rgba(0,0,0,0.06)] transition duration-200",
        valor && "bg-superficie",
      )}
    >
      <canvas
        ref={canvasRef}
        className={cn(
          "pointer-events-none absolute left-2 top-[20%] origin-top-left scale-50 pr-20 invert-0",
          sumindo ? "opacity-100" : "opacity-0",
        )}
      />
      <input
        id="mensagem"
        ref={inputRef}
        value={valor}
        onChange={(e) => !sumindo && setValor(e.target.value)}
        aria-label="Mensagem para o agente"
        autoComplete="off"
        className={cn(
          "relative z-10 h-full w-full rounded-full border-none bg-transparent pl-5 pr-14 text-[15px] text-texto focus:outline-none",
          sumindo && "text-transparent",
        )}
        type="text"
      />
      <button
        type="submit"
        aria-label="Enviar"
        disabled={!valor || ocupado}
        className="absolute right-2 top-1/2 z-20 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full bg-azul text-white transition duration-200 disabled:bg-superficie disabled:text-texto-3"
      >
        <motion.svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-4 w-4"
        >
          <path stroke="none" d="M0 0h24v24H0z" fill="none" />
          <motion.path
            d="M5 12l14 0"
            initial={{ strokeDasharray: "50%", strokeDashoffset: "50%" }}
            animate={{ strokeDashoffset: valor ? 0 : "50%" }}
            transition={{ duration: 0.3, ease: "linear" }}
          />
          <path d="M13 18l6 -6" />
          <path d="M13 6l6 6" />
        </motion.svg>
      </button>
      <div className="pointer-events-none absolute inset-0 flex items-center rounded-full">
        <AnimatePresence mode="wait">
          {!valor && (
            <motion.p
              initial={{ y: 5, opacity: 0 }}
              key={`sugestao-${atual}`}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: -15, opacity: 0 }}
              transition={{ duration: 0.3, ease: "linear" }}
              className="w-[calc(100%-3.5rem)] truncate pl-5 text-left text-[15px] text-texto-3"
            >
              {ocupado ? "O agente está respondendo…" : sugestoes[atual]}
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </form>
  );
}
