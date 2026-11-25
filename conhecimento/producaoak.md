---
name: producaoak
description: >
  Use esta skill sempre que o usuário mencionar a planilha de produção, o arquivo
  Producao, ou qualquer análise que envolva vendas, CNPJs, contas abertas, ativações,
  credenciamentos, produtos, segmentos, status de contas, pendências, cancelamentos
  ou métricas de consultores, supervisores e coordenadores. Use em conjunto com a
  skill UsuariosAK quando houver cruzamento com a planilha de funcionários.
---

# Skill: Planilha de Produção (Producao)

Esta skill define como interpretar e processar a planilha de produção da empresa.

---

## Arquivo

**Nome do arquivo:** `Producao` (formato `.xlsx`)

Esta planilha contém todos os registros de vendas e contas da empresa.

---


## Colunas Relevantes

| Coluna | Descrição |
|---|---|
| `CNPJ` | Identificador da conta — usado principalmente para contagem |
| `Matricula` | Matrícula de quem vendeu (geralmente consultor, mas pode ser supervisor ou coordenador) |
| `NomeExecutivoLegal` | Nome de quem vendeu |
| `NomeSupervisor` | Nome do supervisor responsável |
| `NomeCoordenador` | Nome do coordenador responsável |
| `Tipo_Consultor` | Indica se o registro é do projeto **Presencial** ou **Remoto** (valores na planilha vêm em CamelCase: `Presencial` / `Remoto`, não em UPPERCASE) |
| `DataDigitacao` | Data em que o CNPJ foi inserido no sistema |
| `DataBase` | Data de referência do mês de análise — sempre dentro do mês analisado |
| `DataAberturaConta` | Data em que a conta foi aberta |
| `DataCredenciamento` | Data em que o credenciamento ocorreu |
| `Segmento` | Tipo do cliente |
| `Produto` | Tipo do produto vendido |
| `Status` | Situação atual do registro |
| `Substatus` | Detalhe da situação — usado para determinar abertura e ativação |

---

## Projetos

A coluna `Tipo_Consultor` já identifica o projeto diretamente:

- **`Presencial`** — projeto presencial (todos exceto Mariana Kruger)
- **`Remoto`** — projeto remoto (equipe da Mariana Kruger)

> Atenção: na planilha os valores vêm como `Presencial` e `Remoto` (CamelCase), **não** em maiúsculas. Em filtros Python isso importa: `df['Tipo_Consultor'] == 'Presencial'` funciona, `== 'PRESENCIAL'` retorna vazio.

> Sempre separar Presencial e Remoto em qualquer análise. Nunca misturar, salvo instrução explícita.

---

## Segmentos

| Valor | Descrição |
|---|---|
| `CLIENTE_MEI` | Microempreendedor individual |
| `EMPRESA_DIGITAL` | Empresa digital |
| `DEMAIS_SEGMENTOS_PJ` | Demais segmentos — **o mais lucrativo, sempre destacar** |

---

## Produtos

Os produtos são **sempre** separados em dois grupos: **M0/M1** e **M2**. Nunca misturar esses grupos em uma análise.

### Apelidos comuns (uso interno)

Quando o usuário falar de forma abreviada, traduzir assim:

| Apelido | Produto na planilha |
|---|---|
| **Conta** | `CONTA_CORRENTE_PJ` |
| **GET** (referência à GetNet) | `CREDENCIAMENTO` |

Esses apelidos aparecem com frequência em regras de gatilho, metas e campanhas.

### Grupo M0/M1 — produção do mês

| Produto | Descrição |
|---|---|
| `CONTA_CORRENTE_PJ` | Conta corrente do mês (apelido: **Conta**) |
| `CREDENCIAMENTO` | Credenciamento do mês (apelido: **GET**) |

### Grupo M2 — reavaliação 2 meses após abertura

| Produto | Descrição |
|---|---|
| `CONTA_CORRENTE_PJ_M2` | Reavaliação da conta corrente |
| `CREDENCIAMENTO_M2` | Reavaliação do credenciamento |

**Regra do M2:**
- O M2 surge **2 meses-calendário após a `DataAberturaConta`** do registro original — e essa âncora vale para **os dois produtos**: tanto `CONTA_CORRENTE_PJ_M2` quanto `CREDENCIAMENTO_M2` nascem contados a partir da **mesma** `DataAberturaConta`, não de datas separadas
- A `DataAberturaConta` é a mesma nos registros original e M2 (é o que amarra o M2 ao seu M0/M1 de origem)
- São 2 meses-calendário, não 60 dias: abriu em 26/junho → reaparece em agosto
- O objetivo do M2 é garantir a **ativação** (reativação) da conta
- `CONTA_CORRENTE_PJ_M2` → **sempre existe** para toda conta aberta
- `CREDENCIAMENTO_M2` → **só existe se a conta foi credenciada**
- Portanto, M2 de conta e M2 de credenciamento **não aparecem sempre juntos**

**Separação obrigatória:** Toda análise deve apresentar M0/M1 e M2 separadamente — nunca somar ou misturar os dois grupos, salvo instrução explícita do usuário.

**Relação Conta x Credenciamento (dentro do mesmo grupo):** Para existir um credenciamento, precisa existir uma conta. Logo, um mesmo CNPJ pode aparecer com dois produtos dentro do M0/M1 (`CONTA_CORRENTE_PJ` e `CREDENCIAMENTO`) ou dentro do M2 (`CONTA_CORRENTE_PJ_M2` e `CREDENCIAMENTO_M2`).

---

## Status

O `Status` conta a **história do ciclo da conta**. Ele não é um rótulo estático: muda conforme o que acontece (ou não acontece) com a conta ao longo dos meses. E — ponto crítico — o comportamento da `DataBase` depende de qual status a conta assume.

| Valor | O que significa |
|---|---|
| `DIGITADO` | Conta digitada no Portal e ainda **em andamento** neste mês. Foi lançada mas o ciclo ainda não se resolveu (não abriu, ou abriu mas ainda está no mês corrente) |
| `REPESCAGEM` | Conta que **abriu no mês passado e ainda não ativou**. Está sendo "repescada" neste mês para tentar a ativação |
| `VALIDADO` | **Status final** — a conta completou o ciclo (abriu e ativou) e o banco já mandou o fechamento. Números congelados. É onde ficam os pontos efetivamente conquistados |
| `CANCELADO` | Conta cancelada |
| `ANALISE_CANCELAMENTO` | Conta em processo de cancelamento |

### O ciclo passo a passo (exemplo: digitada em Agosto)

Suponha que hoje é **Agosto** e um consultor digita a conta no Portal AK.

1. **Nasce como `DIGITADO`.** A `DataBase` fica em Agosto. A conta está em andamento.

2. **Virou o mês (Setembro) e nada aconteceu** (não abriu, não ativou, não cancelou): o status **continua `DIGITADO`** e apenas a **`DataBase` é atualizada para o mês atual (Setembro)**. A conta segue na fila até resolver.

3. **A conta abriu em Agosto mas não ativou:** em Setembro ela aparece como **`REPESCAGEM`** — e a **`DataBase` também é atualizada** para o mês atual. `REPESCAGEM` é, por definição, **tudo que abriu no mês anterior e não ativou**. Ela fica sendo "repescada" para tentar a ativação.

4. **A conta abriu E ativou dentro de Agosto:** assim que o **banco envia o fechamento**, o status muda para **`VALIDADO`** e a **`DataBase` PERMANECE em Agosto** — porque digitação, abertura e ativação aconteceram todas no mesmo mês, então o ciclo M0/M1 se encerrou ali. Diferente de `DIGITADO` e `REPESCAGEM`, o `VALIDADO` **não rola a `DataBase`**: ele congela no mês em que o ciclo se completou.

5. **Dois meses depois**, essa mesma conta reaparece como **M2** (`CONTA_CORRENTE_PJ_M2`, e `CREDENCIAMENTO_M2` se houve credenciamento) para fechar o ciclo 100% com a reativação.

> **Comportamento da `DataBase` por status — resumo:**
> - `DIGITADO` → `DataBase` **rola** para o mês atual a cada virada de mês (ciclo ainda aberto).
> - `REPESCAGEM` → `DataBase` **rola** para o mês atual (ciclo ainda aberto, aguardando ativação).
> - `VALIDADO` → `DataBase` **permanece** no mês em que a conta abriu e ativou (ciclo encerrado, congela).

> ⚠️ **Não existe coluna de data de ativação.** A produção não registra "quando ativou" como um campo. O que indica ativação é o `Substatus` (ex.: `CONTA ATIVA`), e o desfecho do ciclo é lido pelo `Status` + `DataBase`, não por uma data de ativação — ela não existe na planilha.

**Regra padrão de análise:**
```
Quero contar produção / resultados?  → filtrar VALIDADO + DIGITADO + REPESCAGEM
Quero saber cancelamentos?           → filtrar CANCELADO + ANALISE_CANCELAMENTO
```

> ⚠️ `VALIDADO` é o estado final de um registro válido. Em qualquer mês já encerrado (não o mês corrente), a esmagadora maioria dos registros aparece como `VALIDADO` — é ali que estão os pontos efetivamente conquistados. Não esquecer de incluí-lo ao contar produção; filtrar apenas `DIGITADO + REPESCAGEM` descarta a maior parte da produção dos meses fechados.

> ⚠️ Produtos do grupo **M2** (`CONTA_CORRENTE_PJ_M2` e `CREDENCIAMENTO_M2`) **nunca têm REPESCAGEM** — podem ter VALIDADO, DIGITADO, CANCELADO e ANALISE_CANCELAMENTO. Apenas produtos do grupo **M0/M1** podem ter REPESCAGEM.

---

## Comparativo entre Meses — qual data usar

Existe uma distinção importante entre **em que mês o CNPJ está sendo analisado** e **quando o evento de fato aconteceu**:

- A `DataBase` define o **mês de análise** do CNPJ no funil (em qual mês aquele registro está sendo acompanhado). É a data padrão para dizer a que mês um registro pertence.
- Mas quando a pergunta é um **comparativo de eventos entre meses** — "quantas contas foram abertas neste mês contra o mês passado?", ou o mesmo para credenciamento — a data correta é a **data exata do evento**, não a `DataBase`.

### Regra do comparativo

| O que se compara | Data a usar | Filtro em `Produto` |
|---|---|---|
| **Contas abertas** por mês | `DataAberturaConta` (data exata da abertura da conta) | `CONTA_CORRENTE_PJ` |
| **Credenciamentos** por mês | `DataCredenciamento` (data exata do credenciamento) | `CREDENCIAMENTO` |

- Cada linha de produto vai na **sua própria data exata** e no **seu próprio produto** — Conta com `DataAberturaConta` + `CONTA_CORRENTE_PJ`; Credenciamento com `DataCredenciamento` + `CREDENCIAMENTO`. Nunca cruzar a data de um com o produto do outro.
- Como sempre, **Conta e Credenciamento são apresentados separadamente** — são naturezas diferentes, não somar na mesma régua.
- Para agrupar por mês, usar **mês/ano** da data exata (ex.: contas abertas em junho = registros de `CONTA_CORRENTE_PJ` cuja `DataAberturaConta` cai em junho).

> ⚠️ Não usar `DataBase` nem `DataDigitacao` para comparativo de contas abertas ou de credenciamentos entre meses. `DataBase` diz em que mês o CNPJ está sendo acompanhado; ela **não** é a data em que a conta abriu. Para "quando abriu de fato", só `DataAberturaConta`; para "quando credenciou de fato", só `DataCredenciamento`.

---

## Substatus — Abertura e Ativação

### Produto: CONTA_CORRENTE_PJ

**Conta aberta** (inclui pendentes e ativas):
```
PENDENTE ATIVAÇÃO DA CONTA PJ
PENDENTE ATIVAÇÃO DA CONTA PJ (JA HOUVE MOVIMENTAÇÃO)
CONTA ATIVA
```

**Conta ativa especificamente:**
```
CONTA ATIVA
```

> Uma conta ativa também é uma conta aberta — o fluxo é: abre primeiro, depois ativa.

### Produto: CREDENCIAMENTO

> Credenciamento não tem "conta aberta" — a conta já existe. Contar apenas pendentes e ativos.

**Pendente de ativação:**
```
PENDENTE INSTALAÇÃO MAQUINA GETNET
PENDENTE ATIVAÇÃO DO CREDENCIAMENTO
PENDENTE ATIVAÇÃO DO CREDENCIAMENTO (JA HOUVE MOVIMENTAÇÃO)
```

**Credenciamento ativo:**
```
CREDENCIAMENTO GETNET ATIVO
```

### Outros Substatus que aparecem na planilha

Além dos substatus de abertura/ativação acima, a planilha contém outros valores que **não** se enquadram na contagem padrão de "conta aberta" nem "ativa". Devem ser ignorados nas contagens de funil padrão, salvo análise específica:

- `PENDENTE ABERTURA` — conta digitada mas ainda não aberta no banco
- `LINK EXPIRADO 30 DIAS` — link de abertura caducou sem o cliente concluir
- `CONTA DERIVADA`, `CONTA ABERTA DERIVADA` — conta derivada de outra conta existente
- `CONTA ABERTA E ENCERRADA MÊS` — conta aberta e fechada no mesmo período
- `CONTA ANTIGA ESTÁ ENCERRADA HÁ MENOS DE 180 DIAS`
- `CONTA ANTIGA ESTÁ INATIVA HÁ MENOS DE 180 DIAS`
- `CONTA ABERTA SEM RASTRO PORTAL FVE`
- `CLIENTE POSSUI CONTA ANTIGA E ATIVA`
- `CREDENCIAMENTO CANCELADO` — credenciamento que foi cancelado (não conta como pendente nem ativo)
- `(vazio / NaN)` — registros sem substatus, geralmente DIGITADO recente

> Regra prática: se um substatus não está na lista de "Conta aberta", "Conta ativa", "Pendente de credenciamento" ou "Credenciamento ativo", ele **não entra** nas métricas de funil. Pode ser citado em análises pontuais de qualidade ou de cancelamento.

---

## Regras Gerais de Análise

- **Status padrão:** Para contar produção, filtrar VALIDADO + DIGITADO + REPESCAGEM (exceto cancelamentos, ou M2 que só tem DIGITADO/VALIDADO). Meses fechados são majoritariamente VALIDADO
- **Produtos independentes:** Conta Corrente PJ e Credenciamento são sempre analisados separadamente, mesmo sendo o mesmo CNPJ
- **CNPJ:** Usado para contagem — um mesmo CNPJ pode aparecer mais de uma vez com produtos diferentes
- **DataBase:** Referência do mês de análise do CNPJ no funil — pode ser qualquer dia dentro do mês. **Não** é a data em que a conta abriu
- **DataDigitacao:** Pode ser de um mês diferente da DataBase — isso é normal
- **Comparativo de eventos entre meses:** para comparar **contas abertas** entre meses, usar `DataAberturaConta` (produto `CONTA_CORRENTE_PJ`); para comparar **credenciamentos**, usar `DataCredenciamento` (produto `CREDENCIAMENTO`). São as datas exatas do evento — nunca a `DataBase`. Ver seção "Comparativo entre Meses"
- **Vendedor:** Geralmente consultor, mas supervisores e coordenadores também podem aparecer como vendedores
- **Remoto e presencial sempre separados** em qualquer análise

---

## Pontuação

Três colunas numéricas controlam a pontuação. Valores zerados quando não se aplicam, raramente null.

> 🎯 **Gatilho e qualquer análise de PONTOS: não filtrar por Status.** Para somar pontos (coluna `Pontos`), agregar diretamente por `Matricula` × mês × produto **sem olhar o Status**. Registros `CANCELADO` e `ANALISE_CANCELAMENTO` já têm `Pontos = 0`, então não interferem no total; e os pontos válidos ficam distribuídos entre `VALIDADO` (a maioria), `DIGITADO` e `REPESCAGEM`. Filtrar status numa soma de pontos só cria risco de descartar pontos legítimos. O filtro de status (VALIDADO + DIGITADO + REPESCAGEM) vale para **contagem de registros/contas** — não para soma de pontos.

| Coluna | Produto | Descrição |
|---|---|---|
| `PontuacaoDigitada` | Apenas `CONTA_CORRENTE_PJ` | Pontuação inserida pelo vendedor na criação da conta |
| `OportunidadesDePontos` | Todos os produtos | Pontos possíveis caso o produto seja ativado |
| `Pontos` | Todos os produtos | Pontos efetivamente conquistados após ativação |

### Regras por produto

**M0/M1 — CONTA_CORRENTE_PJ:**
```
PontuacaoDigitada     → preenchida na criação, some (zera) se cancelada
OportunidadesDePontos → aparece quando a conta abre, some (zera) quando ativa
Pontos                → aparecem quando a conta ativa
```

**M0/M1 — CREDENCIAMENTO:**
```
PontuacaoDigitada     → não existe (sempre zero)
OportunidadesDePontos → aparece quando o credenciamento existe, some (zera) quando ativa
Pontos                → aparecem quando o credenciamento ativa
```

**M2 — CONTA_CORRENTE_PJ_M2 e CREDENCIAMENTO_M2:**
```
PontuacaoDigitada     → não existe (sempre zero)
OportunidadesDePontos → aparece quando o M2 entra (já como pendente de ativação)
Pontos                → aparecem quando o M2 ativa
```

### Regra importante — Oportunidade x Pontos

A oportunidade **não garante** que todos os pontos serão convertidos. O banco faz análises próprias e pode converter apenas parte:

```
Exemplo: 8 de OportunidadesDePontos → pode virar apenas 5 de Pontos
```

Assim que ativa:
- `OportunidadesDePontos` → **zera**
- `Pontos` → **preenchido** com o valor aprovado pelo banco

Essa regra vale igualmente para todos os produtos.

---

### Consulta de pontuação por produto

As métricas de pontuação podem ser consultadas de forma **granular por produto** ou em **total consolidado**. Filtrar pela coluna `Produto` para isolar o produto desejado antes de somar.

**Granular por produto** — filtrar `Produto` e somar a coluna desejada:

| O que o usuário quer | Grupo | Filtro em `Produto` | Coluna a somar |
|---|---|---|---|
| Pontuação digitada de Conta Corrente | M0/M1 | `CONTA_CORRENTE_PJ` | `PontuacaoDigitada` |
| Oportunidade de pontos de Conta Corrente | M0/M1 | `CONTA_CORRENTE_PJ` | `OportunidadesDePontos` |
| Pontos de Conta Corrente | M0/M1 | `CONTA_CORRENTE_PJ` | `Pontos` |
| Oportunidade de pontos de Credenciamento | M0/M1 | `CREDENCIAMENTO` | `OportunidadesDePontos` |
| Pontos de Credenciamento | M0/M1 | `CREDENCIAMENTO` | `Pontos` |
| Oportunidade de pontos de M2 Conta | M2 | `CONTA_CORRENTE_PJ_M2` | `OportunidadesDePontos` |
| Pontos de M2 Conta | M2 | `CONTA_CORRENTE_PJ_M2` | `Pontos` |
| Oportunidade de pontos de M2 Credenciamento | M2 | `CREDENCIAMENTO_M2` | `OportunidadesDePontos` |
| Pontos de M2 Credenciamento | M2 | `CREDENCIAMENTO_M2` | `Pontos` |

**Total consolidado** — somar a coluna sem filtrar por produto:

```
PontuacaoDigitada total (M0/M1)      → soma de PontuacaoDigitada em CONTA_CORRENTE_PJ + CREDENCIAMENTO
OportunidadesDePontos total (M0/M1)  → soma de OportunidadesDePontos em CONTA_CORRENTE_PJ + CREDENCIAMENTO
Pontos total (M0/M1)                 → soma de Pontos em CONTA_CORRENTE_PJ + CREDENCIAMENTO

OportunidadesDePontos total (M2)     → soma de OportunidadesDePontos em CONTA_CORRENTE_PJ_M2 + CREDENCIAMENTO_M2
Pontos total (M2)                    → soma de Pontos em CONTA_CORRENTE_PJ_M2 + CREDENCIAMENTO_M2
```

> Ao exibir totais, sempre indicar o grupo (M0/M1 ou M2). Nunca somar M0/M1 e M2 juntos no total, salvo instrução explícita do usuário.
