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


# ---------- pontos críticos (régua das skills: gatilho) ----------

from nucleo import analises  # noqa: E402


@pytest.fixture
def cfg_producao(cfg):
    ent = cfg.caminho_fluxo(r"Central\Entrada")
    pd.DataFrame({
        "Matricula": [1, 2, 3, 4, 5, 6, 7],
        "NomeUsuario": ["ANA", "BIA", "CAIO", "DUDA", "EDU", "FABI", "SUP"],
        "Cargo": ["CONSULTOR"] * 6 + ["SUPERVISOR"],
        "DataAdmissao": ["2025-01-01", "2025-01-01", "2025-01-01", "2026-10-01", "2025-01-01", "2025-01-01", "2024-01-01"],
        "DataDesligamento": [None] * 7,
        "Situacao": [None, None, None, None, "FÉRIAS", "AFASTAMENTO", None],
        "Nome_Supervisor": ["SUP A", "SUP A", "SUP B", "SUP B", "SUP A", "SUP B", "SUP A"],
        "Nome_Coordenador": ["COORD"] * 7,
        "DiasTrabalhados": [14, 14, 14, 14, 7, 0, 14],
    }).to_excel(ent / "Usuarios" / "Usuarios_Atual.xlsx", index=False)
    (cfg.raiz_fluxo / "Central" / "Parcial").mkdir(parents=True, exist_ok=True)
    linhas = [  # (matricula, produto, pontos)
        (1, "CONTA_CORRENTE_PJ", 20), (1, "CREDENCIAMENTO", 10),
        (2, "CONTA_CORRENTE_PJ", 10), (2, "CREDENCIAMENTO", 10),
        (3, "CONTA_CORRENTE_PJ", 2), (3, "CONTA_CORRENTE_PJ_M2", 50),
        (6, "CONTA_CORRENTE_PJ", 5),
        (99, "CONTA_CORRENTE_PJ", 8),
    ]
    pd.DataFrame({
        "Matricula": [m for m, _, _ in linhas],
        "NomeExecutivoLegal": ["X" if m != 99 else "ORFAO" for m, _, _ in linhas],
        "NomeSupervisor": ["SUP VELHO" if m == 99 else "?" for m, _, _ in linhas],
        "NomeCoordenador": ["COORD VELHO" if m == 99 else "?" for m, _, _ in linhas],
        "Tipo_Consultor": ["Presencial"] * len(linhas),
        "Produto": [pr for _, pr, _ in linhas],
        "Pontos": [pt for _, _, pt in linhas],
        "DataBase": ["2026-11-20"] * len(linhas),
    }).to_excel(cfg.raiz_fluxo / "Central" / "Parcial" / "Producao do Mes.xlsx", index=False)
    return cfg


def test_pontos_criticos_pela_regua_do_gatilho(cfg_producao):
    # 24/11: 14 de 19 DU passados → ritmo do consultor 4º mês+ = 16×14/19 ≈ 11,8 Conta e 12×14/19 ≈ 8,8 GET
    r = analises.pontos_criticos(cfg_producao, coordenador="COORD", hoje=HOJE)
    assert (r["du_passados"], r["du_mes"]) == (14, 19)
    eq = {e["supervisor"]: e for e in r["equipes"]}
    a, b = eq["SUP A"], eq["SUP B"]
    # ANA 20/10 no ritmo; BIA 10/10 → 85% em Conta = atenção; EDU de férias e zerado = crítico, com selo
    assert a["consultores_no_ritmo"] == 1 and a["consultores_atencao"] == 1
    assert len(a["consultores_criticos"]) == 1 and "EDU" in a["consultores_criticos"][0] and "férias" in a["consultores_criticos"][0]
    # CAIO: M2 não conta → 2 de Conta = crítico; DUDA tem 54 dias = experiência, fora da régua
    assert len(b["consultores_criticos"]) == 1 and b["consultores_criticos"][0].startswith("CAIO")
    assert b["em_experiencia"] == ["DUDA (0/0)"]
    # supervisor: 160/120 absoluto, só M0/M1 → SUP A tem 30/20 = crítico
    assert a["gatilho"] == "160/120" and a["faixa"] == "critico"
    assert r["resumo"]["em_experiencia_fora_da_regua"] == 1
    assert r["alertas"]["producao_em_licenca"] == ["FABI"]


def test_pontos_criticos_supervisao_sem_ativos_e_orfao(cfg_producao):
    r = analises.pontos_criticos(cfg_producao, hoje=HOJE)
    assert {e["supervisor"] for e in r["equipes"]} == {"SUP A", "SUP B"}
    assert r["equipes_sem_ativos"] == [{"coordenador": "COORD VELHO", "supervisor": "SUP VELHO", "conta": 8.0, "get": 0.0}]
    assert r["alertas"]["matricula_orfa_com_producao"] == {"total": 1, "primeiros": ["ORFAO"]}


def test_pontos_criticos_filtro_sem_resultado(cfg_producao):
    with pytest.raises(Exception, match="nenhuma equipe"):
        analises.pontos_criticos(cfg_producao, coordenador="NINGUEM", hoje=HOJE)


# ---------- rotinas ----------

from nucleo import rotinas  # noqa: E402


def test_rotina_cria_edita_marca_e_apaga(cfg):
    r = rotinas.salvar(cfg, {"nome": "Chamados", "pedido": "Consulte o portal --dias 1", "hora": "10:00",
                             "dias": ["sex", "seg", "xyz"]})
    assert r["dias"] == ["seg", "sex"] and r["ativa"] and r["ultima_execucao"] is None
    r2 = rotinas.salvar(cfg, {**r, "hora": "11:30", "ativa": False})
    assert r2["id"] == r["id"] and r2["hora"] == "11:30" and not r2["ativa"]
    assert rotinas.marcar_executada(cfg, r["id"])["ultima_execucao"]
    assert len(rotinas.listar(cfg)) == 1
    rotinas.apagar(cfg, r["id"])
    assert rotinas.listar(cfg) == []


@pytest.mark.parametrize("ruim", [
    {"nome": "", "pedido": "x", "hora": "10:00", "dias": ["seg"]},
    {"nome": "a", "pedido": "x", "hora": "25:00", "dias": ["seg"]},
    {"nome": "a", "pedido": "x", "hora": "10:00", "dias": []},
])
def test_rotina_invalida_e_recusada(cfg, ruim):
    with pytest.raises(rotinas.ErroAgente):
        rotinas.salvar(cfg, ruim)


def test_tarefas_do_pc_le_o_agendador():
    tarefas = rotinas.tarefas_do_pc()
    assert isinstance(tarefas, list)
    assert all(t["nome"].startswith("AK") for t in tarefas)


# ---------- conhecimento ----------

from nucleo import conhecimento  # noqa: E402


def test_skills_listadas_com_descricao_e_leitura():
    itens = {i["nome"]: i["descricao"] for i in conhecimento.listar()}
    assert {"contextoak", "producaoak", "usuariosak", "gatilhoak", "fveak",
            "diaria-relatorio-ak", "parcial-consolidada-ak-v2"} <= set(itens)
    assert "Parcial Consolidada" in itens["parcial-consolidada-ak-v2"]
    assert "Almeida Kruger" in itens["contextoak"]
    texto = conhecimento.ler("gatilhoak")
    assert "Plano de Ação" in texto and len(texto) < 28_000
    with pytest.raises(conhecimento.ErroAgente):
        conhecimento.ler("../config")


def test_remoto_brasil_usa_gatilho_do_presencial():
    assert analises._gatilho_consultor("Remoto_Brasil", 5) == (16, 12)
    assert analises._gatilho_consultor("Remoto", 5) == (20, 8)
    assert analises._gatilho_consultor("Presencial", 1) == (12, 4)
    assert analises._gatilho_consultor("Remoto", 2) == (16, 6)


# ---------- geradores ----------

def test_script_do_projeto_resolve_caminho_e_exige_lista_fora():
    c = Config()
    _, script, comando = scripts.montar_comando(c, "relatorio_diario")
    assert script.name == "relatorio_diario.py" and script.parent.name == "geradores" and script.exists()
    with pytest.raises(scripts.ErroScript, match="exige --fora"):
        scripts.montar_comando(c, "parcial_consolidada")
    ok = r"C:\Users\mateus.ferreira\Downloads\Diária\Lista Fora Novembro.xlsx"
    assert scripts.montar_comando(c, "parcial_consolidada", {"--fora": ok})[2][-1] == ok
    for ruim in (r"C:\Windows\x.xlsx", r"C:\Users\mateus.ferreira\Downloads\x.exe"):
        with pytest.raises(scripts.ErroScript):
            scripts.montar_comando(c, "parcial_consolidada", {"--fora": ruim})


def test_entregar_gerado_so_das_pastas_de_saida(cfg, tmp_path):
    saida = tmp_path / "saida"
    saida.mkdir()
    (saida / "Relatório Diário 01.12.2026.xlsx").write_bytes(b"PK teste")
    cfg.bruto["pastas_entrega"] = [str(saida)]
    r = arquivos.entregar_gerado(cfg, str(saida / "Relatório Diário 01.12.2026.xlsx"))
    assert r["nome_arquivo"].startswith("Relatório Diário") and r["conteudo_base64"]
    for ruim in (str(tmp_path / "fora.xlsx"), str(saida / ".." / "fora.xlsx"), str(saida / "x.exe")):
        with pytest.raises(arquivos.ErroArquivo):
            arquivos.entregar_gerado(cfg, ruim)


BACKUP_23_11 = Path(r"C:\Users\mateus.ferreira\Documents\Fluxo VBA Teste\Central\backups\2026-11-25_084452\Diaria Comparativo")
RELATORIO_23_11 = Path(r"C:\Users\mateus.ferreira\Documents\Relatório Diária Atualizado\Comparativo\Claude outputs\Relatório Diário 23.11.2026.xlsx")


@pytest.mark.skipif(not (BACKUP_23_11.exists() and RELATORIO_23_11.exists()), reason="base de 23/11 não disponível")
def test_relatorio_diario_reproduz_o_de_23_11(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "geradores"))
    import relatorio_diario as rd
    codigo = rd.main(["--anterior", str(RELATORIO_23_11), "--producao", str(BACKUP_23_11 / "Producao.xlsx"),
                      "--usuarios", str(BACKUP_23_11 / "Usuarios" / "Usuarios_Atual.xlsx"),
                      "--saida", str(tmp_path), "--resumo", str(tmp_path / "r.json")])
    r = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert codigo == 0 and r["ok"] and r["linhas"] == 416 and r["pontos_digitados"] == 21990.5
    novo = pd.read_excel(r["arquivo"], sheet_name="Conta PJ - Consultor", engine="calamine", header=None)
    orig = pd.read_excel(RELATORIO_23_11, sheet_name="Conta PJ - Consultor", engine="calamine", header=None)
    assert novo.fillna("").astype(str).equals(orig.fillna("").astype(str))
