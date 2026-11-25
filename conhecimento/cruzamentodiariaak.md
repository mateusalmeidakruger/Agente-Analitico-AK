---
name: cruzamentodiariaak
description: >
  Use esta skill sempre que for necessário cruzar os dados da planilha de produção
  (Producao) com a planilha de usuários (Usuarios_Atual). Acione quando a análise
  envolver enriquecer registros de produção com dados do funcionário (nome, status,
  supervisor, coordenador), identificar consultores zerados (ativos sem produção),
  detectar produção lançada por desligados ou afastados, montar a equipe de um
  supervisor para análises individuais, ou qualquer análise que exija unir as
  duas planilhas pela matrícula. Sempre usar em conjunto com as skills UsuariosAK
  e ProducaoAK.
---

# Skill: Cruzamento Diária AK (Producao × Usuarios_Atual)

Esta skill define **a lógica de encontro** entre a planilha de produção
e a planilha de usuários. Não documenta colunas — para isso, ver
`ProducaoAK` e `UsuariosAK`.

> **Pressupõe `ContextoAK`** (vocabulário, hierarquia, princípios) e
> `ProducaoAK` + `UsuariosAK` (dicionário das colunas de cada planilha).
> Aqui só vive a regra do join.

---

## Princípio Central

> **`Usuarios_Atual` é a fonte da verdade para dados do funcionário.**

Mesmo que a planilha de produção contenha `NomeExecutivoLegal`,
`NomeSupervisor` e `NomeCoordenador`, esses campos **devem ser
descartados** na análise e substituídos pelos equivalentes vindos de
`Usuarios_Atual`.

Garante consistência e evita divergências causadas por atualizações de
equipe que já constam em Usuários mas ainda não foram refletidas na
produção.

---

## Chave de Cruzamento

| Campo na Producao | Campo em Usuarios_Atual |
|---|---|
| `Matricula` | `Matricula` |

O join é **sempre pela matrícula**. Nunca cruzar por nome.

---

## O que vem de cada planilha

- **De `Usuarios_Atual`** (fonte da verdade): Matrícula, Nome,
  Supervisor, Coordenador, Situação, Data de Admissão, Data de
  Desligamento, Dias Trabalhados, Projeção de Dias. *Definições e
  nomes exatos das colunas em `UsuariosAK`.*

- **De `Producao`**: tudo que descreve a venda em si — CNPJ, Tipo de
  projeto (`Tipo_Consultor`), datas do ciclo, Segmento, Produto,
  Status, Substatus, Pontos. *Definições e nomes exatos em
  `ProducaoAK`.*

---

## Tipos de Join

### LEFT JOIN de Producao → Usuarios_Atual (padrão)

Para analisar produção: partir da produção e trazer os dados do usuário.

```
Producao.Matricula → Usuarios_Atual.Matricula
```

- Matrícula da produção **existe** em Usuários → enriquecer normalmente
  com os campos de `Usuarios_Atual`
- Matrícula da produção **não existe** em Usuários → caso especial
  (ver abaixo)

### LEFT JOIN de Usuarios_Atual → Producao

Para identificar consultores zerados: partir dos usuários e verificar
se têm produção.

```
Usuarios_Atual.Matricula → Producao.Matricula
```

- Filtrar apenas funcionários **ativos** (sem desligamento e sem
  situação de licença) nos cargos de Consultor, Supervisor e
  Coordenador
- Se o usuário **não aparece** na produção → está **zerado** no período

---

## Casos Especiais

### Matrícula órfã (existe em Producao, não em Usuarios)

Significa que o funcionário foi **desligado em mês anterior** e saiu da
planilha de usuários. Regras:

- O status é **obrigatoriamente Desligado**
- Os campos de nome, supervisor e coordenador vêm da **própria
  produção** (`NomeExecutivoLegal`, `NomeSupervisor`,
  `NomeCoordenador`) — única exceção à regra geral, pois não há outra
  fonte disponível
- O registro **não é descartado** — entra nas métricas de produção
  normalmente
- É sinalizado no bloco de alertas como desligado com produção no
  período

### Funcionário desligado recente com produção

Funcionário presente em `Usuarios_Atual` com `DataDesligamento`
preenchida e com produção no período → sinalizar como **alerta crítico**
(produção lançada por desligado recente).

### Funcionário em licença com produção

Funcionário em licença (Situação preenchida com Afastado/Atestado/etc.)
com produção no período → sinalizar como **atenção** (verificar se é
lançamento retroativo).

### Nome divergente entre Producao e Usuarios

Ignorar a diferença — usar sempre `Usuarios_Atual`. A divergência pode
existir sem ser erro (mudança de nome civil, ajuste de cadastro).

---

## Montagem da Equipe de um Supervisor

Análises por equipe (boletins, dashboards individuais por supervisor)
exigem listar os subordinados de um supervisor específico. A equipe
**deve ser a união de duas fontes**:

### Lista A — Equipe atual (Usuarios_Atual)
```
Consultores com Matricula_Supervisor = matrícula_do_supervisor
                   E Cargo = CONSULTOR
```
> Filtrar `Cargo = CONSULTOR` é obrigatório: o próprio supervisor pode
> aparecer como subordinado de si mesmo na planilha (quando lança
> produção em nome próprio, como uma indicação no FVE).

### Lista B — Ex-equipe ativa na produção (matrículas órfãs)
```
Matrículas em Producao com NomeSupervisor = nome_do_supervisor
       que NÃO estão em Usuarios_Atual
```

São funcionários desligados em meses anteriores cuja produção ainda
aparece (especialmente comum no grupo M2, que reflete vendas de 2 meses
atrás).

### União: Equipe = A ∪ B

- **Lista A**: enriquecida normalmente por Usuarios_Atual (status =
  ATIVO/FÉRIAS/etc.)
- **Lista B**: status = DESLIGADO obrigatoriamente; nome vem da
  produção; **não entra no contador de consultores ativos**; **não
  entra no denominador da produtividade** (DiasTrabalhados = 0); **mas
  a produção e os pontos entram em todos os totais**

Sem esta união, o supervisor vê totais menores no boletim do que
encontra no portal — e essa divergência destrói a confiança no número.

---

## Regras de Padronização ao Cruzar

1. **Nome** → `NomeUsuario` de Usuarios_Atual
2. **Supervisor** → `Nome_Supervisor` de Usuarios_Atual
3. **Coordenador** → `Nome_Coordenador` de Usuarios_Atual
4. **Projeto (Presencial/Remoto)** → `Tipo_Consultor` da Producao
5. **Status do funcionário** → derivar pelas regras da `UsuariosAK`

Atenção aos nomes reais das colunas — Producao usa CamelCase sem
underscore (`NomeSupervisor`), Usuarios_Atual usa com underscore
(`Nome_Supervisor`).

---

## Separação Presencial × Remoto

O cruzamento **sempre respeita a separação dos projetos** (princípio
inegociável, ver `ContextoAK`):

- Usar `Tipo_Consultor` da produção como discriminador
- Ao cruzar com Usuários, manter o agrupamento — nunca misturar
  Presencial com Remoto
- Para identificação de quem é Remoto via Usuários (sem `Tipo_Consultor`),
  aplicar a regra da Mariana Kruger (ver `UsuariosAK`)

---

## Análises Típicas Habilitadas por Este Cruzamento

1. **Produção enriquecida** — cada linha da produção passa a ter nome,
   supervisor, coordenador e status vindos de Usuarios_Atual.
2. **Consultores zerados** — ativos sem nenhum registro na produção no
   período.
3. **Produção por equipe** — agrupamento Coord → Sup → Consultor usando
   a hierarquia de Usuarios_Atual.
4. **Equipe individual de supervisor** — união de equipe atual com
   matrículas órfãs ativas na produção do período (ver seção "Montagem
   da Equipe de um Supervisor").
5. **Alertas de integridade** — desligados, afastados, matrículas
   órfãs.
6. **Produtividade por dia trabalhado** — cruzamento de `DiasTrabalhados`
   com volume de produção.

---

## Observações Gerais

- **Nunca usar os campos de nome, supervisor ou coordenador da produção
  como referência** — exceto no caso de matrícula órfã, onde são a
  única fonte disponível.
- Ao apresentar resultados, respeitar a hierarquia: Coordenador →
  Supervisor → Consultor.
- Remoto e Presencial sempre separados, salvo instrução explícita.
- Regras de status, dias trabalhados e experiência seguem integralmente
  `UsuariosAK`.
- Regras de filtro por Status, Substatus e Produto seguem integralmente
  `ProducaoAK`.
