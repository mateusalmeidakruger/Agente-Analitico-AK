"""Pontos críticos da produção do mês, pela régua das skills da AK (gatilhoak, usuariosak, contextoak).

Régua absoluta (contextoak, princípio 9): cada nível contra o seu gatilho, nunca contra a média do time.
- Consultor (gatilhoak, Regra 2): Conta E GET, só M0/M1, pela tabela do mês de casa do projeto.
- Supervisor: soma absoluta da equipe, só M0/M1 (Presencial 160/120, Remoto 300/120).
- Coordenador Presencial: produtividade = pontos M0/M1/M2 ÷ dias equivalentes (22 Conta / 15 GET).
  Coordenador Remoto: régua do supervisor Remoto (300/120, absoluto, só M0/M1).
Mês em andamento: compara com o RITMO do gatilho até hoje = gatilho × DU passados ÷ DU do mês.
Crítico: abaixo de 50% do ritmo em Conta ou em GET. Atenção: abaixo do ritmo. No ritmo: os dois em dia.
Experiência (< 90 dias) fica fora da régua mas aparece; férias aparecem com selo; licença fica fora; produção de desligado
e matrícula órfã entram nos totais e viram alerta (cruzamentodiariaak).
Premissa sem skill: Tipo_Consultor Remoto_Brasil usa a tabela de consultor do Remoto.
"""
import calendar
from datetime import date, timedelta

import pandas as pd

from . import arquivos
from .base_do_dia import dias_uteis_entre
from .erros import ErroAgente

CONTA, GET = "CONTA_CORRENTE_PJ", "CREDENCIAMENTO"
CONTA_M2, GET_M2 = "CONTA_CORRENTE_PJ_M2", "CREDENCIAMENTO_M2"
EXPERIENCIA_DIAS = 90
CORTE_CRITICO = 0.5
REMOTO_COORD = ("MARIANA FREIRE KRUGER", "MARIANA KRUGER")

GATILHO_CONSULTOR = {  # (conta, get) por faixa de mês de casa: 1º, 2º-3º, 4º+
    "Presencial": [(12, 4), (14, 8), (16, 12)],
    "Remoto": [(12, 4), (16, 6), (20, 8)],
}
GATILHO_SUPERVISOR = {"Presencial": (160, 120), "Remoto": (300, 120)}
GATILHO_COORD_PRODUTIVIDADE = (22, 15)


def _matricula(v):
    if v is None or (isinstance(v, float) and v != v):
        return ""
    if isinstance(v, float):
        v = int(v)
    return str(v).strip().removesuffix(".0")


def _du(cfg, hoje):
    """DU passados (1º do mês até ontem; hoje não conta) e DU do mês inteiro."""
    inicio = hoje.replace(day=1)
    fim_mes = hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1])
    vespera = inicio - timedelta(days=1)
    passados = dias_uteis_entre(cfg, vespera, hoje - timedelta(days=1)) if hoje > inicio else 0
    return passados, dias_uteis_entre(cfg, vespera, fim_mes)


def _mes_de_casa(admissao, hoje):
    if pd.isna(admissao):
        return None
    return (hoje.year - admissao.year) * 12 + (hoje.month - admissao.month) + 1


def _gatilho_consultor(projeto, mes_casa):
    tabela = GATILHO_CONSULTOR["Remoto" if projeto in ("Remoto", "Remoto_Brasil") else "Presencial"]
    if mes_casa is None or mes_casa >= 4:
        return tabela[2]
    return tabela[0] if mes_casa <= 1 else tabela[1]


def _faixa(conta, get, alvo_conta, alvo_get):
    """Situação contra o ritmo: a pior razão entre Conta e GET decide (precisa bater os dois)."""
    pior = min(conta / alvo_conta if alvo_conta else 1, get / alvo_get if alvo_get else 1)
    if pior < CORTE_CRITICO:
        return "critico", pior
    return ("atencao" if pior < 1 else "no_ritmo"), pior


def pontos_criticos(cfg, coordenador=None, supervisor=None, hoje=None):
    hoje = hoje or date.today()
    du_passados, du_total = _du(cfg, hoje)
    if du_passados == 0:
        raise ErroAgente("primeiro dia útil do mês: ainda não há ritmo para comparar")
    fator = du_passados / du_total

    u = arquivos.ler_tabela(cfg, "usuarios_atual", colunas=[
        "Matricula", "NomeUsuario", "Cargo", "DataAdmissao", "DataDesligamento", "Situacao",
        "Nome_Supervisor", "Nome_Coordenador", "DiasTrabalhados"])
    u["mat"] = u["Matricula"].map(_matricula)
    u["Cargo"] = u["Cargo"].astype(str).str.upper()
    u["adm"] = pd.to_datetime(u["DataAdmissao"], errors="coerce")
    u["desligado"] = u["DataDesligamento"].notna()
    u["sit"] = u["Situacao"].fillna("").astype(str).str.upper()
    u["ferias"] = ~u["desligado"] & u["sit"].str.startswith("F")
    u["licenca"] = ~u["desligado"] & (u["sit"] != "") & ~u["ferias"]
    por_mat = u.drop_duplicates("mat").set_index("mat")

    p = arquivos.ler_tabela(cfg, "producao_mes", colunas=[
        "Matricula", "NomeExecutivoLegal", "NomeSupervisor", "NomeCoordenador", "Tipo_Consultor",
        "Produto", "Pontos", "DataBase"])
    if p.empty:
        raise ErroAgente("a Produção do mês está vazia")
    p["mat"] = p["Matricula"].map(_matricula)
    p["Pontos"] = pd.to_numeric(p["Pontos"], errors="coerce").fillna(0)
    base_ate = pd.to_datetime(p["DataBase"]).max()

    # hierarquia sempre da Usuarios_Atual; matrícula órfã usa a da própria produção
    conhecida = p["mat"].isin(por_mat.index)
    p["sup"] = p["mat"].map(por_mat["Nome_Supervisor"]).where(conhecida, p["NomeSupervisor"]).fillna("(sem supervisor)")
    p["coord"] = p["mat"].map(por_mat["Nome_Coordenador"]).where(conhecida, p["NomeCoordenador"]).fillna("(sem coordenador)")

    conta = p[p["Produto"] == CONTA].groupby("mat")["Pontos"].sum()
    get = p[p["Produto"] == GET].groupby("mat")["Pontos"].sum()
    projeto_prod = (p[p["Tipo_Consultor"].isin(["Presencial", "Remoto", "Remoto_Brasil"])]
                    .groupby("mat")["Tipo_Consultor"].agg(lambda s: s.value_counts().index[0]))

    def filtra(df, col_coord, col_sup):
        if coordenador:
            df = df[df[col_coord].astype(str).str.upper().str.contains(coordenador.upper(), regex=False)]
        if supervisor:
            df = df[df[col_sup].astype(str).str.upper().str.contains(supervisor.upper(), regex=False)]
        return df

    # sem filtro, nomes de entrantes e alertas vão resumidos (a empresa inteira precisa caber no chat)
    filtrado = bool(coordenador or supervisor)

    # ---------- consultores (ativos e férias; licença fica fora) ----------
    c = u[(u["Cargo"] == "CONSULTOR") & ~u["desligado"] & ~u["licenca"]].copy()
    c = filtra(c, "Nome_Coordenador", "Nome_Supervisor")
    pf = filtra(p, "coord", "sup")
    if pf.empty and c.empty:
        raise ErroAgente("nenhuma equipe com esse filtro")

    consultores = []
    for _, r in c.iterrows():
        projeto = projeto_prod.get(r["mat"])
        if projeto is None:
            projeto = "Remoto" if str(r["Nome_Coordenador"]).upper() in REMOTO_COORD else "Presencial"
        mes_casa = _mes_de_casa(r["adm"], hoje)
        dias_casa = (pd.Timestamp(hoje) - r["adm"]).days if pd.notna(r["adm"]) else None
        g_conta, g_get = _gatilho_consultor(projeto, mes_casa)
        vc, vg = float(conta.get(r["mat"], 0)), float(get.get(r["mat"], 0))
        faixa, pior = _faixa(vc, vg, g_conta * fator, g_get * fator)
        experiencia = dias_casa is not None and dias_casa < EXPERIENCIA_DIAS
        if experiencia:
            faixa = "experiencia"  # gatilhoak: só entra na régua com 90 dias; aparece, mas não é cobrado
        consultores.append({
            "nome": r["NomeUsuario"], "supervisor": r["Nome_Supervisor"], "coordenador": r["Nome_Coordenador"],
            "projeto": projeto, "mes_casa": mes_casa,
            "experiencia": experiencia, "ferias": bool(r["ferias"]),
            "conta": round(vc, 1), "get": round(vg, 1), "gatilho": f"{g_conta}/{g_get}",
            "faixa": faixa, "pct_do_ritmo": round(pior * 100),
        })

    # ---------- equipes (supervisor): soma absoluta, M0/M1, inclui desligados e órfãos ----------
    ativos_eq = c.groupby(["Nome_Coordenador", "Nome_Supervisor"]).size()
    equipes = []
    for (coord, sup), g in pf.groupby(["coord", "sup"]):
        projeto = "Remoto" if str(coord).upper() in REMOTO_COORD else "Presencial"
        g_conta, g_get = GATILHO_SUPERVISOR[projeto]
        tc = float(g.loc[g["Produto"] == CONTA, "Pontos"].sum())
        tg = float(g.loc[g["Produto"] == GET, "Pontos"].sum())
        faixa, pior = _faixa(tc, tg, g_conta * fator, g_get * fator)
        membros = [x for x in consultores if x["supervisor"] == sup and x["coordenador"] == coord]
        equipes.append({
            "coordenador": coord, "supervisor": sup, "projeto": projeto,
            "vaga_sem_supervisor": str(sup).upper().startswith("TBA"),
            "consultores_ativos": int(ativos_eq.get((coord, sup), 0)),
            "conta": round(tc, 1), "get": round(tg, 1), "gatilho": f"{g_conta}/{g_get}",
            "ritmo_ate_hoje": f"{g_conta * fator:.0f}/{g_get * fator:.0f}",
            "faixa": faixa, "pct_do_ritmo": round(pior * 100),
            # "NOME · conta/get de gatilho · % do ritmo" (compacto: a empresa inteira cabe no chat)
            "consultores_criticos": [
                f"{x['nome']} · {x['conta']:g}/{x['get']:g} de {x['gatilho']} · {x['pct_do_ritmo']}%"
                + (f" · {x['mes_casa']}º mês" if x["mes_casa"] and x["mes_casa"] <= 3 else "")
                + (" · férias" if x["ferias"] else "")
                for x in sorted(membros, key=lambda x: x["pct_do_ritmo"]) if x["faixa"] == "critico"],
            "consultores_atencao": sum(x["faixa"] == "atencao" for x in membros),
            "consultores_no_ritmo": sum(x["faixa"] == "no_ritmo" for x in membros),
            "em_experiencia": ([f"{x['nome']} ({x['conta']:g}/{x['get']:g})" for x in membros if x["faixa"] == "experiencia"]
                               if filtrado else sum(x["faixa"] == "experiencia" for x in membros)),
        })
    # supervisão sem nenhum consultor ativo (desligada, vaga TBA, ex-coordenação): só soma nos totais
    sem_ativos = [{"coordenador": e["coordenador"], "supervisor": e["supervisor"], "conta": e["conta"], "get": e["get"]}
                  for e in equipes if e["consultores_ativos"] == 0]
    equipes = [e for e in equipes if e["consultores_ativos"] > 0]
    ordem = {"critico": 0, "atencao": 1, "no_ritmo": 2}
    equipes.sort(key=lambda e: (e["projeto"], e["coordenador"], ordem[e["faixa"]], e["pct_do_ritmo"]))

    # ---------- coordenações ----------
    coordenacoes = []
    for coord, g in pf.groupby("coord"):
        if str(coord).upper() in REMOTO_COORD:
            g_conta, g_get = GATILHO_SUPERVISOR["Remoto"]
            tc = float(g.loc[g["Produto"] == CONTA, "Pontos"].sum())
            tg = float(g.loc[g["Produto"] == GET, "Pontos"].sum())
            faixa, pior = _faixa(tc, tg, g_conta * fator, g_get * fator)
            coordenacoes.append({"coordenador": coord, "projeto": "Remoto", "regua": "absoluta 300/120, só M0/M1",
                                 "conta": round(tc, 1), "get": round(tg, 1), "faixa": faixa, "pct_do_ritmo": round(pior * 100)})
            continue
        dias = u[(u["Cargo"] == "CONSULTOR") & (u["Nome_Coordenador"] == coord)]["DiasTrabalhados"]
        equivalentes = float(pd.to_numeric(dias, errors="coerce").fillna(0).sum()) / du_passados
        if equivalentes == 0:
            continue  # ex-coordenação: a produção residual aparece em equipes_sem_ativos
        tc = float(g.loc[g["Produto"].isin([CONTA, CONTA_M2]), "Pontos"].sum())
        tg = float(g.loc[g["Produto"].isin([GET, GET_M2]), "Pontos"].sum())
        prod_c = tc / equivalentes if equivalentes else 0.0
        prod_g = tg / equivalentes if equivalentes else 0.0
        gc, gg = GATILHO_COORD_PRODUTIVIDADE
        faixa, pior = _faixa(prod_c, prod_g, gc * fator, gg * fator)
        coordenacoes.append({"coordenador": coord, "projeto": "Presencial",
                             "regua": "produtividade 22/15 com M2 ÷ dias equivalentes (meta do mês inteiro)",
                             "dias_equivalentes": round(float(equivalentes), 1),
                             "produtividade_conta": round(prod_c, 1), "produtividade_get": round(prod_g, 1),
                             "faixa": faixa, "pct_do_ritmo": round(pior * 100)})

    # ---------- alertas de integridade (cruzamentodiariaak) ----------
    com_pontos = pf[pf["Pontos"] > 0]
    mats = set(com_pontos["mat"])
    orfas = sorted(set(com_pontos.loc[~com_pontos["mat"].isin(por_mat.index), "NomeExecutivoLegal"].dropna()))
    deslig = sorted(por_mat.loc[por_mat.index.isin(mats) & por_mat["desligado"], "NomeUsuario"].dropna().unique())
    licenca = sorted(por_mat.loc[por_mat.index.isin(mats) & por_mat["licenca"], "NomeUsuario"].dropna().unique())

    contagem = {f: sum(x["faixa"] == f for x in consultores) for f in ("critico", "atencao", "no_ritmo", "experiencia")}
    return {
        "base_ate": f"{base_ate:%d/%m/%Y %H:%M}",
        "du_passados": du_passados, "du_mes": du_total,
        "regua": {
            "consultor": "gatilho Regra 2 (Conta E GET, só M0/M1) pelo mês de casa; Presencial 12/4 · 14/8 · 16/12, "
                         "Remoto 12/4 · 16/6 · 20/8 (Remoto_Brasil usa a do Remoto: premissa, não está na skill)",
            "supervisor": "soma absoluta da equipe, só M0/M1: Presencial 160/120, Remoto 300/120",
            "coordenador": "Presencial: produtividade 22/15 com M2 ÷ dias equivalentes; Remoto: 300/120 absoluto",
            "ritmo": f"mês em andamento: gatilho × {du_passados}/{du_total} DU; crítico < {int(CORTE_CRITICO * 100)}% "
                     "do ritmo em Conta ou GET, atenção < 100%",
        },
        "resumo": {
            "equipes": len(equipes),
            "equipes_criticas": sum(e["faixa"] == "critico" for e in equipes),
            "equipes_atencao": sum(e["faixa"] == "atencao" for e in equipes),
            "consultores": len(consultores),
            "consultores_criticos": contagem["critico"],
            "consultores_atencao": contagem["atencao"],
            "consultores_no_ritmo": contagem["no_ritmo"],
            "em_experiencia_fora_da_regua": contagem["experiencia"],
            "em_ferias": sum(x["ferias"] for x in consultores),
        },
        "coordenacoes": coordenacoes,
        "equipes": equipes,
        "alertas": {k: (v if filtrado else {"total": len(v), "primeiros": v[:5]}) for k, v in {
            "producao_de_desligado": deslig,
            "matricula_orfa_com_producao": orfas,
            "producao_em_licenca": licenca,
        }.items()},
        "equipes_sem_ativos": sem_ativos,
    }
