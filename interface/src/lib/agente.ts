// O agente: regras, ferramentas (servidor ak_local no PC + planilha de chamados pelo
// Microsoft 365) e o ciclo de uma resposta com o Claude do próprio plano (capability sample).
import { codigoErro, type FerramentaPagina, type Mcp, type Sample } from "./claude";
import { agenda, buscarEmails, buscarPessoa, lerEmail } from "./outlook";
import type { Anexo, Mensagem, UsoFerramenta } from "./tipos";

export const HOST = "host:ak_local";
export const M365 = "Microsoft 365";
const PLANILHA_CHAMADOS =
  "file:///b!xbRcSjqQRke3QXsCSBZcy4WPVA9CvvJHgM9uPW62Uw-YfXUN0gMCR4w2qJCOMY1P/01LVVIORSGNPRGBYMEPZHYXSJJDE3NNXPI";
const LIMITE_RESULTADO = 28_000; // o resultado de uma ferramenta vai até 32 KB
const TURNOS_HISTORICO = 20;

function regras(): string {
  const hoje = new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" });
  return `Você é o Agente Analítico AK, o analista de dados da Almeida Kruger (correspondente do Santander: contas PJ e Getnet). Quem fala com você é o Mateus, do time de dados. Hoje é ${hoje}.

Como responder:
- Português do Brasil, direto. Número primeiro, explicação depois. Tabelas em markdown quando houver mais de 3 linhas.
- Antes de dar números da base, chame status_base. Se "liberada" vier falso, comece a resposta com o "aviso".
- Diga sempre a data e o arquivo de onde veio o número (ex.: "Parcial2 de 24/11").
- Nunca invente número. Se nenhuma ferramenta traz o dado, diga que essa análise ainda não está disponível no agente.
- Análises de zerados, projeção do mês, constância e destaques AINDA NÃO têm ferramenta: diga que estão em construção.
- Outlook (SÓ LEITURA): buscar_emails (com uri lê o e-mail inteiro), agenda_outlook e buscar_pessoa. Você NÃO envia, não responde e não apaga e-mail; se pedirem, diga que o agente só lê o Outlook. Ao citar um e-mail, diga remetente, assunto e quando chegou. Para o conteúdo completo, use buscar_emails com a uri.
- Agendamentos: a ferramenta agendamentos traz as rotinas cadastradas pelo Mateus (aba Agendamentos) e as tarefas AK do Agendador do Windows (última/próxima execução e se deu certo). Para criar ou mudar rotina, oriente o Mateus a usar a aba Agendamentos.
- Pontos críticos: use pontos_criticos (filtre por coordenador ou supervisor quando o pedido for de uma equipe; sem filtro, nomes de experiência e alertas vêm só contados). A régua é a das skills (gatilhoak), absoluta: cada nível contra o seu gatilho, no ritmo do mês (gatilho × DU passados ÷ DU do mês). Crítico = abaixo de 50% do ritmo em Conta OU GET (precisa bater os dois); atenção = abaixo do ritmo.
  Responda nesta ordem, Presencial e Remoto separados, Coordenador → Supervisor → Consultor:
  1. Uma linha: base_ate, DU passados/DU do mês e o resumo (equipes críticas/atenção, consultores críticos/atenção/no ritmo, quantos em experiência fora da régua).
  2. Coordenações: Presencial por produtividade (22/15 com M2 ÷ dias equivalentes) e Remoto pela régua do supervisor Remoto (300/120), com a faixa e o % do ritmo.
  3. Tabela das equipes críticas e em atenção: supervisor, Conta e GET da equipe × ritmo até hoje (gatilho 160/120 Presencial, 300/120 Remoto), % do ritmo.
  4. Por equipe crítica, os consultores críticos (já vêm como "NOME · conta/get de gatilho · % do ritmo").
  5. Alertas de integridade (produção de desligado, matrícula órfã, produção em licença): sempre citar, nunca esconder.
  Experiência (menos de 90 dias) fica fora da régua mas aparece com o selo "Experiência". equipes_sem_ativos (supervisão desligada ou ex-coordenação) só entra nos totais: não cobrar nem citar como ponto de atenção. vaga_sem_supervisor=true é vaga (TBA). Remoto_Brasil (remotos em equipes presenciais) usa a tabela de consultor do Presencial, como no Relatório Diário.

Conhecimento da AK (skills): a fonte oficial das regras de negócio são as skills. Antes de analisar ou explicar Produção, Usuários, cruzamento, gatilho ou FVE, chame ler_skill com a skill certa (producaoak, usuariosak, cruzamentodiariaak, gatilhoak, fveak; contextoak para vocabulário e postura; textos-comparativo-fve para os e-mails do Comparativo FVE; diaria-relatorio-ak para o Relatório Diário (Conta PJ por consultor, supervisor e coordenador); parcial-consolidada-ak-v2 para a Parcial Consolidada (Produção Conta PJ × FVE AK+JGK, lista Fora). Essas duas descrevem como os relatórios são montados: use para explicar ou conferir números; gerar os arquivos continua sendo feito fora do chat). Não chame de novo uma skill que já leu nesta resposta. Princípios que valem sempre (contextoak):
1. Presencial e Remoto sempre separados, salvo pedido explícito.
2. Hierarquia sempre Coordenador → Supervisor → Consultor.
3. M0/M1 (CONTA_CORRENTE_PJ, CREDENCIAMENTO) e M2 (…_M2) sempre separados; nunca somar.
4. Conta e GET sempre distintos; taxas de natureza diferente.
5. Nome, supervisor, coordenador e status vêm da Usuarios_Atual (cruzar pela Matricula), nunca da Produção — exceto matrícula órfã.
6. Mês de qualquer análise = DataBase. Comparativo de eventos: contas abertas por DataAberturaConta, credenciamentos por DataCredenciamento.
7. Experiência = menos de 90 dias corridos de casa; aparece sinalizada, nunca escondida.
8. Alertas de integridade (produção de desligado, matrícula órfã, lançamento em licença) são primeira classe.
9. Pontos é a métrica-rainha; somar Pontos sem filtrar Status. Sempre absoluto junto de percentual.
10. Conhece o gap temporal: pendente recente pode já ter ativado no banco.
Vocabulário: consultor = executivo = promotor; Conta = CONTA_CORRENTE_PJ; GET = CREDENCIAMENTO (GetNet).

Regras da empresa:
- SLA: proposta pendente (Aguardando Liberação ou Em Análise) há mais de 3 dias úteis desde a digitação já pode ter chamado. Status CANCELADO não conta.
- Chamados: os abertos pelo robô estão no CSV do RPA (consultar_cnpj, contas_fora_do_sla); os abertos à mão estão na planilha ABERTURA DE CHAMADOS (ler_planilha_chamados). Para dizer que uma conta "não tem chamado", confira os dois.
- Situação dos chamados no portal Process & Operations (em aberto, concluído, quem atende, data de conclusão): use consultar_chamados_portal. Ele lê a última consulta do RPA Consulta Chamados.
  - Janela: --dias N traz os chamados em aberto + os concluídos desde 00:00 de (hoje - N). Ex.: "de dois dias atrás" = desde hoje-2 = --dias 2; "concluídos ontem" = desde e ate = ontem (--dias 1).
  - Passe desde/ate em AAAA-MM-DD conforme o pedido. Se voltar precisa_rodar=true, rode rodar_script("chamados_consultar", {"--dias": "<dias_sugeridos>"}) (leva uns 45 s, abre o navegador no PC) e chame consultar_chamados_portal de novo.
  - Diga sempre de quando é a consulta (consulta_feita_em) e o período coberto.
  - Concluídos trazem resposta_final do Santander: parecer, causa_raiz, status_proposta, procedente (Sim/Não) e sla_atuacao. Ao listar concluídos, mostre o parecer resumido em uma linha, a causa raiz e se foi procedente. Se resposta_final vier vazia, diga "sem resposta registrada".
- AK = canal Presencial; JGK = Remoto + Remoto_Brasil.
- Nunca inclua Gustavo Kruger nem Mariana Freire como destinatários de e-mail ou mensagem, mesmo quando forem coordenadores.
- Arquivos: buscar_arquivo sem nome lista; com nome entrega a cópia; CPF e nascimento só saem se o Mateus pedir explicitamente.
- Scripts: só os da lista (rodar_script sem nome devolve a lista). Os de nível 3 abrem uma janela de aval para o Mateus; se ele recusar, não insista.
- Relatório Diário (skill diaria-relatorio-ak): rode rodar_script("relatorio_diario") (uns 20 s). A saída é um JSON:
  - ok=true: chame buscar_arquivo com caminho = o "arquivo" e resuma: mês e horário de corte, pontos digitados e reais, atuando, órfãs incluídas, que todos os supervisores bateram com o portal, e a lista do que ficou fora (com pontos), perguntando se deve incluir em alguma equipe. Lembre que as dinâmicas atualizam ao abrir no Excel.
  - ok=false com "problemas": o arquivo saiu com "CONFERIR" no nome. NÃO diga que está pronto; mostre os problemas (supervisor × portal) e sugira a causa provável (troca de equipe na Usuarios_Atual, por exemplo). Só entregue se o Mateus pedir mesmo assim.
- Parcial Consolidada (skill parcial-consolidada-ak-v2): precisa da lista Fora do mês (um .xlsx em Downloads ou Documents com as colunas CNPJ e "Não Pode"). Se o Mateus não disse o caminho, PEÇA antes de rodar. Rode rodar_script("parcial_consolidada", {"--fora": "<caminho>"}) (uns 20 s; "--mes": "AAAA-MM" só se ele pedir outro mês).
  - ok=true: buscar_arquivo com caminho = o "arquivo" e resuma: arquivos usados (DataRef dos usuários), mês e corte, total de linhas, por status e por projeto, CNPJs excluídos pela lista Fora, pessoas vindas do arquivo de usuários antigo, duplicados, CNPJs vazios e CPFs não achados.
  - "parar_e_pedir": repasse o pedido ao Mateus exatamente (ex.: baixar o FVE de novo sem abrir no Excel).`;
}

const corta = (s: string, n = 160) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

function paraTexto(valor: unknown): string {
  const s = typeof valor === "string" ? valor : JSON.stringify(valor);
  return s.length > LIMITE_RESULTADO ? `${s.slice(0, LIMITE_RESULTADO)}\n…(cortado: peça um recorte menor)` : s;
}

function desembrulhar(payload: unknown): unknown {
  // o servidor devolve listas e textos como {"result": ...}
  if (payload && typeof payload === "object" && !Array.isArray(payload)) {
    const chaves = Object.keys(payload as object);
    if (chaves.length === 1 && chaves[0] === "result") return (payload as { result: unknown }).result;
  }
  return payload;
}

function mensagemErro(e: unknown): string {
  const codigo = codigoErro(e);
  const msg = typeof e === "object" && e && "message" in e ? String((e as { message: string }).message) : String(e);
  if (codigo === "server_not_connected")
    return "O servidor ak_local não respondeu. Abra o agente no app desktop do Claude, com o ak_local ligado.";
  if (codigo === "not_in_manifest") return "Essa ferramenta não foi liberada para esta página.";
  if (codigo === "cancelled") return "O Mateus cancelou a chamada no app.";
  if (codigo === "needs_reauth") return "O conector precisa ser reconectado em Configurações → Conectores.";
  return msg.replace(/^Error executing tool \w+: /, "");
}

/** Resposta de uma ferramenta que devolve lista: sempre um array (vazio se não veio nada). */
export function comoLista<T>(valor: unknown): T[] {
  if (Array.isArray(valor)) return valor as T[];
  if (valor && typeof valor === "object" && Array.isArray((valor as { itens?: unknown }).itens))
    return (valor as { itens: T[] }).itens;
  return [];
}

export async function chamarPc(mcp: Mcp, ferramenta: string, entrada: Record<string, unknown> = {}, signal?: AbortSignal) {
  const r = await mcp.callTool(HOST, ferramenta, entrada, { cache: false, signal });
  return desembrulhar(r.payload);
}

export type Eventos = {
  aoEscrever: (texto: string) => void;
  aoUsarFerramenta: (uso: UsoFerramenta) => void;
  aoReceberArquivo: (anexo: Anexo, base64: string | null) => void;
  pedirAval: (pedido: { script: string; descricao: string; comando: string[] }) => Promise<boolean>;
  aoRodarScript: (estado: { etapas: string[]; atual: number } | null) => void;
};

function ferramentas(mcp: Mcp | null, ev: Eventos): FerramentaPagina[] {
  const registrar = (nome: string, entrada: Record<string, unknown>, resumo: string, erro = false) =>
    ev.aoUsarFerramenta({ nome, entrada, resumo: corta(resumo), erro });

  // embrulha uma ferramenta: registra o uso e devolve o erro em texto para o Claude
  const ferramenta = (
    name: string,
    description: string,
    properties: Record<string, unknown>,
    exec: (input: Record<string, unknown>, signal: AbortSignal) => Promise<{ resultado: unknown; resumo: string }>,
    required: string[] = [],
  ): FerramentaPagina => ({
    name,
    description,
    inputSchema: { type: "object", properties, ...(required.length ? { required } : {}) },
    execute: async (input, { signal }) => {
      if (!mcp) throw new Error("Ferramentas indisponíveis: abra o agente no app desktop do Claude.");
      try {
        const { resultado, resumo } = await exec(input, signal);
        registrar(name, input, resumo);
        return paraTexto(resultado);
      } catch (e) {
        const msg = e instanceof Error ? e.message : mensagemErro(e);
        registrar(name, input, msg, true);
        throw new Error(msg);
      }
    },
  });

  const pc = async (nome: string, entrada: Record<string, unknown>, signal: AbortSignal) => {
    try {
      return await chamarPc(mcp as Mcp, nome, entrada, signal);
    } catch (e) {
      throw new Error(mensagemErro(e));
    }
  };

  // Ordem = prioridade: se o app limitar a quantidade de ferramentas, as do fim é que ficam de fora.
  return [
    ferramenta("status_base", "Diz se a base do dia foi validada e liberada, com o aviso a mostrar se não foi. Chame antes de dar números.", {}, async (_i, s) => {
      const r = (await pc("status_base", {}, s)) as { liberada: boolean; laudo: { data: string } };
      return { resultado: r, resumo: r.liberada ? `base de ${r.laudo?.data} liberada` : "base não liberada" };
    }),

    ferramenta(
      "rodar_script",
      "Roda um script da lista liberada no PC (Relatório Diário, Parcial, consulta de chamados no portal, validador...). SEM nome: devolve a lista de scripts, com nível (1 leitura, 2 gera arquivo, 3 ação externa) e opções aceitas. opcoes: só as aceitas pelo script, ex.: {\"--dias\": \"2\"}. Nível 3 abre a janela de aval do Mateus antes.",
      { nome: { type: "string" }, opcoes: { type: "object" } },
      async (input, s) => {
        if (!input.nome) {
          const lista = comoLista(await pc("listar_scripts", {}, s));
          return { resultado: lista, resumo: `${lista.length} scripts na lista` };
        }
        const nome = String(input.nome);
        const opcoes = (input.opcoes as Record<string, unknown>) ?? {};
        const etapas = ["Conferindo a lista liberada", `Rodando ${nome} no PC`, "Lendo o resultado"];
        ev.aoRodarScript({ etapas, atual: 0 });
        try {
          let r = (await pc("rodar_script", { nome, opcoes }, s)) as {
            executado: boolean;
            precisa_aval?: boolean;
            comando?: string[];
            ok?: boolean;
            duracao_s?: number;
          };
          if (r.precisa_aval) {
            const lista = comoLista<{ nome: string; descricao: string }>(await pc("listar_scripts", {}, s));
            const aprovado = await ev.pedirAval({
              script: nome,
              descricao: lista.find((x) => x.nome === nome)?.descricao ?? "",
              comando: r.comando ?? [],
            });
            if (!aprovado) return { resultado: "O Mateus recusou o aval. Nada foi executado.", resumo: "aval recusado" };
            ev.aoRodarScript({ etapas, atual: 1 });
            r = (await pc("rodar_script", { nome, opcoes, confirmado: true }, s)) as typeof r;
          } else ev.aoRodarScript({ etapas, atual: 1 });
          ev.aoRodarScript({ etapas, atual: 2 });
          return { resultado: r, resumo: r.ok ? `${nome} ok em ${r.duracao_s}s` : `${nome} terminou com erro` };
        } finally {
          ev.aoRodarScript(null);
        }
      },
    ),

    ferramenta(
      "buscar_arquivo",
      "Arquivos para o Mateus baixar (cartão com Baixar). SEM nome nem caminho: lista os arquivos do RPA disponíveis. Com nome (ex.: usuarios_atual): cópia do arquivo do RPA, inteira ou recortada por filtros. Com caminho: entrega um arquivo que um gerador acabou de criar (o \"arquivo\" do JSON do rodar_script, como o Relatório Diário ou a Parcial).",
      {
        nome: { type: "string", description: "nome do arquivo do RPA, ex.: usuarios_atual" },
        caminho: { type: "string", description: "caminho do arquivo gerado (Relatório Diário, Parcial)" },
        filtros: {
          type: "object",
          description: 'opcional: {"Coluna": "texto contido"} ou {"Coluna": ["valor exato"]}',
        },
        incluir_dados_pessoais: { type: "boolean", description: "só true se o Mateus pedir CPF/nascimento" },
      },
      async (input, s) => {
        if (!input.nome && !input.caminho) {
          const lista = comoLista(await pc("listar_arquivos", {}, s));
          return { resultado: lista, resumo: `${lista.length} arquivos disponíveis` };
        }
        const r = (
          input.caminho
            ? await pc("entregar_gerado", { caminho: String(input.caminho) }, s)
            : await pc("buscar_arquivo", { nome: input.nome, filtros: input.filtros, incluir_dados_pessoais: input.incluir_dados_pessoais }, s)
        ) as Anexo & { conteudo_base64?: string };
        const { conteudo_base64, ...anexo } = r;
        ev.aoReceberArquivo(anexo, conteudo_base64 ?? null);
        return { resultado: anexo, resumo: `${anexo.nome_arquivo}${anexo.linhas != null ? ` · ${anexo.linhas} linhas` : ""}` };
      },
    ),

    ferramenta(
      "consultar_chamados_portal",
      "Chamados Conta PJ do portal Process & Operations pela última consulta do RPA: em aberto + concluídos no período, com a resposta final do Santander nos concluídos (parecer, causa raiz, status da proposta, procedente). desde/ate (AAAA-MM-DD) filtram pela data de conclusão; status 'aberto' ou 'concluido'; cnpj opcional. Se a consulta guardada não cobre o período, volta precisa_rodar=true com dias_sugeridos.",
      {
        desde: { type: "string", description: "AAAA-MM-DD" },
        ate: { type: "string", description: "AAAA-MM-DD" },
        cnpj: { type: "string" },
        status: { type: "string", enum: ["aberto", "concluido"] },
      },
      async (input, s) => {
        const r = (await pc("consultar_chamados_portal", input, s)) as {
          precisa_rodar: boolean;
          dias_sugeridos?: number;
          totais?: { em_aberto: number; concluidos: number; concluidos_com_resposta?: number };
        };
        return {
          resultado: r,
          resumo: r.precisa_rodar
            ? `precisa consultar o portal (--dias ${r.dias_sugeridos})`
            : `${r.totais?.em_aberto ?? 0} em aberto, ${r.totais?.concluidos ?? 0} concluídos (${r.totais?.concluidos_com_resposta ?? 0} com resposta)`,
        };
      },
    ),

    ferramenta(
      "contas_fora_do_sla",
      "Propostas pendentes há mais de 3 dias úteis desde a digitação, marcando quais já têm chamado do robô. Filtros opcionais por parte do nome.",
      { supervisor: { type: "string" }, coordenador: { type: "string" } },
      async (input, s) => {
        const r = (await pc("contas_fora_do_sla", input, s)) as { total: number; sem_chamado_rpa: number };
        return { resultado: r, resumo: `${r.total} contas fora do SLA, ${r.sem_chamado_rpa} sem chamado do robô` };
      },
    ),

    ferramenta(
      "consultar_cnpj",
      "Ficha de um CNPJ: chamados abertos pelo robô e situação da proposta na Parcial2 (consultor, supervisor, dias úteis desde a digitação, se está fora do SLA).",
      { cnpj: { type: "string" } },
      async (input, s) => {
        const r = (await pc("consultar_cnpj", input, s)) as { chamados_rpa: unknown[]; propostas_parcial2: unknown[] };
        return { resultado: r, resumo: `${r.propostas_parcial2.length} proposta(s), ${r.chamados_rpa.length} chamado(s) do robô` };
      },
      ["cnpj"],
    ),

    ferramenta(
      "ler_planilha_chamados",
      "Lê a planilha ABERTURA DE CHAMADOS (SharePoint) e devolve as linhas que contêm o termo (CNPJ, nome, nº do chamado). Sem termo, devolve as últimas 40 linhas. aba: 'controle' (Controle de Chamados, padrão) ou 'formulario' (respostas do formulário).",
      { termo: { type: "string" }, aba: { type: "string", enum: ["controle", "formulario"] } },
      async (input) => {
        const pagina = input.aba === "formulario" ? 1 : 2;
        let texto: string;
        try {
          const r = await (mcp as Mcp).callTool(M365, "read_resource", { uri: PLANILHA_CHAMADOS, startPage: pagina, endPage: pagina });
          texto = typeof r.payload === "string" ? r.payload : (r.content.find((c) => c.type === "text")?.text ?? "");
        } catch (e) {
          throw new Error(`Planilha de chamados: ${mensagemErro(e)}`);
        }
        const linhas = texto.split("\n");
        const inicio = linhas.findIndex((l) => l.startsWith("## Sheet"));
        const cabecalho = linhas.slice(inicio, inicio + 2).join("\n");
        const corpo = linhas.slice(inicio + 2).filter((l) => l.trim());
        const termo = String(input.termo ?? "").trim();
        const digitos = termo.replace(/\D/g, "");
        const achadas = termo
          ? corpo.filter((l) => l.toUpperCase().includes(termo.toUpperCase()) || (digitos.length >= 8 && l.replace(/\D/g, "").includes(digitos)))
          : corpo.slice(-40);
        return {
          resultado: `${cabecalho}\n${achadas.join("\n")}`,
          resumo: termo ? `${achadas.length} linha(s) com "${corta(termo, 30)}"` : `últimas ${achadas.length} linhas`,
        };
      },
    ),

    ferramenta(
      "pontos_criticos",
      "Pontos críticos da produção do mês pela régua do gatilho (skills): consultores, equipes e coordenações contra o ritmo do próprio gatilho até hoje, mais alertas de integridade. Filtros opcionais por parte do nome do coordenador ou do supervisor.",
      { coordenador: { type: "string" }, supervisor: { type: "string" } },
      async (input, s) => {
        const r = (await pc("pontos_criticos", input, s)) as {
          resumo: { equipes: number; equipes_criticas: number; consultores_criticos: number; consultores: number };
        };
        return {
          resultado: r,
          resumo: `${r.resumo.equipes_criticas} de ${r.resumo.equipes} equipes críticas · ${r.resumo.consultores_criticos} de ${r.resumo.consultores} consultores abaixo de 50% do ritmo`,
        };
      },
    ),

    ferramenta(
      "ler_skill",
      "Skills da AK (regras de negócio). SEM nome: lista as skills e quando usar cada uma. Com nome: o texto completo (contextoak, producaoak, usuariosak, cruzamentodiariaak, gatilhoak, fveak, textos-comparativo-fve, diaria-relatorio-ak, parcial-consolidada-ak-v2).",
      { nome: { type: "string" } },
      async (input, s) => {
        if (!input.nome) {
          const lista = comoLista<{ nome: string }>(await pc("listar_skills", {}, s));
          return { resultado: lista, resumo: `${lista.length} skills` };
        }
        const r = await pc("ler_skill", { nome: String(input.nome) }, s);
        return { resultado: r, resumo: String(input.nome) };
      },
    ),

    ferramenta(
      "agendamentos",
      "Rotinas da aba Agendamentos (nome, dias, hora, pedido, ativa, última execução) e as tarefas AK do Agendador do Windows (última e próxima execução e se deu certo).",
      {},
      async (_i, s) => {
        const [rotinas, tarefas] = await Promise.all([
          pc("listar_rotinas", {}, s).then((r) => comoLista(r)),
          pc("tarefas_do_pc", {}, s).then((r) => comoLista<{ ok: boolean }>(r)),
        ]);
        return {
          resultado: { rotinas, tarefas_do_pc: tarefas },
          resumo: `${rotinas.length} rotina(s), ${tarefas.length} tarefa(s) no PC, ${tarefas.filter((t) => !t.ok).length} com erro`,
        };
      },
    ),

    ferramenta(
      "buscar_emails",
      "Outlook do Mateus (só leitura). Com uri (mail:///...): o e-mail completo. Sem uri: busca por query (texto no assunto/corpo/anexo), sender (e-mail ou nome completo), afterDateTime/beforeDateTime (ISO ou 'yesterday', 'today'), folderName; sem filtros, os mais recentes da caixa de entrada.",
      {
        uri: { type: "string" },
        query: { type: "string" },
        sender: { type: "string" },
        afterDateTime: { type: "string" },
        beforeDateTime: { type: "string" },
        folderName: { type: "string" },
      },
      async (input, s) => {
        if (input.uri) {
          const t = await lerEmail(mcp as Mcp, String(input.uri), s).catch((e) => {
            throw new Error(`Outlook: ${mensagemErro(e)}`);
          });
          return { resultado: t, resumo: "e-mail lido" };
        }
        const r = await buscarEmails(mcp as Mcp, input, s).catch((e) => {
          throw new Error(`Outlook: ${mensagemErro(e)}`);
        });
        return { resultado: r, resumo: `${r.length} e-mail(s)` };
      },
    ),

    ferramenta(
      "agenda_outlook",
      "Compromissos do calendário do Outlook entre duas datas (AAAA-MM-DD). Sem datas, traz o dia de hoje.",
      { de: { type: "string" }, ate: { type: "string" } },
      async (input, s) => {
        const de = input.de ? new Date(`${input.de}T00:00:00`) : new Date(new Date().setHours(0, 0, 0, 0));
        const ate = input.ate ? new Date(`${input.ate}T23:59:59`) : new Date(de.getTime() + 86_400_000);
        const r = await agenda(mcp as Mcp, de, ate, s).catch((e) => {
          throw new Error(`Outlook: ${mensagemErro(e)}`);
        });
        return { resultado: r, resumo: `${r.length} compromisso(s)` };
      },
    ),

    ferramenta(
      "buscar_pessoa",
      "Acha nome, e-mail e cargo de alguém da empresa pelo nome ou parte do e-mail (diretório do Microsoft 365).",
      { nome: { type: "string" } },
      async (input, s) => {
        const r = await buscarPessoa(mcp as Mcp, String(input.nome), s).catch((e) => {
          throw new Error(`Diretório: ${mensagemErro(e)}`);
        });
        return { resultado: r, resumo: `${r.length} pessoa(s)` };
      },
      ["nome"],
    ),
  ];
}

export async function responder(
  sample: Sample,
  mcp: Mcp | null,
  historico: Mensagem[],
  pergunta: string,
  ev: Eventos,
  signal: AbortSignal,
): Promise<string> {
  const turnos: { role: "user" | "assistant"; content: string }[] = [{ role: "user", content: regras() }];
  for (const m of historico.slice(-TURNOS_HISTORICO)) {
    if (!m.texto.trim()) continue;
    turnos.push({ role: m.papel === "usuario" ? "user" : "assistant", content: m.texto });
  }
  turnos.push({ role: "user", content: pergunta });

  // apps mais antigos não têm sample.limits(): sem ele, tenta com ferramentas e cai para sem
  const lerLimites = sample.limits;
  const limites =
    typeof lerLimites === "function" ? await Promise.resolve().then(() => lerLimites.call(sample)).catch(() => null) : null;
  const ferramentasOk = mcp !== null && (limites === null || Boolean(limites.tools));
  const onText = ({ text }: { text: string }) => ev.aoEscrever(text);

  const semFerramentas = async (motivo: string) => {
    const aviso = `Atenção: nesta visualização você está SEM ferramentas (${motivo}). Diga isso ao Mateus em uma frase e responda só o que der sem dados.`;
    const comAviso = [...turnos.slice(0, -1), { role: "user" as const, content: aviso }, turnos.at(-1)!];
    try {
      return await sample(comAviso, { signal, onText, cache: false });
    } catch (e) {
      // app ainda mais antigo, que só aceita o prompt como texto único
      if (codigoErro(e) !== "invalid_request") throw e;
      const texto = comAviso.map((t) => `${t.role === "user" ? "Mateus" : "Agente"}: ${t.content}`).join("\n\n");
      return await sample(texto, { signal, onText, cache: false });
    }
  };

  const todas = ferramentas(mcp, ev);
  const enviadas = todas.slice(0, limites?.tools?.maxCount ?? todas.length);
  const cortadas = todas.slice(enviadas.length).map((t) => t.name);
  let resultado: { text: string; truncated: boolean };
  if (!ferramentasOk) {
    resultado = await semFerramentas(mcp ? "este app não aceita ferramentas" : "o PC não está conectado");
  } else {
    try {
      resultado = await sample(turnos, {
        signal,
        onText,
        tools: enviadas,
      });
      if (cortadas.length)
        resultado = {
          ...resultado,
          text: `${resultado.text}\n\n_(O app limitou as ferramentas a ${enviadas.length}; ficaram de fora: ${cortadas.join(", ")}.)_`,
        };
    } catch (e) {
      const c = codigoErro(e);
      if (c !== "tools_unavailable" && c !== "invalid_request" && c !== "capability_removed") throw e;
      resultado = await semFerramentas(`o app recusou as ferramentas: ${c}`);
    }
  }
  const { text, truncated } = resultado;
  return truncated ? `${text}\n\n_(A resposta foi cortada no limite de tamanho. Peça uma parte de cada vez.)_` : text;
}
