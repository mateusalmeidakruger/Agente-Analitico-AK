---
name: "parcial-consolidada-ak-v2"
description: "Gera a Parcial Consolidada da AK do mês corrente (produção Conta PJ x FVE AK+JGK, lista Fora e base de usuários). Use no lugar da parcial-consolidada-ak quando pedirem a Parcial."
---

# Parcial Consolidada AK (v2)

Compara o que foi **digitado no portal AK** (Produção) com o que o **banco registrou no FVE** (AK + JGK) no **mês de referência**, com a hierarquia vinda da base de usuários e excluindo os CNPJs da lista Fora.

Validada em 06/10/2026: reproduziu 100% a "Parcial Correta" de outubro/2026 (811 linhas, mesmos CNPJs, status, datas, hierarquia, CPF e projeto).

Use junto com contextoak, producaoak, fveak e usuariosak quando disponíveis.

## Entradas (identificar pelo conteúdo, nunca pelo nome)

| Arquivo | Como reconhecer | Observações |
|---|---|---|
| Produção | .xlsx com Produto, Cnpj, Matricula, DataReferencia, Status | Export do portal. Tem estilos inválidos: ler com `engine='calamine'` (`pip install python-calamine`) |
| FVE (AK e JGK) | .csv com NUMBER_PROCESS, CPF PROMOTOR, CNPJ EMPRESA | `;`, cp1252, **com aspas** (não usar `quoting=3`). Datas podem vir `dd-mm-aaaa` ou `dd/mm/aaaa` |
| Usuários | .xlsx com Matricula, CPF, Cargo, Nome_Supervisor, DataRef | Normalmente dois (mês atual e anterior). Prioridade pela DataRef |
| Lista Fora | planilha com colunas CNPJ e "Não Pode" | **Obrigatória**. Excluir todo CNPJ da lista (a coluna "Não Pode" sempre traz "Fora") |

Ignorar arquivos que começam com `~$` (temporários do Excel) e Parciais já geradas.

## Quando parar e pedir ao usuário (não seguir sem resolver)

- Faltou algum arquivo obrigatório, ou há mais de uma produção / mais de uma lista Fora.
- **CNPJ em notação científica** no FVE (ex.: `6,34181E+13`): o CSV foi aberto e salvo no Excel e os dígitos se perderam. Pedir para baixar o relatório de novo **sem abrir no Excel** (se precisar conferir, abrir no Bloco de Notas). Não tentar recuperar.
- Alguma data do FVE ficou ilegível após a conversão (sinal de formato novo).
- A pasta não está acessível: pedir acesso à pasta (ex.: `Downloads\Diária`).

## Regras

### Mês de referência
- Padrão: o mês predominante da `DataReferencia` da produção (normalmente o **mês corrente**). Se o usuário pedir outro mês, usar o dele.
- Informar o mês usado e a **última DataDigitacao** da produção (horário de corte do export). Exports em horários diferentes geram diferenças esperadas.

### Usuários
1. Empilhar todos os arquivos; manter Cargo em {CONSULTOR, SUPERVISOR, COORDENADOR/GERENTE}.
2. CPF = texto com 11 dígitos (tirar `.0`, só dígitos, zeros à esquerda). Matrícula = texto sem `.0`.
3. Ordenar por DataRef decrescente e criar dois lookups sem duplicatas: por CPF e por Matricula (fica a linha mais recente; quem não está no arquivo novo vem do anterior).
4. ClasificacaoUsuarios vazia = "Presencial". Valores existentes: **Presencial, Remoto, Remoto_Brasil**.

### Produção
1. Produto = `CONTA_CORRENTE_PJ`.
2. Manter as linhas com `DataReferencia` no mês de referência.
3. Colunas: Cnpj, Matricula, NomeExecutivoLegal, NomeSupervisor, NomeCoordenador, DataBase, Status. Trazer CPF pelo lookup de Matricula.

### FVE
1. Empilhar AK + JGK. Converter as duas datas aceitando `-` ou `/`.
2. Manter as linhas com **DATA INDICACAO ou DATA ULTIMA ATUALIZACAO no mês de referência**.
3. Normalizar CPF PROMOTOR e trazer NomeUsuario, Nome_Supervisor, Nome_Coordenador pelo lookup de CPF.

### Consolidação
1. Full outer join Produção x FVE por Cnpj = CNPJ EMPRESA (inteiro).
2. Colunas "Novo" (primeiro valor; se vazio, o segundo): CNPJ (Cnpj → CNPJ EMPRESA), Executivo (NomeUsuario → NomeExecutivoLegal), Supervisor (Nome_Supervisor → NomeSupervisor), Coordenador (Nome_Coordenador → NomeCoordenador), CPF (CPF PROMOTOR → CPF da produção), Data Referencia (DataBase → DATA ULTIMA ATUALIZACAO).
3. Status vazio = **"NÃO DIGITADO NO PORTAL AK"**.
4. Excluir os CNPJs da lista Fora.
5. Projeto = ClasificacaoUsuarios pelo lookup de CPF Novo.
6. Ordenar por Coordenador Novo e Supervisor Novo.

### Saída
- Arquivo `Parcial Consolidada - <Mês> <Ano>.xlsx`, aba "Parcial Consolidada", na própria pasta.
- Colunas: `CNPJ Novo | Executivo Novo | Supervisor Novo | Coordenador Novo | Status | Data Referencia Novo | CPF Novo | Projeto`.
- CNPJ formato `0`, data `dd/mm/aaaa`, CPF texto, cabeçalho em negrito, filtro e primeira linha congelada.
- Se o arquivo estiver aberto no Excel, salvar como `v2`, `v3`... e avisar.

## Comportamentos esperados (não são erro)

- CNPJs que começam com zero aparecem com 12 ou 13 dígitos no Excel (gravado como número).
- Algumas linhas "NÃO DIGITADO" têm Data Referencia anterior ao mês: no FVE a última atualização às vezes é mais antiga que a indicação.
- A ordem das linhas dentro do mesmo supervisor pode diferir da Parcial do Power Query; o conteúdo é o mesmo.
- Referência de volume: outubro/2026 com produção até 06/10 08:34 deu 811 linhas (DIGITADO 643, NÃO DIGITADO 162, ANALISE_CANCELAMENTO 6). Mês fechado de setembro/2026: ~6.680 linhas.

## Script (validado)

Rodar na máquina do usuário, com a pasta conectada: `python3 parcial_v2.py "<pasta>" [AAAA-MM]`. Se faltar o leitor: `pip install python-calamine`.

```python
import pandas as pd, numpy as np, glob, os, sys, re
from openpyxl.styles import Font

PASTA = sys.argv[1]                     # pasta com os arquivos
REF   = pd.Period(sys.argv[2]) if len(sys.argv) > 2 else None   # ex.: 2026-10 (opcional)

def ler_xlsx(f):
    try:    return pd.read_excel(f, sheet_name=0, engine='calamine')   # export do portal tem estilos inválidos
    except Exception: return pd.read_excel(f, sheet_name=0)
def ler_csv(f): return pd.read_csv(f, sep=';', encoding='cp1252', dtype=str)  # COM aspas: não usar quoting=3
def txt(s):  return s.astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
def cpf(s):
    t = txt(s).str.replace(r'\D', '', regex=True)
    return t.str.zfill(11).where(s.notna() & (t != ''))
def data_fve(s):  # aceita dd-mm-aaaa e dd/mm/aaaa
    return pd.to_datetime(s.astype(str).str.strip().str.replace('/', '-'), format='%d-%m-%Y', errors='coerce')

# ---------- 1. Identificar arquivos pelo conteúdo ----------
arqs = [f for f in glob.glob(os.path.join(PASTA, '**', '*.*'), recursive=True)
        if not os.path.basename(f).startswith('~$') and f.lower().endswith(('.xlsx', '.csv'))
        and not os.path.basename(f).lower().startswith('parcial')]
prod, users, fves, fora = [], [], [], []
for f in arqs:
    try: cols = set((ler_csv(f).head(0) if f.lower().endswith('.csv') else ler_xlsx(f).head(0)).columns)
    except Exception as e: print('Não li', f, e); continue
    if {'NUMBER_PROCESS', 'CPF PROMOTOR', 'CNPJ EMPRESA'} <= cols: fves.append(f)
    elif {'Produto', 'Cnpj', 'Matricula', 'DataReferencia', 'Status'} <= cols: prod.append(f)
    elif {'Matricula', 'CPF', 'Cargo', 'Nome_Supervisor', 'DataRef'} <= cols: users.append(f)
    elif {'CNPJ', 'Não Pode'} <= cols: fora.append(f)
erros = []
if len(prod) != 1:  erros.append(f'Produção: esperado 1 arquivo, achei {len(prod)} {prod}')
if not users:       erros.append('Usuários: nenhum arquivo com DataRef')
if not fves:        erros.append('FVE: nenhum CSV')
if len(fora) != 1:  erros.append(f'Lista Fora: esperado 1 arquivo, achei {len(fora)}')
if erros: sys.exit('PARAR E PEDIR AO USUÁRIO:\n- ' + '\n- '.join(erros))

# ---------- 2. Usuários (prioridade pela DataRef mais recente) ----------
u = pd.concat([ler_xlsx(f).assign(Arquivo=os.path.basename(f)) for f in users])
print('Usuários:', u.groupby('Arquivo')['DataRef'].max().astype(str).to_dict())
u = u[u['Cargo'].isin(['CONSULTOR', 'SUPERVISOR', 'COORDENADOR/GERENTE'])].copy()
u['CPF'] = cpf(u['CPF']); u['Matricula'] = txt(u['Matricula'])
u['DataRef'] = pd.to_datetime(u['DataRef'], errors='coerce', dayfirst=True)
u['ClasificacaoUsuarios'] = u['ClasificacaoUsuarios'].fillna('Presencial')
u = u.sort_values('DataRef', ascending=False, kind='stable')
u_cpf = u.dropna(subset=['CPF']).drop_duplicates('CPF'); u_mat = u.drop_duplicates('Matricula')
ref_max = u['DataRef'].max()

# ---------- 3. Produção ----------
p = ler_xlsx(prod[0])
p = p[p['Produto'] == 'CONTA_CORRENTE_PJ'].copy()
p['_mes'] = pd.to_datetime(p['DataReferencia'], errors='coerce').dt.to_period('M')
if REF is None: REF = p['_mes'].mode()[0]
print('Mês de referência:', REF, '| meses na produção:', p['_mes'].value_counts().to_dict())
print('Produção: última DataDigitacao =', pd.to_datetime(p['DataDigitacao'], errors='coerce').max())
p = p[p['_mes'] == REF]
p = p[['Cnpj', 'Matricula', 'NomeExecutivoLegal', 'NomeSupervisor', 'NomeCoordenador', 'DataBase', 'Status']].copy()
p['Matricula'] = txt(p['Matricula'])
p = p.merge(u_mat[['Matricula', 'CPF']], on='Matricula', how='left')

# ---------- 4. FVE (AK + JGK) ----------
f = pd.concat([ler_csv(x).assign(Origem=os.path.basename(x)) for x in fves])
sci = f['CNPJ EMPRESA'].astype(str).str.contains(r'E\+', na=False)
if sci.any(): sys.exit(f'PARAR: {sci.sum()} CNPJs em notação científica em {f.loc[sci,"Origem"].unique()}. '
                       'Pedir para baixar o relatório de novo SEM abrir no Excel.')
for c in ['DATA INDICACAO', 'DATA ULTIMA ATUALIZACAO']:
    f[c] = data_fve(f[c])
    if f[c].isna().any(): sys.exit(f'PARAR: {f[c].isna().sum()} datas ilegíveis em {c}')
mi, ma = f['DATA INDICACAO'].dt.to_period('M'), f['DATA ULTIMA ATUALIZACAO'].dt.to_period('M')
f = f[(mi == REF) | (ma == REF)].copy()
print('FVE no mês:', f['Origem'].value_counts().to_dict())
f['CPF PROMOTOR'] = cpf(f['CPF PROMOTOR'])
f = f.merge(u_cpf[['CPF', 'NomeUsuario', 'Nome_Supervisor', 'Nome_Coordenador']],
            left_on='CPF PROMOTOR', right_on='CPF', how='left').drop(columns='CPF')

# ---------- 5. Consolidação ----------
p['Cnpj'] = pd.to_numeric(p['Cnpj'], errors='coerce').astype('Int64')
f['CNPJ EMPRESA'] = pd.to_numeric(f['CNPJ EMPRESA'], errors='coerce').astype('Int64')
c = p.merge(f, left_on='Cnpj', right_on='CNPJ EMPRESA', how='outer')
o = pd.DataFrame({
    'CNPJ Novo':            c['Cnpj'].fillna(c['CNPJ EMPRESA']),
    'Executivo Novo':       c['NomeUsuario'].fillna(c['NomeExecutivoLegal']),
    'Supervisor Novo':      c['Nome_Supervisor'].fillna(c['NomeSupervisor']),
    'Coordenador Novo':     c['Nome_Coordenador'].fillna(c['NomeCoordenador']),
    'Status':               c['Status'].fillna('NÃO DIGITADO NO PORTAL AK'),
    'Data Referencia Novo': pd.to_datetime(c['DataBase'], errors='coerce').fillna(c['DATA ULTIMA ATUALIZACAO']),
    'CPF Novo':             c['CPF PROMOTOR'].fillna(c['CPF'])})
fz = ler_xlsx(fora[0]); fs = set(pd.to_numeric(fz['CNPJ'], errors='coerce').dropna().astype('int64'))
exc = o['CNPJ Novo'].isin(fs); print('Excluídos pela lista Fora:', o.loc[exc, 'CNPJ Novo'].tolist()); o = o[~exc]
o = o.merge(u_cpf[['CPF', 'ClasificacaoUsuarios', 'DataRef']], left_on='CPF Novo', right_on='CPF', how='left') \
     .drop(columns='CPF').rename(columns={'ClasificacaoUsuarios': 'Projeto'})
print('Pessoas vindas do arquivo de usuários mais antigo:', o[o['DataRef'] < ref_max]['CPF Novo'].nunique())
o = o.drop(columns='DataRef').sort_values(['Coordenador Novo', 'Supervisor Novo'], na_position='last')

# ---------- 6. Checagens ----------
print('Total:', len(o)); print('Status:', o['Status'].value_counts().to_dict()); print('Projeto:', o['Projeto'].value_counts(dropna=False).to_dict())
print('CNPJ vazio:', o['CNPJ Novo'].isna().sum())
d = o[o['CNPJ Novo'].notna() & o['CNPJ Novo'].duplicated(keep=False)]
print('CNPJs duplicados:', d['CNPJ Novo'].nunique(), d['CNPJ Novo'].unique().tolist()[:20])
print('Sem coordenador:', o['Coordenador Novo'].isna().sum(), '| sem supervisor:', o['Supervisor Novo'].isna().sum())
print('CPFs não achados nos usuários:', o.loc[o['Projeto'].isna(), 'CPF Novo'].unique().tolist())

# ---------- 7. Saída ----------
MESES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
base = os.path.join(PASTA, f'Parcial Consolidada - {MESES[REF.month-1]} {REF.year}')
out, n = base + '.xlsx', 2
while True:
    try:
        with pd.ExcelWriter(out, engine='openpyxl') as w:
            o.to_excel(w, sheet_name='Parcial Consolidada', index=False); ws = w.sheets['Parcial Consolidada']
            for cel in ws[1]: cel.font = Font(bold=True)
            ws.auto_filter.ref = ws.dimensions; ws.freeze_panes = 'A2'
            for r in ws.iter_rows(min_row=2):
                r[0].number_format = '0'; r[5].number_format = 'dd/mm/yyyy'; r[6].number_format = '@'
            for col, wd in zip('ABCDEFGH', [17, 40, 32, 32, 28, 14, 14, 14]): ws.column_dimensions[col].width = wd
        break
    except PermissionError:
        out = f'{base} v{n}.xlsx'; n += 1   # arquivo anterior aberto no Excel
print('SALVO:', out)

# ---------- 8. Comparar com Parcial de referência (se houver) ----------
refs = [x for x in glob.glob(os.path.join(PASTA, '*.xlsx')) if 'correta' in os.path.basename(x).lower()]
if refs:
    r = ler_xlsx(refs[0]); r['CNPJ Novo'] = pd.to_numeric(r['CNPJ Novo'], errors='coerce').astype('Int64')
    print('Comparação com', os.path.basename(refs[0]), '| só minha:', (~o['CNPJ Novo'].isin(r['CNPJ Novo'])).sum(),
          '| só referência:', (~r['CNPJ Novo'].isin(o['CNPJ Novo'])).sum())
```

## Resumo para o usuário (sempre, em poucas linhas)

- Como cada arquivo foi identificado e a DataRef de cada base de usuários.
- Mês de referência e horário de corte da produção (última DataDigitacao).
- Total de linhas, contagem por Status e por Projeto.
- CNPJs excluídos pela lista Fora.
- Pessoas vindas do arquivo de usuários mais antigo.
- Duplicados, CNPJs vazios, linhas sem hierarquia e CPFs não encontrados (se houver).
- Se existir uma "Parcial Correta" na pasta, o resultado da comparação.
- Nome do arquivo salvo e quais versões antigas podem ser apagadas.