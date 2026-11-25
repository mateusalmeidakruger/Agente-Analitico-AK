r"""Monta o disparo de retorno dos chamados concluídos (e-mails prontos para o Mateus enviar).

Uso:
    python disparo_retorno.py [--chamados 2295,2319] [--desde AAAA-MM-DD] [--resumo resumo.json]

Parte da última consulta do portal feita pelo agente (dados\consulta_chamados\ultima_consulta.json),
que já traz a resposta final do Santander. Sem --chamados, pega todos os concluídos com resposta
(desde --desde, se vier) que ainda não estão em nenhum envio_*.json anterior.

Regras (mesmo padrão dos disparos de 05/11 a 24/11):
- Um e-mail por supervisor: Para = supervisor + coordenador; Cc = Andressa Fontana.
- NUNCA Gustavo Kruger nem Mariana Freire, nem em Para nem em Cc, mesmo como coordenadores
  (nesses casos vai só o supervisor). Só e-mails corporativos; o da Crislaine é corrigido.
- Assunto "Retorno chamado do <CNPJ> - <motivo da abertura>", sem número do chamado; status no corpo.
- Consultor: registro do robô; se não houver, CPF PROMOTOR do FVE AK/JGK; por fim a Produção.
  Supervisor e coordenador atuais vêm da Usuarios_Atual.
Saída (nada é enviado): envio_<data>.json/.csv e abrir_emails_<data>.html em Disparo Retorno Chamados,
sem sobrescrever (sufixo _2, _3...). O envio continua sendo o Mateus clicando em cada link.
"""
import argparse
import csv
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

import pandas as pd

PROJETO = Path(__file__).resolve().parent.parent
FLUXO = Path(r"C:\Users\mateus.ferreira\Documents\Fluxo VBA Teste")
PASTA = FLUXO / "Disparo Retorno Chamados"
CONSULTA = PROJETO / "dados" / "consulta_chamados" / "ultima_consulta.json"
CENTRAL = FLUXO / "Central" / "Entrada"
CC = "andressa.fontana@almeidakruger.com.br"
DOMINIO = "@almeidakruger.com.br"
NUNCA = {"j.gustavokruger@almeidakruger.com.br", "mariana.freire@almeidakruger.com.br"}
NOMES_NUNCA = ("GUSTAVO KRUGER", "MARIANA FREIRE", "MARIANA KRUGER")
CORRIGIR = {"crislaine.araujo@outlook.com": "crislaine.araujo@almeidakruger.com.br"}
ASSINATURA = "Qualquer dúvida, fico à disposição.\n\nMateus Ferreira\nAnálise de Dados | Almeida Kruger"


class Parar(Exception):
    pass


def digitos(v):
    if isinstance(v, float) and v == v:
        v = int(v)
    return re.sub(r"\D", "", str(v or ""))


def cnpj_fmt(c):
    c = digitos(c).zfill(14)
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def titulo(nome):
    pequenas = {"de", "da", "do", "das", "dos", "e"}
    return " ".join(p.lower() if p.lower() in pequenas else p.capitalize() for p in str(nome).split())


def ja_disparados():
    feitos = set()
    for f in PASTA.glob("envio_*.json"):
        for e in json.loads(f.read_text(encoding="utf-8")):
            feitos |= set(re.findall(r"CCPJ-(\d+)", e.get("chamados", "")))
    return feitos


def motivo(c):
    texto = f"{c.get('titulo') or ''} {c.get('descricao') or ''}".lower()
    if "aguardando libera" in texto:
        return "Aguardando liberação"
    if "abertura web" in texto or "abertura - web" in texto:
        return "Em abertura web acima do SLA"
    if "reset" in texto:
        return "Reset de proposta"
    if "devolu" in texto:
        return "Proposta devolvida"
    if "sla" in texto:
        return "SLA backoffice"
    return (c.get("titulo") or "Chamado").strip()


def retorno(resp):
    parecer = re.sub(r"\s+", " ", str(resp.get("parecer") or "")).strip()
    parecer = re.sub(r"^(bom dia|boa tarde|boa noite|ol[aá]|prezad[oa]s?)[\s,.!:]*", "", parecer, flags=re.I)
    # pontuação do texto do banco: sem espaço antes de vírgula/ponto, com espaço depois
    parecer = re.sub(r"\s+([,.;:!?])", r"\1", parecer)
    parecer = re.sub(r"([,;:])(?=[^\s\d])", r"\1 ", parecer)
    parecer = re.sub(r"\.(?=[A-Za-zÀ-ÿ])", ". ", parecer)
    parecer = re.sub(r"\s{2,}", " ", parecer).strip()
    parecer = parecer[:1].upper() + parecer[1:] if parecer else "Sem detalhe no parecer."
    if not parecer.endswith((".", "!", "?")):
        parecer += "."
    return parecer


def email_valido(e):
    e = str(e or "").strip().lower()
    e = CORRIGIR.get(e, e)
    return e if e.endswith(DOMINIO) and e not in NUNCA else None


def montar(chamados_alvo=None, desde=None):
    if not CONSULTA.exists():
        raise Parar("não há consulta do portal; rode antes o script chamados_consultar")
    consulta = json.loads(CONSULTA.read_text(encoding="utf-8"))
    feitos = ja_disparados()
    alvo = {digitos(x) for x in (chamados_alvo or [])}
    desde_d = date.fromisoformat(desde) if desde else None

    u = pd.read_excel(CENTRAL / "Usuarios" / "Usuarios_Atual.xlsx", engine="calamine")
    u["CPFd"] = u["CPF"].map(digitos).str.zfill(11)
    por_nome = u.drop_duplicates("NomeUsuario").set_index(u.drop_duplicates("NomeUsuario")["NomeUsuario"].astype(str).str.strip().str.upper())
    fve = []
    for f in ("FVE AK.csv", "FVE JGK.csv"):
        try:
            d = pd.read_csv(CENTRAL / f, sep=";", dtype=str, encoding="utf-8")
        except UnicodeDecodeError:
            d = pd.read_csv(CENTRAL / f, sep=";", dtype=str, encoding="latin-1")
        fve.append(d[["CNPJ EMPRESA", "CPF PROMOTOR", "NOME PROMOTOR"]])
    fve = pd.concat(fve)
    fve["cnpj"] = fve["CNPJ EMPRESA"].map(digitos).str.zfill(14)
    fve["cpf"] = fve["CPF PROMOTOR"].map(digitos).str.zfill(11)
    prod = pd.read_excel(CENTRAL / "Producao.xlsx", engine="calamine",
                         usecols=["Cnpj", "NomeExecutivoLegal", "NomeSupervisor", "NomeCoordenador", "DataBase"])
    prod["cnpj"] = prod["Cnpj"].map(digitos).str.zfill(14)
    prod = prod.sort_values("DataBase")

    itens, pulados, avisos = [], [], []
    for c in consulta["chamados"]:
        num = digitos(c.get("chamado"))[-4:]
        resp = c.get("resposta_final") or {}
        concluido = str(c.get("status") or "").lower().startswith("conclu")
        if alvo and num not in alvo:
            continue
        if not concluido or not any(resp.values()):
            if alvo:
                pulados.append({"chamado": num, "motivo": "ainda não concluído ou sem resposta do Santander"})
            continue
        if num in feitos:
            pulados.append({"chamado": num, "motivo": "já disparado antes"})
            continue
        if desde_d and c.get("conclusao") and datetime.strptime(c["conclusao"][:10], "%d/%m/%Y").date() < desde_d:
            continue
        cnpj = digitos(c.get("cnpj")).zfill(14)

        consultor, sup, coord, fonte = c.get("consultor"), c.get("supervisor"), c.get("gerente"), "registro do robô"
        if not consultor:
            m = fve[fve["cnpj"] == cnpj]
            usu = u[u["CPFd"].isin(m["cpf"])] if len(m) else u.iloc[0:0]
            if len(usu):
                r = usu.iloc[0]
                consultor, sup, coord, fonte = r["NomeUsuario"], r["Nome_Supervisor"], r["Nome_Coordenador"], "CPF do promotor no FVE"
            else:
                pr = prod[prod["cnpj"] == cnpj]
                if len(pr):
                    r = pr.iloc[-1]
                    consultor, sup, coord, fonte = r["NomeExecutivoLegal"], r["NomeSupervisor"], r["NomeCoordenador"], "Produção"
        if not consultor:
            pulados.append({"chamado": num, "motivo": f"não achei consultor para o CNPJ {cnpj_fmt(cnpj)}"})
            continue
        # equipe atual pela Usuarios_Atual (fonte da verdade do funcionário)
        atual = por_nome.loc[str(consultor).strip().upper()] if str(consultor).strip().upper() in por_nome.index else None
        if atual is not None and pd.isna(atual.get("DataDesligamento")):
            sup, coord = atual["Nome_Supervisor"], atual["Nome_Coordenador"]
        itens.append({"chamado": f"#STBR-SPAR-CCPJ-{num}", "consultor": titulo(consultor), "supervisor": str(sup).strip(),
                      "coordenador": str(coord or "").strip(), "cnpj": cnpj_fmt(cnpj), "motivo": motivo(c),
                      "status": resp.get("status_proposta") or "-", "retorno": retorno(resp), "fonte_consultor": fonte})

    grupos = {}
    for it in itens:
        grupos.setdefault((it["supervisor"], it["coordenador"]), []).append(it)
    emails = []
    for (sup, coord), its in grupos.items():
        para, nomes = [], []
        for pessoa in (sup, coord):
            if not pessoa or pessoa.upper().startswith(NOMES_NUNCA):
                continue
            linha = por_nome.loc[pessoa.upper()] if pessoa.upper() in por_nome.index else None
            e = email_valido(linha["Email"]) if linha is not None else None
            if e and e not in para:
                para.append(e)
                nomes.append(titulo(pessoa).split()[0])
            elif linha is None or not e:
                avisos.append(f"sem e-mail corporativo para {pessoa} (chamados {', '.join(i['chamado'][-4:] for i in its)})")
        if not para:
            avisos.append(f"chamados {', '.join(i['chamado'][-4:] for i in its)}: nenhum destinatário válido; ficou fora")
            continue
        motivos = sorted({i["motivo"] for i in its})
        if len(its) == 1:
            i = its[0]
            assunto = f"Retorno chamado do {i['cnpj']} - {i['motivo']}"
            miolo = (f"O Santander respondeu o chamado aberto para a conta do(a) consultor(a) {i['consultor']}.\n\n"
                     f"CNPJ: {i['cnpj']}\nStatus da proposta: {i['status']}\nRetorno do banco: {i['retorno']}")
        else:
            assunto = f"Retorno chamados dos CNPJs {', '.join(i['cnpj'] for i in its)} - {' / '.join(motivos)}"
            blocos = [f"{n}) CNPJ: {i['cnpj']}\nConsultor(a): {i['consultor']}\nStatus da proposta: {i['status']}\n"
                      f"Retorno do banco: {i['retorno']}" for n, i in enumerate(its, 1)]
            miolo = f"O Santander respondeu os {len(its)} chamados abertos para as contas da equipe:\n\n" + "\n\n".join(blocos)
        saudacao = " e ".join(nomes)
        emails.append({"chamados": ", ".join(i["chamado"] for i in its), "para": "; ".join(para), "cc": CC,
                       "assunto": assunto, "corpo": f"Olá, {saudacao}!\n\n{miolo}\n\n{ASSINATURA}"})
    return {"consulta_feita_em": consulta.get("gerado_em"), "emails": emails, "itens": itens,
            "pulados": pulados, "avisos": avisos}


def gravar(res):
    hoje = f"{date.today():%Y-%m-%d}"
    base, n = f"{hoje}", 2
    while (PASTA / f"envio_{base}.json").exists():
        base, n = f"{hoje}_{n}", n + 1
    emails = res["emails"]
    (PASTA / f"envio_{base}.json").write_text(json.dumps(emails, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(PASTA / f"envio_{base}.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["chamados", "para", "cc", "assunto", "corpo"], delimiter=";")
        w.writeheader()
        w.writerows(emails)
    lis = []
    for k, e in enumerate(emails, 1):
        para = ",".join(p.strip() for p in e["para"].split(";"))
        href = f"mailto:{para}?cc={quote(e['cc'])}&amp;subject={quote(e['assunto'])}&amp;body={quote(e['corpo'])}"
        lis.append(f"<li><a href=\"{href}\">{k}. {e['assunto']}</a><br><small>Para: {e['para']} · Cc: {e['cc']}</small></li>")
    html = (f"<!doctype html><meta charset=utf-8><title>Retorno chamados {date.today():%d/%m}</title>"
            "<body style='font-family:Segoe UI;max-width:800px;margin:24px auto;line-height:1.5'>"
            f"<h2>Retorno dos chamados resolvidos ({date.today():%d/%m})</h2>"
            "<p>Clique em cada um: o e-mail abre pronto no Outlook. Confira e clique em Enviar.</p>"
            "<ol style='list-style:none;padding:0'>" + "\n".join(lis) + "</ol></body>")
    arq = PASTA / f"abrir_emails_{base}.html"
    arq.write_text(html, encoding="utf-8")
    return arq


def main(argv=None):
    ap = argparse.ArgumentParser(description="Monta o disparo de retorno dos chamados concluídos")
    ap.add_argument("--chamados", help="números separados por vírgula, ex.: 2295,2319")
    ap.add_argument("--desde", help="AAAA-MM-DD: só concluídos a partir desta data")
    ap.add_argument("--resumo")
    a = ap.parse_args(argv)
    try:
        res = montar([x for x in (a.chamados or "").split(",") if x.strip()], a.desde)
        if res["emails"]:
            res["arquivo"] = str(gravar(res))
        saida = {"ok": True, **res, "lembrete": "nada foi enviado: o Mateus abre o HTML e clica em cada e-mail"}
        codigo = 0
    except Parar as e:
        saida, codigo = {"ok": False, "parar_e_pedir": str(e)}, 2
    texto = json.dumps(saida, ensure_ascii=False, indent=2, default=str)
    if a.resumo:
        Path(a.resumo).write_text(texto, encoding="utf-8")
    print(texto)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
