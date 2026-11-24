"""Carrega config.json e scripts.json e resolve os caminhos do agente."""
import json
import os
from pathlib import Path

SERVIDOR = Path(__file__).resolve().parent.parent
PROJETO = SERVIDOR.parent


def _ler_json(nome):
    with open(SERVIDOR / nome, encoding="utf-8") as f:
        return json.load(f)


class Config:
    def __init__(self, dados=None, raiz_fluxo=None):
        self.bruto = _ler_json("config.json")
        self.scripts = _ler_json("scripts.json")["scripts"]
        # AK_DADOS / AK_RAIZ_FLUXO permitem apontar para pastas de teste
        self.dados = Path(dados or os.environ.get("AK_DADOS") or PROJETO / "dados")
        self.raiz_fluxo = Path(raiz_fluxo or os.environ.get("AK_RAIZ_FLUXO") or self.bruto["raiz_fluxo"])
        for sub in ("conversas", "excluidos", "arquivos_entregues", "logs", "validador"):
            (self.dados / sub).mkdir(parents=True, exist_ok=True)

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
