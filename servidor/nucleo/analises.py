"""Análises da produção do mês. Por enquanto: pontos críticos por equipe.

Regras (definidas com o Mateus em 24/11/2026):
- Consultor elegível: CONSULTOR na Usuarios_Atual sem DataDesligamento e sem Situacao (férias,
  afastamento, gestante ficam fora) e com mais de 45 dias de casa. Entrantes vão numa lista à parte.
- Pontos do mês: soma de Pontos M0/M1 (CONTA_CORRENTE_PJ + CREDENCIAMENTO; M2 não entra) na
  Produção do mês. Sem produção = 0.
- Consultor crítico: pontos abaixo de 50% da mediana do seu grupo (Presencial, Remoto, Remoto_Brasil).
- Equipe crítica, dois sinais: pontos por executivo ativo abaixo de 70% da média da coordenação,
  ou 30% ou mais dos elegíveis críticos.
"""
from datetime import date

import pandas as pd

from . import arquivos
from .erros import ErroAgente

PRODUTOS_M0M1 = ("CONTA_CORRENTE_PJ", "CREDENCIAMENTO")
DIAS_ENTRANTE = 45
FATOR_CONSULTOR = 0.5
FATOR_EQUIPE = 0.7
PERCENT_CRITICOS = 0.3


def _matricula(v):
    if v is None or (isinstance(v, float) and v != v):
        return ""
    if isinstance(v, float):
        v = int(v)
    return str(v).strip().removesuffix(".0")


def _consultores_ativos(cfg, hoje):
    u = arquivos.ler_tabela(cfg, "usuarios_atual", colunas=[
        "Matricula", "NomeUsuario", "Cargo", "DataAdmissao", "DataDesligamento", "Situacao",
        "Nome_Supervisor", "Nome_Coordenador"])
    u = u[(u["Cargo"].astype(str).str.upper() == "CONSULTOR") & u["DataDesligamento"].isna()]
    afastados = u[u["Situacao"].notna()]
    u = u[u["Situacao"].isna()].copy()
    u["mat"] = u["Matricula"].map(_matricula)
    adm = pd.to_datetime(u["DataAdmissao"], errors="coerce")
    u["dias_casa"] = (pd.Timestamp(hoje) - adm).dt.days
    return u, afastados


def _producao(cfg):
    p = arquivos.ler_tabela(cfg, "producao_mes", colunas=["Matricula", "Tipo_Consultor", "Produto", "Pontos", "DataBase"])
    p["mat"] = p["Matricula"].map(_matricula)
    return p


def _grupos(cfg, prod):
    """Grupo de cada matrícula: o mais frequente na Produção do mês; se não produziu, na Parcial2."""
    def moda(df):
        df = df[df["Tipo_Consultor"].isin(["Presencial", "Remoto", "Remoto_Brasil"])]
        return df.groupby("mat")["Tipo_Consultor"].agg(lambda s: s.value_counts().index[0]).to_dict()
    grupos = {}
    try:
        p2 = arquivos.ler_tabela(cfg, "parcial2", colunas=["Matricula", "Tipo_Consultor"])
        p2["mat"] = p2["Matricula"].map(_matricula)
        grupos.update(moda(p2))
    except Exception:
        pass
    grupos.update(moda(prod))
    return grupos


def pontos_criticos(cfg, coordenador=None, supervisor=None, hoje=None):
    hoje = hoje or date.today()
    ativos, afastados = _consultores_ativos(cfg, hoje)
    prod = _producao(cfg)
    if prod.empty:
        raise ErroAgente("a Produção do mês está vazia")
    base_ate = pd.to_datetime(prod["DataBase"]).max()

    m0m1 = prod[prod["Produto"].isin(PRODUTOS_M0M1)]
    por_produto = m0m1.pivot_table(index="mat", columns="Produto", values="Pontos", aggfunc="sum", fill_value=0)
    grupos = _grupos(cfg, prod)

    a = ativos.copy()
    a["conta"] = a["mat"].map(por_produto.get("CONTA_CORRENTE_PJ", pd.Series(dtype=float))).fillna(0)
    a["get"] = a["mat"].map(por_produto.get("CREDENCIAMENTO", pd.Series(dtype=float))).fillna(0)
    a["pontos"] = a["conta"] + a["get"]
    a["grupo"] = a["mat"].map(grupos).fillna("Presencial")
    a["sem_grupo_na_base"] = ~a["mat"].isin(grupos)
    a["entrante"] = a["dias_casa"].fillna(0) <= DIAS_ENTRANTE

    eleg = a[~a["entrante"]]
    medianas = eleg.groupby("grupo")["pontos"].median().to_dict()
    a["corte"] = a["grupo"].map(lambda g: medianas.get(g, 0) * FATOR_CONSULTOR)
    a["critico"] = ~a["entrante"] & (a["pontos"] < a["corte"])

    # pontos por ativo: todos os ativos da equipe (entrantes inclusive) no denominador
    eq = a.groupby(["Nome_Coordenador", "Nome_Supervisor"], dropna=False).agg(
        ativos=("mat", "size"), pontos=("pontos", "sum"),
        elegiveis=("entrante", lambda s: int((~s).sum())), criticos=("critico", "sum")).reset_index()
    eq["pontos_por_ativo"] = eq["pontos"] / eq["ativos"]
    media_coord = (eq.groupby("Nome_Coordenador")["pontos"].sum() / eq.groupby("Nome_Coordenador")["ativos"].sum()).to_dict()
    eq["media_coordenacao"] = eq["Nome_Coordenador"].map(media_coord)
    eq["sinal_pontos_por_ativo"] = eq["pontos_por_ativo"] < FATOR_EQUIPE * eq["media_coordenacao"]
    eq["pct_criticos"] = (eq["criticos"] / eq["elegiveis"].where(eq["elegiveis"] > 0)).fillna(0)
    eq["sinal_pct_criticos"] = eq["pct_criticos"] >= PERCENT_CRITICOS
    eq["critica"] = eq["sinal_pontos_por_ativo"] | eq["sinal_pct_criticos"]

    def filtra(df, col_coord, col_sup):
        if coordenador:
            df = df[df[col_coord].astype(str).str.upper().str.contains(coordenador.upper(), regex=False)]
        if supervisor:
            df = df[df[col_sup].astype(str).str.upper().str.contains(supervisor.upper(), regex=False)]
        return df

    eq = filtra(eq, "Nome_Coordenador", "Nome_Supervisor")
    a = filtra(a, "Nome_Coordenador", "Nome_Supervisor")
    afastados = filtra(afastados, "Nome_Coordenador", "Nome_Supervisor")
    if eq.empty:
        raise ErroAgente("nenhuma equipe com esse filtro")

    equipes = []
    for _, e in eq.sort_values(["critica", "pontos_por_ativo"], ascending=[False, True]).iterrows():
        membros = a[(a["Nome_Supervisor"] == e["Nome_Supervisor"]) & (a["Nome_Coordenador"] == e["Nome_Coordenador"])]
        criticos = membros[membros["critico"]].sort_values("pontos")
        equipes.append({
            "supervisor": e["Nome_Supervisor"],
            "coordenador": e["Nome_Coordenador"],
            "vaga_sem_supervisor": str(e["Nome_Supervisor"]).upper().startswith("TBA"),
            "critica": bool(e["critica"]),
            "ativos": int(e["ativos"]),
            "pontos_m0m1": round(float(e["pontos"]), 1),
            "pontos_por_ativo": round(float(e["pontos_por_ativo"]), 1),
            "media_coordenacao_por_ativo": round(float(e["media_coordenacao"]), 1),
            "sinal_pontos_por_ativo": bool(e["sinal_pontos_por_ativo"]),
            "criticos": int(e["criticos"]),
            "elegiveis": int(e["elegiveis"]),
            "pct_criticos": round(float(e["pct_criticos"]) * 100),
            "sinal_pct_criticos": bool(e["sinal_pct_criticos"]),
            "consultores_criticos": [
                {"nome": c["NomeUsuario"], "pontos": round(float(c["pontos"]), 1),
                 "conta": round(float(c["conta"]), 1), "get": round(float(c["get"]), 1),
                 "dias_casa": int(c["dias_casa"]) if pd.notna(c["dias_casa"]) else None}
                for _, c in criticos.iterrows()],
        })

    entrantes = a[a["entrante"]].sort_values("pontos")
    return {
        "base_ate": f"{base_ate:%d/%m/%Y %H:%M}",
        "regras": {
            "consultor_critico": f"pontos M0/M1 do mês < {int(FATOR_CONSULTOR * 100)}% da mediana do grupo; "
                                 f"só ativos com mais de {DIAS_ENTRANTE} dias de casa",
            "equipe_critica": f"pontos por ativo < {int(FATOR_EQUIPE * 100)}% da média da coordenação "
                              f"OU >= {int(PERCENT_CRITICOS * 100)}% dos elegíveis críticos",
        },
        "medianas_por_grupo": {g: round(float(v), 1) for g, v in medianas.items()},
        "resumo": {
            "equipes": len(equipes),
            "equipes_criticas": sum(e["critica"] for e in equipes),
            "consultores_ativos": int(len(a)),
            "consultores_criticos": int(a["critico"].sum()),
            "entrantes_fora_da_regra": int(len(entrantes)),
            "afastados_fora_da_regra": int(len(afastados)),
        },
        "equipes": equipes,
        # entrantes só por equipe (nome e pontos): a lista completa pesava demais no chat
        "entrantes_por_equipe": {
            sup: [f"{r['NomeUsuario']} ({round(float(r['pontos']), 1)} pts)" for _, r in grupo.iterrows()]
            for sup, grupo in entrantes.groupby("Nome_Supervisor")},
        "grupo_de_cada_critico": "o corte do grupo é metade da mediana em medianas_por_grupo",
    }
