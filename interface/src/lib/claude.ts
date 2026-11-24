// Tipos mínimos das capabilities do Artifact usadas aqui (contrato 0.2.99).
export type ErroCapability = { code: string; message: string; text?: string; retryable?: boolean };

export type FerramentaPagina = {
  name: string;
  description: string;
  inputSchema?: { type: "object"; properties?: Record<string, unknown>; required?: string[] };
  execute: (input: Record<string, unknown>, ctx: { signal: AbortSignal }) => unknown;
};

export type Sample = ((
  input: string | { role: "user" | "assistant"; content: string }[],
  opcoes?: {
    onText?: (u: { text: string; delta: string }) => void;
    signal?: AbortSignal;
    tools?: FerramentaPagina[];
    modelTier?: "default" | "complex" | "quick";
    cache?: boolean;
  },
) => Promise<{ text: string; truncated: boolean }>) & {
  // ausente em apps mais antigos
  limits?: () => Promise<{ maxPromptBytes: number; tools?: { maxCount: number } }>;
};

export type Mcp = {
  callTool: (
    server: string,
    tool: string,
    input?: unknown,
    opcoes?: { cache?: false; signal?: AbortSignal },
  ) => Promise<{ payload?: unknown; content: { type: string; text?: string }[] }>;
  listTools: (server?: string) => Promise<{ servers: { server: string; authStatus: string }[] }>;
};

export type Downloads = {
  save: (r: { filename: string; data: Blob | ArrayBuffer | Uint8Array | string }) => Promise<{ status: string }>;
};

type Claude = { use: (nome: string) => Promise<unknown> };

function claude(): Claude | null {
  return (window as unknown as { claude?: Claude }).claude ?? null;
}

export async function usar<T>(nome: "sample" | "mcp" | "downloads"): Promise<T | null> {
  const c = claude();
  if (!c) return null;
  try {
    return ((await c.use(nome)) as T | null) ?? null;
  } catch {
    return null;
  }
}

export function codigoErro(e: unknown): string {
  return typeof e === "object" && e && "code" in e ? String((e as ErroCapability).code) : "upstream_error";
}
