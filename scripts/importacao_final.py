"""
Importação final: popula banco com dados da planilha 2026.
Deve ser executado em banco vazio (após limpeza).
"""
import sys
import os
import unicodedata
import calendar
from datetime import date, timedelta, datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Equipe, Colaborador, PeriodoAquisitivo, Ferias

# ─────────────────────────────────────────────────────────────────────────────
# EQUIPES
# ─────────────────────────────────────────────────────────────────────────────

EQUIPES = [
    'Kali', 'Debian', 'Ubuntu', 'Prestes', 'GMADs', 'Projetos',
    'Administrativo', 'Comercial', 'Transformação Digital', 'Mahle',
    'Pref. Castro', 'Pref. Carambeí', '12x36', 'Agrojem', 'Jazz',
    'Pref. Igarapé', 'Pref. São Mateus do Sul', 'Ergon', 'Operação',
]

# ─────────────────────────────────────────────────────────────────────────────
# COLABORADORES  (nome_upper | equipe | funcao | admissao DD/MM/YYYY)
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
# PERÍODOS AQUISITIVOS E FÉRIAS
# ferias: lista de (data_saida, dias)  — data_retorno é calculada automaticamente
# ─────────────────────────────────────────────────────────────────────────────

PERIODOS = [
    {'nome': 'ALAUMIR MAINARDES DE ALMEIDA',
     'inicio': '17/05/2024', 'fim': '16/05/2025', 'dias': 30, 'limite': '15/04/2026',
     'ferias': [('06/04/2026', 30)]},

    {'nome': 'ALEXANDRE DAROS DA FONSECA',
     'inicio': '11/01/2025', 'fim': '10/01/2026', 'dias': 20, 'limite': '12/10/2026',
     'ferias': [('16/04/2026', 15)]},

    {'nome': 'ALISSON DE LIMA',
     'inicio': '13/11/2024', 'fim': '12/11/2025', 'dias': 30, 'limite': '12/10/2026',
     'ferias': [('29/06/2026', 15), ('21/09/2026', 15)]},

    {'nome': 'ANDRE SWIECH DA SILVA',
     'inicio': '11/09/2024', 'fim': '10/09/2025', 'dias': 30, 'limite': '10/08/2026',
     'ferias': [('04/05/2026', 15), ('13/07/2026', 15)]},

    {'nome': 'ANDREY MEHRET',
     'inicio': '06/03/2025', 'fim': '05/03/2026', 'dias': 30, 'limite': '02/02/2027',
     'ferias': [('16/09/2026', 15)]},

    {'nome': 'BERNARDO BUENO ROSA',
     'inicio': '07/03/2025', 'fim': '06/03/2026', 'dias': 30, 'limite': '03/02/2027',
     'ferias': []},

    {'nome': 'BRENO EDUARDO MACYSZYN',
     'inicio': '06/03/2025', 'fim': '05/03/2026', 'dias': 30, 'limite': '02/02/2027',
     'ferias': []},

    {'nome': 'CARLOS EDUARDO DZAZIO OLIVEIRA',
     'inicio': '08/07/2025', 'fim': '07/07/2026', 'dias': 30, 'limite': '06/06/2027',
     'ferias': []},

    {'nome': 'CLEITOM JOSE DA SILVA',
     'inicio': '26/12/2025', 'fim': '25/12/2026', 'dias': 30, 'limite': '24/11/2027',
     'ferias': []},

    {'nome': 'CRISTIANO MATESEN',
     'inicio': '07/03/2025', 'fim': '06/03/2026', 'dias': 30, 'limite': '03/02/2027',
     'ferias': []},

    {'nome': 'DANILO BOLZAN DE MORAES',
     'inicio': '01/07/2024', 'fim': '30/06/2025', 'dias': 15, 'limite': '30/05/2026',
     'ferias': [('13/04/2026', 15)]},

    {'nome': 'EDUARDO ALAN DOS SANTOS',
     'inicio': '09/12/2024', 'fim': '08/12/2025', 'dias': 17, 'limite': '07/11/2026',
     'ferias': []},

    {'nome': 'EDUARDO HENRIQUE FERREIRA BRUNO',
     'inicio': '19/12/2025', 'fim': '18/12/2026', 'dias': 30, 'limite': '17/11/2027',
     'ferias': []},

    {'nome': 'FABIANO TAVESKI',
     'inicio': '11/09/2025', 'fim': '10/09/2026', 'dias': 30, 'limite': '10/08/2027',
     'ferias': []},

    {'nome': 'FABIO BUENO DE ARAUJO',
     'inicio': '05/02/2025', 'fim': '04/02/2026', 'dias': 30, 'limite': '04/01/2027',
     'ferias': []},

    {'nome': 'FABIO ROBERTO ZIMMERMANN MAIA',
     'inicio': '11/12/2024', 'fim': '10/12/2025', 'dias': 30, 'limite': '09/11/2026',
     'ferias': []},

    {'nome': 'GABRIEL FERNANDES MACHADO',
     'inicio': '28/10/2024', 'fim': '27/10/2025', 'dias': 15, 'limite': '26/09/2026',
     'ferias': [('25/05/2026', 15)]},

    {'nome': 'GABRIEL FORCINETTI CELESTINO PEREIRA',
     'inicio': '14/10/2024', 'fim': '13/10/2025', 'dias': 30, 'limite': '12/09/2026',
     'ferias': [('15/07/2026', 15), ('10/09/2026', 15)]},

    {'nome': 'GUILHERME SIMIONATO POPOATZKI',
     'inicio': '10/03/2025', 'fim': '09/03/2026', 'dias': 30, 'limite': '06/02/2027',
     'ferias': []},

    {'nome': 'GUSTAVO MEDEIROS CARNEIRO',
     'inicio': '17/04/2025', 'fim': '16/04/2026', 'dias': 30, 'limite': '16/03/2027',
     'ferias': []},

    {'nome': 'HIGOR RIBEIRO DE FREITAS',
     'inicio': '13/05/2025', 'fim': '12/05/2026', 'dias': 30, 'limite': '11/04/2027',
     'ferias': [('15/06/2026', 15)]},

    {'nome': 'JACKSON ALEXANDRE ALVES FAGUNDES',
     'inicio': '07/01/2025', 'fim': '06/01/2026', 'dias': 0, 'limite': '06/12/2026',
     'ferias': []},

    {'nome': 'JEIVEDE MAYCON MARTINS',
     'inicio': '23/11/2025', 'fim': '22/11/2026', 'dias': 30, 'limite': '22/10/2027',
     'ferias': []},

    {'nome': 'JESSICA FERNANDA BAZILIO',
     'inicio': '05/03/2025', 'fim': '04/03/2026', 'dias': 30, 'limite': '01/02/2027',
     'ferias': []},

    {'nome': 'JOAO PAULO MARCONDES DE ALMEIDA',
     'inicio': '01/07/2025', 'fim': '30/06/2026', 'dias': 30, 'limite': '30/05/2027',
     'ferias': []},

    {'nome': 'JOAO VITOR CARNEIRO',
     'inicio': '03/06/2025', 'fim': '02/06/2026', 'dias': 30, 'limite': '02/05/2027',
     'ferias': []},

    {'nome': 'JOCELIA MARQUES DE JESUS',
     'inicio': '16/08/2024', 'fim': '15/08/2025', 'dias': 10, 'limite': '15/07/2026',
     'ferias': []},

    {'nome': 'JONATAS BUSNELLO MARQUES',
     'inicio': '03/07/2025', 'fim': '02/07/2026', 'dias': 30, 'limite': '01/06/2027',
     'ferias': [('01/07/2026', 15)]},

    {'nome': 'JOSMARIO DA SILVA JUNIOR',
     'inicio': '17/05/2025', 'fim': '16/05/2026', 'dias': 30, 'limite': '15/04/2027',
     'ferias': []},

    {'nome': 'KELBER OLIVEIRA DA SILVA',
     'inicio': '16/05/2025', 'fim': '15/05/2026', 'dias': 30, 'limite': '14/04/2027',
     'ferias': [('10/06/2026', 15)]},

    {'nome': 'KLEBER AUGUSTO MACHADO PEDROSO',
     'inicio': '25/03/2025', 'fim': '24/03/2026', 'dias': 30, 'limite': '21/02/2027',
     'ferias': [('13/07/2026', 15)]},

    {'nome': 'LAIS CRISTINA LEAL',
     'inicio': '21/10/2024', 'fim': '20/10/2025', 'dias': 15, 'limite': '19/09/2026',
     'ferias': [('18/06/2026', 15)]},

    {'nome': 'LARISSA GUIMARAES VALENTIM',
     'inicio': '04/10/2024', 'fim': '03/10/2025', 'dias': 15, 'limite': '02/09/2026',
     'ferias': [('27/07/2026', 15), ('26/10/2026', 15)]},

    {'nome': 'LEANDRO COSTA',
     'inicio': '06/01/2025', 'fim': '05/01/2026', 'dias': 15, 'limite': '05/12/2026',
     'ferias': []},

    {'nome': 'LEONARDO MATHEUS ANDRADE PACHECO',
     'inicio': '03/08/2024', 'fim': '02/08/2025', 'dias': 15, 'limite': '02/07/2026',
     'ferias': [('02/07/2026', 15)]},

    {'nome': 'LEONARDO SAMPAIO DOS SANTOS',
     'inicio': '01/07/2025', 'fim': '30/06/2026', 'dias': 30, 'limite': '30/05/2027',
     'ferias': [('01/06/2027', 15)]},

    {'nome': 'LUCAS CARGNIN LIMA',
     'inicio': '29/02/2025', 'fim': '28/02/2026', 'dias': 30, 'limite': '28/01/2027',
     'ferias': [('03/11/2026', 15)]},

    {'nome': 'LUCAS RAFAEL GONCALVES DOLENKEI',
     'inicio': '03/05/2025', 'fim': '02/05/2026', 'dias': 30, 'limite': '01/04/2027',
     'ferias': []},

    {'nome': 'LUIZ HENRIQUE RIBEIRO DOS SANTOS',
     'inicio': '06/01/2025', 'fim': '05/01/2026', 'dias': 15, 'limite': '05/12/2026',
     'ferias': [('19/02/2026', 15), ('16/07/2026', 15)]},

    {'nome': 'MARCO AURELIO PEREIRA DA SILVA',
     'inicio': '02/09/2025', 'fim': '01/09/2026', 'dias': 30, 'limite': '01/08/2027',
     'ferias': [('08/03/2026', 15)]},

    {'nome': 'MARIANA NAJLA BURDA ASSENHEIMER',
     'inicio': '04/04/2025', 'fim': '03/04/2026', 'dias': 30, 'limite': '03/03/2027',
     'ferias': []},

    {'nome': 'MATHEUS AUGUSTO SCHMIDT BENTO',
     'inicio': '02/07/2025', 'fim': '01/07/2026', 'dias': 30, 'limite': '31/05/2027',
     'ferias': []},

    {'nome': 'PEDRO HENRIQUE KOPSCH CAXAMBU',
     'inicio': '03/02/2025', 'fim': '02/02/2026', 'dias': 30, 'limite': '02/01/2027',
     'ferias': [('14/04/2026', 15)]},

    {'nome': 'RAFAEL ALMEIDA NUNES',
     'inicio': '02/06/2025', 'fim': '01/06/2026', 'dias': 30, 'limite': '01/05/2027',
     'ferias': []},

    {'nome': 'RAFAEL DE OLIVEIRA',
     'inicio': '26/05/2025', 'fim': '25/05/2026', 'dias': 30, 'limite': '24/04/2027',
     'ferias': []},

    {'nome': 'RAFAEL TELEGA DA SILVA',
     'inicio': '23/03/2025', 'fim': '22/03/2026', 'dias': 11, 'limite': '19/02/2027',
     'ferias': [('30/06/2026', 11)]},

    {'nome': 'RENAN AUGUSTO GEFUNE PERON',
     'inicio': '05/08/2024', 'fim': '04/08/2025', 'dias': 15, 'limite': '04/07/2026',
     'ferias': [('04/05/2026', 15)]},

    {'nome': 'ROBERLEI FONSECA',
     'inicio': '09/06/2025', 'fim': '08/06/2026', 'dias': 30, 'limite': '08/05/2027',
     'ferias': [('16/07/2026', 10)]},

    {'nome': 'ROGERIO RYMSZA',
     'inicio': '16/05/2024', 'fim': '15/05/2025', 'dias': 10, 'limite': '14/04/2026',
     'ferias': [('23/03/2026', 10)]},

    {'nome': 'RUBENS ERNESTO VENSKE',
     'inicio': '25/06/2025', 'fim': '24/06/2026', 'dias': 30, 'limite': '24/05/2027',
     'ferias': []},

    {'nome': 'TARCISIO MAZUR JUNIOR',
     'inicio': '04/07/2024', 'fim': '03/07/2025', 'dias': 30, 'limite': '02/06/2026',
     'ferias': [('06/04/2026', 15), ('20/05/2026', 15)]},

    {'nome': 'THIAGO CHEMPCEKE LIMA',
     'inicio': '10/03/2025', 'fim': '09/03/2026', 'dias': 30, 'limite': '06/02/2027',
     'ferias': [('16/04/2026', 14)]},

    {'nome': 'THOMAS JEFERSSON VAZ',
     'inicio': '03/07/2025', 'fim': '02/07/2026', 'dias': 30, 'limite': '01/06/2027',
     'ferias': []},

    {'nome': 'THOMAS JEFFERSON TIEPO DE QUADROS',
     'inicio': '26/01/2025', 'fim': '25/01/2026', 'dias': 0, 'limite': '25/12/2026',
     'ferias': []},

    {'nome': 'VINICIUS EMANUEL FADINI SILVA',
     'inicio': '15/07/2024', 'fim': '14/07/2025', 'dias': 15, 'limite': '13/06/2026',
     'ferias': [('25/05/2026', 15)]},

    {'nome': 'VITOR AFONSO ALMEIDA DA SILVA',
     'inicio': '29/02/2025', 'fim': '28/02/2026', 'dias': 30, 'limite': '28/01/2027',
     'ferias': []},
]

# E-mail reservado para o admin (não pode ser gerado para colaboradores)
EMAILS_RESERVADOS = {'vitor.silva@pellissari.com.br'}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _sem_acento(texto):
    nfkd = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def _email_base(nome):
    p = _sem_acento(nome).lower().split()
    return f'{p[0]}.{p[-1]}@pellissari.com.br'


def _email_alt1(nome):
    """primeiro.segundo@pellissari.com.br"""
    p = _sem_acento(nome).lower().split()
    segundo = p[1] if len(p) > 2 else p[0]
    return f'{p[0]}.{segundo}@pellissari.com.br'


def _email_alt2(nome):
    """primeirosegundo.ultimo@pellissari.com.br"""
    p = _sem_acento(nome).lower().split()
    return f'{p[0]}{p[1]}.{p[-1]}@pellissari.com.br' if len(p) > 1 else _email_base(nome)


def _email_unico(nome, usados):
    for fn in (_email_base, _email_alt1, _email_alt2):
        e = fn(nome)
        if e not in usados and e not in EMAILS_RESERVADOS:
            return e
    raise ValueError(f'Impossível gerar e-mail único para: {nome}')


def _d(s):
    """DD/MM/YYYY → date. Trata 29/02 em anos não-bissextos como 28/02."""
    d, m, y = int(s[:2]), int(s[3:5]), int(s[6:])
    if d == 29 and m == 2 and not calendar.isleap(y):
        print(f'    [AVISO] 29/02/{y} não existe → usando 28/02/{y}')
        d = 28
    return date(y, m, d)


# ─────────────────────────────────────────────────────────────────────────────
# EXECUÇÃO
# ─────────────────────────────────────────────────────────────────────────────

app = create_app()

with app.app_context():
    agora = datetime.utcnow()

    # ── PASSO 1: Equipes ──────────────────────────────────────────────────────
    print('\n══ PASSO 1 — Equipes ══')
    equipe_map = {}
    for nome in EQUIPES:
        eq = Equipe(nome=nome)
        db.session.add(eq)
        db.session.flush()
        equipe_map[nome] = eq
        print(f'  [+] {nome}')

    # ── PASSO 2: Colaboradores ────────────────────────────────────────────────
    print('\n══ PASSO 2 — Colaboradores ══')
    colab_map = {}   # NOME_UPPER → Colaborador
    emails_usados = set()

    for nome, equipe_nome, funcao, admissao_str in COLABORADORES:
        equipe = equipe_map.get(equipe_nome)
        if not equipe:
            print(f'  [!] Equipe não encontrada: "{equipe_nome}" — pulando {nome}')
            continue

        admissao = _d(admissao_str)
        email = _email_unico(nome, emails_usados)
        emails_usados.add(email)

        c = Colaborador(
            nome=nome.strip().title(),
            email=email,
            senha_hash='',
            data_admissao=admissao,
            funcao=funcao.strip().upper(),
            equipe_id=equipe.id,
            gestor_id=None,
            perfil='colaborador',
            ativo=1,
        )
        c.set_senha('Pellissari@2026')
        db.session.add(c)
        db.session.flush()
        colab_map[nome.upper()] = c
        print(f'  [+] {nome.title()} → {email}')

    # ── PASSO 3: Períodos aquisitivos e férias ────────────────────────────────
    print('\n══ PASSO 3 — Períodos aquisitivos e férias ══')
    n_periodos = 0
    n_ferias = 0

    for p in PERIODOS:
        c = colab_map.get(p['nome'].upper())
        if not c:
            print(f'  [!] Colaborador não encontrado: {p["nome"]}')
            continue

        periodo = PeriodoAquisitivo(
            colaborador_id=c.id,
            data_inicio=_d(p['inicio']),
            data_fim=_d(p['fim']),
            dias_direito=p['dias'],
            data_limite_saida=_d(p['limite']),
        )
        db.session.add(periodo)
        db.session.flush()
        n_periodos += 1

        ferias_list = p.get('ferias', [])
        for saida_str, dias in ferias_list:
            data_inicio = _d(saida_str)
            data_retorno = data_inicio + timedelta(days=dias)
            f = Ferias(
                colaborador_id=c.id,
                periodo_aquisitivo_id=periodo.id,
                data_inicio=data_inicio,
                dias=dias,
                data_retorno=data_retorno,
                status='aprovada',
                aprovado_gestor_em=agora,
                aprovado_rh_em=agora,
            )
            db.session.add(f)
            n_ferias += 1

        label_f = f' + {len(ferias_list)} férias' if ferias_list else ''
        print(f'  [+] {c.nome}: {p["inicio"]} – {p["fim"]} ({p["dias"]}d){label_f}')

    db.session.commit()

    # ── Resumo ────────────────────────────────────────────────────────────────
    print('\n══ RESUMO FINAL ══')
    print(f'  Equipes:       {Equipe.query.count()}')
    print(f'  Colaboradores: {Colaborador.query.count()}')
    print(f'  Períodos:      {PeriodoAquisitivo.query.count()}')
    print(f'  Férias:        {Ferias.query.count()}')
    print('\nImportação concluída!')
