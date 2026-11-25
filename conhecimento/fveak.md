---
name: fveak
description: >
  Use esta skill sempre que o usuário mencionar a planilha FVE, o arquivo FVE_AK,
  o relatório do sistema do banco (Santander), indicações, link do cliente,
  status de abertura de conta no banco, devoluções, negadas, contas em análise,
  contas em abertura web, etapa cliente, ou qualquer análise sobre o funil de
  indicação que acontece ANTES da conta virar produção. Use em conjunto com
  UsuariosAK (para trazer nome do promotor, supervisor e coordenador via CPF)
  e, quando o usuário quiser comparar funil-vs-produção, com ProducaoAK.
---

# Skill: Planilha FVE (FVE_AK)

Esta skill define como interpretar e processar o relatório do **FVE** —
o sistema do Santander onde os consultores da AK fazem as indicações dos
clientes. É o lado **banco** da operação, antes de virar produção.

---

## Arquivos

São **dois arquivos**, um por projeto, ambos no mesmo formato (`.csv`,
separador `;`, encoding latin-1/utf-8):

| Arquivo | Projeto |
|---|---|
| `FVE_AK` | **Presencial** |
| `FVE_JGK` | **Remoto** |

O relatório é **extraído manualmente do FVE**. No momento da extração, o
analista seleciona Presencial ou Remoto no sistema do banco e baixa o
arquivo correspondente. **O conteúdo dos dois arquivos é estruturalmente
idêntico** — mesmas colunas, mesmos status, mesma lógica. **Nenhuma coluna
identifica o projeto**: o projeto é determinado **exclusivamente pelo nome
do arquivo**.

### Regra prática

- Recebeu `FVE_AK` → todos os registros são **Presencial**.
- Recebeu `FVE_JGK` → todos os registros são **Remoto**.
- Recebeu os dois → ao concatenar, **crie uma coluna `Projeto`** com o
  valor derivado do nome do arquivo antes do merge. Sem isso, a análise
  consolidada perde a dimensão de projeto.
- Recebeu um arquivo com nome diferente / renomeado → pergunte ao usuário
  qual projeto é, não chute.

---

## Colunas Principais

São essas que a gente realmente usa. As outras (DDD, TELEFONE, EMAIL,
RAZAO SOCIAL, CPF REPRESENTANTE, NOME REPRESENTANTE, NUMBER_PROCESS, ID,
ORIGEM, CNPJ CORBAN) ficam só como apoio.

| Coluna | Uso |
|---|---|
| `CNPJ EMPRESA` | **Identificador da conta.** Toda contagem é contagem de CNPJs |
| `DATA INDICACAO` | Data em que o consultor lançou a indicação no FVE. Formato `dd-mm-aaaa` |
| `DATA ULTIMA ATUALIZACAO` | Data da última mudança de status. **Esta é a data que vale para qualquer status atual** (Conta Aberta, Em Análise, Devolução, etc.) |
| `CPF PROMOTOR` | **Chave de cruzamento com Usuarios_Atual.** É o único vínculo com a hierarquia AK — o FVE não traz supervisor, coordenador nem executivo |
| `STATUS` | Status atual da indicação no FVE (texto) |
| `CODIGO STATUS` | Código do status (apoio; o canônico para análise é o `STATUS` texto) |

---

## Regra de Ouro das Datas

Esta é a regra mais importante da skill. Errar aqui contamina toda a análise.

| Pergunta | Coluna de data |
|---|---|
| Quantas **indicações** teve no período? | `DATA INDICACAO` |
| Quantas **contas abertas** teve no período? | `DATA ULTIMA ATUALIZACAO` (filtrar `STATUS = "Conta Aberta"`) |
| Quantas estão **em análise** / **devolução** / **negada** / qualquer status hoje? | `DATA ULTIMA ATUALIZACAO` |
| Quantas estão **paradas em abertura web** (cliente não clicou) há X dias? | `DATA ULTIMA ATUALIZACAO` |

> **Não confundir** "contas abertas no FVE" com "contas abertas na produção".
> São métodos de contagem diferentes:
> - **FVE**: status `Conta Aberta` filtrado por `DATA ULTIMA ATUALIZACAO`
> - **Produção (ProducaoAK)**: produto `CONTA_CORRENTE_PJ` filtrado pela data
>   de abertura da conta lá
>
> Os números **não batem exatamente** e isso é normal. O FVE é o que o banco
> registra, a Produção é o que entra no nosso sistema. Quando o usuário
> perguntar "contas abertas", **pergunte qual fonte ele quer** se o contexto
> não deixar claro.

---

## Cruzamento com Usuarios_Atual (UsuariosAK)

O FVE **não traz hierarquia**. Só vem `CPF PROMOTOR` e `NOME PROMOTOR`
(este último frequentemente em grafias diferentes — caixa alta, caixa baixa,
acentos, abreviações, "MARCELLI" sem sobrenome, etc.).

**A chave de join é sempre `CPF PROMOTOR`** contra o CPF do funcionário em
`Usuarios_Atual`. Depois do join você traz:
- Nome oficial do consultor (o do FVE não é confiável)
- Status do funcionário (ATIVO, LICENCIADO, DESLIGADO, FÉRIAS, EXPERIÊNCIA)
- Supervisor
- Coordenador
- Projeto (Presencial / Remoto) — **redundante com o nome do arquivo**,
  mas serve como validação cruzada. Se o CPF estiver marcado como Remoto
  em Usuarios_Atual mas apareceu no `FVE_AK` (Presencial), há
  inconsistência — reportar.

**Casos de borda no join:**
- CPF do FVE não encontrado em Usuarios_Atual → consultor pode ter sido
  desligado e removido da base, ou houve digitação errada. Reportar como
  "CPF sem vínculo na base de usuários", não descartar silenciosamente.
- CPF normalizado: tirar pontos, traços e espaços antes de comparar.
  Zerar à esquerda se vier com menos de 11 dígitos.

### Atenção: o "promotor" nem sempre é consultor

O FVE é um sistema do Santander, não da AK, e às vezes dá problema —
login do consultor cai, sessão trava, etc. Quando isso acontece, é
**comum** o consultor fazer a indicação **pela conta do supervisor ou do
coordenador** dele. Também acontece de supervisor ou coordenador
indicarem por conta própria. Resultado: o `CPF PROMOTOR` da linha pode
pertencer a alguém que **não é consultor**.

**Implicações práticas:**
- Depois do join com Usuarios_Atual, **olhe o cargo** do CPF, não assuma
  que é consultor.
- Em análises agregadas por cargo, **separe** indicações feitas
  por Consultor, Supervisor e Coordenador. Misturar tudo como "produção
  do consultor X" é errado quando o CPF na verdade é do supervisor dele.
- Para atribuir a indicação à equipe certa: se o CPF é de supervisor,
  a indicação pertence à **equipe daquele supervisor** (não dá pra saber
  qual consultor específico da equipe fez, então fica no nível do
  supervisor mesmo). Se é de coordenador, idem no nível do coordenador.
- **Não trate como erro nem como anomalia.** É comportamento esperado da
  operação. Só sinalize na análise quando o usuário pedir o recorte por
  cargo do indicador.

---

## Os Status do FVE

O FVE tem muitos status, mas estes são os que aparecem na prática:

| Status | Significado |
|---|---|
| `Em abertura - Web` | Cliente recebeu o link e **ainda não clicou**. Indicação fresca, parada no consultor/cliente |
| `Etapa Cliente` | Cliente clicou no link e está enviando documentação para o banco analisar |
| `Devolucao` | Banco recebeu a doc, achou problema (imagem ilegível, dado incorreto, etc.) e devolveu. Cliente precisa reenviar |
| `Em Analise` | Banco está analisando. Status **rapidíssimo** — costuma durar segundos a poucas horas |
| `Aguardando Liberacao` | Próximo passo depois de Em Análise. Também rápido. Conta praticamente vai abrir |
| `Aprovada` | Banco aprovou. Está prestes a virar Conta Aberta |
| `Conta Aberta` | **Status final de sucesso.** Conta efetivada no banco. É o que vira produção depois |
| `Negada` | Banco negou. Não adianta insistir, fim da linha para esse CNPJ |
| `Rejeitada Nao Abrir - Web` | Variante de negada, lado web. Fim da linha |
| `Direcionada para a agencia` | Banco mandou o cliente resolver presencialmente na agência. Sai do funil digital — na prática a AK costuma perder essa conta |

### Fluxo normal (caminho feliz)

```
Em abertura - Web   (consultor indicou, cliente nem abriu o link)
        ↓
Etapa Cliente       (cliente clicou e está mandando doc)
        ↓
Em Analise          (banco analisando — segundos/horas)
        ↓
Aguardando Liberacao (rápido também)
        ↓
Aprovada
        ↓
Conta Aberta        ✅ FIM, vira produção
```

### Desvios possíveis (a partir de Etapa Cliente)

```
Etapa Cliente ──→ Devolucao              (volta pra cliente reenviar)
              ──→ Negada                 ❌ fim
              ──→ Rejeitada Nao Abrir    ❌ fim
              ──→ Direcionada Agencia    ⚠️ sai do digital
```

### Agrupamento analítico

Para a maioria das análises, dá pra agrupar os status em três blocos:

- **Pipeline em aberto** (ainda pode virar conta): `Em abertura - Web`,
  `Etapa Cliente`, `Em Analise`, `Aguardando Liberacao`, `Aprovada`,
  `Devolucao` (cliente pode reenviar)
- **Sucesso**: `Conta Aberta`
- **Perda**: `Negada`, `Rejeitada Nao Abrir - Web`, `Direcionada para a agencia`

---

## Métricas Padrão

**Sempre que possível, faça o join com Usuarios_Atual primeiro** para
enriquecer com nome oficial, supervisor, coordenador e projeto. Sem isso a
análise fica anônima (só CPF) e cega para hierarquia.

### Volume

- **Indicações no período**: contar CNPJ EMPRESA filtrando `DATA INDICACAO`
- **Contas abertas no período**: contar CNPJ EMPRESA filtrando
  `STATUS = "Conta Aberta"` por `DATA ULTIMA ATUALIZACAO`
- **Pipeline em aberto hoje**: contar CNPJ EMPRESA dos status do bloco
  "Pipeline em aberto" (sem filtro de data — é foto do agora)

### Qualidade do promotor

- **Taxa de aprovação** = `Conta Aberta` / total de indicações com **decisão
  final** (excluindo pipeline em aberto). Mostrar também a taxa bruta
  (sobre todas as indicações) quando relevante, mas a justa é sobre as
  resolvidas.
- **Taxa de negação** = (`Negada` + `Rejeitada Nao Abrir - Web`) / decisões finais
- **Taxa de devolução** = `Devolucao` / total de indicações que chegaram pelo
  menos em `Etapa Cliente`

### Engajamento do cliente

- **Link parado** = `Em abertura - Web` com `DATA ULTIMA ATUALIZACAO`
  antiga (cliente nunca clicou). Oportunidade de followup do consultor.
- **Lembrar**: o link do FVE tem validade (regra de negócio do banco
  Santander — ver ContextoAK; geralmente 30 dias). Indicações em
  `Em abertura - Web` com mais de ~30 dias provavelmente já expiraram e
  precisam de nova indicação.

### Tempo de ciclo

- **Tempo até abertura** = `DATA ULTIMA ATUALIZACAO` − `DATA INDICACAO`
  para registros em `Conta Aberta`. Mediana por consultor / supervisor /
  coordenador.

---

## Cruzamento com ProducaoAK (Auditoria de Funil)

Quando o usuário pedir comparação FVE × Produção, ou perguntar "abriu no
banco mas não caiu na produção?", o join é por `CNPJ EMPRESA` (FVE) ↔
`CNPJ` (Produção).

**Gaps esperados que valem investigar:**
- CNPJ com `Conta Aberta` no FVE mas **sem registro** em Produção →
  pode ser conta que abriu mas ainda não foi lançada / problema de captura
- CNPJ em `Conta Aberta` no FVE mas em Produção a conta não está ativada →
  pendente de ativação (oportunidade do consultor)

---

## Princípios Inegociáveis

1. **Conte CNPJ, não linha.** Em tese cada linha já é um CNPJ único no
   período, mas valide com `nunique()` antes de afirmar números.
2. **Use a data certa.** Indicação → `DATA INDICACAO`. Qualquer status
   atual → `DATA ULTIMA ATUALIZACAO`. Confundir as duas é o erro mais comum.
3. **Projeto vem do nome do arquivo.** `FVE_AK` = Presencial, `FVE_JGK`
   = Remoto. O conteúdo do arquivo não diz, então a derivação tem que
   acontecer no carregamento — nunca depois.
4. **CPF é a chave.** Nome do promotor no FVE é ruidoso; nunca cruzar por
   nome quando há CPF.
5. **FVE ≠ Produção.** São fontes diferentes para a mesma realidade. Os
   números não batem. Ao reportar "contas abertas", deixe claro qual fonte
   está usando.
6. **Pipeline em aberto é foto, não filme.** Status atual não tem filtro de
   data de início — é o que está aberto hoje, fim.
