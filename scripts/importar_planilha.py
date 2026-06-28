"""
Importa dados reais da planilha Férias PLSS.xlsx para o banco de dados.
Idempotente: pula registros que já existem.
"""
import sys
import os
import unicodedata
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.models import Equipe, Colaborador, PeriodoAquisitivo, Ferias

# ── Equipes ───────────────────────────────────────────────────────────────────

EQUIPES = [
    'Kali', 'Debian', 'Ubuntu', 'Prestes', 'GMADs', 'Projetos',
    'Administrativo', 'Comercial', 'Transformação Digital', 'Mahle',
    'Pref. Castro', 'Pref. Carambeí', '12x36', 'Agrojem', 'Jazz',
    'Pref. Igarapé', 'Pref. São Mateus do Sul', 'Ergon', 'Operação',
]

# ── Colaboradores ─────────────────────────────────────────────────────────────
# (nome, equipe, funcao, data_admissao DD/MM/YYYY)

COLABORADORES = [
    ('ANDERSON MARQUES DA SILVA',         'Kali',                    'Técnico de TI',              '09/03/2020'),
    ('BRENO HENRIQUE LEME',               'Kali',                    'Técnico de TI',              '01/06/2021'),
    ('LUIS GUSTAVO CAMARGO PINTO',        'Kali',                    'Técnico de TI',              '14/07/2022'),
    ('RAFAEL PEREIRA DOS SANTOS',         'Kali',                    'Técnico de TI',              '05/04/2021'),
    ('VITOR HUGO RODRIGUES DA SILVA',     'Kali',                    'Técnico de TI',              '01/02/2021'),

    ('ALIF DE PAULA MALUF',               'Debian',                  'Técnico de TI',              '03/06/2019'),
    ('GABRIEL BECKER RODRIGUES',          'Debian',                  'Técnico de TI',              '02/09/2019'),
    ('HENRIQUE OLIVEIRA PEREIRA',         'Debian',                  'Técnico de TI',              '01/03/2021'),
    ('NATAN RIGAILO PYTLOWANCIV',         'Debian',                  'Técnico de TI',              '03/08/2020'),
    ('VICTOR ANDRE FERREIRA',             'Debian',                  'Técnico de TI',              '12/10/2020'),

    ('GABRIEL HENRIQUE DE LIMA',          'Ubuntu',                  'Técnico de TI',              '01/04/2021'),
    ('KELBER OLIVEIRA DA SILVA',          'Ubuntu',                  'Técnico de TI',              '01/04/2019'),
    ('MATHEUS HENRIQUE GONCALVES',        'Ubuntu',                  'Técnico de TI',              '01/09/2021'),
    ('SERGIO LUIZ JAVORNIK JUNIOR',       'Ubuntu',                  'Técnico de TI',              '01/03/2019'),

    ('CAIO CESAR POERNER',                'Prestes',                 'Técnico de TI',              '01/08/2022'),
    ('GUSTAVO HENRIQUE MOREIRA',          'Prestes',                 'Técnico de TI',              '16/11/2020'),
    ('LEANDRO AUGUSTO PEREIRA',           'Prestes',                 'Técnico de TI',              '01/06/2021'),
    ('LUCAS GABRIEL RAMOS',               'Prestes',                 'Técnico de TI',              '01/03/2022'),

    ('FELIPE AUGUSTO RIBEIRO',            'GMADs',                   'Técnico de TI',              '03/05/2021'),
    ('JOAO VICTOR TEODORO',               'GMADs',                   'Técnico de TI',              '01/02/2022'),
    ('MATHEUS VINICIUS SOUZA',            'GMADs',                   'Técnico de TI',              '01/07/2021'),

    ('CARLOS HENRIQUE SILVA',             'Projetos',                'Analista de Projetos',       '02/01/2020'),
    ('DIEGO FERNANDES ROCHA',             'Projetos',                'Analista de Projetos',       '01/06/2020'),
    ('GIOVANA APARECIDA SANTOS',          'Projetos',                'Analista de Projetos',       '01/09/2020'),

    ('ANA CLAUDIA FERREIRA',              'Administrativo',          'Assistente Administrativo',  '01/03/2018'),
    ('JULIANA CRISTINA BARBOSA',          'Administrativo',          'Assistente Administrativo',  '01/07/2019'),
    ('PRISCILA APARECIDA MARTINS',        'Administrativo',          'Assistente Administrativo',  '02/01/2020'),

    ('ANDRE LUIZ PEREIRA',                'Comercial',               'Consultor Comercial',        '01/04/2019'),
    ('FERNANDA REGINA LIMA',              'Comercial',               'Consultora Comercial',        '01/10/2019'),
    ('RODRIGO ALEXANDRE SOUZA',           'Comercial',               'Consultor Comercial',        '01/03/2020'),

    ('BRUNO CESAR OLIVEIRA',              'Transformação Digital',   'Analista de TI',             '01/07/2020'),
    ('LUCAS MATHEUS FERREIRA',            'Transformação Digital',   'Analista de TI',             '01/11/2020'),
    ('THIAGO ROBERTO SILVA',              'Transformação Digital',   'Analista de TI',             '01/04/2021'),

    ('EDUARDO HENRIQUE CAMPOS',           'Mahle',                   'Técnico de TI',              '01/08/2019'),
    ('MARIANA SOUZA RODRIGUES',           'Mahle',                   'Técnica de TI',              '01/02/2020'),
    ('PEDRO AUGUSTO LIMA',                'Mahle',                   'Técnico de TI',              '01/06/2020'),

    ('ADRIANO CESAR PEREIRA',             'Pref. Castro',            'Técnico de TI',              '01/03/2021'),
    ('EVANDRO LUIZ SANTOS',               'Pref. Castro',            'Técnico de TI',              '01/08/2021'),

    ('FABRICIO AUGUSTO GOMES',            'Pref. Carambeí',          'Técnico de TI',              '01/04/2020'),
    ('JONATAN RODRIGUES PEREIRA',         'Pref. Carambeí',          'Técnico de TI',              '01/09/2020'),

    ('CLAUDEMIR APARECIDO SILVA',         '12x36',                   'Técnico de TI',              '01/01/2020'),
    ('ELIVELTON MARCELO ROCHA',           '12x36',                   'Técnico de TI',              '01/05/2020'),
    ('WELLINGTON ROBERTO SOUZA',          '12x36',                   'Técnico de TI',              '01/09/2020'),

    ('DANIEL HENRIQUE MARTINS',           'Agrojem',                 'Técnico de TI',              '01/06/2021'),
    ('RAFAEL AUGUSTO RODRIGUES',          'Agrojem',                 'Técnico de TI',              '01/11/2021'),

    ('ALEXANDRE CESAR PEREIRA',           'Jazz',                    'Técnico de TI',              '01/03/2020'),
    ('MAURICIO HENRIQUE LIMA',            'Jazz',                    'Técnico de TI',              '01/08/2020'),

    ('MARCOS VINICIUS SOUZA',             'Pref. Igarapé',           'Técnico de TI',              '01/05/2021'),
    ('ROBSON LUIZ FERREIRA',              'Pref. Igarapé',           'Técnico de TI',              '01/10/2021'),

    ('EDER AUGUSTO SILVA',                'Pref. São Mateus do Sul', 'Técnico de TI',              '01/04/2020'),
    ('LUCAS ROBERTO PEREIRA',             'Pref. São Mateus do Sul', 'Técnico de TI',              '01/09/2020'),

    ('FLAVIO CESAR GOMES',                'Ergon',                   'Técnico de TI',              '01/07/2019'),
    ('IVAN RODRIGUES MARTINS',            'Ergon',                   'Técnico de TI',              '01/01/2020'),

    ('MAURO HENRIQUE SANTOS',             'Operação',                'Técnico de Operação',        '01/03/2018'),
    ('RENATO AUGUSTO LIMA',               'Operação',                'Técnico de Operação',        '01/08/2018'),
    ('WAGNER ROBERTO SILVA',              'Operação',                'Técnico de Operação',        '01/01/2019'),
]

# ── Períodos aquisitivos e férias ─────────────────────────────────────────────
# (nome, ini, fim, dias_direito, limite_saida, [(saida, dias, retorno), ...])

PERIODOS = [
    # ANDERSON MARQUES DA SILVA
    ('ANDERSON MARQUES DA SILVA', '09/03/2022', '08/03/2023', 30, '07/09/2023',
     [('20/07/2023', 30, '19/08/2023')]),
    ('ANDERSON MARQUES DA SILVA', '09/03/2023', '08/03/2024', 30, '07/09/2024',
     [('12/08/2024', 15, '27/08/2024'), ('07/01/2025', 15, '22/01/2025')]),
    ('ANDERSON MARQUES DA SILVA', '09/03/2024', '08/03/2025', 30, '07/09/2025',
     [('01/07/2025', 30, '31/07/2025')]),

    # BRENO HENRIQUE LEME
    ('BRENO HENRIQUE LEME', '01/06/2022', '31/05/2023', 30, '29/11/2023',
     [('02/10/2023', 30, '01/11/2023')]),
    ('BRENO HENRIQUE LEME', '01/06/2023', '31/05/2024', 30, '29/11/2024',
     [('03/02/2025', 30, '05/03/2025')]),
    ('BRENO HENRIQUE LEME', '01/06/2024', '31/05/2025', 30, '29/11/2025', []),

    # LUIS GUSTAVO CAMARGO PINTO
    ('LUIS GUSTAVO CAMARGO PINTO', '14/07/2023', '13/07/2024', 30, '12/01/2025',
     [('06/01/2025', 30, '05/02/2025')]),
    ('LUIS GUSTAVO CAMARGO PINTO', '14/07/2024', '13/07/2025', 30, '12/01/2026', []),

    # RAFAEL PEREIRA DOS SANTOS
    ('RAFAEL PEREIRA DOS SANTOS', '05/04/2022', '04/04/2023', 30, '03/10/2023',
     [('04/09/2023', 30, '04/10/2023')]),
    ('RAFAEL PEREIRA DOS SANTOS', '05/04/2023', '04/04/2024', 30, '03/10/2024',
     [('14/10/2024', 15, '29/10/2024'), ('20/01/2025', 15, '04/02/2025')]),
    ('RAFAEL PEREIRA DOS SANTOS', '05/04/2024', '04/04/2025', 30, '03/10/2025', []),

    # VITOR HUGO RODRIGUES DA SILVA
    ('VITOR HUGO RODRIGUES DA SILVA', '01/02/2022', '31/01/2023', 30, '31/07/2023',
     [('03/07/2023', 30, '02/08/2023')]),
    ('VITOR HUGO RODRIGUES DA SILVA', '01/02/2023', '31/01/2024', 30, '31/07/2024',
     [('01/07/2024', 15, '16/07/2024'), ('06/01/2025', 15, '21/01/2025')]),
    ('VITOR HUGO RODRIGUES DA SILVA', '01/02/2024', '31/01/2025', 30, '31/07/2025', []),

    # ALIF DE PAULA MALUF
    ('ALIF DE PAULA MALUF', '03/06/2021', '02/06/2022', 30, '01/12/2022',
     [('07/11/2022', 30, '07/12/2022')]),
    ('ALIF DE PAULA MALUF', '03/06/2022', '02/06/2023', 30, '01/12/2023',
     [('04/12/2023', 30, '03/01/2024')]),
    ('ALIF DE PAULA MALUF', '03/06/2023', '02/06/2024', 30, '01/12/2024',
     [('02/12/2024', 15, '17/12/2024'), ('05/05/2025', 15, '20/05/2025')]),
    ('ALIF DE PAULA MALUF', '03/06/2024', '02/06/2025', 30, '01/12/2025', []),

    # GABRIEL BECKER RODRIGUES
    ('GABRIEL BECKER RODRIGUES', '02/09/2021', '01/09/2022', 30, '01/03/2023',
     [('06/02/2023', 30, '08/03/2023')]),
    ('GABRIEL BECKER RODRIGUES', '02/09/2022', '01/09/2023', 30, '01/03/2024',
     [('04/03/2024', 30, '03/04/2024')]),
    ('GABRIEL BECKER RODRIGUES', '02/09/2023', '01/09/2024', 30, '01/03/2025',
     [('03/02/2025', 15, '18/02/2025'), ('14/07/2025', 15, '29/07/2025')]),
    ('GABRIEL BECKER RODRIGUES', '02/09/2024', '01/09/2025', 30, '01/03/2026', []),

    # HENRIQUE OLIVEIRA PEREIRA
    ('HENRIQUE OLIVEIRA PEREIRA', '01/03/2022', '28/02/2023', 30, '28/08/2023',
     [('07/08/2023', 30, '06/09/2023')]),
    ('HENRIQUE OLIVEIRA PEREIRA', '01/03/2023', '29/02/2024', 30, '28/08/2024',
     [('05/08/2024', 30, '04/09/2024')]),
    ('HENRIQUE OLIVEIRA PEREIRA', '01/03/2024', '28/02/2025', 30, '28/08/2025', []),

    # NATAN RIGAILO PYTLOWANCIV
    ('NATAN RIGAILO PYTLOWANCIV', '03/08/2021', '02/08/2022', 30, '01/02/2023',
     [('02/01/2023', 30, '01/02/2023')]),
    ('NATAN RIGAILO PYTLOWANCIV', '03/08/2022', '02/08/2023', 30, '01/02/2024',
     [('02/01/2024', 30, '01/02/2024')]),
    ('NATAN RIGAILO PYTLOWANCIV', '03/08/2023', '02/08/2024', 30, '01/02/2025',
     [('02/01/2025', 15, '17/01/2025'), ('05/05/2025', 15, '20/05/2025')]),
    ('NATAN RIGAILO PYTLOWANCIV', '03/08/2024', '02/08/2025', 30, '01/02/2026', []),

    # VICTOR ANDRE FERREIRA
    ('VICTOR ANDRE FERREIRA', '12/10/2021', '11/10/2022', 30, '11/04/2023',
     [('03/04/2023', 30, '03/05/2023')]),
    ('VICTOR ANDRE FERREIRA', '12/10/2022', '11/10/2023', 30, '11/04/2024',
     [('01/04/2024', 30, '01/05/2024')]),
    ('VICTOR ANDRE FERREIRA', '12/10/2023', '11/10/2024', 30, '11/04/2025',
     [('07/04/2025', 15, '22/04/2025'), ('21/07/2025', 15, '05/08/2025')]),
    ('VICTOR ANDRE FERREIRA', '12/10/2024', '11/10/2025', 30, '11/04/2026', []),

    # GABRIEL HENRIQUE DE LIMA
    ('GABRIEL HENRIQUE DE LIMA', '01/04/2022', '31/03/2023', 30, '29/09/2023',
     [('04/09/2023', 30, '04/10/2023')]),
    ('GABRIEL HENRIQUE DE LIMA', '01/04/2023', '31/03/2024', 30, '29/09/2024',
     [('02/09/2024', 30, '02/10/2024')]),
    ('GABRIEL HENRIQUE DE LIMA', '01/04/2024', '31/03/2025', 30, '29/09/2025', []),

    # KELBER OLIVEIRA DA SILVA
    ('KELBER OLIVEIRA DA SILVA', '01/04/2021', '31/03/2022', 30, '29/09/2022',
     [('03/10/2022', 30, '02/11/2022')]),
    ('KELBER OLIVEIRA DA SILVA', '01/04/2022', '31/03/2023', 30, '29/09/2023',
     [('07/08/2023', 30, '06/09/2023')]),
    ('KELBER OLIVEIRA DA SILVA', '01/04/2023', '31/03/2024', 30, '29/09/2024',
     [('26/08/2024', 15, '10/09/2024'), ('06/01/2025', 15, '21/01/2025')]),
    ('KELBER OLIVEIRA DA SILVA', '01/04/2024', '31/03/2025', 30, '29/09/2025', []),

    # MATHEUS HENRIQUE GONCALVES
    ('MATHEUS HENRIQUE GONCALVES', '01/09/2022', '31/08/2023', 30, '28/02/2024',
     [('05/02/2024', 30, '06/03/2024')]),
    ('MATHEUS HENRIQUE GONCALVES', '01/09/2023', '31/08/2024', 30, '28/02/2025',
     [('03/02/2025', 15, '18/02/2025'), ('01/09/2025', 15, '16/09/2025')]),
    ('MATHEUS HENRIQUE GONCALVES', '01/09/2024', '31/08/2025', 30, '28/02/2026', []),

    # SERGIO LUIZ JAVORNIK JUNIOR
    ('SERGIO LUIZ JAVORNIK JUNIOR', '01/03/2021', '28/02/2022', 30, '28/08/2022',
     [('01/08/2022', 30, '31/08/2022')]),
    ('SERGIO LUIZ JAVORNIK JUNIOR', '01/03/2022', '28/02/2023', 30, '28/08/2023',
     [('07/08/2023', 30, '06/09/2023')]),
    ('SERGIO LUIZ JAVORNIK JUNIOR', '01/03/2023', '29/02/2024', 30, '28/08/2024',
     [('05/08/2024', 15, '20/08/2024'), ('06/01/2025', 15, '21/01/2025')]),
    ('SERGIO LUIZ JAVORNIK JUNIOR', '01/03/2024', '28/02/2025', 30, '28/08/2025', []),

    # CAIO CESAR POERNER
    ('CAIO CESAR POERNER', '01/08/2023', '31/07/2024', 30, '28/01/2025',
     [('06/01/2025', 30, '05/02/2025')]),
    ('CAIO CESAR POERNER', '01/08/2024', '31/07/2025', 30, '28/01/2026', []),

    # GUSTAVO HENRIQUE MOREIRA
    ('GUSTAVO HENRIQUE MOREIRA', '16/11/2021', '15/11/2022', 30, '15/05/2023',
     [('02/05/2023', 30, '01/06/2023')]),
    ('GUSTAVO HENRIQUE MOREIRA', '16/11/2022', '15/11/2023', 30, '15/05/2024',
     [('06/05/2024', 30, '05/06/2024')]),
    ('GUSTAVO HENRIQUE MOREIRA', '16/11/2023', '15/11/2024', 30, '15/05/2025',
     [('05/05/2025', 15, '20/05/2025'), ('04/08/2025', 15, '19/08/2025')]),
    ('GUSTAVO HENRIQUE MOREIRA', '16/11/2024', '15/11/2025', 30, '15/05/2026', []),

    # LEANDRO AUGUSTO PEREIRA
    ('LEANDRO AUGUSTO PEREIRA', '01/06/2022', '31/05/2023', 30, '29/11/2023',
     [('06/11/2023', 30, '06/12/2023')]),
    ('LEANDRO AUGUSTO PEREIRA', '01/06/2023', '31/05/2024', 30, '29/11/2024',
     [('04/11/2024', 15, '19/11/2024'), ('05/05/2025', 15, '20/05/2025')]),
    ('LEANDRO AUGUSTO PEREIRA', '01/06/2024', '31/05/2025', 30, '29/11/2025', []),

    # LUCAS GABRIEL RAMOS
    ('LUCAS GABRIEL RAMOS', '01/03/2023', '29/02/2024', 30, '28/08/2024',
     [('05/08/2024', 30, '04/09/2024')]),
    ('LUCAS GABRIEL RAMOS', '01/03/2024', '28/02/2025', 30, '28/08/2025', []),

    # FELIPE AUGUSTO RIBEIRO
    ('FELIPE AUGUSTO RIBEIRO', '03/05/2022', '02/05/2023', 30, '01/11/2023',
     [('02/10/2023', 30, '01/11/2023')]),
    ('FELIPE AUGUSTO RIBEIRO', '03/05/2023', '02/05/2024', 30, '01/11/2024',
     [('07/10/2024', 15, '22/10/2024'), ('05/05/2025', 15, '20/05/2025')]),
    ('FELIPE AUGUSTO RIBEIRO', '03/05/2024', '02/05/2025', 30, '01/11/2025', []),

    # JOAO VICTOR TEODORO
    ('JOAO VICTOR TEODORO', '01/02/2023', '31/01/2024', 30, '31/07/2024',
     [('01/07/2024', 30, '31/07/2024')]),
    ('JOAO VICTOR TEODORO', '01/02/2024', '31/01/2025', 30, '31/07/2025',
     [('07/07/2025', 15, '22/07/2025')]),
    ('JOAO VICTOR TEODORO', '01/02/2025', '31/01/2026', 30, '31/07/2026', []),

    # MATHEUS VINICIUS SOUZA
    ('MATHEUS VINICIUS SOUZA', '01/07/2022', '30/06/2023', 30, '29/12/2023',
     [('04/12/2023', 30, '03/01/2024')]),
    ('MATHEUS VINICIUS SOUZA', '01/07/2023', '30/06/2024', 30, '29/12/2024',
     [('02/12/2024', 30, '01/01/2025')]),
    ('MATHEUS VINICIUS SOUZA', '01/07/2024', '30/06/2025', 30, '29/12/2025', []),

    # CARLOS HENRIQUE SILVA
    ('CARLOS HENRIQUE SILVA', '02/01/2021', '01/01/2022', 30, '01/07/2022',
     [('04/07/2022', 30, '03/08/2022')]),
    ('CARLOS HENRIQUE SILVA', '02/01/2022', '01/01/2023', 30, '01/07/2023',
     [('03/07/2023', 30, '02/08/2023')]),
    ('CARLOS HENRIQUE SILVA', '02/01/2023', '01/01/2024', 30, '01/07/2024',
     [('01/07/2024', 15, '16/07/2024'), ('06/01/2025', 15, '21/01/2025')]),
    ('CARLOS HENRIQUE SILVA', '02/01/2024', '01/01/2025', 30, '01/07/2025', []),

    # DIEGO FERNANDES ROCHA
    ('DIEGO FERNANDES ROCHA', '01/06/2021', '31/05/2022', 30, '29/11/2022',
     [('07/11/2022', 30, '07/12/2022')]),
    ('DIEGO FERNANDES ROCHA', '01/06/2022', '31/05/2023', 30, '29/11/2023',
     [('06/11/2023', 30, '06/12/2023')]),
    ('DIEGO FERNANDES ROCHA', '01/06/2023', '31/05/2024', 30, '29/11/2024',
     [('04/11/2024', 15, '19/11/2024'), ('05/05/2025', 15, '20/05/2025')]),
    ('DIEGO FERNANDES ROCHA', '01/06/2024', '31/05/2025', 30, '29/11/2025', []),

    # GIOVANA APARECIDA SANTOS
    ('GIOVANA APARECIDA SANTOS', '01/09/2021', '31/08/2022', 30, '28/02/2023',
     [('06/02/2023', 30, '08/03/2023')]),
    ('GIOVANA APARECIDA SANTOS', '01/09/2022', '31/08/2023', 30, '28/02/2024',
     [('05/02/2024', 30, '06/03/2024')]),
    ('GIOVANA APARECIDA SANTOS', '01/09/2023', '31/08/2024', 30, '28/02/2025',
     [('03/02/2025', 15, '18/02/2025'), ('14/07/2025', 15, '29/07/2025')]),
    ('GIOVANA APARECIDA SANTOS', '01/09/2024', '31/08/2025', 30, '28/02/2026', []),

    # ANA CLAUDIA FERREIRA
    ('ANA CLAUDIA FERREIRA', '01/03/2020', '28/02/2021', 30, '28/08/2021',
     [('02/08/2021', 30, '01/09/2021')]),
    ('ANA CLAUDIA FERREIRA', '01/03/2021', '28/02/2022', 30, '28/08/2022',
     [('01/08/2022', 30, '31/08/2022')]),
    ('ANA CLAUDIA FERREIRA', '01/03/2022', '28/02/2023', 30, '28/08/2023',
     [('07/08/2023', 15, '22/08/2023'), ('06/01/2025', 15, '21/01/2025')]),
    ('ANA CLAUDIA FERREIRA', '01/03/2023', '29/02/2024', 30, '28/08/2024',
     [('05/08/2024', 30, '04/09/2024')]),
    ('ANA CLAUDIA FERREIRA', '01/03/2024', '28/02/2025', 30, '28/08/2025', []),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalizar(texto):
    nfkd = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def _gerar_email(nome):
    partes = _normalizar(nome).lower().split()
    if len(partes) >= 2:
        return f'{partes[0]}.{partes[-1]}@pellissari.com.br'
    return f'{partes[0]}@pellissari.com.br'


def _d(s):
    d, m, y = s.split('/')
    return date(int(y), int(m), int(d))


# ── Importação ────────────────────────────────────────────────────────────────

def importar():
    app = create_app('development')
    with app.app_context():
        _importar_equipes()
        _importar_colaboradores()
        _importar_periodos()
        db.session.commit()
        print('\nImportação concluída.')


def _importar_equipes():
    print('\n=== Equipes ===')
    for nome in EQUIPES:
        existe = Equipe.query.filter_by(nome=nome).first()
        if existe:
            print(f'  [~] {nome}')
        else:
            db.session.add(Equipe(nome=nome))
            db.session.flush()
            print(f'  [+] {nome}')


def _importar_colaboradores():
    print('\n=== Colaboradores ===')
    for nome, equipe_nome, funcao, admissao_str in COLABORADORES:
        email = _gerar_email(nome)
        existe = Colaborador.query.filter_by(email=email).first()
        if existe:
            print(f'  [~] {nome} ({email})')
            continue

        equipe = Equipe.query.filter_by(nome=equipe_nome).first()
        if not equipe:
            print(f'  [!] Equipe não encontrada: {equipe_nome} — pulando {nome}')
            continue

        d, m, y = admissao_str.split('/')
        admissao = date(int(y), int(m), int(d))

        c = Colaborador(
            nome=nome,
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
        print(f'  [+] {nome} ({email})')


def _importar_periodos():
    print('\n=== Períodos aquisitivos e férias ===')
    for nome_col, ini_str, fim_str, dias_dir, limite_str, blocos in PERIODOS:
        email = _gerar_email(nome_col)
        colab = Colaborador.query.filter_by(email=email).first()
        if not colab:
            colab = Colaborador.query.filter_by(nome=nome_col).first()
        if not colab:
            print(f'  [!] Colaborador não encontrado: {nome_col} — pulando período')
            continue

        ini = _d(ini_str)
        fim = _d(fim_str)
        limite = _d(limite_str)

        periodo = PeriodoAquisitivo.query.filter_by(
            colaborador_id=colab.id,
            data_inicio=ini,
        ).first()
        if not periodo:
            periodo = PeriodoAquisitivo(
                colaborador_id=colab.id,
                data_inicio=ini,
                data_fim=fim,
                dias_direito=dias_dir,
                data_limite_saida=limite,
            )
            db.session.add(periodo)
            db.session.flush()
            print(f'  [+] Período {nome_col}: {ini_str}–{fim_str}')
        else:
            print(f'  [~] Período {nome_col}: {ini_str}–{fim_str}')

        for saida_str, dias, retorno_str in blocos:
            saida = _d(saida_str)
            retorno = _d(retorno_str)

            existe_ferias = Ferias.query.filter_by(
                periodo_aquisitivo_id=periodo.id,
                data_inicio=saida,
            ).first()
            if existe_ferias:
                print(f'      [~] Férias {saida_str} ({dias}d)')
                continue

            f = Ferias(
                colaborador_id=colab.id,
                periodo_aquisitivo_id=periodo.id,
                data_inicio=saida,
                dias=dias,
                data_retorno=retorno,
                status='aprovada',
            )
            db.session.add(f)
            print(f'      [+] Férias {saida_str} ({dias}d) → retorno {retorno_str}')


if __name__ == '__main__':
    importar()
