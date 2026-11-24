import base64
import io
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "servidor"))

from nucleo import arquivos, base_do_dia, chamados, conversas, scripts  # noqa: E402
from nucleo.config import Config  # noqa: E402

HOJE = date(2026, 11, 24)


@pytest.fixture
def cfg(tmp_path):
    fluxo = tmp_path / "fluxo"
    (fluxo / "Central" / "laudos").mkdir(parents=True)
    (fluxo / "Central" / "auditorias").mkdir(parents=True)
    (fluxo / "Central" / "Entrada" / "Usuarios").mkdir(parents=True)
    (fluxo / "RPA Chamados SLA").mkdir(parents=True)

    (fluxo / "Central" / "laudos" / "2026-11-24_085757.json").write_text(
        json.dumps({"status": "APROVADO", "data_referencia": "2026-11-24"}), encoding="utf-8")
    pd.DataFrame({
        "Matricula": [1, 2], "NomeUsuario": ["ANA", "BRUNO"], "CPF": ["111", "222"],
        "Data_Nascimento": ["2000-01-01", "1990-01-01"], "Nome_Supervisor": ["ARAGON", "SORAYA"],
    }).to_excel(fluxo / "Central" / "Entrada" / "Usuarios" / "Usuarios_Atual.xlsx", index=False)
    pd.DataFrame({
        "Cnpj": [1694030000108, 48582672000189, 11111111000111],
        "RazaoSocial": ["ZERO A ESQUERDA", "COM CHAMADO", "RECENTE"],
        "NomeExecutivoLegal": ["C1", "C2", "C3"], "NomeSupervisor": ["SUP A", "SUP A", "SUP B"],
        "NomeCoordenador": ["ARAGON", "ARAGON", "LEANDRO"], "Tipo_Consultor": ["Presencial"] * 3,
        # 17/11 → 24/11 = 5 DU (20/11 é feriado); 21/11 sábado → 24/11 = 2 DU
        "DataDigitacao": ["2026-11-17 10:00", "2026-11-17 11:00", "2026-11-21 09:00"],
        "StatusLink": ["Aguardando Liberacao", "Em Analise", "Aguardando Liberacao"],
        "DataAberturaConta": [None, None, None], "Status": ["DIGITADO"] * 3,
    }).to_excel(fluxo / "Central" / "Entrada" / "Parcial2.xlsx", index=False)
    (fluxo / "RPA Chamados SLA" / "chamados_abertos.csv").write_text(
        "cnpj;chamado;aberto_em;gerente;consultor;supervisor;status;data_status\n"
        "48582672000189;#STBR-SPAR-CCPJ-2209;04/11/2026 16:44;ARAGON;C2;SUP A;Em Analise;05/03\n",
        encoding="utf-8")
    (fluxo / "eco.py").write_text("import sys; print('ok', *sys.argv[1:])", encoding="utf-8")

    c = Config(dados=tmp_path / "dados", raiz_fluxo=fluxo)
    c.bruto["arquivos"]["producao"]["caminho"] = "Central\\Entrada\\Parcial2.xlsx"
    c.scripts = {
        "eco": {"descricao": "teste", "caminho": "eco.py", "nivel": 1, "args_fixos": ["--x"],
                "args_opcoes": {"--cnpj": r"^\d{14}$"}},
        "externo": {"descricao": "teste", "caminho": "eco.py", "nivel": 3, "args_opcoes": {}},
        "desligado": {"descricao": "teste", "caminho": "eco.py", "nivel": 1, "habilitado": False},
    }
    return c


# ---------- conversas ----------

def test_conversa_salva_carrega_lista_e_vai_para_excluidos(cfg):
    id_ = conversas.salvar(cfg, {"titulo": "Zerados", "mensagens": [{"papel": "usuario", "texto": "oi"}]})
    assert conversas.carregar(cfg, id_)["titulo"] == "Zerados"
    assert [c["id"] for c in conversas.listar(cfg)] == [id_]
    conversas.apagar(cfg, id_)
    assert conversas.listar(cfg) == []
    assert (cfg.dados / "excluidos" / f"{id_}.json").exists()


@pytest.mark.parametrize("ruim", ["../../x", "C:\\Windows\\a", "2026-11-24_xyz"])
def test_conversa_recusa_id_fora_do_formato(cfg, ruim):
    with pytest.raises(conversas.ErroConversa):
        conversas.carregar(cfg, ruim)


# ---------- arquivos ----------

def test_usuarios_sai_sem_cpf_e_nascimento_por_padrao(cfg):
    r = arquivos.buscar(cfg, "usuarios_atual")
    df = pd.read_excel(io.BytesIO(base64.b64decode(r["conteudo_base64"])), engine="calamine")
    assert "CPF" not in df.columns and "Data_Nascimento" not in df.columns
    assert set(r["dados_pessoais_removidos"]) >= {"CPF", "Data_Nascimento"}


def test_usuarios_com_dados_pessoais_quando_pedido(cfg):
    r = arquivos.buscar(cfg, "usuarios_atual", incluir_dados_pessoais=True)
    df = pd.read_excel(r["caminho_copia"], engine="calamine")
    assert "CPF" in df.columns


def test_recorte_por_filtro(cfg):
    r = arquivos.buscar(cfg, "usuarios_atual", filtros={"Nome_Supervisor": "arag"})
    assert r["linhas"] == 1


def test_arquivo_fora_da_lista_e_coluna_inexistente_sao_recusados(cfg):
    with pytest.raises(arquivos.ErroArquivo):
        arquivos.buscar(cfg, "C:\\Windows\\win.ini")
    with pytest.raises(arquivos.ErroArquivo):
        arquivos.buscar(cfg, "usuarios_atual", filtros={"NaoExiste": "x"})


def test_arquivo_grande_sem_filtro_e_recusado(cfg):
    cfg.bruto["limite_entrega_mb"] = 0.000001
    with pytest.raises(arquivos.ErroArquivo, match="recorte"):
        arquivos.buscar(cfg, "producao")


def test_original_nao_e_alterado(cfg):
    origem = cfg.caminho_fluxo(cfg.arquivos["usuarios_atual"]["caminho"])
    antes = (origem.stat().st_mtime, origem.read_bytes())
    arquivos.buscar(cfg, "usuarios_atual", filtros={"Nome_Supervisor": "x"})
    assert (origem.stat().st_mtime, origem.read_bytes()) == antes


# ---------- base do dia ----------

def test_status_base_liberada_e_avisos(cfg):
    assert base_do_dia.status(cfg, HOJE)["liberada"] is True
    r = base_do_dia.status(cfg, date(2026, 11, 25))
    assert r["liberada"] is False and "2026-11-24" in r["aviso"]
    (cfg.caminho_fluxo("Central\\auditorias") / "2026-11-24_090000.json").write_text(
        json.dumps({"registrado_em": "2026-11-24T09:00:00", "veredito": "SEGURAR"}), encoding="utf-8")
    assert base_do_dia.status(cfg, HOJE)["liberada"] is False


def test_dias_uteis_pula_fim_de_semana_e_feriado(cfg):
    assert base_do_dia.dias_uteis_entre(cfg, date(2026, 11, 17), HOJE) == 4  # 18, 19, 23, 24 (20 feriado)
    assert base_do_dia.dias_uteis_entre(cfg, date(2026, 11, 21), HOJE) == 2  # 23, 24


# ---------- chamados ----------

def test_consultar_cnpj_recupera_zero_a_esquerda_e_marca_sla(cfg):
    r = chamados.consultar_cnpj(cfg, "01.694.030/0001-08", hoje=HOJE)
    assert r["cnpj"] == "01694030000108"
    assert r["propostas_parcial2"][0]["fora_do_sla"] is True
    assert r["chamados_rpa"] == []


def test_contas_fora_do_sla(cfg):
    r = chamados.contas_fora_do_sla(cfg, hoje=HOJE)
    assert {c["cnpj"]: c["tem_chamado_rpa"] for c in r["contas"]} == {
        "01694030000108": False, "48582672000189": True}
    assert r["sem_chamado_rpa"] == 1
    assert chamados.contas_fora_do_sla(cfg, coordenador="leandro", hoje=HOJE)["total"] == 0


# ---------- scripts ----------

def test_script_liberado_roda_e_grava_log(cfg):
    r = scripts.rodar(cfg, "eco", {"--cnpj": "01694030000108"})
    assert r["ok"] and "ok --x --cnpj 01694030000108" in r["saida"]
    assert Path(r["log"]).exists()


@pytest.mark.parametrize("nome,opcoes", [
    ("nao_existe", None),
    ("desligado", None),
    ("eco", {"--enviar": "1"}),
    ("eco", {"--cnpj": "123; del *"}),
])
def test_script_recusado(cfg, nome, opcoes):
    with pytest.raises(scripts.ErroScript):
        scripts.rodar(cfg, nome, opcoes)


def test_nivel_3_sem_aval_nao_roda(cfg):
    r = scripts.rodar(cfg, "externo")
    assert r["executado"] is False and r["precisa_aval"] is True
    assert list((cfg.dados / "logs").glob("*")) == []


def test_excluir_duas_vezes_o_mesmo_id_nao_sobrescreve(cfg):
    id_ = conversas.salvar(cfg, {"titulo": "A"})
    conversas.apagar(cfg, id_)
    conversas.salvar(cfg, {"id": id_, "titulo": "B"})
    conversas.apagar(cfg, id_)
    assert len(list((cfg.dados / "excluidos").glob(f"{id_}*.json"))) == 2


# ---------- consulta no portal ----------

def _consulta(cfg, gerado="24/11/2026 16:14", desde="22/11/2026"):
    chamados_ = [
        {"chamado": "#A", "cnpj": "35643897000156", "status": "Concluído", "conclusao": "24/11/2026 12:35",
         "resposta_final": {"parecer": "Proposta resetada", "causa_raiz": "Erro sistêmico", "sla_atuacao": "."}},
        {"chamado": "#B", "cnpj": "69469815000110", "status": "Concluído", "conclusao": "22/11/2026 00:10"},
        {"chamado": "#C", "cnpj": "01694030000108", "status": "Em andamento", "conclusao": None},
    ]
    arq = cfg.dados / "consulta_chamados" / "ultima_consulta.json"
    arq.write_text(json.dumps({"gerado_em": gerado, "filtro": {"concluidos_desde": desde},
                               "totais": {}, "chamados": chamados_}), encoding="utf-8")


def test_portal_sem_consulta_pede_para_rodar_com_os_dias_certos(cfg):
    r = chamados.consultar_portal(cfg, desde="2026-11-22", hoje=HOJE)
    assert r["precisa_rodar"] and r["dias_sugeridos"] == 2


def test_portal_janela_comeca_a_meia_noite(cfg):
    _consulta(cfg)  # --dias 2 em 24/11 cobre desde 22/11 00:00
    r = chamados.consultar_portal(cfg, desde="2026-11-22", hoje=HOJE)
    assert not r["precisa_rodar"]
    assert {c["chamado"] for c in r["chamados"]} == {"#A", "#B", "#C"}  # #B concluído 22/11 00:10 entra
    r = chamados.consultar_portal(cfg, desde="2026-11-23", status="concluido", hoje=HOJE)
    assert [c["chamado"] for c in r["chamados"]] == ["#A"]


def test_portal_pede_mais_dias_quando_a_consulta_nao_cobre(cfg):
    _consulta(cfg)
    r = chamados.consultar_portal(cfg, desde="2026-11-20", hoje=HOJE)
    assert r["precisa_rodar"] and r["dias_sugeridos"] == 4


def test_portal_consulta_de_outro_dia_pede_para_rodar(cfg):
    _consulta(cfg, gerado="23/11/2026 09:00", desde="21/11/2026")
    r = chamados.consultar_portal(cfg, hoje=HOJE)
    assert r["precisa_rodar"] and r["dias_sugeridos"] == 7


def test_portal_filtro_por_cnpj_e_data_invalida(cfg):
    _consulta(cfg)
    r = chamados.consultar_portal(cfg, cnpj="01.694.030/0001-08", hoje=HOJE)
    assert [c["chamado"] for c in r["chamados"]] == ["#C"]
    with pytest.raises(Exception, match="AAAA-MM-DD"):
        chamados.consultar_portal(cfg, desde="22/11", hoje=HOJE)


def test_script_de_consulta_monta_saida_na_pasta_do_agente():
    c = Config()
    _, _, comando = scripts.montar_comando(c, "chamados_consultar", {"--dias": "2"})
    assert comando[-2:] == ["--dias", "2"]
    assert comando[comando.index("--saida") + 1].endswith(r"consulta_chamados\ultima_consulta.json")
    with pytest.raises(scripts.ErroScript):
        scripts.montar_comando(c, "chamados_consultar", {"--dias": "61"})


def test_portal_traz_resposta_dos_concluidos_sem_campos_vazios(cfg):
    _consulta(cfg)
    r = chamados.consultar_portal(cfg, cnpj="35643897000156", hoje=HOJE)
    assert r["chamados"][0]["resposta_final"] == {"parecer": "Proposta resetada", "causa_raiz": "Erro sistêmico"}
    assert r["totais"]["concluidos_com_resposta"] == 1


def test_portal_consulta_da_versao_antiga_pede_para_rodar(cfg):
    arq = cfg.dados / "consulta_chamados" / "ultima_consulta.json"
    arq.write_text(json.dumps({"gerado_em": "24/11/2026 16:20", "filtro": {"concluidos_desde": "22/11/2026"},
                               "chamados": [{"chamado": "#X", "status": "Concluído"}]}), encoding="utf-8")
    r = chamados.consultar_portal(cfg, hoje=HOJE)
    assert r["precisa_rodar"] and "versão antiga" in r["motivo"]
