import { IconAlertTriangle, IconDownload, IconFileSpreadsheet, IconTool } from "@tabler/icons-react";
import { motion } from "motion/react";
import { memo, useMemo } from "react";
import { Avatar } from "@/components/Avatar";
import { paraHtml } from "@/lib/markdown";
import type { Anexo, Mensagem, UsoFerramenta } from "@/lib/tipos";
import { cn } from "@/lib/utils";

const NOMES: Record<string, string> = {
  status_base: "Conferiu a base do dia",
  listar_arquivos: "Listou os arquivos",
  buscar_arquivo: "Preparou o arquivo",
  consultar_cnpj: "Consultou o CNPJ",
  contas_fora_do_sla: "Buscou as contas fora do SLA",
  ler_planilha_chamados: "Leu a planilha de chamados",
  listar_scripts: "Listou os scripts",
  rodar_script: "Rodou o script",
  dias_uteis: "Contou os dias úteis",
};

export function Ferramentas({ usos }: { usos: UsoFerramenta[] }) {
  if (!usos.length) return null;
  return (
    <ul className="flex flex-wrap gap-1.5">
      {usos.map((u, i) => (
        <li
          key={`${u.nome}-${i}`}
          title={JSON.stringify(u.entrada)}
          className={cn(
            "flex max-w-full items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[12px]",
            u.erro ? "border-vermelho/30 text-vermelho" : "border-borda bg-superficie text-texto-2",
          )}
        >
          {u.erro ? <IconAlertTriangle className="h-3.5 w-3.5 shrink-0" /> : <IconTool className="h-3.5 w-3.5 shrink-0" stroke={1.6} />}
          <span className="truncate">
            {NOMES[u.nome] ?? u.nome} · {u.resumo}
          </span>
        </li>
      ))}
    </ul>
  );
}

function tamanho(bytes: number) {
  return bytes > 1_048_576 ? `${(bytes / 1_048_576).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function dataHora(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export function CartaoArquivo({
  anexo,
  disponivel,
  aoBaixar,
}: {
  anexo: Anexo;
  disponivel: boolean;
  aoBaixar: () => void;
}) {
  return (
    <div className="flex w-full max-w-md items-center gap-3 rounded-xl border border-borda bg-janela p-3">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-planilha-suave text-planilha">
        <IconFileSpreadsheet className="h-5 w-5" stroke={1.6} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-medium text-texto">{anexo.nome_arquivo}</p>
        <p className="truncate text-[12px] text-texto-3">
          {anexo.linhas != null ? `${anexo.linhas.toLocaleString("pt-BR")} linhas · ` : ""}
          {tamanho(anexo.tamanho_bytes)} · base de {dataHora(anexo.modificado_origem)}
          {anexo.dados_pessoais_removidos.length > 0 ? " · sem CPF/nascimento" : ""}
        </p>
      </div>
      {disponivel ? (
        <button
          type="button"
          onClick={aoBaixar}
          className="flex shrink-0 items-center gap-1 rounded-full bg-azul px-3 py-1 text-[12px] font-medium text-white hover:brightness-110"
        >
          <IconDownload className="h-3.5 w-3.5" stroke={2} />
          Baixar
        </button>
      ) : (
        <span title={anexo.caminho_copia} className="shrink-0 text-[11px] text-texto-3">
          cópia no PC
        </span>
      )}
    </div>
  );
}

const Markdown = memo(function Markdown({ texto }: { texto: string }) {
  const html = useMemo(() => paraHtml(texto), [texto]);
  return <div className="resposta text-[14px] text-texto" dangerouslySetInnerHTML={{ __html: html }} />;
});

export function Bolha({
  m,
  escrevendo,
  arquivosProntos,
  aoBaixar,
}: {
  m: Mensagem;
  escrevendo?: boolean;
  arquivosProntos: Set<string>;
  aoBaixar: (a: Anexo) => void;
}) {
  if (m.papel === "usuario") {
    return (
      <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
        <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-azul px-3.5 py-2 text-[14px] leading-relaxed text-white">
          {m.texto}
        </p>
      </motion.div>
    );
  }
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="flex min-w-0 gap-3">
      <Avatar tamanho={30} className="mt-0.5" />
      <div className="flex min-w-0 flex-1 flex-col gap-2.5">
      {m.ferramentas && <Ferramentas usos={m.ferramentas} />}
      {m.texto ? (
        <Markdown texto={m.texto} />
      ) : (
        escrevendo && (
          <motion.p
            className="text-[14px] text-texto-3"
            animate={{ opacity: [0.4, 1, 0.4] }}
            transition={{ repeat: Infinity, duration: 1.6 }}
          >
            Pensando…
          </motion.p>
        )
      )}
      {m.anexos?.map((a) => (
        <CartaoArquivo key={a.caminho_copia} anexo={a} disponivel={arquivosProntos.has(a.caminho_copia)} aoBaixar={() => aoBaixar(a)} />
      ))}
      {m.erro && (
        <p className="flex items-start gap-1.5 rounded-lg border border-vermelho/30 px-3 py-2 text-[13px] text-vermelho">
          <IconAlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          {m.erro}
        </p>
      )}
      </div>
    </motion.div>
  );
}
