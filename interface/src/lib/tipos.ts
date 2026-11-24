// Formato salvo em dados\conversas\<id>.json pelo servidor ak_local.
export type Anexo = {
  nome_arquivo: string;
  caminho_copia: string;
  origem: string;
  modificado_origem: string;
  linhas: number | null;
  tamanho_bytes: number;
  mime: string;
  dados_pessoais_removidos: string[];
  aviso?: string;
};

export type UsoFerramenta = { nome: string; entrada: Record<string, unknown>; resumo: string; erro?: boolean };

export type Mensagem = {
  papel: "usuario" | "agente";
  texto: string;
  hora: string;
  ferramentas?: UsoFerramenta[];
  anexos?: Anexo[];
  erro?: string;
};

export type Conversa = {
  id?: string;
  titulo: string;
  criada?: string;
  atualizada?: string;
  base_do_dia?: string | null;
  mensagens: Mensagem[];
};

export type ResumoConversa = { id: string; titulo: string; criada: string; atualizada: string; mensagens: number };

export type StatusBase = {
  liberada: boolean;
  aviso: string | null;
  laudo: { arquivo: string | null; data: string | null; status: string | null };
  auditoria: { arquivo: string | null; data: string | null; veredito: string | null };
};
