# Agente Analítico AK

Chat analítico da Almeida Kruger. Especificação: https://claude.ai/artifact/7qWo9Yso5Y7tVssTkU4HvJ

Projeto separado do `Fluxo VBA Teste`: o agente só **lê** os arquivos de lá e **chama** scripts de uma lista fechada. Nada lá é alterado.

## Servidor local `ak_local` (MCP)

Fica em `servidor\`. O Artifact do chat (app desktop do Claude) chama estas ferramentas:

| Ferramenta | O que faz |
| --- | --- |
| `status_base` | Laudo do validador + veredito do auditor-base; aviso quando a base do dia não foi liberada |
| `dias_uteis` | Dias úteis entre duas datas (feriados no `config.json`) |
| `listar_conversas`, `carregar_conversa`, `salvar_conversa`, `apagar_conversa` | Conversas em `dados\conversas\<id>.json`; excluir move para `dados\excluidos` (nunca sobrescreve) |
| `listar_arquivos`, `buscar_arquivo` | Cópia (inteira ou recortada por filtro) dos arquivos do RPA, em `dados\arquivos_entregues`; CPF e nascimento saem removidos por padrão |
| `consultar_cnpj`, `contas_fora_do_sla` | Chamados do RPA + situação na Parcial2; fora do SLA = pendente há mais de 3 dias úteis desde a digitação (CANCELADO não conta) |
| `consultar_chamados_portal` | Última consulta do RPA Consulta Chamados (em aberto + concluídos desde 00:00 de hoje - N); avisa quantos `--dias` rodar quando a consulta não cobre o período |
| `pontos_criticos` | Régua das skills (gatilhoak): consultor contra o gatilho do mês de casa (Conta E GET, só M0/M1), supervisor 160/120 (Remoto 300/120), coordenador Presencial 22/15 por dias equivalentes; tudo no ritmo do mês (gatilho × DU passados ÷ DU do mês). Crítico < 50% do ritmo; experiência fora da régua; alertas de integridade |
| `listar_rotinas`, `salvar_rotina`, `apagar_rotina`, `marcar_rotina_executada` | Rotinas da aba Agendamentos em `dadosgendamentos.json` (dias, hora, pedido ao agente); avisam no sino com o agente aberto |
| `tarefas_do_pc` | Tarefas AK do Agendador do Windows (só leitura, `schtasks /query`) |
| `listar_skills`, `ler_skill` | Skills da AK em `conhecimento\` (contextoak, producaoak, usuariosak, cruzamentodiariaak, gatilhoak, fveak, textos-comparativo-fve, diaria-relatorio-ak, parcial-consolidada-ak-v2); o agente lê a skill certa antes de cada análise |
| `entregar_gerado` | Entrega (Baixar) um arquivo recém-gerado, só das pastas de saída (`pastas_entrega` do config) |
| `listar_scripts`, `rodar_script` | Só o que está em `scripts.json`; nível 3 exige `confirmado=true` e começa desabilitado |

A planilha ABERTURA DE CHAMADOS e o Outlook (e-mails, agenda, diretório) não passam pelo servidor: o Artifact lê pelo conector Microsoft 365, que só tem permissão de leitura.

## Interface (Artifact)

Fica em `interface\` (React + Tailwind + Motion, componentes do Aceternity UI). Publicada em https://claude.ai/artifact/QDrJigPUayddHFPWFVDuX7 e só funciona com o PC no app desktop do Claude (o `ak_local` é um servidor local).

```
cd interface
npm install
npm run build      # gera dist\agente-analitico-ak.html, o arquivo publicado
```

## Instalar

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## Ligar no app desktop do Claude

Em `%APPDATA%\Claude\claude_desktop_config.json`, dentro de `mcpServers`:

```json
"ak_local": {
  "command": "C:\\Users\\mateus.ferreira\\Documents\\Agente Analitico AK\\.venv\\Scripts\\python.exe",
  "args": ["C:\\Users\\mateus.ferreira\\Documents\\Agente Analitico AK\\servidor\\ak_local.py"]
}
```

Depois feche e abra o app.

## Testar

```
.venv\Scripts\python -m pytest -q testes
```

## Pastas

- `servidor\config.json`: caminhos liberados, feriados, regra do SLA.
- `servidor\scripts.json`: scripts liberados e seus níveis.
- `dados\` (fora do git): conversas, entregas, logs de scripts, laudos do validador do agente.

## Geradores (`geradores\`)

Rodam como scripts nível 2 do agente (`rodar_script`), e também direto pelo terminal:

| Gerador | Skill | O que faz |
| --- | --- | --- |
| `relatorio_diario.py` | diaria-relatorio-ak | Parte do último `Relatório Diário DD.MM.AAAA.xlsx` da pasta Claude outputs, edita o XML (sem recriar), roda as 4 validações da skill e grava ao lado, sem sobrescrever. Se algum supervisor não bater com o portal, sai com "CONFERIR" no nome e código 3. Conferido: refaz o de 23/11 idêntico (416 linhas, Por Supervisor e Por Coordenador 100%) e abre no Excel. |
| `parcial_consolidada.py` | parcial-consolidada-ak-v2 | Script validado da skill: Produção Conta PJ × FVE AK+JGK do mês, sem a lista Fora (`--fora`, obrigatória). Grava em `Downloads\Diária`. Para e pede quando falta arquivo ou o FVE veio em notação científica. |

```
.venv\Scripts\python geradoreselatorio_diario.py
.venv\Scripts\python geradores\parcial_consolidada.py --fora "C:\...\Lista Fora Novembro.xlsx"
```
