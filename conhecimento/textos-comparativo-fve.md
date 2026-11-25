---
name: textos-comparativo-fve
description: "Use quando o usuário pedir para gerar, atualizar ou reescrever os textos de e-mail do comparativo FVE. Esses textos acompanham o Dashboard Comparativo FVE e são enviados por e-mail aos coordenadores da AK. Não gerar via código — escrever diretamente no chat."
---

# Skill: Textos do Comparativo FVE

## O que é

O comparativo FVE compara os primeiros N dias úteis do mês atual contra os
primeiros N dias úteis do mês anterior, usando dados do FVE (sistema Santander).
Os textos são o corpo do e-mail que acompanha o print do dashboard, enviados
pelo Abdiel a cada coordenador da AK.

---

## Regras de entrega

1. **Gerar no chat, nunca por código.** Não existe script de geração de texto.
   O Claude escreve os textos diretamente na conversa para o usuário copiar.

2. **Cada texto em seu próprio bloco de código** para que o usuário
   clique no botão Copiar e cole direto no e-mail. Um bloco por
   coordenador, sem misturar.

3. **Emojis**: usar com moderação para tornar a leitura mais agradável e
   leve. Bons usos:
   - Foguete para destaques de performance excepcional
   - Gráfico de barras para números e métricas
   - Seta pra cima para crescimento, seta pra baixo para queda
   - Alvo para metas e oportunidades
   - Braço forte para incentivo e força de time
   - Check verde para positivo e parabéns
   - Alerta para pontos de atenção
   Uns 4 a 6 emojis por texto, máximo.

4. **Tom comercial e motivacional.** Esses textos vão para coordenadores
   de equipe comercial. O tom deve:
   - Celebrar quem está bem: parabenizar, reconhecer, usar linguagem como
     "parabéns", "excelente trabalho", "resultado completo"
   - Incentivar quem está bem a ir mais longe: "vamos time", "mantém esse
     ritmo", "tem tudo pra ser o melhor mês"
   - Para quem está mal: NÃO usar tom punitivo. Falar em oportunidade,
     potencial, destravar, criar oportunidade. Ex: "tem oportunidade de
     recuperar", "o time tem potencial", "precisa criar essa oportunidade"
   - Ser leve e agradável de ler, não um relatório frio de números

5. **Insights obrigatórios**: não apenas listar números (eles vão ver os
   números nos gráficos). Identificar:
   - Se o problema é de volume (indicações) ou conversão (funil travando)
   - Supervisores que se destacaram positiva ou negativamente, e por quê
   - Padrões (ex: indicações subindo mas contas não acompanhando)
   - Pipeline aberto que pode mudar o cenário nos próximos dias
   - Casos individuais que merecem ação (zerados, quedas bruscas, saltos)

6. **Não seguir o modelo rigidamente.** O arquivo de referência
   (Dashboards/Texto_Email_FVE_VisaoGeral.md) mostra a estrutura habitual,
   mas o texto deve se adaptar ao que os dados mostram.

---

## Regra de quem pode ser citado (nome por nome)

Só entra no texto quem ainda está na operação. Antes de citar qualquer
supervisor, conferir a lista do dashboard.

- **Nunca citar supervisão desligada** em destaque, em "onde ficar de olho",
  em "zerados" ou em qualquer ponto de atenção. Não faz sentido cobrar ou
  comentar o desempenho de quem não está mais na equipe. O erro clássico:
  o desligado teve indicação e conta aberta no mês passado, então aparece na
  base como uma queda de 100% e vira "ponto de atenção" sozinho.
- **A fonte é o `Saida/Resumo_FVE_*.json`.** A lista `supervisores` de cada
  coordenação já vem filtrada e é a única que pode ser citada nominalmente.
  Os nomes retirados ficam em `supervisores_ocultos`, e o critério está
  escrito em `regra_detalhamento`.
- **O critério do filtro**: sai do detalhamento a supervisão sem responsável
  ativo em `Usuarios_Atual` (desligado ou rótulo de vaga tipo `TBA ...`) que
  também não tem nenhum consultor ativo abaixo dela. Supervisor desligado que
  ainda tem consultor ativo CONTINUA aparecendo, porque aquele time existe e
  precisa de dono.
- **Total ≠ soma do detalhamento.** Os números totais (cards, total da
  coordenação, ritmo, conversão) trazem tudo, inclusive o que veio de
  supervisão já desligada. Quando houver `supervisores_ocultos`, cabe uma
  frase curta explicando que o total é o resultado inteiro e o detalhamento
  mostra só quem está ativo. Não citar o nome do desligado nessa frase quando
  o texto for para o coordenador em tom de cobrança; basta a explicação.

---

## Regra do Ritmo Diário

O dashboard sempre mostra a seção de ritmo diário e necessidade (quantas
contas/dia pra igualar o mês anterior). Essa seção fica no gráfico, mas:

- **Se os dois meses têm a mesma quantidade de dias úteis**: NÃO incluir
  a seção de ritmo no texto. Quando os meses são iguais em período, o
  comparativo direto (cresceu/caiu X%) já diz tudo. O ritmo diário fica
  redundante. Manter o marcador [Imagem 3] pro print do gráfico, mas
  sem texto descritivo sobre ritmo.

- **Se os meses têm dias úteis diferentes**: incluir a seção de ritmo
  normalmente, porque aí a comparação direta de volume não funciona e
  o ritmo/dia vira a métrica justa.

Verificar os dias úteis de cada mês antes de escrever.

---

## Textos a gerar

São 7 textos (ou mais, se a estrutura de coordenadores mudar):

1. Visão Geral Presencial — enviada a todos os coordenadores
2. Maysa Souza Moreira — coordenação presencial
3. Leandro Augusto de Pontes Fidelis — coordenação presencial
4. Marcio Sckio — coordenação presencial
5. Marcio Anacleto da Silva — coordenação presencial
6. Antonio Carlos Pereira da Costa — coordenação presencial
7. Remoto (Mariana Freire Kruger) — coordenação remota

Se a estrutura mudar, o usuário vai informar.

---

## Onde buscar os dados

A pasta do projeto é Comparativo no computador do usuário.

1. Resumo FVE — Saida/Resumo_FVE_*.json é a fonte oficial dos números e da
   lista de quem pode ser citado (`supervisores` / `supervisores_ocultos`).
2. Dashboard FVE — o HTML em Saida/Dashboard_Comparativo_FVE_*.html
   tem os mesmos números já formatados.
3. FVE CSV — Dados/FVE AK.csv e Dados/FVE JGK.csv para análise
   complementar (pipeline aberto, distribuição de status, negadas,
   ritmo por dia, promotores individuais).
4. Usuarios_Atual — Dados/Usuarios_Atual.xlsx se precisar de hierarquia ou
   para confirmar se alguém está ativo.

Fluxo: ler o resumo JSON para números oficiais, rodar análise no CSV via
device_bash para insights extras, cruzar os dois para escrever.

---

## Estrutura sugerida de cada texto

Adaptar conforme o que os dados pedem:

- Título com nome do coordenador
- Contexto breve (janela, fonte)
- Números principais com significado e tom motivacional
- [Imagem 1]
- Resultado por supervisão/coordenação com insights e reconhecimento
- [Imagem 2]
- [Imagem 3] (print do ritmo — sempre manter o marcador pro gráfico)
- Diagnóstico, oportunidades e mensagem de incentivo
- [Imagem 4]

---

## O que NÃO fazer

- Não gerar arquivos na pasta Dashboards para textos
- Não rodar scripts Python para gerar texto
- Não usar tom frio, punitivo ou de cobrança — sempre motivacional
- Não repetir frases boilerplate em todos os textos
- Não mandar tudo em um bloco só — separar por coordenador
- Não incluir seção de ritmo diário no texto quando os meses têm
  dias úteis iguais
- Não citar supervisão desligada em destaque, queda, zerado ou ponto de
  atenção — usar sempre a lista `supervisores` do resumo JSON