"""Carrega config.json e scripts.json e resolve os caminhos do agente.

Os dois arquivos são relidos quando mudam no disco: ligar um script ou trocar uma pasta não exige
reiniciar o app do Claude (só código Python novo exige).
"""
import json
import os
from pathlib import Path

SERVIDOR = Path(__file__).resolve().parent.parent
PROJETO = SERVIDOR.parent


def _ler_json(nome):
    with open(SERVIDOR / nome, encoding="utf-8") as f:
        return json.load(f)


class _Recarregavel:
    """Conteúdo de um JSON do servidor, relido quando a data de modificação muda."""

    def __init__(self, nome, extrair=lambda d: d):
        self.nome, self.extrair, self.mtime, self.valor = nome, extrair, None, None

    def obter(self):
        mtime = (SERVIDOR / self.nome).stat().st_mtime
        if mtime != self.mtime:
            self.valor, self.mtime = self.extrair(_ler_json(self.nome)), mtime
        return self.valor


class Config:
    def __init__(self, dados=None, raiz_fluxo=None):
        self._bruto = _Recarregavel("config.json")
        self._scripts = _Recarregavel("scripts.json", lambda d: d["scripts"])
        self._scripts_fixos = None  # testes podem fixar a lista
        # AK_DADOS / AK_RAIZ_FLUXO permitem apontar para pastas de teste
        self.dados = Path(dados or os.environ.get("AK_DADOS") or PROJETO / "dados")
        self.raiz_fluxo = Path(raiz_fluxo or os.environ.get("AK_RAIZ_FLUXO") or self.bruto["raiz_fluxo"])
        for sub in ("conversas", "excluidos", "arquivos_entregues", "logs", "validador", "consulta_chamados"):
            (self.dados / sub).mkdir(parents=True, exist_ok=True)

    @property
    def bruto(self):
        return self._bruto.obter()

    @property
    def scripts(self):
        return self._scripts_fixos if self._scripts_fixos is not None else self._scripts.obter()

    @scripts.setter
    def scripts(self, valor):
        self._scripts_fixos = valor

    def caminho_fluxo(self, relativo):
        return self.raiz_fluxo / relativo

    @property
    def arquivos(self):
        return self.bruto["arquivos"]

    @property
    def feriados(self):
        return self.bruto.get("feriados", [])

    @property
    def limite_entrega_bytes(self):
        return int(self.bruto.get("limite_entrega_mb", 10) * 1024 * 1024)
