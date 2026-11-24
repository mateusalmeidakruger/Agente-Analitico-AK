"""Rotinas do Mateus (aba Agendamentos) em dados\\agendamentos.json e tarefas AK do Agendador do Windows.

As rotinas só disparam com o agente aberto: na hora, a página mostra o aviso no sino com o botão
Executar. O que roda sozinho, com o PC ligado, continua sendo o Agendador do Windows.
"""
import csv
import io
import json
import re
import subprocess
import uuid
from datetime import date, datetime

from .erros import ErroAgente

DIAS = ("seg", "ter", "qua", "qui", "sex", "sab", "dom")


def _arquivo(cfg):
    return cfg.dados / "agendamentos.json"


def _ler(cfg):
    p = _arquivo(cfg)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def _gravar(cfg, rotinas):
    p = _arquivo(cfg)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(rotinas, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def listar(cfg):
    return sorted(_ler(cfg), key=lambda r: (r.get("hora", ""), r.get("nome", "")))


def salvar(cfg, rotina):
    """Cria (sem id) ou atualiza uma rotina. Devolve a rotina gravada."""
    if not isinstance(rotina, dict):
        raise ErroAgente("a rotina precisa ser um objeto")
    nome = str(rotina.get("nome") or "").strip()
    pedido = str(rotina.get("pedido") or "").strip()
    hora = str(rotina.get("hora") or "").strip()
    dias = [d for d in (rotina.get("dias") or []) if d in DIAS]
    if not nome or not pedido:
        raise ErroAgente("a rotina precisa de nome e do pedido ao agente")
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", hora):
        raise ErroAgente("hora no formato HH:MM, ex.: 10:00")
    if not dias:
        raise ErroAgente(f"escolha ao menos um dia: {', '.join(DIAS)}")

    rotinas = _ler(cfg)
    atual = next((r for r in rotinas if r["id"] == rotina.get("id")), None)
    nova = {
        "id": atual["id"] if atual else uuid.uuid4().hex[:8],
        "nome": nome[:80],
        "pedido": pedido[:1000],
        "hora": hora,
        "dias": [d for d in DIAS if d in dias],
        "ativa": bool(rotina.get("ativa", True)),
        "ultima_execucao": atual.get("ultima_execucao") if atual else None,
        "criada": atual.get("criada") if atual else datetime.now().isoformat(timespec="seconds"),
    }
    rotinas = [r for r in rotinas if r["id"] != nova["id"]] + [nova]
    _gravar(cfg, rotinas)
    return nova


def apagar(cfg, id_rotina):
    rotinas = _ler(cfg)
    if not any(r["id"] == id_rotina for r in rotinas):
        raise ErroAgente(f"rotina {id_rotina} não existe")
    _gravar(cfg, [r for r in rotinas if r["id"] != id_rotina])
    return id_rotina


def marcar_executada(cfg, id_rotina, quando=None):
    rotinas = _ler(cfg)
    alvo = next((r for r in rotinas if r["id"] == id_rotina), None)
    if not alvo:
        raise ErroAgente(f"rotina {id_rotina} não existe")
    alvo["ultima_execucao"] = (quando or datetime.now()).isoformat(timespec="seconds")
    _gravar(cfg, rotinas)
    return alvo


# ---------- Agendador do Windows ----------

def _data_hora(texto):
    try:
        return datetime.strptime(texto.strip(), "%d/%m/%Y %H:%M:%S").isoformat(timespec="minutes")
    except ValueError:
        return None


def tarefas_do_pc(prefixo="AK"):
    """Tarefas do Agendador cujo nome começa com o prefixo. Só leitura (schtasks /query)."""
    try:
        r = subprocess.run(["schtasks", "/query", "/fo", "CSV", "/v"], capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise ErroAgente(f"não consegui ler o Agendador do Windows: {e}") from e
    bruto = r.stdout
    for cod in ("utf-8", "cp850", "cp1252"):
        try:
            texto = bruto.decode(cod)
            break
        except UnicodeDecodeError:
            continue
    tarefas, vistas = [], set()
    # colunas por posição (o cabeçalho vem no idioma do Windows)
    for c in csv.reader(io.StringIO(texto)):
        if len(c) < 12 or not c[1].startswith("\\" + prefixo):
            continue
        nome = c[1].lstrip("\\")
        if nome in vistas:  # uma linha por gatilho
            continue
        vistas.add(nome)
        ultimo = c[6].strip()
        tarefas.append({
            "nome": nome,
            "habilitada": c[11].strip().lower().startswith(("habilit", "enabl")),
            "status": c[3].strip(),
            "proxima_execucao": _data_hora(c[2]),
            "ultima_execucao": _data_hora(c[5]),
            "ultimo_resultado": ultimo,
            "ok": ultimo == "0",
            "descricao": c[10].strip() if c[10].strip() not in ("N/A", "") else None,
        })
    return sorted(tarefas, key=lambda t: t["nome"])


def hoje_semana(d=None):
    return DIAS[(d or date.today()).weekday()]
