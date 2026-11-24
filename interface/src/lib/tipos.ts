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

export type EmailResumo = {
  id: string;
  uri: string;
  assunto: string;
  remetente: string;
  email_remetente: string;
  recebido: string;
  resumo: string;
  lido: boolean;
  importante: boolean;
  anexos: boolean;
  link: string;
};

export type EventoAgenda = { assunto: string; inicio: string; fim: string; fuso: string; local: string; organizador: string; link: string };

export type DiaSemana = "seg" | "ter" | "qua" | "qui" | "sex" | "sab" | "dom";

export type Rotina = {
  id?: string;
  nome: string;
  pedido: string;
  hora: string;
  dias: DiaSemana[];
  ativa: boolean;
  ultima_execucao?: string | null;
};

export type TarefaPc = {
  nome: string;
  habilitada: boolean;
  status: string;
  proxima_execucao: string | null;
  ultima_execucao: string | null;
  ultimo_resultado: string;
  ok: boolean;
  descricao: string | null;
};

export type Notificacao =
  | { tipo: "email"; id: string; quando: string; email: EmailResumo }
  | { tipo: "rotina"; id: string; quando: string; rotina: Rotina };
