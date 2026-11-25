"""Entrega cópias dos arquivos do RPA. Os originais só são lidos, nunca alterados."""
import base64
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

from .erros import ErroAgente

MIME = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".html": "text/html",
}


class ErroArquivo(ErroAgente):
    pass


def _info(cfg, chave):
    if chave not in cfg.arquivos:
        raise ErroArquivo(f"arquivo {chave!r} não está na lista; use um de: {', '.join(cfg.arquivos)}")
    item = cfg.arquivos[chave]
    return item, cfg.caminho_fluxo(item["caminho"])


def _modificado(p):
    return datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")


def listar(cfg):
    saida = []
    for chave, item in cfg.arquivos.items():
        p = cfg.caminho_fluxo(item["caminho"])
        existe = p.exists()
        saida.append({
            "nome": chave,
            "descricao": item["descricao"],
            "existe": existe,
            "modificado": _modificado(p) if existe else None,
            "tamanho_mb": round(p.stat().st_size / 1048576, 2) if existe else None,
            "tem_dados_pessoais": bool(item.get("colunas_sensiveis")),
        })
    return saida


def ler_tabela(cfg, chave, colunas=None):
    item, p = _info(cfg, chave)
    if not p.exists():
        raise ErroArquivo(f"{p} não existe")
    if p.suffix.lower() == ".csv":
        sep = item.get("csv_sep", ";")
        try:
            return pd.read_csv(p, sep=sep, dtype=str, usecols=colunas, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(p, sep=sep, dtype=str, usecols=colunas, encoding="latin-1")
    return pd.read_excel(p, engine="calamine", usecols=colunas)


def _aplicar_filtros(df, filtros):
    for coluna, valor in (filtros or {}).items():
        if coluna not in df.columns:
            raise ErroArquivo(f"coluna {coluna!r} não existe; colunas: {', '.join(map(str, df.columns))}")
        texto = df[coluna].astype(str).str.strip().str.upper()
        if isinstance(valor, list):
            df = df[texto.isin([str(v).strip().upper() for v in valor])]
        else:
            df = df[texto.str.contains(str(valor).strip().upper(), regex=False, na=False)]
    return df


def buscar(cfg, chave, filtros=None, incluir_dados_pessoais=False, com_conteudo=True):
    """Copia o arquivo (ou um recorte dele) para dados\\arquivos_entregues e devolve os dados da cópia.

    filtros: {"Coluna": "texto contido"} ou {"Coluna": ["valor exato", ...]}, sem diferenciar maiúsculas.
    """
    item, origem = _info(cfg, chave)
    if not origem.exists():
        raise ErroArquivo(f"{origem} não existe")
    sensiveis = [] if incluir_dados_pessoais else item.get("colunas_sensiveis", [])
    pasta = cfg.dados / "arquivos_entregues" / f"{datetime.now():%Y-%m-%d}"
    pasta.mkdir(parents=True, exist_ok=True)
    carimbo = f"{datetime.now():%H%M%S}"
    linhas = None

    if not filtros and not sensiveis:
        if origem.stat().st_size > cfg.limite_entrega_bytes:
            raise ErroArquivo(
                f"{origem.name} tem {origem.stat().st_size / 1048576:.1f} MB, acima do limite de "
                f"{cfg.limite_entrega_bytes / 1048576:.0f} MB; peça um recorte com filtros"
            )
        destino = pasta / f"{origem.stem}_{carimbo}{origem.suffix}"
        shutil.copy2(origem, destino)
    else:
        df = _aplicar_filtros(ler_tabela(cfg, chave), filtros)
        df = df.drop(columns=[c for c in sensiveis if c in df.columns])
        linhas = len(df)
        sufixo = "_recorte" if filtros else ""
        destino = pasta / f"{origem.stem}{sufixo}_{carimbo}.xlsx"
        df.to_excel(destino, index=False)

    tamanho = destino.stat().st_size
    resposta = {
        "nome_arquivo": destino.name,
        "caminho_copia": str(destino),
        "origem": str(origem),
        "modificado_origem": _modificado(origem),
        "linhas": linhas,
        "tamanho_bytes": tamanho,
        "mime": MIME.get(destino.suffix.lower(), "application/octet-stream"),
        "dados_pessoais_removidos": [c for c in sensiveis],
    }
    if com_conteudo:
        if tamanho > cfg.limite_entrega_bytes:
            resposta["aviso"] = "cópia grande demais para ir pelo chat; está em caminho_copia"
        else:
            resposta["conteudo_base64"] = base64.b64encode(Path(destino).read_bytes()).decode("ascii")
    return resposta


def entregar_gerado(cfg, caminho):
    """Entrega um arquivo que um gerador acabou de criar (Relatório Diário, Parcial), só das pastas de entrega."""
    p = Path(caminho).resolve()
    pastas = [Path(x).resolve() for x in cfg.bruto.get("pastas_entrega", [])]
    if p.suffix.lower() not in MIME or not any(p.is_relative_to(x) for x in pastas):
        raise ErroArquivo("só entrego .xlsx/.csv/.html das pastas de saída dos geradores: " + "; ".join(map(str, pastas)))
    if not p.is_file():
        raise ErroArquivo(f"{p} não existe")
    tamanho = p.stat().st_size
    resposta = {
        "nome_arquivo": p.name, "caminho_copia": str(p), "origem": str(p), "modificado_origem": _modificado(p),
        "linhas": None, "tamanho_bytes": tamanho, "mime": MIME[p.suffix.lower()], "dados_pessoais_removidos": [],
    }
    if tamanho > cfg.limite_entrega_bytes:
        resposta["aviso"] = "arquivo grande demais para ir pelo chat; está no caminho indicado"
    else:
        resposta["conteudo_base64"] = base64.b64encode(p.read_bytes()).decode("ascii")
    return resposta
