# Agente Analítico AK

Chat analítico da Almeida Kruger. Especificação: https://claude.ai/artifact/7qWo9Yso5Y7tVssTkU4HvJ

Projeto separado do `Fluxo VBA Teste`: o agente só **lê** os arquivos de lá e **chama** scripts de uma lista fechada. Nada lá é alterado.

## Servidor local `ak_local` (MCP)

Fica em `servidor\`. O Artifact do chat (app desktop do Claude) chama estas ferramentas:

| Ferramenta | O que faz |
| --- | --- |
| `status_base` | Laudo do validador + veredito do auditor-base; aviso quando a base do dia não foi liberada |
| `dias_uteis` | Dias úteis entre duas datas (feriados no `config.json`) |
| `listar_conversas`, `carregar_conversa`, `salvar_conversa`, `apagar_conversa` | Conversas em `dados\conversas\<id>.json`; apagar move para `dados\lixeira` |
| `listar_arquivos`, `buscar_arquivo` | Cópia (inteira ou recortada por filtro) dos arquivos do RPA, em `dados\arquivos_entregues`; CPF e nascimento saem removidos por padrão |
| `consultar_cnpj`, `contas_fora_do_sla` | Chamados do RPA + situação na Parcial2; fora do SLA = pendente há mais de 3 dias úteis desde a digitação (CANCELADO não conta) |
| `listar_scripts`, `rodar_script` | Só o que está em `scripts.json`; nível 3 exige `confirmado=true` e começa desabilitado |

A planilha ABERTURA DE CHAMADOS não passa pelo servidor: o Artifact lê pelo conector Microsoft 365.

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
