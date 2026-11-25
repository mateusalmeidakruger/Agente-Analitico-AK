---
name: gatilhoak
description: >
  Use esta skill sempre que o usuário mencionar gatilho, meta mínima do consultor,
  classificação Verde/Amarelo/Vermelho/Plano de Ação, gatilho reduzido, gatilho
  progressivo, ou qualquer análise que envolva verificar se um consultor
  atingiu a meta mensal de pontos. Acionar também quando o usuário pedir para
  avaliar produção dos últimos 3 meses, classificar consultores por desempenho ou
  identificar quem precisa de plano de ação. Usar sempre em conjunto com ProducaoAK
  (origem dos pontos) e UsuariosAK (identificação Presencial/Remoto e tempo de casa).
---

# Skill: Regra do Gatilho

Esta skill define como avaliar se um consultor atingiu a meta mensal de pontos (o "gatilho") e como classificá-lo a partir dos últimos 3 meses.

> **Pressupõe `ContextoAK`** — vocabulário, princípios e cultura. Em particular: "consultor", "executivo" e "promotor" são a mesma pessoa (o vendedor); esta skill padroniza em **consultor**.

---

## Visão Geral

> ⚠️ **Três níveis têm gatilho — não confundir.** Esta seção e as **Regras 1 e 2** abaixo (mês de casa, progressividade, classificação Verde/Amarelo/Vermelho) valem **só para o consultor**. **Supervisor** e **Coordenador** têm gatilho próprio, com métrica, valores e grupo de produto diferentes — ver **"Gatilho de Supervisor e Coordenador"** mais abaixo. Nunca aplicar a régua de um nível no outro.

O **gatilho** é a meta mínima de pontos que cada consultor precisa atingir no mês.
A avaliação é feita olhando os **3 meses anteriores ao mês corrente**, e o consultor é classificado pela quantidade de meses em que bateu o gatilho dentro dessa janela.

Existem **duas regras de gatilho** ao longo do tempo:

1. **Mar/Abr/Mai/26** — regra de exceção (gatilho reduzido temporário)
2. **Jun/26 em diante** — regra nova progressiva (depende do tempo de casa)

A separação **Presencial × Remoto** é obrigatória em qualquer análise (ver UsuariosAK). Cada projeto tem seus próprios valores.

---

## Janela de Avaliação

- O mês de cada registro de produção é determinado pela coluna **`DataBase`** da planilha Producao (ver ProducaoAK). Sempre extrair o mês a partir dela — nunca usar `DataDigitacao`, `DataAberturaConta` ou outras datas para definir o mês de gatilho.
- Avaliação mensal: olha sempre os **3 meses anteriores** ao mês corrente.
- Ex.: avaliação em **junho/26** → janela = **mar, abr, mai/26**.
- Ex.: avaliação em **julho/26** → janela = **abr, mai, jun/26**.
- Um consultor só entra na régua quando já tem **90 dias corridos** de casa (ou seja, terminou o período de experiência — ver UsuariosAK).
- Os pontos feitos durante a experiência **contam** na avaliação (a experiência cobre os primeiros meses que serão olhados na primeira avaliação).

---

## Regra 1 — Mar/Abr/Mai/26 (gatilho reduzido, "vale o melhor")

Vale **somente** para avaliação dos meses de março, abril e maio/26.
Basta atingir **um dos dois** critérios (vale o que for melhor para o consultor).

### Presencial
- **50 pontos M0/M1/M2** *OU*
- **30 pontos M0/M1**

### Remoto
- **60 pontos M0/M1/M2** *OU*
- **40 pontos M0/M1**

### Definição dos grupos de produto (coluna `Produto` da Producao)
- **M0/M1** = `CONTA_CORRENTE_PJ` + `CREDENCIAMENTO`
- **M0/M1/M2** = soma dos 4 produtos (inclui `CONTA_CORRENTE_PJ_M2` e `CREDENCIAMENTO_M2`)

> Nesta regra, **M2 conta** para o total.

---

## Regra 2 — Junho/26 em diante (gatilho progressivo, precisa Conta E GET)

A partir de Junho/26 entra a regra nova:

- Precisa atingir **Conta E GET** no mesmo mês (não é "ou" — tem que bater os dois).
- **Apenas M0/M1**. M2 **não entra em nenhum cálculo do gatilho**.
- O gatilho **varia conforme o "mês de casa" do consultor naquele mês avaliado** (progressivo, para não punir quem está começando).

### Apelidos das colunas (coluna `Produto` da Producao)
- **Conta** = `CONTA_CORRENTE_PJ`
- **GET** = `CREDENCIAMENTO` (referência à GetNet)

> Esses apelidos estão documentados também na skill ProducaoAK e são usados em toda regra de gatilho.

### Presencial

| Mês de casa | Conta (≥) | GET (≥) |
|---|---|---|
| 1º mês | 12 | 4 |
| 2º e 3º mês | 14 | 8 |
| 4º mês em diante | 16 | 12 |

### Remoto

| Mês de casa | Conta (≥) | GET (≥) |
|---|---|---|
| 1º mês | 12 | 4 |
| 2º e 3º mês | 16 | 6 |
| 4º mês em diante | 20 | 8 |

### Como calcular o "mês de casa"
- 1º mês de casa = mês da `DataAdmissao`.
- 2º mês = mês seguinte. E assim por diante.
- Ex.: admitido em **15/04/2026** → abril/26 = 1º mês de casa, maio/26 = 2º, junho/26 = 3º, julho/26 = 4º…

> O gatilho usado em cada mês da janela depende do **mês de casa que o consultor tinha naquele mês específico** — não do mês de casa atual.

---

## Transição entre as duas regras

Para uma janela de avaliação que cruza Maio→Junho/26, **cada mês usa a regra vigente naquele mês**:

- Mar, Abr, Mai/26 → Regra 1 (vale "ou", inclui M2)
- Jun/26 em diante → Regra 2 (vale "e", progressivo, só M0/M1)

### Exemplo de transição
Consultor **Presencial admitido em abril/26**, avaliado em **julho/26** → janela abr/mai/jun:

| Mês avaliado | Regra | Mês de casa | Gatilho aplicado |
|---|---|---|---|
| Abril/26 | Regra 1 (exceção) | 1º | 30 M0/M1 *ou* 50 M0/M1/M2 |
| Maio/26 | Regra 1 (exceção) | 2º | 30 M0/M1 *ou* 50 M0/M1/M2 |
| Junho/26 | Regra 2 (nova) | 3º | 14 Conta *e* 8 GET |

> Na Regra 1 a progressividade **não se aplica** — todo consultor (1º mês ou veterano) tem o mesmo gatilho dentro da exceção.

---

## Classificação Final

Depois de verificar mês a mês se bateu o gatilho, conta-se quantos dos 3 meses da janela foram atingidos:

| Meses com gatilho | Classificação |
|---|---|
| 3 de 3 | 🟢 **Verde** |
| 2 de 3 | 🟡 **Amarelo** |
| 1 de 3 | 🔴 **Vermelho** |
| 0 de 3 | ⚪ **Plano de Ação** |

> A classificação é por **contagem de meses**, não pela soma total de pontos. Um consultor que fez 200 pontos só em um mês e zero nos outros fica Vermelho.

---

## Gatilho de Supervisor e Coordenador

> ⚠️ **Régua diferente da do consultor.** Tudo acima (Regra 1, Regra 2, mês de casa, progressividade) é **exclusivo do consultor**. Supervisor e coordenador são avaliados por **outra métrica**, com **outros valores** e **outro grupo de produto**. Os três gatilhos coexistem — nunca aplicar um no lugar do outro.

Os dois níveis exigem **Conta E GET no mesmo mês** (o "+" das artes significa "e", nunca "ou").

### Mapa dos gatilhos (referência anti-confusão)

| Nível | Projeto | Métrica | Conta | GET | Grupo de produto | ÷ dias? |
|---|---|---|---|---|---|---|
| **Consultor** | Presencial e Remoto (valores próprios) | Absoluta, individual | varia (Regra 1/2) | varia (Regra 1/2) | R1: inclui M2 · R2: **só M0/M1** | Não |
| **Supervisor** | **Presencial** | Absoluta, soma da equipe | **160** | **120** | **Só M0/M1** | Não |
| **Supervisor** | **Remoto** | Absoluta, soma da equipe | **300** | **120** | **Só M0/M1** | Não |
| **Coordenador** | **Presencial** | **Produtividade** | **22** | **15** | **M0/M1/M2 (com M2)** | **Sim** |
| **Coordenador** | **Remoto** | Sem gatilho próprio → usa o do Supervisor Remoto | **300** | **120** | **Só M0/M1** | Não |

### Supervisor — total absoluto da equipe

Soma dos pontos de **todos os consultores sob aquele supervisor** (agrupar por `Nome_Supervisor`, ver UsuariosAK). É **valor absoluto**: não se divide por dias úteis. **Só M0/M1** — M2 (`..._M2`) **não entra** (igual à Regra 2 do consultor). Os valores **diferem por projeto**:

**Presencial**

| Produto | Gatilho (≥) | Grupo |
|---|---|---|
| Conta (`CONTA_CORRENTE_PJ`) | **160 pontos** | M0/M1 |
| GET (`CREDENCIAMENTO`) | **120 pontos** | M0/M1 |

Bate no mês quando **Conta ≥ 160 E GET ≥ 120**.

**Remoto**

| Produto | Gatilho (≥) | Grupo |
|---|---|---|
| Conta (`CONTA_CORRENTE_PJ`) | **300 pontos** | M0/M1 |
| GET (`CREDENCIAMENTO`) | **120 pontos** | M0/M1 |

Bate no mês quando **Conta ≥ 300 E GET ≥ 120**.

> A única diferença entre os dois é a **Conta** (160 Presencial × 300 Remoto). O **GET é 120** nos dois. O Remoto abre mais conta, por isso a barra de conta é mais alta.

### Coordenador — produtividade da coordenação

> "Coordenador", "Gerente" e "Gerente Regional" são o **mesmo cargo** (na `Usuarios_Atual` o valor é `COORDENADOR/GERENTE`). A arte "Gerente Regional" **é o coordenador** — não é um nível acima.

#### Coordenador Presencial

Métrica de **produtividade**: pontos de toda a coordenação **divididos pelos dias úteis trabalhados**, usando o `dias_equivalentes` já definido na UsuariosAK.

| Produto | Gatilho (≥) | Grupo |
|---|---|---|
| Conta (`CONTA_CORRENTE_PJ`) | **22 de produtividade** | M0/M1/M2 |
| GetNet (`CREDENCIAMENTO`) | **15 de produtividade** | M0/M1/M2 |

```
produtividade_conta = Σ pontos Conta (M0/M1/M2) da coordenação ÷ dias_equivalentes
produtividade_get   = Σ pontos GET  (M0/M1/M2) da coordenação ÷ dias_equivalentes

dias_equivalentes   = Σ(DiasTrabalhados de TODOS os consultores da coordenação) ÷ DU_passados
```
(Fórmula, `DU_passados` e a regra de **não filtrar por status** estão na UsuariosAK.)

- **Único dos três que inclui M2.** Atenção: supervisor e Regra 2 do consultor usam só M0/M1 — aqui o numerador soma **M0/M1/M2**.
- ⚠️ Não confundir com a **produtividade de eficiência** (AnalistaDiaria / UsuariosAK), que usa o mesmo denominador mas conta **só M0/M1**. Para o gatilho do coordenador, **M2 entra**.
- Bate no mês quando **produtividade_conta ≥ 22 E produtividade_get ≥ 15**.

> ⚠️ Como o Remoto não tem coordenador com gatilho próprio, **essa produtividade 22/15 vale para o Presencial**.

#### Coordenador Remoto

O Remoto **não tem gatilho de coordenador próprio** — toda a operação Remoto é coordenada por uma só pessoa (**Mariana Kruger**, ver UsuariosAK). Por orientação do usuário, se for preciso avaliar o coordenador Remoto, **usa-se o mesmo gatilho do Supervisor Remoto** (300 Conta + 120 GET, **absoluto**, só M0/M1) — "dá na mesma". Ou seja, o coordenador Remoto **não** usa a régua de produtividade (22/15) do Presencial.

### Ainda não definido (não inventar)

As artes trazem só o **gatilho mensal** de cada nível. Sobre o resto **não há informação** — confirmar com o usuário antes de assumir:

1. **Janela e classificação** — não está dito se supervisor/coordenador seguem a régua de 3 meses → Verde/Amarelo/Vermelho/Plano de Ação, ou se é só bateu/não bateu no mês.
2. **Vigência** — não há data de início informada para esses gatilhos.

> **Resolvido — Presencial × Remoto:** Supervisor Presencial 160/120 · Supervisor Remoto 300/120 · Coordenador Presencial 22/15 (produtividade, M0/M1/M2) · Coordenador Remoto = mesmo do Supervisor Remoto (300/120, absoluto).

---

## Quem entra na análise

Parte da `Usuarios_Atual` (ver UsuariosAK):

1. Considerar apenas funcionários **ativos** (regras de status na UsuariosAK).
2. **Excluir quem está em experiência** (menos de 90 dias corridos desde DataAdmissao — ver UsuariosAK).
3. Cruzar com a Producao pela `Matricula`. Se não houver produção em algum mês, considerar **0 pontos** naquele mês (não bateu).
4. Separar **Presencial** e **Remoto** desde o início — nunca misturar os dois projetos.

---

## Pontuação utilizada

- Coluna `Pontos` da planilha Producao (ver ProducaoAK).
- Agregação: soma de `Pontos` por `Matricula` × mês × produto.
- Para a Regra 2, calcular separadamente os totais de **Conta** (`CONTA_CORRENTE_PJ`) e **GET** (`CREDENCIAMENTO`) por mês.

---

## Algoritmo de Avaliação (passo a passo)

Para cada consultor ativo, fora da experiência:

1. Determinar o **projeto** (Presencial ou Remoto) via UsuariosAK.
2. Definir a **janela** = últimos 3 meses anteriores ao mês corrente.
3. Para cada mês da janela:
   a. Identificar a regra vigente (Regra 1 se for Mar/Abr/Mai/26; Regra 2 se for Jun/26 em diante).
   b. Calcular o **mês de casa** do consultor naquele mês.
   c. Aplicar o gatilho correspondente (projeto + regra + mês de casa).
   d. Marcar `Bateu_mes = Sim/Não`.
4. Contar quantos meses bateu.
5. Aplicar a classificação (Verde / Amarelo / Vermelho / Plano de Ação).

---

## Formato de Saída

Esta skill é **agnóstica de formato de saída** — ela define apenas a regra de cálculo e classificação. O resultado pode ser apresentado em:

- Planilha Excel (.xlsx)
- Dashboard HTML
- Relatório em BI (Power BI, Looker, etc.)
- Tabela inline na conversa
- Qualquer outro formato que o usuário pedir

Quando o usuário pedir uma análise de gatilho:

0. Identificar o **nível** pedido — consultor, supervisor ou coordenador — e usar a régua daquele nível (nunca misturar; ver "Gatilho de Supervisor e Coordenador").
1. Aplicar a regra correta conforme o mês e o projeto.
2. Calcular Bateu/Não Bateu por mês e a Classificação final.
3. Sempre apresentar **Presencial e Remoto separados** (skill UsuariosAK).
4. Adaptar o formato de saída ao que o usuário pediu — Excel detalhado, dashboard visual, resumo executivo, etc.

Sugestões de informação que costumam ser úteis em qualquer formato:

- Identificação do consultor (Matrícula, Nome, Supervisor, Coordenador, Projeto)
- DataAdmissao e mês de casa em cada mês avaliado
- Pontos relevantes por mês (Conta e GET, ou M0/M1 e Total, conforme a regra vigente)
- Indicação de bateu/não bateu por mês
- Quantidade de meses com gatilho e classificação final
- Cores sugeridas: Verde (#C6EFCE), Amarelo (#FFEB9C), Vermelho (#FFC7CE), Plano de Ação (#D9D9D9)
