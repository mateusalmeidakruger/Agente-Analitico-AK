---
name: contextoak
description: >
  Use sempre que a conversa envolver análise, dashboard, planilha, gatilho,
  cruzamento ou qualquer trabalho operacional da Almeida Kruger. Fornece o
  contexto de negócio, o vocabulário, a hierarquia, o ciclo do CNPJ (M0/M1 vs
  M2), os princípios analíticos inegociáveis e a postura esperada de quem
  analisa dados da AK. É a fundação que ancora todas as outras skills da
  família (ProducaoAK, UsuariosAK, CruzamentoDiariaAK, GatilhoAK,
  AnalistaDiaria, DashboardAK). Acionar também quando surgir dúvida sobre
  "o que é a AK", "o que significa GET / Conta / FVE / M2", ou sobre a
  diferença entre Presencial e Remoto.
---

# Skill: Contexto AK — Negócio, Cultura e Postura

Esta skill é a base de tudo. As outras skills da AK definem **como** fazer
cada coisa; esta define **por quê** e **dentro de que mundo**. Sem ler aqui,
o resto vira tabela técnica sem alma.

> Esta skill **não define cálculo, coluna nem formato**. Para regras de
> dados ver `ProducaoAK` e `UsuariosAK`; para regras de cruzamento, ver
> `CruzamentoDiariaAK`; para gatilho ver `GatilhoAK`; para análise ver
> `AnalistaDiaria`; para apresentação ver `DashboardAK`.

---

## O Negócio

A **Almeida Kruger (AK)** é uma empresa comercial parceira do **Santander**.
Vende dois produtos do banco para comerciantes (PJ):

- **Conta Corrente PJ** — abertura de conta empresarial no Santander
- **Credenciamento GetNet** — a máquina de cartão (a "maquininha")

A AK é **terceirizada**. Não controla o sistema, não valida abertura nem
ativação — o **banco é a fonte da verdade**. A AK indica, acompanha o
cliente e organiza a operação comercial; o Santander valida e devolve os
status no ritmo dele.

### Implicação central

Toda análise da AK convive com um **gap temporal conhecido**: o que está
"pendente" no sistema pode já estar ativo no mundo real, e a base só vai
refletir isso quando o banco devolver a atualização. O analista bom sabe
disso e não confunde *atraso de informação* com *falha de ativação*.

---

## Os Dois Projetos

A operação é dividida em dois projetos com modelos de venda **distintos**.
**Nunca misturar Presencial e Remoto numa mesma análise**, salvo instrução
explícita.

### Presencial

- Consultor vai **de porta em porta**, marca visita, percorre comércios
- Operação ativa de rua, mais "musculosa"
- Maior parte da empresa

### Remoto

- Consultor trabalha **de casa**, vende por **internet e WhatsApp**
- Sem visita física
- Coordenado por **Mariana Kruger** — toda equipe Remoto está abaixo dela

Por que separar: os dois projetos têm públicos, ritmos, custos e
desafios diferentes. As regras de gatilho são diferentes para cada um
(ver `GatilhoAK`). Comparar Presencial com Remoto sem qualificar é erro
de leitura.

### Identificação técnica

- Em `Producao.xlsx`: coluna `Tipo_Consultor` (valores `Presencial` /
  `Remoto`, CamelCase)
- Em `Usuarios_Atual.xlsx`: derivar pela hierarquia — todos abaixo de
  Mariana Kruger são Remoto, o resto é Presencial (ver `UsuariosAK`)

---

## A Hierarquia

```
Coordenador  →  Supervisor  →  Consultor
                                (vendedor, ponta da operação)
```

**Sempre apresentar nessa ordem**, do mais alto pro mais baixo. Inverter
quebra a leitura mental que toda a operação usa.

Os três cargos relevantes para qualquer análise são esses. Demais cargos
(administrativo, financeiro, etc.) ficam fora salvo pedido explícito.

---

## Vocabulário (glossário oficial)

A AK convive com **muitos sinônimos** para a mesma coisa, vindos de
sistemas e contextos diferentes. Esta tabela é a referência única.

### O vendedor

| Termo | Onde aparece |
|---|---|
| **Consultor** | Conversa do dia a dia (uso padrão) |
| **Executivo** | Planilhas internas (Producao, Usuarios) |
| **Promotor** | FVE (sistema do Santander) |

> Os três são **a mesma pessoa**. Em qualquer análise, padronizar como
> **consultor** ao apresentar — é o termo menos formal e mais usado
> internamente.

### Os produtos

| Termo | Significado |
|---|---|
| **Conta** / **Conta PJ** | `CONTA_CORRENTE_PJ` na produção |
| **GET** / **GetNet** / **Credenciamento** | `CREDENCIAMENTO` na produção (a maquininha) |
| **Conta M2** | `CONTA_CORRENTE_PJ_M2` — reativação 2 meses após abertura |
| **GET M2** | `CREDENCIAMENTO_M2` — reativação 2 meses após abertura |

### Os sistemas

| Termo | O que é |
|---|---|
| **FVE** / **Parceiro Santander** / **sistema do banco** | Sistema do Santander onde o consultor indica o cliente e gera o link |
| **Portal** / **ERP** / **portal AK** | Sistema interno da AK onde o consultor digita a indicação |

### Eventos no ciclo

| Termo | O que é |
|---|---|
| **Indicação** | Lançamento no FVE (lado banco). Gera o link de 30 dias para o cliente |
| **Digitação** | Lançamento no portal AK (lado interno). Gera a `DataDigitacao` |
| **Abertura** | Quando o banco efetiva a conta. Gera a `DataAberturaConta` |
| **Ativação** | Quando o cliente começa a usar (movimentação mínima na conta / no credenciamento). É **aqui que a AK efetivamente lucra** |

---

## O Ciclo de uma Venda

```
1. Consultor faz INDICAÇÃO no FVE          → gera link (30 dias)
2. Consultor faz DIGITAÇÃO no Portal AK    → DataDigitacao
3. Cliente abre a conta no link            → DataAberturaConta
4. Cliente ATIVA (movimenta valor mínimo)  → AK lucra
5. 2 MESES depois, conta volta como M2     → cliente precisa reativar
6. Cliente reativa M2                      → AK lucra de novo, ciclo TERMINA
```

### Regras do link (FVE)

- O link gerado dura **30 dias corridos**
- Expirou e o cliente não fez nada → o portal AK **cancela
  automaticamente** na próxima atualização
- Cliente quis voltar depois? Nova indicação no FVE — **não cria registro
  novo**, atualiza a data da indicação existente

### M0/M1 e M2 — o ciclo em duas vidas

Toda conta vive em **duas etapas separadas** na produção:

**Vida 1 — M0/M1 (mês da abertura)**
- Produtos: `CONTA_CORRENTE_PJ` e `CREDENCIAMENTO`
- Cliente abriu e tem que ativar nesse mês
- Taxa típica de ativação Conta: ~100%. Conta abriu, conta ativa.
- Taxa típica de ativação GET: o desafio real da operação

**Vida 2 — M2 (exatos 2 meses-calendário depois)**
- Produtos: `CONTA_CORRENTE_PJ_M2` e `CREDENCIAMENTO_M2`
- Mesma conta volta a aparecer, **pendente de reativação**
- Cliente precisa continuar usando — não basta ter ativado e sumido
- Taxa típica de ativação Conta M2: ~90% (continua fácil)
- Taxa típica de ativação GET M2: também é desafio
- **M2 é o ciclo final.** Reativou em M2 = comissão máxima extraída. Não
  existe M3, M4

> M2 é exatamente **2 meses-calendário** depois da `DataAberturaConta`,
> não 60 dias. Abriu em 26/junho → reaparece em agosto.

### A armadilha cultural do M2

> **Mês forte de M0/M1 hoje → M2 garantido daqui a dois meses → consultor
> relaxa no M0/M1 do mês do M2 → tombo dois meses depois.**

Um consultor que teve junho forte em M0/M1, em agosto colhe M2 fácil
(reativação é mais simples que abrir do zero). A tentação: viver da
safra de M2 e parar de plantar M0/M1 novo. Resultado previsível:
**outubro fica órfão**, porque agosto teve M0/M1 fraco — não tem M2
para colher.

**Por isso M0/M1 e M2 são sempre apresentados separadamente. Nunca somar.**
Somar esconde exatamente esse vício.

Pontuação alta hoje pode ser **falsa segurança**. O que importa é o **mix
saudável** entre plantio (M0/M1) e colheita (M2). Equipe que só colhe M2
está se autodestruindo em câmera lenta.

---

## Onde Está o Lucro

A AK **só lucra quando o cliente ativa**. Volume aberto não paga.

Dentro da ativação, existe uma hierarquia de valor que a coluna `Pontos`
da produção **já reflete**:

### Segmento (coluna `Segmento`)

```
DEMAIS_SEGMENTOS_PJ  >  EMPRESA_DIGITAL  >  CLIENTE_MEI
   (mais lucrativo)                       (menos lucrativo)
```

`DEMAIS_SEGMENTOS_PJ` é o foco — sempre destacar.

### Tempo de constituição da empresa

Empresa com **mais de 1 ano** vale mais que recém-aberta. É um cliente
consolidado, com fluxo, com histórico — comissão maior.

### Pontuação máxima por linha de produção

| Cenário ótimo | Pontos |
|---|---|
| Conta ativada, DEMAIS_SEGMENTOS_PJ, >1 ano | **4 pts** (teto da conta) |
| GET ativado, DEMAIS_SEGMENTOS_PJ, >1 ano | **6 pts** (teto do GET) |

> GET vale mais que conta. E o ideal absoluto é **mesmo cliente com
> conta ativa + GET ativo** — vendeu o pacote completo, capturou o
> produto mais lucrativo. Conta sem GET = oportunidade perdida.

A coluna `Pontos` é a **métrica-rainha**. Já condensa segmento + tempo +
ativação num único número. Por isso o gatilho é por pontuação (ver
`GatilhoAK`).

---

## As Datas e o Gap Temporal

Como a AK **não é fonte da verdade**, existem datas de atualização que
dizem **até quando o status reflete a realidade**:

- Data de atualização da **abertura da conta**
- Data de atualização da **ativação da conta**
- Data de atualização da **abertura do credenciamento**
- Data de atualização da **ativação do credenciamento**

Essas datas **não estão na planilha de produção** — são informação
**manual**, comunicada quando o banco devolve a atualização. Hoje pode
ser 26/06, mas a atualização de ativação da conta pode estar travada em
22/06: tudo que ativou entre 22 e 26 ainda não aparece.

**Implicação prática:** pendente recente pode ser *falso pendente* — já
ativou, só não chegou na base. O analista honesto menciona o horizonte
de confiança quando interpreta volume de pendentes recentes.

### A `DataBase` — só importa mês/ano

A coluna `DataBase` da produção é uma **referência aleatória dentro do
mês**. O dia em si não diz nada — só importa **mês e ano**. Serve para
marcar em qual mês aquele CNPJ está sendo analisado.

Se um CNPJ foi digitado em junho mas não abriu nem ativou nem cancelou,
sua `DataBase` rola pra julho automaticamente (geralmente vira algo como
01/julho). O CNPJ continua na fila até resolver.

Por isso o **mês de qualquer análise é definido pela `DataBase`** — não
pela `DataDigitacao`, não pela `DataAberturaConta`. Quem usar outra data
para definir mês está errado.

### Os três momentos do mês

Toda análise tem que saber em qual momento o mês está:

| Momento | O que se vê | Confiabilidade |
|---|---|---|
| **Mês corrente** (em andamento) | Status com lag, pendentes podem ativar, projeção linear faz sentido | Estimativa |
| **Mês recém-fechado** (em contestação) | Calendário fechou, banco ainda não retornou final, 1 a 2 semanas de janela onde números mexem | Parcial — vai mudar |
| **Mês consolidado** (`VALIDADO`) | Status terminal, números congelados | Verdade definitiva |

**Projeção linear só faz sentido no mês corrente.** Mês fechado tem
fechamento real, não projeção. O status `VALIDADO` é o destino terminal
de toda conta consolidada.

---

## A Régua: Como Ler um Consultor

Existe uma **ordem inegociável de leitura** que vale para qualquer
análise da AK:

```
1. Pontos                 ← métrica-rainha, ranking primário, base do gatilho
2. Composição dos pontos  ← Conta vs GET, M0/M1 vs M2
3. Ativações              ← absoluto (Contas Ativas + GETs Ativos)
4. Mix no mesmo cliente   ← conta+GET juntos é o padrão-ouro
```

### O que faz um consultor ser bom

Existem **dois caminhos legítimos** para pontuação alta:

- **Caminho eficiente**: pouco volume, ativação alta, mix bom
- **Caminho força bruta**: volume gigante, ativação proporcionalmente
  menor mas absoluta suficiente

Ambos valem. O que **não vale** é pontuação baixa — fim de papo.

### O que faz um consultor ser ruim

- Pontuação baixa, simples assim
- Volume aberto sem ativação (taxa baixa em Conta especialmente — pode
  ser sinal de cliente fantasma ou indicação ruim)
- Vive de M2, abandona M0/M1
- Conta sem GET de forma sistemática

### Onde o gatilho entra

O gatilho marca o ponto em que o consultor **se paga** (cobre o custo
dele pra empresa) e ainda gera margem. Não bater o gatilho é o sinal
objetivo de quem está custando mais do que rendendo.

Detalhamento do cálculo, regra mar-mai/26 (exceção) vs jun/26+ (nova,
progressiva por mês de casa), classificação Verde/Amarelo/Vermelho/Plano
de Ação → ver **`GatilhoAK`**.

---

## Princípios Analíticos Inegociáveis

Esses valem em **qualquer modo, qualquer formato, qualquer pergunta**:

1. **Presencial e Remoto sempre separados.** Nunca consolidar, salvo
   instrução explícita.
2. **Hierarquia Coordenador → Supervisor → Consultor.** Nunca inverter.
3. **M0/M1 e M2 sempre apresentados separadamente.** Nunca somar, salvo
   instrução explícita.
4. **Conta e GET (Credenciamento) sempre distintos** dentro de cada grupo
   de produto. Taxas de ativação são naturezas diferentes — não
   comparar Conta e GET na mesma régua.
5. **Fonte da verdade do funcionário é Usuarios_Atual.** Nome, supervisor,
   coordenador e status vêm de lá, nunca da produção (ver
   `CruzamentoDiariaAK`).
6. **Mês de qualquer análise = `DataBase`** (não `DataDigitacao`, não
   `DataAberturaConta`).
7. **Funcionários em experiência aparecem com badge `⚠️ Experiência`** —
   nunca silenciar.
8. **Alertas de integridade são primeira classe** — produção de
   desligado, matrícula órfã, lançamento em licença. Nunca esconder,
   nunca minimizar.
9. **Régua é absoluta, não relativa.** Comparações são contra **gatilho**
   e **projeção do mês corrente** — não contra média de equipe nem mês
   anterior. Em equipe ruim, todo mundo aparece ruim. É o efeito
   desejado.

---

## Postura do Analista

Quem analisa dados da AK:

1. **Tem opinião absoluta, não relativa.** A régua é gatilho e projeção —
   nunca "comparado com a média do time".
2. **Escolhe o que destacar.** Não tudo merece observação. Prioriza o
   acionável pelo leitor (que costuma ser o supervisor).
3. **Questiona a pergunta quando faz sentido.** Se o pedido for "ranking
   top 10 por volume", entrega, mas pode apontar: "o top 1 só trabalhou
   4 dias — quer reordenar?". Não é desobediência, é cuidado.
4. **Conecta blocos.** A leitura final cruza o que viu nos números —
   não trata cada métrica como ilha.
5. **Não inventa hipótese sem dado.** Toda observação parte de um número
   ou padrão observado. Especulação sem ancoragem é proibida.
6. **Recomendação é convite, não ordem.** Sugere, pergunta, abre
   caminho — não decreta.
7. **Conhece o gap temporal** e o cita quando relevante. Não trata
   pendente recente como falha de ativação.

---

## Vícios a Evitar

A operação tem armadilhas analíticas recorrentes:

- **Vício do volume**: priorizar quem vende mais ignorando ativação.
  Antídoto: ranking por **Pontos** (já filtra ativação), leitura crítica
  sempre comenta qualidade.
- **Vício do percentual**: consultor que abriu 2 e ativou as 2 tem 100%
  — não é "campeão". Antídoto: sempre apresentar **absoluto junto do
  percentual**.
- **Vício do template**: rodar blocos sem pensar. Antídoto: a Leitura do
  Mês é obrigatória justamente pra forçar pensamento crítico (ver
  `AnalistaDiaria` bloco 8).
- **Vício da uniformidade**: tratar Presencial e Remoto como iguais.
  Antídoto: separação inegociável.
- **Vício do silêncio**: omitir desligados, omitir experiência, omitir
  zerados pra equipe parecer melhor. Antídoto: regra explícita de
  visibilidade (princípios 7 e 8).
- **Vício do M2**: tratar pontuação alta vinda de M2 como sucesso sem
  olhar M0/M1 do mês corrente. Antídoto: separação M0/M1 vs M2 sempre.
- **Vício da comparação relativa**: comparar consultor/supervisor com a
  média do time. Antídoto: régua absoluta (gatilho, projeção).

---

## Quem Lê

O leitor principal dos dashboards e análises é o **Supervisor**, olhando
a equipe dele. Em segundo plano: coordenador olhando seus supervisores,
direção olhando o todo.

Isso pauta tom e densidade: análise para supervisor é **acionável**
(o que fazer com cada consultor), não institucional. A AnalistaDiaria
existe para entregar conteúdo nesse nível; o DashboardAK existe para
apresentar de forma navegável.

---

## TODO — Captura futura

- **Jargão interno / frases que circulam na AK** — máximas que o time
  repete em reunião, expressões internas, regras não escritas. Quando
  emergirem, adicionar em uma seção de "Falas da Casa".
- **Documentação da skill do FVE** (status do lado banco, ciclo no
  sistema do Santander) — virará uma quarta data source quando criada.

---

## Como Esta Skill se Integra

| Skill | O que esta skill ancora |
|---|---|
| `ProducaoAK` | Sentido de cada coluna (Pontos, Segmento, Status, M0/M1 vs M2) |
| `UsuariosAK` | Por que separar Presencial/Remoto, por que três cargos só |
| `CruzamentoDiariaAK` | Por que Usuarios é fonte da verdade |
| `GatilhoAK` | O que o gatilho representa (ponto em que consultor se paga) |
| `AnalistaDiaria` | Régua de leitura, princípios, postura, vícios |
| `DashboardAK` | Quem é o leitor, ordem de apresentação |

Toda skill da família AK **pressupõe** o que está aqui. Quando algo
parecer arbitrário em outra skill, a justificativa provavelmente está
nesta.
