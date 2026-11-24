"""Chamados do RPA + situação da proposta na Parcial2 + regra do SLA (3 dias úteis).

A planilha ABERTURA DE CHAMADOS não passa por aqui: o Artifact lê pelo conector Microsoft 365.
"""
import json
import re
from datetime import date, datetime

import pandas as pd

from . import arquivos
from .base_do_dia import dias_uteis_entre
from .erros import ErroAgente

COLUNAS_PARCIAL2 = [
    "Cnpj", "RazaoSocial", "NomeExecutivoLegal", "NomeSupervisor", "NomeCoordenador",
    "Tipo_Consultor", "DataDigitacao", "StatusLink", "DataAberturaConta", "Status",
]


def so_digitos_cnpj(valor):
    if isinstance(valor, float):  # CNPJ lido como número perde os zeros à esquerda
        if valor != valor:  # NaN
            return ""
        valor = int(valor)
    d = re.sub(r"\D", "", str(valor or ""))
    return d.zfill(14) if d else ""


def _chamados_rpa(cfg):
    df = arquivos.ler_tabela(cfg, "chamados_rpa")
    df["cnpj"] = df["cnpj"].map(so_digitos_cnpj)
    return df


def _parcial2(cfg):
    df = arquivos.ler_tabela(cfg, "parcial2", colunas=COLUNAS_PARCIAL2)
    df["Cnpj"] = df["Cnpj"].map(so_digitos_cnpj)
    df["DataDigitacao"] = pd.to_datetime(df["DataDigitacao"], errors="coerce")
    return df


def _linha_proposta(cfg, r, hoje):
    dig = r["DataDigitacao"]
    du = dias_uteis_entre(cfg, dig.date(), hoje) if pd.notna(dig) else None
    pendente = (r["StatusLink"] in cfg.bruto["status_pendentes_sla"]
                and r["Status"] not in cfg.bruto.get("status_ignorados_sla", []))
    return {
        "cnpj": r["Cnpj"],
        "razao_social": r["RazaoSocial"],
        "consultor": r["NomeExecutivoLegal"],
        "supervisor": r["NomeSupervisor"],
        "coordenador": r["NomeCoordenador"],
        "tipo_consultor": r["Tipo_Consultor"],
        "data_digitacao": dig.date().isoformat() if pd.notna(dig) else None,
        "status_link": r["StatusLink"],
        "status": r["Status"],
        "dias_uteis_desde_digitacao": du,
        "fora_do_sla": bool(pendente and du is not None and du > cfg.bruto["sla_dias_uteis"]),
    }


def consultar_cnpj(cfg, cnpj, hoje=None):
    hoje = hoje or date.today()
    alvo = so_digitos_cnpj(cnpj)
    if len(alvo) != 14:
        raise ErroAgente(f"CNPJ inválido: {cnpj!r}")
    rpa = _chamados_rpa(cfg)
    p2 = _parcial2(cfg)
    propostas = [_linha_proposta(cfg, r, hoje) for _, r in p2[p2["Cnpj"] == alvo].iterrows()]
    return {
        "cnpj": alvo,
        "chamados_rpa": rpa[rpa["cnpj"] == alvo].fillna("").to_dict("records"),
        "propostas_parcial2": propostas,
        "regra_sla": f"pendente ({', '.join(cfg.bruto['status_pendentes_sla'])}) por mais de "
                     f"{cfg.bruto['sla_dias_uteis']} dias úteis desde a digitação já pode ter chamado",
    }


def contas_fora_do_sla(cfg, supervisor=None, coordenador=None, hoje=None):
    """Propostas pendentes há mais de N dias úteis, marcando quais já têm chamado do RPA."""
    hoje = hoje or date.today()
    p2 = _parcial2(cfg)
    p2 = p2[p2["StatusLink"].isin(cfg.bruto["status_pendentes_sla"])]
    if supervisor:
        p2 = p2[p2["NomeSupervisor"].astype(str).str.upper().str.contains(supervisor.upper(), regex=False)]
    if coordenador:
        p2 = p2[p2["NomeCoordenador"].astype(str).str.upper().str.contains(coordenador.upper(), regex=False)]
    com_chamado = set(_chamados_rpa(cfg)["cnpj"])
    linhas = []
    for _, r in p2.iterrows():
        item = _linha_proposta(cfg, r, hoje)
        if item["fora_do_sla"]:
            item["tem_chamado_rpa"] = item["cnpj"] in com_chamado
            linhas.append(item)
    linhas.sort(key=lambda i: (i["supervisor"] or "", -(i["dias_uteis_desde_digitacao"] or 0)))
    return {
        "total": len(linhas),
        "sem_chamado_rpa": sum(not i["tem_chamado_rpa"] for i in linhas),
        "contas": linhas,
        "observacao": "tem_chamado_rpa olha só o CSV do robô; chamados abertos à mão estão na planilha "
                      "ABERTURA DE CHAMADOS, que o Artifact lê pelo conector Microsoft 365",
    }


# ---------- consulta no portal (RPA Consulta Chamados) ----------

def _data_br(texto):
    """'24/11/2026 12:35' ou '24/11/2026' → date; vazio → None."""
    if not texto:
        return None
    return datetime.strptime(texto[:10], "%d/%m/%Y").date()


def consultar_portal(cfg, desde=None, ate=None, cnpj=None, status=None, hoje=None):
    """Lê a última consulta do portal e filtra.

    Janela do RPA: --dias N traz os chamados em aberto e os concluídos desde 00:00 de (hoje - N).
    desde/ate (AAAA-MM-DD) filtram pela data de conclusão; os em aberto entram sempre, a não ser
    que status="concluido". Se a consulta guardada não cobre `desde`, diz quantos dias rodar.
    """
    hoje = hoje or date.today()
    try:
        desde_d = date.fromisoformat(desde) if desde else None
        ate_d = date.fromisoformat(ate) if ate else None
    except ValueError:
        raise ErroAgente("datas no formato AAAA-MM-DD, ex.: 2026-11-22") from None
    if status not in (None, "aberto", "concluido"):
        raise ErroAgente('status deve ser "aberto" ou "concluido"')
    arq = cfg.dados / "consulta_chamados" / "ultima_consulta.json"

    def rodar(dias, motivo):
        return {"precisa_rodar": True, "motivo": motivo, "dias_sugeridos": dias,
                "como": f'rodar_script("chamados_consultar", {{"--dias": "{dias}"}}) e depois consultar de novo'}

    dias_para_desde = (hoje - desde_d).days if desde_d else 7
    if not arq.exists():
        return rodar(max(dias_para_desde, 0), "ainda não há consulta do portal feita pelo agente")

    dados = json.loads(arq.read_text(encoding="utf-8"))
    gerado = datetime.strptime(dados["gerado_em"], "%d/%m/%Y %H:%M")
    cobre_desde = _data_br(dados["filtro"]["concluidos_desde"])
    if desde_d and desde_d < cobre_desde:
        return rodar(dias_para_desde, f"a última consulta só cobre concluídos desde {cobre_desde:%d/%m}")
    if gerado.date() < hoje:
        return rodar(max(dias_para_desde, (hoje - cobre_desde).days),
                     f"a última consulta é de {gerado:%d/%m %H:%M}, não de hoje")

    alvo = re.sub(r"\D", "", cnpj or "")
    linhas = []
    for c in dados["chamados"]:
        concluido = str(c.get("status") or "").lower().startswith("conclu")
        if status == "aberto" and concluido or status == "concluido" and not concluido:
            continue
        if alvo and c.get("cnpj") != alvo.zfill(14):
            continue
        if concluido:
            dia = _data_br(c.get("conclusao") or c.get("ultima_atualizacao"))
            if desde_d and dia and dia < desde_d or ate_d and dia and dia > ate_d:
                continue
        linhas.append({**c, "descricao": (c.get("descricao") or "")[:300]})

    abertos = sum(not str(c.get("status") or "").lower().startswith("conclu") for c in linhas)
    return {
        "precisa_rodar": False,
        "consulta_feita_em": f"{gerado:%d/%m/%Y %H:%M}",
        "cobre_concluidos_desde": f"{cobre_desde:%d/%m/%Y}",
        "filtro_aplicado": {"desde": desde, "ate": ate, "cnpj": alvo or None, "status": status},
        "totais": {"em_aberto": abertos, "concluidos": len(linhas) - abertos},
        "chamados": linhas,
        "regra_janela": "--dias N = em aberto + concluídos desde 00:00 de (hoje - N)",
    }
