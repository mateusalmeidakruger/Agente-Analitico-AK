---
name: usuariosak
description: >
  Use esta skill sempre que o usuário mencionar a planilha de usuários, o arquivo
  Usuarios_Atual, ou qualquer análise que envolva funcionários, cargos, matrículas,
  situação de funcionários, hierarquia de equipes, supervisores, coordenadores ou
  consultores. Também acione esta skill quando precisar identificar quem está ativo,
  licenciado, desligado, em férias ou em experiência. Use em conjunto com outras
  skills quando houver cruzamento com outras planilhas.
---

# Skill: Tabela de Usuários (Usuarios_Atual)

Esta skill define como interpretar e processar a planilha de funcionários da empresa.

---

## Arquivo

**Nome do arquivo:** `Usuarios_Atual` (formato `.xlsx`)

Esta planilha contém **todos os funcionários da empresa**, ativos ou não.

---

## Colunas Relevantes

| Coluna | Descrição |
|---|---|
| `Matricula` | Identificador único do funcionário na empresa |
| `NomeUsuario` | Nome completo da pessoa |
| `CPF` | Documento — útil para cruzamento com arquivos externos que contenham apenas CPF |
| `Email` | Email corporativo — reservado para uso futuro (ex: envios em massa) |
| `Cargo` | Função da pessoa na empresa (valores UPPERCASE: `CONSULTOR`, `SUPERVISOR`, `COORDENADOR/GERENTE`) |
| `DataAdmissao` | Data de entrada na empresa |
| `DataDesligamento` | Data de saída — se preenchida, a pessoa está desligada |
| `Situacao` | Estado atual do funcionário (ex: Férias, Afastado, Gestante, Atestado) — vazia quando ativo |
| `DiasTrabalhados` | Quantidade de dias úteis trabalhados no mês até o dia anterior ao atual |
| `ProjecaoDiasTrabalhados` | Projeção de dias trabalhados caso a pessoa trabalhe o mês inteiro |
| `Nome_Supervisor` | Nome do supervisor direto do funcionário (**com underscore**) |
| `Matricula_Supervisor` | Matrícula do supervisor |
| `Nome_Coordenador` | Nome do coordenador responsável pelo funcionário (**com underscore**) |
| `Matricula_Coordenador` | Matrícula do coordenador |

> ⚠️ **Atenção aos nomes reais das colunas**: as colunas de hierarquia vêm com underscore (`Nome_Supervisor`, `Nome_Coordenador`, `Matricula_Coordenador`, `Matricula_Supervisor`), enquanto na planilha de Produção elas vêm sem underscore (`NomeSupervisor`, `NomeCoordenador`). Em código Python, isso muda o nome do campo entre os dois DataFrames.

> ⚠️ O cargo `COORDENADOR/GERENTE` traz a barra `/` no valor — usar exatamente assim em filtros.

---

## Cargos Relevantes e Hierarquia

Focar apenas nestes três cargos:

```
Consultor  →  Supervisor  →  Coordenador
(vendedor)     (lidera          (lidera
              consultores)     supervisores)
```

- **Consultor**: vendedor, nível base
- **Supervisor**: lidera consultores
- **Coordenador**: nível mais alto, lidera supervisores

> Ignorar demais cargos a não ser que explicitamente solicitado.

---

## Projetos: Presencial e Remoto

A empresa possui dois projetos distintos que **sempre devem ser tratados separadamente**:

### Projeto Remoto
Coordenado por **MARIANA KRUGER**, que pode aparecer na planilha com dois nomes e duas matrículas diferentes devido a um erro de sistema. Ambos os registros representam a **mesma pessoa**:

| Nome na planilha | Matrícula |
|---|---|
| MARIANA FREIRE KRUGER | 12958 |
| MARIANA KRUGER | REMOTO |

> ⚠️ A matrícula `REMOTO` é um texto literal — exceção única na planilha onde todas as demais matrículas são numéricas.

**Regras do projeto remoto:**
- Qualquer funcionário vinculado a MARIANA KRUGER (qualquer variação do nome ou matrícula) pertence ao **projeto remoto**
- O projeto remoto **sempre aparece separado** do presencial em qualquer análise
- Nunca misturar remoto com presencial, salvo aviso explícito do usuário

### Identificação prática em Python

```python
mariana_mats = {'12958', 'REMOTO'}
usr['Matricula_str'] = usr['Matricula'].astype(str)

def is_remoto(row):
    if str(row['Matricula']) in mariana_mats: return True
    if str(row['Matricula_Coordenador']) in mariana_mats: return True
    return False

usr_remoto = usr[usr.apply(is_remoto, axis=1)]
usr_presencial = usr[~usr.apply(is_remoto, axis=1)]
```

> Importante: na planilha de **Produção** (`Producao.xlsx`), o projeto é identificado direto pela coluna `Tipo_Consultor` (`Presencial` / `Remoto`). Na planilha de **Usuários**, não existe essa coluna — a identificação se dá pela hierarquia (todos abaixo de Mariana = Remoto).

### Projeto Presencial
- Todos os demais coordenadores e suas equipes
- É o projeto padrão quando não há indicação de remoto

---

## Regras de Status do Funcionário

### 1. Desligado
- `DataDesligamento` está **preenchida** com qualquer data
- Independente do que estiver na coluna `Situacao`

### 2. Licença
- `DataDesligamento` está **vazia** E
- `Situacao` contém qualquer valor que não seja Férias (ex: Afastado, Gestante, Atestado, etc.)

### 3. Férias
- `DataDesligamento` está **vazia** E
- `Situacao` = `Férias`
- Tratar como ativo por padrão, mas sinalizar se perguntado

### 4. Ativo
- `DataDesligamento` está **vazia** E
- `Situacao` está **vazia** (sem nenhuma ocorrência)

**Resumo da lógica:**
```
DataDesligamento preenchida?            → Desligado
Situacao = Férias?                      → Férias (conta como ativo)
Situacao preenchida com outra coisa?    → Licença
Situacao vazia + sem desligamento?      → Ativo
```

---

## Regra de Dias Trabalhados

- `DiasTrabalhados` representa os dias úteis trabalhados **até o dia anterior à data atual**
- O dia atual **nunca é contado** (ainda não encerrado)
- **Exemplo:** Hoje é 11/06. Passou feriado em 04/06. Total de dias úteis anteriores = 7 dias trabalhados (de 01/06 a 10/06, excluindo feriados e o próprio dia 11)

---

## Regra de Dias Equivalentes (para Supervisor / Coordenador)

Para comparar equipes de tamanhos diferentes de forma justa, usa-se o conceito de **dias equivalentes**. Aplica-se **apenas nos níveis de Supervisor e Coordenador** — no nível de consultor não se normaliza por dias (a métrica é sempre absoluta).

### Fórmula

```
dias_equivalentes = Σ(DiasTrabalhados dos consultores da equipe) ÷ DU_passados
```

Onde:
- `Σ(DiasTrabalhados ...)` = soma da coluna `DiasTrabalhados` de **todos os consultores** sob aquele supervisor (ou todos sob aquele coordenador, no nível superior).
- `DU_passados` = número de dias úteis decorridos do mês até o dia anterior ao atual (mesma base usada em `DiasTrabalhados`).

> ⚠️ **Não filtrar por status do funcionário.** A soma inclui ativos, férias, licença e desligados no período. A coluna `DiasTrabalhados` já reflete a realidade de cada um: quem teve férias parciais aparece com menos dias, desligado aparece com os dias até o desligamento, licença com zero ou parcial. Filtrar por status duplica o desconto e infla a produtividade artificialmente. O filtro é apenas `Nome_Supervisor` (ou `Nome_Coordenador`) + `Cargo = CONSULTOR`.

### Interpretação

O resultado é o **número de consultores-equivalentes em pé** durante o período. Neutraliza férias, licenças, atestados e desligamentos parciais — sem precisar fazer essa neutralização manualmente.

**Exemplo:** Um supervisor tem 10 consultores na equipe (independente de status). Até hoje passaram 10 DU. Somando a coluna `DiasTrabalhados` de todos eles, dá 80 (alguns trabalharam 10, outros menos por férias parciais, um foi desligado no meio do mês).

```
dias_equivalentes = 80 ÷ 10 = 8 consultores-equivalentes
```

Lê-se: "essa equipe operou como se tivesse 8 consultores em pé o mês inteiro."

### Uso típico

Sempre que houver métrica de produtividade por equipe (pontos por DU, ativações por DU, etc.), o denominador no nível de supervisor/coordenador é `dias_equivalentes`. Ex.:

```
Produtividade de pontos da equipe = Pontos M0/M1 ÷ dias_equivalentes
```

> A produtividade de **pontos** considera apenas **M0/M1**, nunca M2 — ver justificativa em `AnalistaDiaria` (seção Eficiência). M2 é colheita de venda de 2 meses atrás, não cabe na régua de esforço do mês corrente.

### Quando NÃO usar

- Nível de consultor: usar valores absolutos.
- Quando o usuário pedir explicitamente "produtividade por consultor cabeça" (média simples ignorando dias).
- Análises de período fechado em que a planilha já tem o total de DU consolidado (aí divide pelos DU reais do mês fechado).

---

## Cálculo Automático de Dias Úteis

`DU_passados` (e o `DU_mes_total`, usado em projeções e em análise de mês fechado) podem ser calculados automaticamente, sem precisar preencher manualmente. A regra que vale na AK é **feriados nacionais apenas** — feriados estaduais e municipais não descontam, porque a empresa tem colaboradores espalhados pelo Brasil.

### Função canônica em Python

```python
import holidays
from datetime import date, timedelta
from calendar import monthrange

br_holidays = holidays.Brazil()  # feriados nacionais

def dias_uteis(inicio: date, fim: date) -> int:
    """Conta dias úteis entre inicio e fim (inclusive), excluindo
    sábados, domingos e feriados nacionais brasileiros."""
    total = 0
    d = inicio
    while d <= fim:
        if d.weekday() < 5 and d not in br_holidays:  # 0=seg ... 4=sex
            total += 1
        d += timedelta(days=1)
    return total

def du_passados(hoje: date = None) -> int:
    """Dias úteis decorridos do início do mês até ontem.
    Hoje nunca conta (regra da AK: o dia atual ainda não encerrou)."""
    hoje = hoje or date.today()
    inicio_mes = hoje.replace(day=1)
    ontem = hoje - timedelta(days=1)
    if ontem < inicio_mes:
        return 0  # primeiro dia útil do mês
    return dias_uteis(inicio_mes, ontem)

def du_mes_total(hoje: date = None) -> int:
    """Dias úteis totais do mês corrente (do dia 1 ao último dia)."""
    hoje = hoje or date.today()
    inicio_mes = hoje.replace(day=1)
    ultimo_dia = monthrange(hoje.year, hoje.month)[1]
    fim_mes = hoje.replace(day=ultimo_dia)
    return dias_uteis(inicio_mes, fim_mes)
```

### Dependência

Requer a biblioteca `holidays` (Python). Instalar com `pip install holidays`. Ela mantém atualizada a lista de feriados nacionais brasileiros — incluindo móveis (Carnaval, Sexta-feira Santa, Corpus Christi) que dependem da data da Páscoa.

### Coerência com `DiasTrabalhados` da planilha

A coluna `DiasTrabalhados` em `Usuarios_Atual` é preenchida por outro processo (sistema externo). Se esse processo usar uma lista de feriados **diferente** da nacional (ex: incluir um feriado regional), pode haver divergência pequena entre o `DU_passados` calculado em Python e a soma de dias da planilha. Em meses com feriado, vale uma conferência rápida: o `DU_passados` deve bater com a média de `DiasTrabalhados` dos consultores que trabalharam o mês inteiro sem férias/licença.

---

## Regra de Experiência

- Um funcionário está em **período de experiência** se tiver **menos de 90 dias corridos** desde a `DataAdmissao`
- A contagem é em **dias corridos** (não dias úteis, não meses de calendário)
- **Exemplo:** Admitido em 15/04 → experiência encerra em 14/07 (90 dias depois). No dia 90 a pessoa já é efetivada.

---

## Cruzamento com Outras Planilhas

A planilha de Usuários é a **fonte da verdade do funcionário** e pode ser cruzada com as outras duas bases. **A chave de cruzamento depende de com qual base vamos cruzar**, porque cada base traz um identificador diferente do funcionário:

| Base de destino | Identificador que ela traz | Chave a usar |
|---|---|---|
| **Produção** (`Producao.xlsx`) | Só a **matrícula** (não tem CPF) | Cruzar por `Matricula` |
| **FVE** (sistema do Santander) | Só o **CPF** (não tem matrícula) | Cruzar por `CPF` |

- **Cruzando com a Produção** → usar `Matricula`. A produção identifica o vendedor apenas pela matrícula, então é por ela que se enriquece o registro com nome, hierarquia e status vindos de Usuários.
- **Cruzando com o FVE** → usar `CPF`. O FVE (onde o consultor aparece como "promotor") identifica a pessoa apenas pelo CPF, então o `CPF` de Usuários é a ponte.
- **Por `Nome_Supervisor` / `Nome_Coordenador`**: para agrupar equipes hierarquicamente dentro da própria base de Usuários.

> Regra prática: **Produção = matrícula, FVE = CPF.** Escolher a chave errada não casa os registros.

---

## Observações Gerais

- Sempre filtrar pelos **três cargos principais** (Consultor, Supervisor, Coordenador) salvo instrução contrária
- Ao apresentar dados de equipe, respeitar a **hierarquia**: Coordenador → Supervisor → Consultor
- Ao calcular métricas de produtividade, considerar apenas funcionários **ativos** (salvo pedido específico)
- Remoto e presencial **sempre separados** em qualquer análise
