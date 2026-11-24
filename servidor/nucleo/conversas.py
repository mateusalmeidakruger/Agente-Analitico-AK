"""Conversas salvas como JSON, uma por id, em dados\\conversas."""
import json
import re
import shutil
import uuid
from datetime import datetime

from .erros import ErroAgente

ID_VALIDO = re.compile(r"^\d{4}-\d{2}-\d{2}_[0-9a-f]{8}$")


class ErroConversa(ErroAgente):
    pass


def novo_id(agora=None):
    agora = agora or datetime.now()
    return f"{agora:%Y-%m-%d}_{uuid.uuid4().hex[:8]}"


def _caminho(cfg, id_conversa):
    if not ID_VALIDO.match(id_conversa or ""):
        raise ErroConversa(f"id inválido: {id_conversa!r} (formato AAAA-MM-DD_xxxxxxxx)")
    return cfg.dados / "conversas" / f"{id_conversa}.json"


def listar(cfg):
    itens = []
    for p in (cfg.dados / "conversas").glob("*.json"):
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        itens.append({
            "id": c.get("id", p.stem),
            "titulo": c.get("titulo", "(sem título)"),
            "criada": c.get("criada"),
            "atualizada": c.get("atualizada"),
            "mensagens": len(c.get("mensagens", [])),
        })
    return sorted(itens, key=lambda i: i["atualizada"] or "", reverse=True)


def carregar(cfg, id_conversa):
    p = _caminho(cfg, id_conversa)
    if not p.exists():
        raise ErroConversa(f"conversa {id_conversa} não existe")
    return json.loads(p.read_text(encoding="utf-8"))


def salvar(cfg, conversa):
    """Grava a conversa inteira. Sem id, cria um novo. Devolve o id."""
    if not isinstance(conversa, dict):
        raise ErroConversa("a conversa precisa ser um objeto JSON")
    agora = datetime.now().isoformat(timespec="seconds")
    conversa = dict(conversa)
    conversa.setdefault("id", novo_id())
    conversa.setdefault("criada", agora)
    conversa.setdefault("titulo", "Nova conversa")
    conversa.setdefault("mensagens", [])
    conversa["atualizada"] = agora
    p = _caminho(cfg, conversa["id"])
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(conversa, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
    return conversa["id"]


def apagar(cfg, id_conversa):
    """Move para dados\\lixeira (dá para recuperar)."""
    p = _caminho(cfg, id_conversa)
    if not p.exists():
        raise ErroConversa(f"conversa {id_conversa} não existe")
    destino = cfg.dados / "lixeira" / p.name
    shutil.move(str(p), str(destino))
    return str(destino)
