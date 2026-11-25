r"""Gera o Relatório Diário AK (skill diaria-relatorio-ak) a partir do relatório anterior.

Uso:
    python relatorio_diario.py [--anterior ARQ.xlsx] [--producao Producao.xlsx] [--usuarios Usuarios_Atual.xlsx]
                               [--saida PASTA] [--resumo resumo.json]

Sem argumentos: pega o Relatório Diário mais recente da pasta de relatórios, a Producao e a Usuarios_Atual
validadas da Central\Entrada, e grava "Relatório Diário DD.MM.AAAA.xlsx" (data = dia da última digitação)
na mesma pasta do anterior, sem sobrescrever (v2, v3...).

O arquivo é editado direto no XML, como a skill manda (o openpyxl não abre as dinâmicas). Antes de gravar,
roda as validações obrigatórias da skill; se algum supervisor não bater com a produção, o arquivo sai com
"CONFERIR" no nome e o código de saída é 3.
"""
import argparse
import json
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd

PASTA_RELATORIOS = Path(r"C:\Users\mateus.ferreira\Documents\Relatório Diária Atualizado\Comparativo\Claude outputs")
CENTRAL = Path(r"C:\Users\mateus.ferreira\Documents\Fluxo VBA Teste\Central\Entrada")

CONTA, GET = "CONTA_CORRENTE_PJ", "CREDENCIAMENTO"
CONTA_M2, GET_M2 = "CONTA_CORRENTE_PJ_M2", "CREDENCIAMENTO_M2"
CANCELADOS = {"CANCELADO", "ANALISE_CANCELAMENTO"}
# colunas numéricas da tabela dados (K e M..W), na ordem da planilha
NUMERICAS = ["K", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W"]


class ErroRelatorio(Exception):
    pass


def mat(v):
    if v is None or (isinstance(v, float) and v != v):
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip().removesuffix(".0")


def ler(arq, **kw):
    return pd.read_excel(arq, engine="calamine", **kw)


# ---------------------------------------------------------------- estrutura do relatório anterior

def estrutura(anterior):
    """Coordenadores (na ordem da aba Por Supervisor) e supervisores válidos de cada um."""
    # o subtotal é a linha cujo D é SUM(...): lido do XML para não depender do texto da coluna B
    z = zipfile.ZipFile(anterior)
    s2 = z.read("xl/worksheets/sheet2.xml").decode("utf-8")
    sst = strings_compartilhadas(z)
    linhas = {}
    for r, corpo in re.findall(r'<row r="(\d+)"[^>]*>(.*?)</row>', s2, re.S):
        linhas[int(r)] = celulas(corpo, sst)
    sup_rows, sub_rows, total_row = [], [], None
    for r in sorted(linhas):
        c = linhas[r]
        if r < 10:
            continue
        if c.get("A", {}).get("valor", "").strip().upper() == "TOTAL GERAL":
            total_row = r
            break
        f_d = c.get("D", {}).get("formula", "")
        if f_d.upper().startswith("SUM("):
            sub_rows.append(r)
        elif c.get("B", {}).get("valor"):
            sup_rows.append(r)
    if total_row is None or not sub_rows:
        raise ErroRelatorio("não reconheci a aba Por Supervisor (linha Total Geral ou subtotais)")
    coords, inicio = [], sup_rows[0]
    for sub in sub_rows:
        bloco = [r for r in sup_rows if inicio <= r < sub]
        nome_coord = next((linhas[r]["A"]["valor"].strip() for r in bloco if linhas[r].get("A", {}).get("valor")), "")
        coords.append({"coordenador": nome_coord, "supervisores": [linhas[r]["B"]["valor"].strip() for r in bloco],
                       "linhas": bloco, "subtotal": sub})
        inicio = sub + 1
    return {"coordenadores": coords, "total": total_row}


def strings_compartilhadas(z):
    x = z.read("xl/sharedStrings.xml").decode("utf-8")
    return [re.sub(r"<[^>]+>", "", si) for si in re.findall(r"<si>(.*?)</si>", x, re.S)]


def celulas(corpo, sst):
    out = {}
    for col, attrs, inner in re.findall(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)', corpo, re.S):
        v = re.search(r"<v>(.*?)</v>", inner or "")
        f = re.search(r"<f[^>]*>(.*?)</f>", inner or "")
        t = re.search(r'<is><t[^>]*>(.*?)</t></is>', inner or "", re.S)
        valor = v.group(1) if v else (t.group(1) if t else "")
        if 't="s"' in attrs and v:
            valor = sst[int(v.group(1))]
        out[col] = {"valor": unescape(valor), "formula": unescape(f.group(1)) if f else ""}
    return out


def unescape(s):
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&")


# ---------------------------------------------------------------- cálculo das linhas

def calcular(producao, usuarios, est, hoje=None):
    coords = [c["coordenador"] for c in est["coordenadores"]]
    ordem_coord = {c: i for i, c in enumerate(coords)}
    validos = {s for c in est["coordenadores"] for s in c["supervisores"]}

    p = producao.copy()
    p["mat"] = p["Matricula"].map(mat)
    p["DataBase"] = pd.to_datetime(p["DataBase"], errors="coerce")
    mes = p["DataBase"].max().to_period("M")
    p = p[p["DataBase"].dt.to_period("M") == mes]
    p = p[p["Tipo_Consultor"].astype(str) != "Remoto"]  # equipe da Mariana fica fora; Remoto_Brasil entra
    for c in ("Pontos", "OportunidadesDePontos", "PontuacaoDigitada"):
        p[c] = pd.to_numeric(p[c], errors="coerce").fillna(0)
    corte = pd.to_datetime(p["DataDigitacao"], errors="coerce").max()

    u = usuarios.copy()
    u["mat"] = u["Matricula"].map(mat)
    u["Cargo"] = u["Cargo"].astype(str).str.upper().str.strip()
    u = u.drop_duplicates("mat")
    por_mat = u.set_index("mat")

    def numeros(m):
        g = p[p["mat"] == m]
        soma = lambda prod, col: float(g.loc[g["Produto"] == prod, col].sum())
        conta = g[(g["Produto"] == CONTA) & ~g["Status"].astype(str).isin(CANCELADOS)]
        valores = {
            "K": int(conta["Cnpj"].nunique()),
            "M": soma(CONTA, "PontuacaoDigitada"),
            "P": soma(CONTA, "OportunidadesDePontos"), "Q": soma(CONTA, "Pontos"),
            "R": soma(GET, "OportunidadesDePontos"), "S": soma(GET, "Pontos"),
            "T": soma(CONTA_M2, "OportunidadesDePontos"), "U": soma(CONTA_M2, "Pontos"),
            "V": soma(GET_M2, "OportunidadesDePontos"), "W": soma(GET_M2, "Pontos"),
        }
        valores["N"] = valores["P"] + valores["R"] + valores["T"] + valores["V"]
        valores["O"] = valores["Q"] + valores["S"] + valores["U"] + valores["W"]
        return valores

    com_producao = set(p["mat"])
    linhas = []

    # Lista A: consultores da Usuarios_Atual nas coordenações do relatório
    a = u[(u["Cargo"] == "CONSULTOR") & u["Nome_Coordenador"].isin(coords)]
    fora = []
    for _, r in a.iterrows():
        # consultor cujo supervisor não está no relatório fica fora, com aviso. Caso típico: supervisor do
        # relatório lançando em nome próprio sob "TBA ..." (Eder de Jesus Santos até 23/11). Se ele virou
        # consultor de uma equipe do relatório (Eder sob o Rafael em 25/11), entra normalmente.
        if str(r["Nome_Supervisor"]).strip() not in validos:
            n = numeros(r["mat"])
            if n["M"] or n["N"] or n["O"]:
                fora.append({"mat": r["mat"],
                             "tipo": "produção do próprio supervisor" if str(r["NomeUsuario"]).strip() in validos
                             else "supervisor fora do relatório",
                             "nome": r["NomeUsuario"], "supervisor": r["Nome_Supervisor"],
                             "pontos_digitados": n["M"], "pontos_reais": n["O"]})
            continue
        deslig = pd.to_datetime(r["DataDesligamento"], errors="coerce")
        sit = str(r["Situacao"] if pd.notna(r["Situacao"]) else "").strip().upper()
        if pd.notna(deslig):
            posicao = "DESLIGADO"
            if deslig.to_period("M") != mes and r["mat"] not in com_producao:
                continue
        elif sit.startswith("F"):
            posicao = "FÉRIAS"
        elif sit:
            posicao = "LICENCA"
        else:
            posicao = "ATIVO"
        linhas.append({
            "A": r["mat"], "B": r["NomeUsuario"], "C": r["Nome_Supervisor"], "D": r["Nome_Coordenador"],
            "E": r.get("Regiao"), "F": r.get("Rede"),
            "G": pd.to_datetime(r["DataAdmissao"], errors="coerce"), "H": deslig,
            "I": posicao, "orfa": False, **numeros(r["mat"]),
        })

    # Lista B: matrículas órfãs (na produção do mês, fora da Usuarios_Atual)
    coord_do_sup = (u[u["Cargo"] == "SUPERVISOR"].drop_duplicates("NomeUsuario")
                    .set_index("NomeUsuario")["Nome_Coordenador"])
    for m, g in p[~p["mat"].isin(por_mat.index)].groupby("mat"):
        ult = g.sort_values("DataDigitacao").iloc[-1]
        sup = str(ult["NomeSupervisor"]).strip()
        n = numeros(m)
        if sup not in validos:
            fora.append({"tipo": "órfã de supervisor fora do relatório", "nome": ult["NomeExecutivoLegal"],
                         "supervisor": sup, "pontos_digitados": n["M"], "pontos_reais": n["O"]})
            continue
        coord = coord_do_sup.get(sup, ult["NomeCoordenador"])
        linhas.append({
            "A": m, "B": ult["NomeExecutivoLegal"], "C": sup, "D": coord,
            "E": ult.get("Regiao"), "F": ult.get("Rede"), "G": pd.NaT, "H": pd.NaT,
            "I": "DESLIGADO", "orfa": True, **n,
        })

    # produção de quem não entra (supervisor lançando em nome próprio, coordenação fora do relatório)
    ja_avisados = {l["A"] for l in linhas} | {f["mat"] for f in fora if "mat" in f}
    for m, g in p[p["mat"].isin(por_mat.index) & ~p["mat"].isin(ja_avisados)].groupby("mat"):
        r = por_mat.loc[m]
        n = numeros(m)
        if n["M"] == 0 and n["O"] == 0 and n["N"] == 0:
            continue
        tipo = ("produção do próprio supervisor" if r["Cargo"] == "SUPERVISOR"
                else f"{str(r['Cargo']).lower()} fora das coordenações do relatório")
        fora.append({"tipo": tipo, "nome": r["NomeUsuario"], "supervisor": g["NomeSupervisor"].iloc[-1],
                     "pontos_digitados": n["M"], "pontos_reais": n["O"]})

    linhas.sort(key=lambda l: (ordem_coord.get(l["D"], 99), str(l["C"]), l["orfa"], str(l["B"])))

    # visão do portal: produção do mês por NomeSupervisor (validação 2 da skill)
    portal = {}
    for sup, g in p.groupby(p["NomeSupervisor"].astype(str).str.strip()):
        portal[sup] = {"M": float(g.loc[g["Produto"] == CONTA, "PontuacaoDigitada"].sum()),
                       "O": float(g["Pontos"].sum()), "N": float(g["OportunidadesDePontos"].sum())}
    return {"linhas": linhas, "fora": fora, "mes": str(mes), "corte": corte, "portal": portal}


# ---------------------------------------------------------------- escrita no XML

ESTILO_DADOS = {"A": 110, "B": 106, "C": 106, "D": 106, "E": 104, "F": 104, "G": 105, "H": 105, "I": 103,
                "J": 22, "K": 112, "L": 113, "M": 112, "N": 120, **{c: 112 for c in "OPQRSTUVW"}}
ESTILO_VAZIO = {**ESTILO_DADOS, "E": 106, "F": 106, "G": 111, "H": 111}
COLUNAS = "ABCDEFGHIJKLMNOPQRSTUVW"
ATRIB_LINHA = 'spans="1:23" ht="33.75" customHeight="1" x14ac:dyDescent="0.3"'
ULTIMA_LINHA_MODELO = 537

# sheet4 (Dados Conta PJ), colunas B..J  ->  coluna da tabela dados
PIVOT_DADOS = dict(zip("BCDEFGHIJ", ["M", "S", "P", "Q", "R", "T", "U", "V", "W"]))
# sheet2 (Por Supervisor)  ->  coluna da tabela dados
POR_SUP = {"H": "M", "I": "P", "J": "Q", "L": "R", "M": "S", "O": "T", "P": "U", "R": "V", "S": "W"}
# sheet5 (Por Coordenador)  ->  coluna da tabela dados
POR_COORD = {"G": "M", "H": "P", "I": "Q", "K": "R", "L": "S", "N": "T", "O": "U", "Q": "V", "R": "W"}


def num(v):
    v = float(v)
    return str(int(v)) if v.is_integer() else repr(v)


def serial(d):
    return (pd.Timestamp(d).normalize() - pd.Timestamp("1899-12-30")).days


def vazio_num(v):
    return v is None or (isinstance(v, float) and v != v)


def linha_xml(r, l):
    cel = []
    for c in COLUNAS:
        ref, s = f"{c}{r}", ESTILO_DADOS[c]
        if l is None:
            cel.append(f'<c r="{ref}" s="{ESTILO_VAZIO[c]}"/>')
            continue
        v = l.get(c)
        if c in ("J", "L") or vazio_num(v) or (c in "GH" and pd.isna(v)):
            cel.append(f'<c r="{ref}" s="{s}"/>')
        elif c == "A" and str(v).isdigit():
            cel.append(f'<c r="{ref}" s="{s}"><v>{int(v)}</v></c>')
        elif c in "GH":
            cel.append(f'<c r="{ref}" s="{s}"><v>{serial(v)}</v></c>')
        elif c in NUMERICAS:
            cel.append(f'<c r="{ref}" s="{s}"><v>{num(v)}</v></c>')
        else:
            cel.append(f'<c r="{ref}" s="{s}" t="inlineStr"><is><t>{escape(str(v).strip())}</t></is></c>')
    return f'<row r="{r}" {ATRIB_LINHA}>{"".join(cel)}</row>'


def gravar_valor(xml, ref, valor):
    """Troca só o valor em cache de uma célula, mantendo estilo e fórmula."""
    m = re.search(rf'<c r="{ref}"(?P<a>[^>]*?)(?:/>|>(?P<i>.*?)</c>)', xml, re.S)
    if not m:
        return xml
    attrs = re.sub(r'\s+t="[^"]*"', "", m.group("a"))
    interno = m.group("i") or ""
    formula = re.search(r"<f[^>]*/>|<f[^>]*>.*?</f>", interno, re.S)
    f = formula.group(0) if formula else ""
    if isinstance(valor, str):
        novo = f'<c r="{ref}"{attrs} t="str">{f}<v>{escape(valor)}</v></c>'
    else:
        novo = f'<c r="{ref}"{attrs}>{f}<v>{num(valor)}</v></c>'
    return xml[:m.start()] + novo + xml[m.end():]


def ler_linhas(xml, sst):
    return {int(r): celulas(corpo, sst) for r, corpo in re.findall(r'<row r="(\d+)"[^>]*>(.*?)</row>', xml, re.S)}


def zerado():
    return {**{c: 0.0 for c in NUMERICAS}, "atuando": 0}


def agregados(linhas):
    """Somas por supervisor e por coordenador + Atuando (ATIVO ou FÉRIAS)."""
    por_sup, por_coord, total = {}, {}, zerado()
    for l in linhas:
        sup, coord = str(l["C"]).strip(), str(l["D"]).strip()
        por_sup.setdefault(sup, zerado())
        por_coord.setdefault(coord, zerado())
        for alvo in (por_sup[sup], por_coord[coord], total):
            for c in NUMERICAS:
                alvo[c] += l[c]
            alvo["atuando"] += l["I"] in ("ATIVO", "FÉRIAS")
    return por_sup, por_coord, total


def gravar(anterior, saida, res, est):
    linhas = res["linhas"]
    por_sup, por_coord, total = agregados(linhas)
    tmp = Path(tempfile.mkdtemp(prefix="relatorio_diario_"))
    try:
        with zipfile.ZipFile(anterior) as z:
            z.extractall(tmp)
            ordem = z.namelist()
            sst = strings_compartilhadas(z)

        def ler_txt(n):
            return (tmp / n).read_text(encoding="utf-8")

        def gravar_txt(n, t):
            (tmp / n).write_text(t, encoding="utf-8")

        def alvo_de(nome):
            if nome.upper() == "TOTAL GERAL":
                return total
            return por_sup.get(nome) or por_coord.get(nome)

        # 1. Conta PJ - Consultor (tabela dados)
        fim = max(ULTIMA_LINHA_MODELO, 6 + len(linhas))
        s1 = ler_txt("xl/worksheets/sheet1.xml")
        ini, fim_dados = s1.index('<row r="7"'), s1.index("</sheetData>")
        corpo = "".join(linha_xml(7 + i, linhas[i] if i < len(linhas) else None) for i in range(fim - 6))
        s1 = s1[:ini] + corpo + s1[fim_dados:]
        for c in NUMERICAS:
            s1 = gravar_valor(s1, f"{c}5", total[c])
        s1 = re.sub(r'<dimension ref="[^"]*"/>', f'<dimension ref="A1:W{fim}"/>', s1, count=1)
        s1 = re.sub(r'(<pane [^>]*topLeftCell=")[^"]*(")', r"\g<1>A7\g<2>", s1, count=1)
        gravar_txt("xl/worksheets/sheet1.xml", s1)
        if fim > ULTIMA_LINHA_MODELO:
            for n in ("xl/tables/table1.xml", "xl/pivotCache/pivotCacheDefinition2.xml"):
                gravar_txt(n, re.sub(r'ref="A6:W\d+"', f'ref="A6:W{fim}"', ler_txt(n)))

        # 2. dinâmicas: atualizam ao abrir; os valores exibidos também ficam certos
        for n in ("xl/pivotCache/pivotCacheDefinition1.xml", "xl/pivotCache/pivotCacheDefinition2.xml"):
            x = ler_txt(n)
            if "refreshOnLoad=" in x:
                x = re.sub(r'refreshOnLoad="\d"', 'refreshOnLoad="1"', x)
            else:
                x = x.replace("<pivotCacheDefinition ", '<pivotCacheDefinition refreshOnLoad="1" ', 1)
            gravar_txt(n, x)
        s3 = ler_txt("xl/worksheets/sheet3.xml")
        for r, c in ler_linhas(s3, sst).items():
            if r < 4 or not c.get("B", {}).get("valor"):
                continue
            alvo = alvo_de(c.get("A", {}).get("valor", "").strip())
            s3 = gravar_valor(s3, f"B{r}", alvo["atuando"] if alvo else 0)
        gravar_txt("xl/worksheets/sheet3.xml", s3)
        s4 = ler_txt("xl/worksheets/sheet4.xml")
        for r, c in ler_linhas(s4, sst).items():
            nome = c.get("A", {}).get("valor", "").strip()
            if r < 4 or not nome:
                continue
            alvo = alvo_de(nome)
            for col, origem in PIVOT_DADOS.items():
                if col in c:
                    s4 = gravar_valor(s4, f"{col}{r}", alvo[origem] if alvo else 0)
        gravar_txt("xl/worksheets/sheet4.xml", s4)

        # 3. Por Supervisor (D = Capacity e Y = Meta não mudam)
        s2 = ler_txt("xl/worksheets/sheet2.xml")
        cel2 = ler_linhas(s2, sst)

        def fixo(r, col):
            return float(cel2.get(r, {}).get(col, {}).get("valor") or 0)

        vals, dy = {}, {}
        for bloco in est["coordenadores"]:
            for r in bloco["linhas"]:
                a = por_sup.get(cel2[r]["B"]["valor"].strip(), zerado())
                vals[r] = {"E": a["atuando"], **{col: a[orig] for col, orig in POR_SUP.items()}}
                dy[r] = (fixo(r, "D"), fixo(r, "Y"))
            sub = bloco["subtotal"]
            vals[sub] = {k: sum(vals[r][k] for r in bloco["linhas"]) for k in vals[bloco["linhas"][0]]}
            dy[sub] = (fixo(sub, "D"), fixo(sub, "Y"))
        subs = [b["subtotal"] for b in est["coordenadores"]]
        vals[est["total"]] = {k: sum(vals[s][k] for s in subs) for k in vals[subs[0]]}
        dy[est["total"]] = (sum(dy[s][0] for s in subs), sum(dy[s][1] for s in subs))
        for r, v in vals.items():
            d, y = dy[r]
            v = {**v, "F": v["E"] / d if d else 0, "U": v["I"] + v["L"] + v["O"] + v["R"],
                 "V": v["J"] + v["M"] + v["P"] + v["S"]}
            if y:
                v["Z"] = (v["I"] + v["J"] + v["L"] + v["M"]) / y
            for col, valor in v.items():
                s2 = gravar_valor(s2, f"{col}{r}", valor)
        gravar_txt("xl/worksheets/sheet2.xml", s2)

        # 4. Por Coordenador (C = Capacity e W = Meta não mudam)
        s5 = ler_txt("xl/worksheets/sheet5.xml")
        cel5 = ler_linhas(s5, sst)
        nomes_coord = [b["coordenador"] for b in est["coordenadores"]]
        soma = {k: 0.0 for k in ["C", "D", "W", *POR_COORD]}
        for r in sorted(cel5):
            nome = cel5[r].get("B", {}).get("valor", "").strip()
            if r < 7 or nome not in nomes_coord:
                continue
            a = por_coord.get(nome, zerado())
            cap = float(cel5[r].get("C", {}).get("valor") or 0)
            meta = float(cel5[r].get("W", {}).get("valor") or 0)
            v = {"D": a["atuando"], **{col: a[orig] for col, orig in POR_COORD.items()}}
            soma["C"] += cap
            soma["W"] += meta
            for k in ["D", *POR_COORD]:
                soma[k] += v[k]
            v |= {"E": v["D"] / cap if cap else 0, "T": v["H"] + v["K"] + v["N"] + v["Q"],
                  "U": v["I"] + v["L"] + v["O"] + v["R"]}
            if meta:
                v["X"] = (v["H"] + v["I"] + v["K"] + v["L"]) / meta
            for col, valor in v.items():
                s5 = gravar_valor(s5, f"{col}{r}", valor)
        v6 = {k: soma[k] for k in ["D", *POR_COORD]}
        v6 |= {"E": soma["D"] / soma["C"] if soma["C"] else 0, "T": v6["H"] + v6["K"] + v6["N"] + v6["Q"],
               "U": v6["I"] + v6["L"] + v6["O"] + v6["R"]}
        if soma["W"]:
            v6["X"] = (v6["H"] + v6["I"] + v6["K"] + v6["L"]) / soma["W"]
        for col, valor in v6.items():
            s5 = gravar_valor(s5, f"{col}6", valor)
        gravar_txt("xl/worksheets/sheet5.xml", s5)

        # 5. recálculo completo ao abrir; sem calcChain
        wb = ler_txt("xl/workbook.xml")
        if "fullCalcOnLoad=" not in wb:
            wb = wb.replace("<calcPr", '<calcPr fullCalcOnLoad="1"', 1)
        gravar_txt("xl/workbook.xml", re.sub(r'fullCalcOnLoad="\d"', 'fullCalcOnLoad="1"', wb))
        if (tmp / "xl" / "calcChain.xml").exists():
            (tmp / "xl" / "calcChain.xml").unlink()
            ordem = [n for n in ordem if n != "xl/calcChain.xml"]
            for n in ("[Content_Types].xml", "xl/_rels/workbook.xml.rels"):
                gravar_txt(n, re.sub(r"<(?:Override|Relationship)[^>]*calcChain[^>]*/>", "", ler_txt(n)))

        # 6. recompacta com [Content_Types].xml primeiro
        ordem = ["[Content_Types].xml"] + [n for n in ordem if n != "[Content_Types].xml"]
        with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
            for n in ordem:
                if (tmp / n).is_file():
                    z.write(tmp / n, n)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return por_sup, por_coord, total


# ---------------------------------------------------------------- validação e linha de comando

def validar(saida, res, est, por_sup, total):
    """As 4 validações obrigatórias da skill. Devolve (ok, problemas, avisos)."""
    problemas, avisos = [], []
    validos = [s for c in est["coordenadores"] for s in c["supervisores"]]

    # 3. todo supervisor das linhas existe na aba Por Supervisor (e na dinâmica Dados Conta PJ)
    sem_aba = sorted(set(por_sup) - set(validos))
    if sem_aba:
        problemas.append(f"supervisores nas linhas que não estão na aba Por Supervisor: {', '.join(sem_aba)}")
    pivot = ler(saida, sheet_name="Dados Conta PJ", header=None)
    nomes_pivot = {str(x).strip() for x in pivot.iloc[:, 0].dropna()}
    sem_pivot = sorted(s for s in por_sup if s not in nomes_pivot)
    if sem_pivot:
        avisos.append(f"supervisores novos na dinâmica (entram ao atualizar no Excel): {', '.join(sem_pivot)}")

    # 1. Total Geral da Por Supervisor = total da Conta PJ - Consultor, coluna a coluna
    ps = ler(saida, sheet_name="Por Supervisor", header=None)
    linha_total = ps.iloc[est["total"] - 1]
    for col, orig in POR_SUP.items():
        v = float(linha_total.iloc[ord(col) - 65] or 0)
        if abs(v - total[orig]) > 1e-6:
            problemas.append(f"Total Geral da Por Supervisor, coluna {col}: {v:g} × {total[orig]:g} na Conta PJ - Consultor")

    # 2. cada supervisor = produção do mês com NomeSupervisor = ele (visão do portal)
    for sup in validos:
        nosso = por_sup.get(sup, zerado())
        portal = res["portal"].get(sup, {"M": 0.0, "O": 0.0, "N": 0.0})
        for chave, rotulo in (("M", "digitada"), ("O", "pontos"), ("N", "oportunidades")):
            if abs(nosso[chave] - portal[chave]) > 1e-6:
                problemas.append(f"{sup}: {rotulo} {nosso[chave]:g} no relatório × {portal[chave]:g} no portal")

    # 4. o arquivo abre (todas as abas)
    for aba in ("Conta PJ - Consultor", "Por Supervisor", "Dinamica Atuando", "Dados Conta PJ", "Por Coordenador"):
        try:
            ler(saida, sheet_name=aba, header=None)
        except Exception as e:  # noqa: BLE001
            problemas.append(f"a aba {aba} não abre: {e}")
    return not problemas, problemas, avisos


def mais_recente(pasta):
    def data(p):
        m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", p.name)
        return datetime(int(m[3]), int(m[2]), int(m[1])) if m else datetime.min
    arquivos = [p for p in pasta.glob("Relatório Diário *.xlsx") if not p.name.startswith("~$")]
    if not arquivos:
        raise ErroRelatorio(f"nenhum Relatório Diário em {pasta}")
    return max(arquivos, key=lambda p: (data(p), p.stat().st_mtime))


def nome_livre(pasta, base):
    alvo, n = pasta / f"{base}.xlsx", 2
    while alvo.exists():
        alvo, n = pasta / f"{base} v{n}.xlsx", n + 1
    return alvo


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gera o Relatório Diário AK a partir do anterior")
    ap.add_argument("--anterior")
    ap.add_argument("--producao", default=str(CENTRAL / "Producao.xlsx"))
    ap.add_argument("--usuarios", default=str(CENTRAL / "Usuarios" / "Usuarios_Atual.xlsx"))
    ap.add_argument("--saida")
    ap.add_argument("--resumo")
    a = ap.parse_args(argv)

    anterior = Path(a.anterior) if a.anterior else mais_recente(PASTA_RELATORIOS)
    pasta = Path(a.saida) if a.saida else anterior.parent
    pasta.mkdir(parents=True, exist_ok=True)
    est = estrutura(anterior)
    res = calcular(ler(a.producao), ler(a.usuarios), est)
    data_nome = res["corte"].strftime("%d.%m.%Y")
    tmp = pasta / f"~gerando_{datetime.now():%H%M%S}.xlsx"
    por_sup, por_coord, total = gravar(anterior, tmp, res, est)
    ok, problemas, avisos = validar(tmp, res, est, por_sup, total)
    destino = nome_livre(pasta, f"Relatório Diário {data_nome}" + ("" if ok else " - CONFERIR"))
    tmp.replace(destino)

    orfas = [l for l in res["linhas"] if l["orfa"]]
    resumo = {
        "ok": ok,
        "arquivo": str(destino),
        "anterior": str(anterior),
        "mes": res["mes"],
        "corte_producao": res["corte"].strftime("%d/%m/%Y %H:%M"),
        "linhas": len(res["linhas"]),
        "orfas_incluidas": len(orfas),
        "atuando": total["atuando"],
        "pontos_digitados": total["M"],
        "pontos_reais_total": total["O"],
        "oportunidade_total": total["N"],
        "por_coordenador": {c: {"digitada": v["M"], "pontos_reais": v["O"], "atuando": v["atuando"]}
                            for c, v in por_coord.items()},
        "supervisores_batem_com_portal": ok,
        "problemas": problemas,
        "avisos": avisos,
        "ficaram_fora": [{k: f[k] for k in ("tipo", "nome", "supervisor", "pontos_digitados", "pontos_reais")}
                         for f in res["fora"]],
        "lembrete": "as dinâmicas e fórmulas atualizam sozinhas ao abrir no Excel",
    }
    texto = json.dumps(resumo, ensure_ascii=False, indent=2, default=str)
    if a.resumo:
        Path(a.resumo).write_text(texto, encoding="utf-8")
    print(texto)
    return 0 if ok else 3


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ErroRelatorio as e:
        print(json.dumps({"ok": False, "erro": str(e)}, ensure_ascii=False))
        sys.exit(2)
