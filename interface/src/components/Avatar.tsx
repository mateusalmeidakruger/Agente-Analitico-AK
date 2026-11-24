import { cn } from "@/lib/utils";

// Avatar do agente: pinguim desenhado em SVG (próprio, sem imagem de banco).
export function Avatar({ tamanho = 28, className }: { tamanho?: number; className?: string }) {
  return (
    <span
      className={cn("inline-flex shrink-0 items-center justify-center rounded-full bg-[#e8eef7] ring-1 ring-borda", className)}
      style={{ width: tamanho, height: tamanho }}
      aria-hidden="true"
    >
      <svg viewBox="0 0 100 100" width={tamanho * 0.86} height={tamanho * 0.86}>
        {/* cabeça */}
        <path d="M8 70C8 31 28 14 50 14s42 17 42 56c0 8-7 12-42 12S8 78 8 70z" fill="#141414" />
        {/* rosto em coração */}
        <path d="M21 72c-5-20-1-38 14-42 8-2 13 2 15 8 2-6 7-10 15-8 15 4 19 22 14 42-9 6-49 6-58 0z" fill="#fff" />
        {/* olhos */}
        <circle cx="37" cy="47" r="5.2" fill="#141414" />
        <circle cx="38.8" cy="45.3" r="1.7" fill="#fff" />
        <circle cx="63" cy="47" r="5.2" fill="#141414" />
        <circle cx="64.8" cy="45.3" r="1.7" fill="#fff" />
        {/* bochechas */}
        <ellipse cx="31" cy="55" rx="4.6" ry="2.6" fill="#f3a3ad" opacity="0.85" />
        <ellipse cx="69" cy="55" rx="4.6" ry="2.6" fill="#f3a3ad" opacity="0.85" />
        {/* bico */}
        <path d="M40 65.5c3 5 17 5 20 0" fill="#f4a64f" stroke="#141414" strokeWidth="1.4" />
        <path d="M33.5 63.5C35 55 43 52 50 52s15 3 16.5 11.5C60 66 40 66 33.5 63.5z" fill="#f4a64f" stroke="#141414" strokeWidth="1.4" strokeLinejoin="round" />
        <ellipse cx="46" cy="56.5" rx="1.8" ry="1" fill="#d9843a" />
        <ellipse cx="54" cy="56.5" rx="1.8" ry="1" fill="#d9843a" />
      </svg>
    </span>
  );
}
