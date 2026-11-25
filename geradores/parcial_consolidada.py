r"""Gera a Parcial Consolidada AK (skill parcial-consolidada-ak-v2): Produção Conta PJ × FVE AK+JGK.

Uso:
    python parcial_consolidada.py --fora LISTA.xlsx [--mes AAAA-MM] [--producao ARQ] [--fve ARQ ...]
                                  [--usuarios ARQ ...] [--saida PASTA] [--resumo resumo.json]

Sem --producao/--fve/--usuarios, usa a base validada da Central\Entrada (Producao, FVE AK, FVE JGK,
Usuarios_Atual + o Usuarios do mês anterior). A lista Fora é obrigatória (colunas CNPJ e "Não Pode"):
a skill manda parar e pedir ao usuário quando ela falta.

Lógica idêntica ao script validado da skill (bateu 100% com a "Parcial Correta" de outubro/2026).
Saída: "Parcial Consolidada - <Mês> <Ano>.xlsx" na pasta de saída, sem sobrescrever (v2, v3...).
Códigos de saída: 0 ok; 2 parou e precisa do usuário (arquivo faltando, CNPJ em notação científica...).
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl.styles import Font

CENTRAL = Path(r"C:\Users\mateus.ferreira\Documents\Fluxo VBA Teste\Central\Entrada")
SAIDA_PADRAO = Path(r"C:\Users\mateus.ferreira\Downloads\Diária")
MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro",
         "Outubro", "Novembro", "Dezembro"]


class Parar(Exception):
    """A skill manda parar e pedir ao usuário."""


def ler_xlsx(f):
    try:
        return pd.read_excel(f, sheet_name=0, engine="calamine")  # export do portal tem estilos inválidos
    except Exception:  # noqa: BLE001
        return pd.read_excel(f, sheet_name=0)


def ler_csv(f):
    return pd.read_csv(f, sep=";", encoding="cp1252", dtype=str)  # COM aspas: não usar quoting=3


def txt(s):
    return s.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)


def cpf(s):
    t = txt(s).str.replace(r"\D", "", regex=True)
    return t.str.zfill(11).where(s.notna() & (t != ""))


def data_fve(s):  # aceita dd-mm-aaaa e dd/mm/aaaa
    return pd.to_datetime(s.astype(str).str.strip().str.replace("/", "-"), format="%d-%m-%Y", errors="coerce")


def usuarios_padrao():
    pasta = CENTRAL / "Usuarios"
    atual = pasta / "Usuarios_Atual.xlsx"
    ref = pd.to_datetime(ler_xlsx(atual)["DataRef"], errors="coerce").max()
    anterior = pasta / f"Usuarios_{MESES[(ref.month - 2) % 12]}.xlsx"
    return [atual] + ([anterior] if anterior.exists() else [])


def gerar(producao, fves, usuarios, fora, ref=None, saida=SAIDA_PADRAO):
    log = {}
    # ---------- usuários (prioridade pela DataRef mais recente) ----------
    u = pd.concat([ler_xlsx(f).assign(Arquivo=Path(f).name) for f in usuarios])
    log["usuarios"] = {k: str(v) for k, v in u.groupby("Arquivo")["DataRef"].max().items()}
    u = u[u["Cargo"].isin(["CONSULTOR", "SUPERVISOR", "COORDENADOR/GERENTE"])].copy()
    u["CPF"] = cpf(u["CPF"])
    u["Matricula"] = txt(u["Matricula"])
    u["DataRef"] = pd.to_datetime(u["DataRef"], errors="coerce", dayfirst=True)
    u["ClasificacaoUsuarios"] = u["ClasificacaoUsuarios"].fillna("Presencial")
    u = u.sort_values("DataRef", ascending=False, kind="stable")
    u_cpf = u.dropna(subset=["CPF"]).drop_duplicates("CPF")
    u_mat = u.drop_duplicates("Matricula")
    ref_max = u["DataRef"].max()

    # ---------- produção ----------
    p = ler_xlsx(producao)
    p = p[p["Produto"] == "CONTA_CORRENTE_PJ"].copy()
    p["_mes"] = pd.to_datetime(p["DataReferencia"], errors="coerce").dt.to_period("M")
    if ref is None:
        ref = p["_mes"].mode()[0]
    log["mes_referencia"] = str(ref)
    log["corte_producao"] = str(pd.to_datetime(p["DataDigitacao"], errors="coerce").max())
    p = p[p["_mes"] == ref]
    p = p[["Cnpj", "Matricula", "NomeExecutivoLegal", "NomeSupervisor", "NomeCoordenador", "DataBase", "Status"]].copy()
    p["Matricula"] = txt(p["Matricula"])
    p = p.merge(u_mat[["Matricula", "CPF"]], on="Matricula", how="left")

    # ---------- FVE (AK + JGK) ----------
    f = pd.concat([ler_csv(x).assign(Origem=Path(x).name) for x in fves])
    sci = f["CNPJ EMPRESA"].astype(str).str.contains(r"E\+", na=False)
    if sci.any():
        raise Parar(f"{sci.sum()} CNPJs em notação científica em {list(f.loc[sci, 'Origem'].unique())}. "
                    "Baixe o relatório do FVE de novo SEM abrir no Excel.")
    for c in ["DATA INDICACAO", "DATA ULTIMA ATUALIZACAO"]:
        f[c] = data_fve(f[c])
        if f[c].isna().any():
            raise Parar(f"{f[c].isna().sum()} datas ilegíveis em {c} no FVE (formato novo?)")
    mi, ma = f["DATA INDICACAO"].dt.to_period("M"), f["DATA ULTIMA ATUALIZACAO"].dt.to_period("M")
    f = f[(mi == ref) | (ma == ref)].copy()
    log["fve_no_mes"] = f["Origem"].value_counts().to_dict()
    f["CPF PROMOTOR"] = cpf(f["CPF PROMOTOR"])
    f = f.merge(u_cpf[["CPF", "NomeUsuario", "Nome_Supervisor", "Nome_Coordenador"]],
                left_on="CPF PROMOTOR", right_on="CPF", how="left").drop(columns="CPF")

    # ---------- consolidação ----------
    p["Cnpj"] = pd.to_numeric(p["Cnpj"], errors="coerce").astype("Int64")
    f["CNPJ EMPRESA"] = pd.to_numeric(f["CNPJ EMPRESA"], errors="coerce").astype("Int64")
    c = p.merge(f, left_on="Cnpj", right_on="CNPJ EMPRESA", how="outer")
    o = pd.DataFrame({
        "CNPJ Novo": c["Cnpj"].fillna(c["CNPJ EMPRESA"]),
        "Executivo Novo": c["NomeUsuario"].fillna(c["NomeExecutivoLegal"]),
        "Supervisor Novo": c["Nome_Supervisor"].fillna(c["NomeSupervisor"]),
        "Coordenador Novo": c["Nome_Coordenador"].fillna(c["NomeCoordenador"]),
        "Status": c["Status"].fillna("NÃO DIGITADO NO PORTAL AK"),
        "Data Referencia Novo": pd.to_datetime(c["DataBase"], errors="coerce").fillna(c["DATA ULTIMA ATUALIZACAO"]),
        "CPF Novo": c["CPF PROMOTOR"].fillna(c["CPF"]),
    })
    fz = ler_xlsx(fora)
    if not {"CNPJ", "Não Pode"} <= set(fz.columns):
        raise Parar(f"a lista Fora {Path(fora).name} não tem as colunas CNPJ e 'Não Pode'")
    fs = set(pd.to_numeric(fz["CNPJ"], errors="coerce").dropna().astype("int64"))
    exc = o["CNPJ Novo"].isin(fs)
    log["excluidos_lista_fora"] = [int(x) for x in o.loc[exc, "CNPJ Novo"].tolist()]
    o = o[~exc]
    o = (o.merge(u_cpf[["CPF", "ClasificacaoUsuarios", "DataRef"]], left_on="CPF Novo", right_on="CPF", how="left")
         .drop(columns="CPF").rename(columns={"ClasificacaoUsuarios": "Projeto"}))
    log["pessoas_do_arquivo_de_usuarios_antigo"] = int(o[o["DataRef"] < ref_max]["CPF Novo"].nunique())
    o = o.drop(columns="DataRef").sort_values(["Coordenador Novo", "Supervisor Novo"], na_position="last")

    # ---------- checagens ----------
    d = o[o["CNPJ Novo"].notna() & o["CNPJ Novo"].duplicated(keep=False)]
    log |= {
        "total": len(o),
        "por_status": o["Status"].value_counts().to_dict(),
        "por_projeto": {str(k): v for k, v in o["Projeto"].value_counts(dropna=False).items()},
        "cnpj_vazio": int(o["CNPJ Novo"].isna().sum()),
        "cnpjs_duplicados": [int(x) for x in d["CNPJ Novo"].unique()[:20]],
        "sem_coordenador": int(o["Coordenador Novo"].isna().sum()),
        "sem_supervisor": int(o["Supervisor Novo"].isna().sum()),
        "cpfs_nao_achados": [x for x in o.loc[o["Projeto"].isna(), "CPF Novo"].unique().tolist() if isinstance(x, str)],
    }

    # ---------- saída ----------
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    base = saida / f"Parcial Consolidada - {MESES[ref.month - 1]} {ref.year}"
    out, n = Path(f"{base}.xlsx"), 2
    while out.exists():
        out, n = Path(f"{base} v{n}.xlsx"), n + 1
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        o.to_excel(w, sheet_name="Parcial Consolidada", index=False)
        ws = w.sheets["Parcial Consolidada"]
        for cel in ws[1]:
            cel.font = Font(bold=True)
        ws.auto_filter.ref = ws.dimensions
        ws.freeze_panes = "A2"
        for r in ws.iter_rows(min_row=2):
            r[0].number_format = "0"
            r[5].number_format = "dd/mm/yyyy"
            r[6].number_format = "@"
        for col, wd in zip("ABCDEFGH", [17, 40, 32, 32, 28, 14, 14, 14]):
            ws.column_dimensions[col].width = wd
    log["arquivo"] = str(out)
    return log


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gera a Parcial Consolidada AK (Produção Conta PJ × FVE AK+JGK)")
    ap.add_argument("--fora", required=True, help="lista Fora (colunas CNPJ e 'Não Pode')")
    ap.add_argument("--mes", help="AAAA-MM (padrão: mês predominante da produção)")
    ap.add_argument("--producao", default=str(CENTRAL / "Producao.xlsx"))
    ap.add_argument("--fve", nargs="+", default=[str(CENTRAL / "FVE AK.csv"), str(CENTRAL / "FVE JGK.csv")])
    ap.add_argument("--usuarios", nargs="+")
    ap.add_argument("--saida", default=str(SAIDA_PADRAO))
    ap.add_argument("--resumo")
    a = ap.parse_args(argv)
    try:
        if not Path(a.fora).exists():
            raise Parar(f"a lista Fora não existe: {a.fora}")
        log = gerar(a.producao, a.fve, a.usuarios or usuarios_padrao(), a.fora,
                    pd.Period(a.mes) if a.mes else None, a.saida)
        codigo, log = 0, {"ok": True, **log}
    except Parar as e:
        codigo, log = 2, {"ok": False, "parar_e_pedir": str(e)}
    texto = json.dumps(log, ensure_ascii=False, indent=2, default=str)
    if a.resumo:
        Path(a.resumo).write_text(texto, encoding="utf-8")
    print(texto)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
