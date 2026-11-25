---
name: "diaria-relatorio-ak"
description: "Gera a Diária do Relatório Diário AK (Conta PJ por consultor, supervisor e coordenador) a partir do relatório anterior, da Produção e do Usuarios_Atual, batendo com os supervisores."
---

# Diária — Relatório Diário AK

Atualiza o arquivo **Relatório Diário DD.MM.AAAA.xlsx** com a produção do dia, no mesmo modelo, e garante que a aba **Por Supervisor** feche com a aba **Conta PJ - Consultor** e com o portal (produção por supervisor).

Usar junto com `contextoak`, `producaoak`, `usuariosak` e `cruzamentodiariaak`. Regras de produto, status e pontuação vêm de lá.

Validada em 15/10/2026: os 35 supervisores bateram 100% com a produção do portal.

## Entradas (identificar pelo conteúdo, não pelo nome)

| Arquivo | Como reconhecer |
|---|---|
| Relatório Diário anterior | .xlsx com abas `Conta PJ - Consultor`, `Por Supervisor`, `Por Coordenador` e as ocultas `Dinamica Atuando` e `Dados Conta PJ` |
| Produção | .xlsx com Cnpj, Matricula, Produto, Status, DataBase, Pontos, OportunidadesDePontos, PontuacaoDigitada, Tipo_Consultor |
| Usuários | .xlsx com Matricula, NomeUsuario, Cargo, Nome_Supervisor, Nome_Coordenador, Situacao, DataDesligamento, Regiao, Rede |

Ler as planilhas com `engine='calamine'` (`pip install python-calamine --break-system-packages`). Matrícula sempre como texto sem `.0`.

**O openpyxl não abre o relatório** (as tabelas dinâmicas têm itens calculados "Fórmula1/2/3" e dão erro). Editar o arquivo **direto no XML** (descompactar, alterar e recompactar). Nunca recriar o arquivo do zero.

## Período

- A produção pode vir exportada com o ano todo. Usar **apenas o mês corrente pela `DataBase`** (ex.: `DataBase` em outubro/2026).
- Não filtrar Status para somar pontos (cancelados já têm 0).
- Informar no fim a última `DataDigitacao` (horário de corte do export).

## Escopo

- Coordenadores do relatório: os que aparecem na aba Por Coordenador (hoje LEANDRO AUGUSTO DE PONTES FIDELIS, MARCIO SCKIO, ARAGON ARAUJO DE ARAGAO e GUSTAVO KRUGER).
- Produção: tudo do mês, **exceto `Tipo_Consultor = Remoto`** (equipe da Mariana). Consultores **Remoto_Brasil** que estão em equipes presenciais **entram**, como sempre entraram.
- Supervisores válidos: os nomes da coluna B da aba Por Supervisor (inclui os TBA e quem está com zero, como Henry).

## Montagem das linhas (tabela `dados`, aba Conta PJ - Consultor)

**Lista A — usuários:** `Cargo = CONSULTOR` e `Nome_Coordenador` em um dos coordenadores do relatório.
- POSIÇÃO: `DataDesligamento` preenchida → `DESLIGADO`; `Situacao` = Férias → `FÉRIAS`; outra Situacao → `LICENCA`; vazia → `ATIVO`.
- Desligado só entra se o desligamento foi no mês corrente ou se ele tem produção no mês.
- Supervisor, coordenador, região, rede, admissão (DT INÍCIO) e desligamento (DT FIM) vêm do Usuarios_Atual.

**Lista B — matrículas órfãs** (na produção do mês, fora do Usuarios_Atual):
- POSIÇÃO = `DESLIGADO` (não conta em Atuando, mas os pontos entram nos totais).
- Nome, supervisor, região e rede vêm da produção (último registro).
- Coordenador = coordenador **atual** do supervisor (pela linha do supervisor no Usuarios_Atual); se não achar, usar o da produção. Isso evita o mesmo supervisor aparecer sob dois coordenadores.
- Só entra se o supervisor dela estiver na lista de supervisores válidos.

**Ficam fora e vão para o aviso ao usuário:**
- Produção lançada pelo próprio supervisor (cargo SUPERVISOR), que na produção aparece sob "TBA ...". Ex.: Eder de Jesus Santos e Soraya Alves da Silva Ramos.
- Órfãs de supervisores que não estão no relatório (ex.: Jessica Guimarães Costa, Evelin Caren Lima Bispo, Natalie Helena Slemer Ferreira, Renan Senne de Castro, Bruno Oliveira). Informar pontos de cada um e perguntar se quer incluir em alguma equipe.

Ordenar por Coordenador → Supervisor → (usuários antes de órfãos) → Nome.

## Colunas por consultor (mês pela DataBase)

| Coluna | Cálculo |
|---|---|
| QTDADE CNPJ (K) | CNPJs distintos de `CONTA_CORRENTE_PJ` com Status fora de CANCELADO/ANALISE_CANCELAMENTO |
| PONTUAÇÃO DIGITADA - M0 (M) | soma de `PontuacaoDigitada` em `CONTA_CORRENTE_PJ` |
| OPORTUNIDADE / PONTOS REAIS - CONTA (P/Q) | `OportunidadesDePontos` / `Pontos` de `CONTA_CORRENTE_PJ` |
| OPORTUNIDADE / PONTOS REAIS - GET (R/S) | idem `CREDENCIAMENTO` |
| ... - CONTA - M2 (T/U) | idem `CONTA_CORRENTE_PJ_M2` |
| ... - GET - M2 (V/W) | idem `CREDENCIAMENTO_M2` |
| OPORTUNIDADE TOTAL (N) / PONTOS REAIS TOTAL (O) | soma das quatro oportunidades / dos quatro pontos |

Colunas J ("1") e L ("Coluna2") ficam vazias.

## Escrita no XML

Arquivos: `sheet1` = Conta PJ - Consultor, `sheet2` = Por Supervisor, `sheet3` = Dinamica Atuando, `sheet4` = Dados Conta PJ, `sheet5` = Por Coordenador (conferir em `xl/workbook.xml` + rels).

1. **sheet1:** substituir as linhas 7 a 537 (a tabela `dados` vai de A6:W537; manter esse ref). Linhas de dados com os estilos: A=110, B/C/D=106, E/F=104, G/H=105 (datas como serial do Excel), I=103, J=22, K=112, L=113, M=112, N=120, O–W=112. Textos como `t="inlineStr"`. Linhas que sobrarem ficam em branco com os mesmos estilos (G/H=111, E/F=106). Se passar de 531 linhas, aumentar o ref da tabela em `xl/tables/table1.xml`. Atualizar o valor em cache de K5 e M5:W5 (totais). Ajustar o painel congelado para `topLeftCell="A7"`.
2. **Pivots:** colocar `refreshOnLoad="1"` nos dois `pivotCacheDefinition` (o Excel atualiza ao abrir). Também atualizar os valores já exibidos para quem abrir sem atualizar:
   - sheet3 (Atuando): contagem de linhas com POSIÇÃO ATIVO ou FÉRIAS por supervisor, por coordenador e Total Geral.
   - sheet4 (Dados Conta PJ), colunas B–J nesta ordem: Digitada, Pts GET, Opp Conta, Pts Conta, Opp GET, Opp Conta M2, Pts Conta M2, Opp GET M2, Pts GET M2. Por supervisor, coordenador e Total Geral.
3. **sheet2 (Por Supervisor):** linhas de supervisor 10–20, 22–33, 35–40, 42–47; subtotais 21, 34, 41, 48; Total Geral 49. Atualizar cache de E (Atuando), F=E/D, H, I, J, L, M, O, P, R, S, U=I+L+O+R, V=J+M+P+S, Z=(I+J+L+M)/Y. Subtotal = soma do bloco; total = soma dos subtotais. Não mexer em D (Capacity) nem Y (Meta).
4. **sheet5 (Por Coordenador):** linhas 7–10 e total 6. D=Atuando, E=D/C, G, H, I, K, L, N, O, Q, R, T=H+K+N+Q, U=I+L+O+R, X=(H+I+K+L)/W. Não mexer em C nem W.
5. Em `xl/workbook.xml`, `calcPr` com `fullCalcOnLoad="1"`; remover `xl/calcChain.xml` (e sua entrada em `[Content_Types].xml` e em `workbook.xml.rels`).
6. Recompactar com `[Content_Types].xml` primeiro: `zip -X -D out.xlsx '[Content_Types].xml' && zip -r -X -D out.xlsx . -x '[Content_Types].xml'`.

Para trocar o valor de uma célula: localizar `<c r="REF" ...>`, manter atributos (sem o `t`) e a `<f>` se houver, e gravar `<v>novo</v>`.

## Validação obrigatória (antes de entregar)

1. Total da aba Por Supervisor (linha Total Geral) = total da aba Conta PJ - Consultor, coluna a coluna.
2. Para cada supervisor do relatório: soma das linhas dele = soma da produção do mês com `NomeSupervisor` = ele (visão do portal), em Digitada, Pontos e Oportunidades. Diferença precisa ser zero; se não for, investigar antes de entregar.
3. Todo supervisor das linhas existe na aba Por Supervisor e na pivot Dados Conta PJ.
4. Abrir com calamine (e, se houver, converter com `soffice --headless --convert-to xlsx`) para garantir que o arquivo abre.

## Entrega

- Nome: `Relatório Diário DD.MM.AAAA.xlsx` com a data de hoje. Se houver pasta conectada, salvar ao lado do relatório anterior.
- Mensagem curta: mês usado e horário de corte; total de pontos digitados e reais; confirmação de que os supervisores bateram; quantas órfãs entraram; a lista do que ficou fora (com pontos) e a pergunta se deve incluir. Lembrar que as dinâmicas atualizam ao abrir no Excel.