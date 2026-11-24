"""Roda só os scripts de scripts.json, com argumentos conferidos, tempo máximo e log."""
import json
import os
import re
import subprocess
from datetime import datetime

from .erros import ErroAgente

LIMITE_SAIDA = 20000


class ErroScript(ErroAgente):
    pass


def listar(cfg):
    return [
        {"nome": n, "descricao": s["descricao"], "nivel": s["nivel"], "habilitado": s.get("habilitado", True),
         "opcoes": sorted(s.get("args_opcoes", {}))}
        for n, s in cfg.scripts.items()
    ]


def montar_comando(cfg, nome, opcoes=None):
    if nome not in cfg.scripts:
        raise ErroScript(f"script {nome!r} não está na lista liberada")
    s = cfg.scripts[nome]
    if not s.get("habilitado", True):
        raise ErroScript(f"script {nome!r} está desabilitado nesta fase")
    opcoes = opcoes or {}
    permitidas = s.get("args_opcoes", {})
    for chave in s.get("args_obrigatorios", []):
        if chave not in opcoes:
            raise ErroScript(f"{nome} exige {chave}")
    args = [a.replace("{dados}", str(cfg.dados)) for a in s.get("args_fixos", [])]
    for chave, valor in opcoes.items():
        if chave not in permitidas:
            raise ErroScript(f"opção {chave!r} não é permitida em {nome}; permitidas: {sorted(permitidas)}")
        if not re.fullmatch(permitidas[chave], str(valor)):
            raise ErroScript(f"valor {valor!r} recusado para {chave}")
        args += [chave, str(valor)]
    script = cfg.caminho_fluxo(s["caminho"])
    if not script.exists():
        raise ErroScript(f"{script} não existe")
    return s, script, [cfg.bruto.get("python_scripts", "python"), str(script), *args]


def _cortar(texto):
    texto = texto or ""
    return texto if len(texto) <= LIMITE_SAIDA else "...(início cortado)...\n" + texto[-LIMITE_SAIDA:]


def rodar(cfg, nome, opcoes=None, confirmado=False):
    s, script, comando = montar_comando(cfg, nome, opcoes)
    if s["nivel"] >= 3 and not confirmado:
        return {"executado": False, "precisa_aval": True, "comando": comando,
                "mensagem": "ação externa: mostre o comando ao Mateus e só rode de novo com confirmado=true depois do clique dele"}
    inicio = datetime.now()
    try:
        # sem isso o Python filho escreve em cp1252 quando a saída é capturada
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        r = subprocess.run(comando, cwd=script.parent, capture_output=True, text=True, env=env,
                           encoding="utf-8", errors="replace", timeout=s.get("timeout_s", 600))
        codigo, saida, erro = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        codigo, saida, erro = None, e.stdout or "", f"tempo máximo de {s.get('timeout_s')} s estourado"
        if isinstance(saida, bytes):
            saida = saida.decode("utf-8", "replace")
    resultado = {
        "executado": True,
        "script": nome,
        "nivel": s["nivel"],
        "comando": comando,
        "inicio": inicio.isoformat(timespec="seconds"),
        "duracao_s": round((datetime.now() - inicio).total_seconds(), 1),
        "codigo_retorno": codigo,
        "ok": codigo == 0,
        "saida": _cortar(saida),
        "erro": _cortar(erro),
    }
    log = cfg.dados / "logs" / f"{inicio:%Y-%m-%d_%H%M%S}_{nome}.json"
    log.write_text(json.dumps({**resultado, "confirmado": confirmado}, ensure_ascii=False, indent=2), encoding="utf-8")
    resultado["log"] = str(log)
    return resultado
