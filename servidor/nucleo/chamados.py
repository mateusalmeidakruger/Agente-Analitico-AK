"""Chamados do RPA + situação da proposta na Parcial2 + regra do SLA (3 dias úteis).

A planilha ABERTURA DE CHAMADOS não passa por aqui: o Artifact lê pelo conector Microsoft 365.
"""
import re
from datetime import date

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
