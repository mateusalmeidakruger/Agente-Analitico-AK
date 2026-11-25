"""Servidor MCP local do Agente Analítico AK (stdio).

Liga no app desktop do Claude como o servidor "ak_local". Toda regra de segurança fica aqui:
caminhos e scripts só da lista, originais só lidos, ação externa só com aval.
"""
import functools
import math
from datetime import date
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from nucleo import analises, arquivos, base_do_dia, chamados, conhecimento, conversas, rotinas, scripts
from nucleo.config import Config
from nucleo.erros import ErroAgente

cfg = Config()

servidor = MCPServer(
    name="ak_local",
    instructions=(
        "Ferramentas do PC do Mateus para o Agente Analítico AK. Antes de responder com números, "
        "chame status_base: se 'liberada' for falso, comece a resposta com o 'aviso'. "
        "Nunca inclua Gustavo Kruger nem Mariana Freire em envios. Scripts de nível 3 só rodam "
        "com confirmado=true depois do clique de aval do Mateus."
    ),
)


def ferramenta(leitura: bool):
    """Registra a ferramenta e devolve ao chat o motivo das recusas (sem isso o modelo só vê 'Error executing tool').

    leitura=True marca a ferramenta como só leitura: o app desktop só deixa a página chamar sem
    confirmação as ferramentas marcadas assim; as outras ele cancela quando não consegue perguntar.
    """
    anotacoes = ToolAnnotations(readOnlyHint=True) if leitura else ToolAnnotations(readOnlyHint=False, destructiveHint=False)

    def registrar(fn):
        @functools.wraps(fn)
        def envolvida(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except ErroAgente as e:
                raise ToolError(str(e)) from e
        return servidor.tool(annotations=anotacoes)(envolvida)
    return registrar


def _limpo(obj: Any) -> Any:
    """Deixa a resposta serializável: NaN vira None, datas viram texto."""
    if isinstance(obj, dict):
        return {str(k): _limpo(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_limpo(v) for v in obj]
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


# ---------- base do dia ----------

@ferramenta(leitura=True)
def status_base() -> dict:
    """Diz se a base do dia foi validada (laudo APROVADO) e liberada pelo auditor-base, com o aviso a mostrar se não foi."""
    return _limpo(base_do_dia.status(cfg))


@ferramenta(leitura=True)
def dias_uteis(inicio: str, fim: str) -> int:
    """Dias úteis depois de `inicio` até `fim` (AAAA-MM-DD), sem fins de semana e feriados do config."""
    return base_do_dia.dias_uteis_entre(cfg, date.fromisoformat(inicio), date.fromisoformat(fim))


# ---------- conversas ----------

@ferramenta(leitura=True)
def listar_conversas() -> dict:
    """Lista as conversas salvas (id, título, datas, nº de mensagens), da mais recente para a mais antiga."""
    return {"itens": conversas.listar(cfg)}


@ferramenta(leitura=True)
def carregar_conversa(id: str) -> dict:
    """Carrega uma conversa salva pelo id (AAAA-MM-DD_xxxxxxxx)."""
    return conversas.carregar(cfg, id)


@ferramenta(leitura=False)
def salvar_conversa(conversa: dict) -> str:
    """Grava a conversa inteira (titulo, mensagens, base_do_dia...). Sem 'id', cria uma nova. Devolve o id."""
    return conversas.salvar(cfg, conversa)


@ferramenta(leitura=False)
def apagar_conversa(id: str) -> str:
    """Move a conversa para dados\excluidos no PC (dá para recuperar). Só quando o Mateus pedir."""
    return conversas.apagar(cfg, id)


# ---------- arquivos do RPA ----------

@ferramenta(leitura=True)
def listar_arquivos() -> dict:
    """Arquivos do RPA que o agente pode entregar, com data de modificação e tamanho."""
    return {"itens": arquivos.listar(cfg)}


@ferramenta(leitura=False)
def buscar_arquivo(nome: str, filtros: dict | None = None, incluir_dados_pessoais: bool = False) -> dict:
    """Entrega uma CÓPIA de um arquivo do RPA (nome vindo de listar_arquivos), inteiro ou recortado.

    filtros: {"Coluna": "texto contido"} ou {"Coluna": ["valor exato", ...]}, sem diferenciar maiúsculas.
    CPF e nascimento saem removidos, a não ser que incluir_dados_pessoais=true (só para o Mateus).
    A resposta traz conteudo_base64 para o botão Baixar.
    """
    return _limpo(arquivos.buscar(cfg, nome, filtros, incluir_dados_pessoais))


# ---------- chamados ----------

@ferramenta(leitura=True)
def consultar_cnpj(cnpj: str) -> dict:
    """Ficha de um CNPJ: chamados abertos pelo RPA e situação da proposta na Parcial2, com dias úteis desde a digitação e se está fora do SLA."""
    return _limpo(chamados.consultar_cnpj(cfg, cnpj))


@ferramenta(leitura=True)
def contas_fora_do_sla(supervisor: str | None = None, coordenador: str | None = None) -> dict:
    """Propostas pendentes há mais de 3 dias úteis desde a digitação, marcando quais já têm chamado do RPA. Filtros por parte do nome."""
    return _limpo(chamados.contas_fora_do_sla(cfg, supervisor, coordenador))


@ferramenta(leitura=True)
def consultar_chamados_portal(desde: str | None = None, ate: str | None = None, cnpj: str | None = None,
                              status: str | None = None) -> dict:
    """Chamados Conta PJ do portal Process & Operations, pela última consulta do RPA Consulta Chamados.

    desde/ate (AAAA-MM-DD) filtram pela data de conclusão; status: "aberto" ou "concluido".
    A janela do RPA é --dias N = em aberto + concluídos desde 00:00 de (hoje - N). Se a consulta
    guardada não cobre o período, volta precisa_rodar=true com os dias certos para rodar_script.
    """
    return _limpo(chamados.consultar_portal(cfg, desde, ate, cnpj, status))


# ---------- análises ----------

@ferramenta(leitura=True)
def pontos_criticos(coordenador: str | None = None, supervisor: str | None = None) -> dict:
    """Pontos críticos da produção do mês, por equipe (supervisor).

    Consultor crítico: ativo com mais de 45 dias de casa e pontos M0/M1 do mês (Conta + GET, sem M2)
    abaixo de 50% da mediana do seu grupo (Presencial, Remoto, Remoto_Brasil). Equipe crítica:
    pontos por ativo abaixo de 70% da média da coordenação OU 30%+ dos elegíveis críticos.
    Filtros por parte do nome do coordenador ou do supervisor.
    """
    return _limpo(analises.pontos_criticos(cfg, coordenador, supervisor))


# ---------- agendamentos ----------

@ferramenta(leitura=True)
def listar_rotinas() -> dict:
    """Rotinas cadastradas pelo Mateus (aba Agendamentos): nome, dias, hora, pedido ao agente, ativa, última execução."""
    return {"itens": rotinas.listar(cfg), "hoje": rotinas.hoje_semana()}


@ferramenta(leitura=False)
def salvar_rotina(rotina: dict) -> dict:
    """Cria ou atualiza uma rotina: {id?, nome, pedido, hora "HH:MM", dias ["seg".."dom"], ativa}."""
    return rotinas.salvar(cfg, rotina)


@ferramenta(leitura=False)
def apagar_rotina(id: str) -> str:
    """Remove uma rotina da aba Agendamentos. Só quando o Mateus pedir."""
    return rotinas.apagar(cfg, id)


@ferramenta(leitura=False)
def marcar_rotina_executada(id: str) -> dict:
    """Registra que a rotina rodou hoje (para não avisar de novo no mesmo dia)."""
    return rotinas.marcar_executada(cfg, id)


@ferramenta(leitura=True)
def tarefas_do_pc() -> dict:
    """Tarefas AK do Agendador do Windows: última e próxima execução e se o último resultado foi ok."""
    return {"itens": rotinas.tarefas_do_pc()}


# ---------- conhecimento (skills da AK) ----------

@ferramenta(leitura=True)
def listar_skills() -> dict:
    """Skills da AK disponíveis (regras de negócio): nome e quando usar cada uma."""
    return {"itens": conhecimento.listar()}


@ferramenta(leitura=True)
def ler_skill(nome: str) -> str:
    """Texto completo de uma skill da AK (contextoak, producaoak, usuariosak, cruzamentodiariaak, gatilhoak, fveak, textos-comparativo-fve, diaria-relatorio-ak, parcial-consolidada-ak-v2)."""
    return conhecimento.ler(nome)


# ---------- scripts ----------

@ferramenta(leitura=True)
def listar_scripts() -> dict:
    """Scripts liberados, com nível (1 leitura, 2 gera arquivo, 3 ação externa) e opções aceitas."""
    return {"itens": scripts.listar(cfg)}


@ferramenta(leitura=False)
def rodar_script(nome: str, opcoes: dict | None = None, confirmado: bool = False) -> dict:
    """Roda um script da lista liberada. opcoes: {"--cnpj": "..."} só com as opções permitidas.

    Nível 3 sem confirmado=true não roda: devolve o comando para o Mateus aprovar.
    """
    return scripts.rodar(cfg, nome, opcoes, confirmado)


if __name__ == "__main__":
    servidor.run()
