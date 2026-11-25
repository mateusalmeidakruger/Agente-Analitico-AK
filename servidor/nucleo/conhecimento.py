"""Skills da AK (regras de negócio) que o agente consulta: pasta conhecimento\ do projeto.

São as mesmas skills instaladas no Claude Code (~/.claude/skills). O agente lê a skill inteira
só quando a pergunta precisa dela, em vez de carregar tudo em toda resposta.
"""
import re

from .config import PROJETO
from .erros import ErroAgente

PASTA = PROJETO / "conhecimento"


def _descricao(texto):
    m = re.search(r"^description:\s*(.*?)\n(?=\w+:|---)", texto, re.S | re.M)
    if not m:
        return ""
    d = m.group(1).strip().lstrip(">|").strip().strip('"')
    return re.sub(r"\s+", " ", d)


def listar():
    return [{"nome": p.stem, "descricao": _descricao(p.read_text(encoding="utf-8"))[:400]}
            for p in sorted(PASTA.glob("*.md"))]


def ler(nome):
    nomes = {p.stem for p in PASTA.glob("*.md")}
    if nome not in nomes:
        raise ErroAgente(f"skill {nome!r} não existe; use uma de: {', '.join(sorted(nomes))}")
    return (PASTA / f"{nome}.md").read_text(encoding="utf-8")
