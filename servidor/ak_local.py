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

from nucleo import arquivos, base_do_dia, chamados, conversas, scripts
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


def ferramenta(fn):
    """Registra a ferramenta e devolve ao chat o motivo das recusas (sem isso o modelo só vê 'Error executing tool')."""
    @functools.wraps(fn)
    def envolvida(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ErroAgente as e:
            raise ToolError(str(e)) from e
    return servidor.tool()(envolvida)


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

@ferramenta
def status_base() -> dict:
    """Diz se a base do dia foi validada (laudo APROVADO) e liberada pelo auditor-base, com o aviso a mostrar se não foi."""
    return _limpo(base_do_dia.status(cfg))


@ferramenta
def dias_uteis(inicio: str, fim: str) -> int:
    """Dias úteis depois de `inicio` até `fim` (AAAA-MM-DD), sem fins de semana e feriados do config."""
    return base_do_dia.dias_uteis_entre(cfg, date.fromisoformat(inicio), date.fromisoformat(fim))


# ---------- conversas ----------

@ferramenta
def listar_conversas() -> list:
    """Lista as conversas salvas (id, título, datas, nº de mensagens), da mais recente para a mais antiga."""
    return conversas.listar(cfg)


@ferramenta
def carregar_conversa(id: str) -> dict:
    """Carrega uma conversa salva pelo id (AAAA-MM-DD_xxxxxxxx)."""
    return conversas.carregar(cfg, id)


@ferramenta
def salvar_conversa(conversa: dict) -> str:
    """Grava a conversa inteira (titulo, mensagens, base_do_dia...). Sem 'id', cria uma nova. Devolve o id."""
    return conversas.salvar(cfg, conversa)


@ferramenta
def apagar_conversa(id: str) -> str:
    """Move a conversa para a lixeira do agente (dá para recuperar). Só quando o Mateus pedir."""
    return conversas.apagar(cfg, id)


# ---------- arquivos do RPA ----------

@ferramenta
def listar_arquivos() -> list:
    """Arquivos do RPA que o agente pode entregar, com data de modificação e tamanho."""
    return arquivos.listar(cfg)


@ferramenta
def buscar_arquivo(nome: str, filtros: dict | None = None, incluir_dados_pessoais: bool = False) -> dict:
    """Entrega uma CÓPIA de um arquivo do RPA (nome vindo de listar_arquivos), inteiro ou recortado.

    filtros: {"Coluna": "texto contido"} ou {"Coluna": ["valor exato", ...]}, sem diferenciar maiúsculas.
    CPF e nascimento saem removidos, a não ser que incluir_dados_pessoais=true (só para o Mateus).
    A resposta traz conteudo_base64 para o botão Baixar.
    """
    return _limpo(arquivos.buscar(cfg, nome, filtros, incluir_dados_pessoais))


# ---------- chamados ----------

@ferramenta
def consultar_cnpj(cnpj: str) -> dict:
    """Ficha de um CNPJ: chamados abertos pelo RPA e situação da proposta na Parcial2, com dias úteis desde a digitação e se está fora do SLA."""
    return _limpo(chamados.consultar_cnpj(cfg, cnpj))


@ferramenta
def contas_fora_do_sla(supervisor: str | None = None, coordenador: str | None = None) -> dict:
    """Propostas pendentes há mais de 3 dias úteis desde a digitação, marcando quais já têm chamado do RPA. Filtros por parte do nome."""
    return _limpo(chamados.contas_fora_do_sla(cfg, supervisor, coordenador))


# ---------- scripts ----------

@ferramenta
def listar_scripts() -> list:
    """Scripts liberados, com nível (1 leitura, 2 gera arquivo, 3 ação externa) e opções aceitas."""
    return scripts.listar(cfg)


@ferramenta
def rodar_script(nome: str, opcoes: dict | None = None, confirmado: bool = False) -> dict:
    """Roda um script da lista liberada. opcoes: {"--cnpj": "..."} só com as opções permitidas.

    Nível 3 sem confirmado=true não roda: devolve o comando para o Mateus aprovar.
    """
    return scripts.rodar(cfg, nome, opcoes, confirmado)


if __name__ == "__main__":
    servidor.run()
