"""
Sincroniza o banco com os dados da planilha 2026.
Idempotente — pode ser executado múltiplas vezes.

Saídas de log: CRIADO / ATUALIZADO / DESATIVADO / IGNORADO
"""
import sys
import os
import unicodedata
import calendar
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.models import Equipe, Colaborador, PeriodoAquisitivo, Ferias

# ─────────────────────────────────────────────────────────────────────────────
# DADOS — PASSO 1: Equipes
# ─────────────────────────────────────────────────────────────────────────────

EQUIPES = [
    'Kali', 'Debian', 'Ubuntu', 'Prestes', 'GMADs', 'Projetos',
    'Administrativo', 'Comercial', 'Transformação Digital', 'Mahle',
    'Pref. Castro', 'Pref. Carambeí', '12x36', 'Agrojem', 'Jazz',
    'Pref. Igarapé', 'Pref. São Mateus do Sul', 'Ergon', 'Operação',
]

# ─────────────────────────────────────────────────────────────────────────────
# DADOS — PASSO 2: Colaboradores ativos
# (nome, equipe, funcao, admissao DD/MM/YYYY)
# ─────────────────────────────────────────────────────────────────────────────

COLABORADORES = [
    ('AIRTON SCHMIDT DE ARAUJO JUNIOR',         'Prestes',               'PROGRAMADOR JUNIOR II',          '20/05/2025'),
    ('ALAUMIR MAINARDES DE ALMEIDA',            '12x36',                 'TECNICO DE INFORMATICA JUNIOR',  '17/05/2021'),
    ('ALEXANDRE DAROS DA FONSECA',              'Kali',                  'TECNICO DE INFORMATICA JUNIOR',  '11/01/2024'),
    ('ALISSON DE LIMA',                         'Agrojem',               'TECNICO DE INFORMATICA JUNIOR',  '13/11/2023'),
    ('ANDRE SWIECH DA SILVA',                   'Debian',                'TECNICO DE INFORMATICA SENIOR',  '11/09/2017'),
    ('ANDREY MEHRET',                           'Ubuntu',                'TECNICO DE INFORMATICA PLENO',   '06/03/2023'),
    ('BERNARDO BUENO ROSA',                     'Pref. Castro',          'TECNICO DE INFORMATICA JUNIOR',  '07/03/2022'),
    ('BRENO EDUARDO MACYSZYN',                  'Kali',                  'TECNICO DE INFORMATICA JUNIOR',  '06/03/2023'),
    ('CARLOS EDUARDO DZAZIO OLIVEIRA',          'Pref. Carambeí',        'AUXILIAR TECNICO II',            '08/07/2025'),
    ('CLEITOM JOSE DA SILVA',                   'Jazz',                  'TECNICO DE INFORMATICA JUNIOR',  '26/12/2023'),
    ('CRISTIANO MATESEN',                       'Pref. Carambeí',        'AUXILIAR TECNICO III',           '07/03/2022'),
    ('DANILO BOLZAN DE MORAES',                 'Mahle',                 'TECNICO DE INFORMATICA JUNIOR',  '01/07/2024'),
    ('EDUARDO ALAN DOS SANTOS',                 'Prestes',               'AUXILIAR TECNICO III',           '09/12/2024'),
    ('EDUARDO HENRIQUE FERREIRA BRUNO',         'GMADs',                 'TECNICO DE INFORMATICA PLENO I', '19/12/2018'),
    ('FABIANO TAVESKI',                         'Pref. Carambeí',        'TECNICO DE INFORMATICA JUNIOR',  '11/09/2023'),
    ('FABIO BUENO DE ARAUJO',                   'Transformação Digital', 'DESENVOLVEDOR JUNIOR',           '05/02/2025'),
    ('FABIO ROBERTO ZIMMERMANN MAIA',           'Operação',              'SUPERVISOR IV',                  '11/12/2023'),
    ('GABRIEL FERNANDES MACHADO',               'Debian',                'TECNICO DE INFORMATICA JUNIOR',  '28/10/2024'),
    ('GABRIEL FORCINETTI CELESTINO PEREIRA',    '12x36',                 'TECNICO DE INFORMATICA JUNIOR',  '14/10/2024'),
    ('GUILHERME SIMIONATO POPOATZKI',           'Transformação Digital', 'SUPERVISOR II',                  '10/03/2020'),
    ('GUSTAVO MEDEIROS CARNEIRO',               'Pref. Igarapé',         'AUXILIAR TECNICO II',            '17/04/2024'),
    ('HIGOR RIBEIRO DE FREITAS',                'Transformação Digital', 'TECNICO DE INFORMATICA JUNIOR',  '13/05/2024'),
    ('JACKSON ALEXANDRE ALVES FAGUNDES',        'Mahle',                 'TECNICO DE INFORMATICA PLENO I', '07/01/2020'),
    ('JEIVEDE MAYCON MARTINS',                  'Pref. Castro',          'TECNICO DE INFORMATICA JUNIOR',  '23/11/2022'),
    ('JESSICA FERNANDA BAZILIO',                'Administrativo',        'ANALISTA FINANCEIRO',            '05/03/2025'),
    ('JOAO PAULO MARCONDES DE ALMEIDA',         'Projetos',              'TECNICO DE INFORMATICA PLENO I', '01/07/2021'),
    ('JOAO VITOR CARNEIRO',                     'Projetos',              'TECNICO DE INFORMATICA JUNIOR',  '03/06/2024'),
    ('JOCELIA MARQUES DE JESUS',                'Administrativo',        'ANALISTA DE RH',                 '16/08/2024'),
    ('JONATAS BUSNELLO MARQUES',                'GMADs',                 'TECNICO DE INFORMATICA JUNIOR',  '03/07/2023'),
    ('JOSMARIO DA SILVA JUNIOR',                'Debian',                'TECNICO DE INFORMATICA PLENO I', '17/05/2021'),
    ('KELBER OLIVEIRA DA SILVA',                '12x36',                 'TECNICO DE INFORMATICA PLENO I', '16/05/2022'),
    ('KLEBER AUGUSTO MACHADO PEDROSO',          'Debian',                'CUSTOMER SUCESS III',            '25/03/2024'),
    ('LAIS CRISTINA LEAL',                      'Comercial',             'SUPERVISOR II',                  '21/10/2024'),
    ('LARISSA GUIMARAES VALENTIM',              'Ubuntu',                'TECNICO DE INFORMATICA PLENO I', '04/10/2021'),
    ('LEANDRO COSTA',                           'Comercial',             'SUPERVISOR I',                   '06/01/2025'),
    ('LEONARDO MATHEUS ANDRADE PACHECO',        '12x36',                 'TECNICO DE INFORMATICA JUNIOR',  '03/08/2023'),
    ('LEONARDO SAMPAIO DOS SANTOS',             'GMADs',                 'AUXILIAR TECNICO III',           '01/07/2024'),
    ('LUCAS CARGNIN LIMA',                      'Ubuntu',                'SUPERVISOR',                     '01/03/2018'),
    ('LUCAS RAFAEL GONCALVES DOLENKEI',         'Projetos',              'TECNICO DE INFORMATICA JUNIOR',  '03/05/2023'),
    ('LUIZ HENRIQUE RIBEIRO DOS SANTOS',        'GMADs',                 'AUXILIAR TECNICO I',             '06/01/2025'),
    ('MARCO AURELIO PEREIRA DA SILVA',          'Debian',                'TECNICO DE INFORMATICA SENIOR',  '02/09/2020'),
    ('MARIANA NAJLA BURDA ASSENHEIMER',         'Transformação Digital', 'TECNICO DE INFORMATICA JUNIOR',  '04/04/2022'),
    ('MATHEUS AUGUSTO SCHMIDT BENTO',           'Transformação Digital', 'PROGRAMADOR JUNIOR II',          '02/07/2025'),
    ('PEDRO HENRIQUE KOPSCH CAXAMBU',           'Prestes',               'PROGRAMADOR PLENO I',            '03/02/2023'),
    ('RAFAEL ALMEIDA NUNES',                    '12x36',                 'AUXILIAR TECNICO II',            '02/06/2025'),
    ('RAFAEL DE OLIVEIRA',                      'Pref. São Mateus do Sul','TECNICO DE INFORMATICA JUNIOR', '26/05/2025'),
    ('RAFAEL TELEGA DA SILVA',                  'Prestes',               'PROGRAMADOR SENIOR IV',          '23/03/2020'),
    ('RENAN AUGUSTO GEFUNE PERON',              'Ergon',                 'TECNICO DE INFORMATICA JUNIOR',  '05/08/2024'),
    ('ROBERLEI FONSECA',                        'Comercial',             'SUPERVISOR II',                  '09/06/2025'),
    ('ROGERIO RYMSZA',                          'Mahle',                 'TECNICO DE INFORMATICA JUNIOR',  '16/05/2022'),
    ('RUBENS ERNESTO VENSKE',                   'Prestes',               'ANALISTA DE SISTEMA SENIOR II',  '25/06/2020'),
    ('TARCISIO MAZUR JUNIOR',                   'Debian',                'TECNICO DE INFORMATICA PLENO I', '04/07/2023'),
    ('THIAGO CHEMPCEKE LIMA',                   'Prestes',               'TECNICO DE INFORMATICA JUNIOR',  '10/03/2025'),
    ('THOMAS JEFERSSON VAZ',                    'Mahle',                 'AUXILIAR TECNICO II',            '03/07/2025'),
    ('THOMAS JEFFERSON TIEPO DE QUADROS',       'Kali',                  'TECNICO DE INFORMATICA JUNIOR',  '26/01/2024'),
    ('VINICIUS EMANUEL FADINI SILVA',           'Kali',                  'TECNICO DE INFORMATICA JUNIOR',  '15/07/2024'),
    ('VITOR AFONSO ALMEIDA DA SILVA',           'Kali',                  'GERENTE DE PROJETO II',          '01/03/2021'),
]

# ─────────────────────────────────────────────────────────────────────────────
# DADOS — PASSO 4: Períodos aquisitivos e férias
# (nome, inicio, fim, dias_direito, limite, [(saida, dias, retorno), ...])
# dias_direito=0 → período concluído sem registro de datas individuais
# ─────────────────────────────────────────────────────────────────────────────

PERIODOS = [
    ('ALAUMIR MAINARDES DE ALMEIDA',         '17/05/2024','16/05/2025', 30,'15/04/2026',
     [('06/04/2026', 30, '06/05/2026')]),

    ('ALEXANDRE DAROS DA FONSECA',           '11/01/2025','10/01/2026', 20,'12/10/2026',
     [('16/04/2026', 15, '01/05/2026')]),

    ('ALISSON DE LIMA',                      '13/11/2024','12/11/2025', 30,'12/10/2026',
     [('29/06/2026', 15, '14/07/2026'), ('21/09/2026', 15, '06/10/2026')]),

    ('ANDRE SWIECH DA SILVA',                '11/09/2024','10/09/2025', 30,'10/08/2026',
     [('04/05/2026', 15, '19/05/2026'), ('13/07/2026', 15, '28/07/2026')]),

    ('ANDREY MEHRET',                        '06/03/2025','05/03/2026', 30,'02/02/2027',
     [('16/09/2026', 15, '01/10/2026')]),

    ('BERNARDO BUENO ROSA',                  '07/03/2025','06/03/2026', 30,'03/02/2027',
     []),

    ('BRENO EDUARDO MACYSZYN',               '06/03/2025','05/03/2026', 30,'02/02/2027',
     []),

    ('CARLOS EDUARDO DZAZIO OLIVEIRA',       '08/07/2025','07/07/2026', 30,'06/06/2027',
     []),

    ('CLEITOM JOSE DA SILVA',                '26/12/2025','25/12/2026', 30,'24/11/2027',
     []),

    ('CRISTIANO MATESEN',                    '07/03/2025','06/03/2026', 30,'03/02/2027',
     []),

    ('DANILO BOLZAN DE MORAES',              '01/07/2024','30/06/2025', 15,'30/05/2026',
     [('13/04/2026', 15, '28/04/2026')]),

    ('EDUARDO ALAN DOS SANTOS',              '09/12/2024','08/12/2025', 17,'07/11/2026',
     []),

    ('EDUARDO HENRIQUE FERREIRA BRUNO',      '19/12/2025','18/12/2026', 30,'17/11/2027',
     []),

    ('FABIANO TAVESKI',                      '11/09/2025','10/09/2026', 30,'10/08/2027',
     []),

    ('FABIO BUENO DE ARAUJO',               '05/02/2025','04/02/2026', 30,'04/01/2027',
     []),

    ('FABIO ROBERTO ZIMMERMANN MAIA',        '11/12/2024','10/12/2025', 30,'09/11/2026',
     []),

    ('GABRIEL FERNANDES MACHADO',            '28/10/2024','27/10/2025', 15,'26/09/2026',
     [('25/05/2026', 15, '09/06/2026')]),

    ('GABRIEL FORCINETTI CELESTINO PEREIRA', '14/10/2024','13/10/2025', 30,'12/09/2026',
     [('15/07/2026', 15, '30/07/2026'), ('10/09/2026', 15, '25/09/2026')]),

    ('GUILHERME SIMIONATO POPOATZKI',        '10/03/2025','09/03/2026', 30,'06/02/2027',
     []),

    ('GUSTAVO MEDEIROS CARNEIRO',            '17/04/2025','16/04/2026', 30,'16/03/2027',
     []),

    ('HIGOR RIBEIRO DE FREITAS',             '13/05/2025','12/05/2026', 30,'11/04/2027',
     [('15/06/2026', 15, '30/06/2026')]),

    # dias_direito=0: período concluído (férias já gozadas sem registro de datas)
    ('JACKSON ALEXANDRE ALVES FAGUNDES',     '07/01/2025','06/01/2026',  0,'06/12/2026',
     []),

    ('JEIVEDE MAYCON MARTINS',               '23/11/2025','22/11/2026', 30,'22/10/2027',
     []),

    ('JESSICA FERNANDA BAZILIO',             '05/03/2025','04/03/2026', 30,'01/02/2027',
     []),

    ('JOAO PAULO MARCONDES DE ALMEIDA',      '01/07/2025','30/06/2026', 30,'30/05/2027',
     []),

    ('JOAO VITOR CARNEIRO',                  '03/06/2025','02/06/2026', 30,'02/05/2027',
     []),

    ('JOCELIA MARQUES DE JESUS',             '16/08/2024','15/08/2025', 10,'15/07/2026',
     []),

    ('JONATAS BUSNELLO MARQUES',             '03/07/2025','02/07/2026', 30,'01/06/2027',
     [('01/07/2026', 15, '16/07/2026')]),

    ('JOSMARIO DA SILVA JUNIOR',             '17/05/2025','16/05/2026', 30,'15/04/2027',
     []),

    ('KELBER OLIVEIRA DA SILVA',             '16/05/2025','15/05/2026', 30,'14/04/2027',
     [('10/06/2026', 15, '25/06/2026')]),

    ('KLEBER AUGUSTO MACHADO PEDROSO',       '25/03/2025','24/03/2026', 30,'21/02/2027',
     [('13/07/2026', 15, '28/07/2026')]),

    ('LAIS CRISTINA LEAL',                   '21/10/2024','20/10/2025', 15,'19/09/2026',
     [('18/06/2026', 15, '03/07/2026')]),

    ('LARISSA GUIMARAES VALENTIM',           '04/10/2024','03/10/2025', 15,'02/09/2026',
     [('27/07/2026', 15, '11/08/2026'), ('26/10/2026', 15, '10/11/2026')]),

    ('LEANDRO COSTA',                        '06/01/2025','05/01/2026', 15,'05/12/2026',
     []),

    ('LEONARDO MATHEUS ANDRADE PACHECO',     '03/08/2024','02/08/2025', 15,'02/07/2026',
     [('02/07/2026', 15, '17/07/2026')]),

    ('LEONARDO SAMPAIO DOS SANTOS',          '01/07/2025','30/06/2026', 30,'30/05/2027',
     [('01/06/2027', 15, '16/06/2027')]),

    # 29/02/2025 não existe → convertido para 28/02/2025 automaticamente
    ('LUCAS CARGNIN LIMA',                   '29/02/2025','28/02/2026', 30,'28/01/2027',
     [('03/11/2026', 15, '18/11/2026')]),

    ('LUCAS RAFAEL GONCALVES DOLENKEI',      '03/05/2025','02/05/2026', 30,'01/04/2027',
     []),

    ('LUIZ HENRIQUE RIBEIRO DOS SANTOS',     '06/01/2025','05/01/2026', 15,'05/12/2026',
     [('19/02/2026', 15, '06/03/2026'), ('16/07/2026', 15, '31/07/2026')]),

    ('MARCO AURELIO PEREIRA DA SILVA',       '02/09/2025','01/09/2026', 30,'01/08/2027',
     [('08/03/2026', 15, '18/08/2026')]),

    ('MARIANA NAJLA BURDA ASSENHEIMER',      '04/04/2025','03/04/2026', 30,'03/03/2027',
     []),

    ('MATHEUS AUGUSTO SCHMIDT BENTO',        '02/07/2025','01/07/2026', 30,'31/05/2027',
     []),

    ('PEDRO HENRIQUE KOPSCH CAXAMBU',        '03/02/2025','02/02/2026', 30,'02/01/2027',
     [('14/04/2026', 15, '29/04/2026')]),

    ('RAFAEL ALMEIDA NUNES',                 '02/06/2025','01/06/2026', 30,'01/05/2027',
     []),

    ('RAFAEL DE OLIVEIRA',                   '26/05/2025','25/05/2026', 30,'24/04/2027',
     []),

    ('RAFAEL TELEGA DA SILVA',               '23/03/2025','22/03/2026', 11,'19/02/2027',
     [('30/06/2026', 11, '11/07/2026')]),

    ('RENAN AUGUSTO GEFUNE PERON',           '05/08/2024','04/08/2025', 15,'04/07/2026',
     [('04/05/2026', 15, '19/05/2026')]),

    ('ROBERLEI FONSECA',                     '09/06/2025','08/06/2026', 30,'08/05/2027',
     [('16/07/2026', 10, '26/07/2026')]),

    ('ROGERIO RYMSZA',                       '16/05/2024','15/05/2025', 10,'14/04/2026',
     [('23/03/2026', 10, '02/04/2026')]),

    ('RUBENS ERNESTO VENSKE',                '25/06/2025','24/06/2026', 30,'24/05/2027',
     []),

    ('TARCISIO MAZUR JUNIOR',                '04/07/2024','03/07/2025', 30,'02/06/2026',
     [('06/04/2026', 15, '21/04/2026'), ('20/05/2026', 15, '04/06/2026')]),

    ('THIAGO CHEMPCEKE LIMA',                '10/03/2025','09/03/2026', 30,'06/02/2027',
     [('16/04/2026', 14, '30/04/2026')]),

    ('THOMAS JEFERSSON VAZ',                 '03/07/2025','02/07/2026', 30,'01/06/2027',
     []),

    # dias_direito=0: período concluído sem registro de datas individuais
    ('THOMAS JEFFERSON TIEPO DE QUADROS',    '26/01/2025','25/01/2026',  0,'25/12/2026',
     []),

    ('VINICIUS EMANUEL FADINI SILVA',        '15/07/2024','14/07/2025', 15,'13/06/2026',
     [('25/05/2026', 15, '09/06/2026')]),

    # 29/02/2025 não existe → convertido para 28/02/2025 automaticamente
    ('VITOR AFONSO ALMEIDA DA SILVA',        '29/02/2025','28/02/2026', 30,'28/01/2027',
     []),
]

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _normalizar(texto):
    nfkd = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def _gerar_email(nome):
    partes = _normalizar(nome).lower().split()
    return f'{partes[0]}.{partes[-1]}@pellissari.com.br'


def _email_unico(nome):
    """Gera email garantindo unicidade no banco (adiciona sufixo numérico se necessário)."""
    base = _gerar_email(nome)
    email = base
    sufixo = 2
    while Colaborador.query.filter_by(email=email).first():
        local, dominio = base.split('@')
        email = f'{local}{sufixo}@{dominio}'
        sufixo += 1
    return email


def _d(s):
    """Converte DD/MM/YYYY → date. Trata 29/02 em anos não bissextos como 28/02."""
    d, m, y = int(s[:2]), int(s[3:5]), int(s[6:])
    if d == 29 and m == 2 and not calendar.isleap(y):
        print(f'    [AVISO] 29/02/{y} não existe → usando 28/02/{y}')
        d = 28
    return date(y, m, d)


def _log(tag, msg):
    simbolo = {
        'CRIADO':     '[+]',
        'ATUALIZADO': '[~]',
        'DESATIVADO': '[x]',
        'IGNORADO':   '[-]',
    }.get(tag, f'[{tag}]')
    print(f'  {simbolo} {tag}: {msg}')


def _encontrar_colab(nome):
    """Busca por nome exato (case-insensitive). Não usa email para evitar colisões."""
    return Colaborador.query.filter(
        db.func.upper(Colaborador.nome) == nome.upper()
    ).first()


# ─────────────────────────────────────────────────────────────────────────────
# PASSOS
# ─────────────────────────────────────────────────────────────────────────────

def passo1_equipes():
    print('\n══ PASSO 1 — Equipes ══')
    for nome in EQUIPES:
        if Equipe.query.filter_by(nome=nome).first():
            _log('IGNORADO', nome)
        else:
            db.session.add(Equipe(nome=nome))
            db.session.flush()
            _log('CRIADO', nome)


def passo2_colaboradores():
    print('\n══ PASSO 2 — Colaboradores ══')
    for nome, equipe_nome, funcao, admissao_str in COLABORADORES:
        equipe = Equipe.query.filter_by(nome=equipe_nome).first()
        if not equipe:
            print(f'  [!] Equipe não encontrada: "{equipe_nome}" — pulando {nome}')
            continue

        admissao = _d(admissao_str)
        colab = _encontrar_colab(nome)

        if colab:
            mudancas = []
            if colab.equipe_id != equipe.id:
                mudancas.append(f'equipe: {colab.equipe.nome} → {equipe_nome}')
                colab.equipe_id = equipe.id
            if colab.funcao != funcao:
                mudancas.append('função atualizada')
                colab.funcao = funcao
            if colab.data_admissao != admissao:
                mudancas.append(f'admissão: {colab.data_admissao} → {admissao}')
                colab.data_admissao = admissao
            if not colab.ativo:
                mudancas.append('reativado')
                colab.ativo = 1
            if mudancas:
                _log('ATUALIZADO', f'{nome} ({", ".join(mudancas)})')
            else:
                _log('IGNORADO', nome)
        else:
            email = _email_unico(nome)
            c = Colaborador(
                nome=nome.title(),
                email=email,
                senha_hash='',
                data_admissao=admissao,
                funcao=funcao,
                equipe_id=equipe.id,
                gestor_id=None,
                perfil='colaborador',
                ativo=1,
            )
            c.set_senha('Pellissari@2026')
            db.session.add(c)
            db.session.flush()
            _log('CRIADO', f'{nome} ({email})')


def passo3_desativar():
    print('\n══ PASSO 3 — Desativar colaboradores removidos ══')
    nomes_ativos = {nome.upper() for nome, *_ in COLABORADORES}

    for c in Colaborador.query.filter_by(ativo=1).all():
        if 'adilson' in c.nome.lower():
            _log('IGNORADO', f'{c.nome} (Adilson — protegido)')
            continue
        if c.nome.upper() in nomes_ativos:
            _log('IGNORADO', c.nome)
        else:
            c.ativo = 0
            _log('DESATIVADO', c.nome)


def passo4_periodos():
    print('\n══ PASSO 4 — Períodos aquisitivos e férias ══')

    # Limpa todos os períodos e férias dos colaboradores gerenciados
    print('  [limpando períodos/férias dos colaboradores da lista...]')
    for nome, *_ in COLABORADORES:
        c = _encontrar_colab(nome)
        if not c:
            continue
        n_ferias = Ferias.query.filter_by(colaborador_id=c.id).delete()
        n_periodos = PeriodoAquisitivo.query.filter_by(colaborador_id=c.id).delete()
        if n_periodos or n_ferias:
            print(f'    limpo: {nome} ({n_periodos} períodos, {n_ferias} férias)')
    db.session.flush()

    # Importa os novos períodos
    print('  [importando períodos e férias...]')
    for nome, ini_s, fim_s, dias_dir, lim_s, blocos in PERIODOS:
        colab = _encontrar_colab(nome)
        if not colab:
            print(f'  [!] Colaborador não encontrado: {nome}')
            continue

        ini = _d(ini_s)
        fim = _d(fim_s)
        lim = _d(lim_s)

        periodo = PeriodoAquisitivo(
            colaborador_id=colab.id,
            data_inicio=ini,
            data_fim=fim,
            dias_direito=dias_dir,
            data_limite_saida=lim,
        )
        db.session.add(periodo)
        db.session.flush()
        _log('CRIADO', f'Período {nome}: {ini_s} – {fim_s} ({dias_dir}d, limite {lim_s})')

        for saida_s, dias, retorno_s in blocos:
            saida = _d(saida_s)
            retorno = _d(retorno_s)
            f = Ferias(
                colaborador_id=colab.id,
                periodo_aquisitivo_id=periodo.id,
                data_inicio=saida,
                dias=dias,
                data_retorno=retorno,
                status='aprovada',
            )
            db.session.add(f)
            print(f'      [+] Férias: {saida_s} ({dias}d) → retorno {retorno_s}')


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    app = create_app('development')
    with app.app_context():
        passo1_equipes()
        passo2_colaboradores()
        passo3_desativar()
        passo4_periodos()
        db.session.commit()
        print('\n✓ Sincronização 2026 concluída com sucesso.')


if __name__ == '__main__':
    main()
