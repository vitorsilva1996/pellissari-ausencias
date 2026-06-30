"""
Migração do sistema de permissões.

O que faz:
  1. Cria as novas tabelas (perfis, permissoes, perfil_permissoes, colaborador_equipes)
     via db.create_all() — seguro para executar múltiplas vezes.
  2. Cadastra 15 permissões e 5 perfis padrão (se ainda não existirem).
  3. Associa cada colaborador ao perfil correspondente ao seu campo `perfil` (string).
  4. Popula colaborador_equipes para gestores com base na equipe atual.

Idempotente — pode ser executado novamente sem duplicar dados.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Colaborador, Equipe, Permissao, Perfil

app = create_app()

# ── Definições ────────────────────────────────────────────────────────────────

PERMISSOES = [
    # (codigo, descricao, modulo)
    ('ferias.solicitar',        'Solicitar férias',                'Férias'),
    ('ferias.aprovar_1',        'Aprovar férias (1º nível/gestor)', 'Férias'),
    ('ferias.aprovar_2',        'Aprovar férias (2º nível/RH)',    'Férias'),
    ('ferias.cancelar',         'Cancelar férias de outros',       'Férias'),
    ('dayoff.solicitar',        'Solicitar day off',               'Day Off'),
    ('dayoff.aprovar',          'Aprovar day off',                 'Day Off'),
    ('colaboradores.ver',       'Ver colaboradores',               'Colaboradores'),
    ('colaboradores.cadastrar', 'Cadastrar colaboradores',         'Colaboradores'),
    ('colaboradores.editar',    'Editar colaboradores',            'Colaboradores'),
    ('colaboradores.desativar', 'Desativar/reativar colaboradores','Colaboradores'),
    ('colaboradores.periodos',  'Gerenciar períodos aquisitivos',  'Colaboradores'),
    ('painel.ver',              'Ver painel gerencial',            'Painel'),
    ('painel.exportar',         'Exportar relatórios',             'Painel'),
    ('configuracoes.perfis',    'Gerenciar perfis de acesso',      'Configurações'),
    ('configuracoes.equipes',   'Gerenciar equipes',               'Configurações'),
]

# Mapa perfil_nome → lista de codigos de permissoes
PERFIS = {
    'Colaborador': [
        'ferias.solicitar', 'dayoff.solicitar',
    ],
    'Gestor': [
        'ferias.solicitar', 'ferias.aprovar_1',
        'dayoff.solicitar', 'dayoff.aprovar',
        'colaboradores.ver', 'painel.ver',
    ],
    'RH': [
        'ferias.solicitar', 'ferias.aprovar_1', 'ferias.aprovar_2', 'ferias.cancelar',
        'dayoff.solicitar', 'dayoff.aprovar',
        'colaboradores.ver', 'colaboradores.cadastrar', 'colaboradores.editar',
        'colaboradores.desativar', 'colaboradores.periodos',
        'painel.ver', 'painel.exportar',
        'configuracoes.perfis', 'configuracoes.equipes',
    ],
    'Diretoria': [
        'colaboradores.ver', 'painel.ver', 'painel.exportar',
    ],
    'Administrador': [p[0] for p in PERMISSOES],  # todas as permissões
}

# Mapeamento string legada → nome do Perfil
_PERFIL_STR_MAP = {
    'colaborador': 'Colaborador',
    'gestor':      'Gestor',
    'rh':          'RH',
    'diretoria':   'Diretoria',
}


# ── Execução ─────────────────────────────────────────────────────────────────

with app.app_context():

    # 1. Cria tabelas novas + adiciona colunas ausentes em tabelas existentes
    print('1. Criando/verificando tabelas e colunas...')
    db.create_all()

    # Adicionar perfil_id em colaboradores se não existir (ALTER TABLE seguro)
    with db.engine.connect() as conn:
        res = conn.execute(db.text(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "  AND TABLE_NAME = 'colaboradores' "
            "  AND COLUMN_NAME = 'perfil_id'"
        ))
        if res.scalar() == 0:
            conn.execute(db.text(
                'ALTER TABLE colaboradores '
                'ADD COLUMN perfil_id INT NULL, '
                'ADD CONSTRAINT fk_colab_perfil '
                '  FOREIGN KEY (perfil_id) REFERENCES perfis(id)'
            ))
            conn.commit()
            print('   [+] coluna perfil_id adicionada a colaboradores')
        else:
            print('   [-] coluna perfil_id já existe')

    print('   OK')

    # 2. Permissões
    print('\n2. Cadastrando permissões...')
    perm_map = {}  # codigo → objeto Permissao
    for codigo, descricao, modulo in PERMISSOES:
        existing = Permissao.query.filter_by(codigo=codigo).first()
        if existing:
            perm_map[codigo] = existing
            print(f'   [-] {codigo} (já existe)')
        else:
            p = Permissao(codigo=codigo, descricao=descricao, modulo=modulo)
            db.session.add(p)
            db.session.flush()
            perm_map[codigo] = p
            print(f'   [+] {codigo}')

    db.session.commit()

    # 3. Perfis padrão
    print('\n3. Cadastrando perfis...')
    perfil_map = {}  # nome → objeto Perfil
    for nome, codigos in PERFIS.items():
        existing = Perfil.query.filter_by(nome=nome).first()
        if existing:
            perfil_map[nome] = existing
            print(f'   [-] {nome} (já existe)')
        else:
            perf = Perfil(nome=nome)
            perf.permissoes = [perm_map[c] for c in codigos if c in perm_map]
            db.session.add(perf)
            db.session.flush()
            perfil_map[nome] = perf
            print(f'   [+] {nome} ({len(perf.permissoes)} permissões)')

    db.session.commit()

    # 4. Migrar colaboradores: preencher perfil_id
    print('\n4. Associando colaboradores aos perfis...')
    atualizados = 0
    for c in Colaborador.query.all():
        if c.perfil_id is not None:
            continue  # já migrado
        nome_perfil = _PERFIL_STR_MAP.get(c.perfil)
        if nome_perfil and nome_perfil in perfil_map:
            c.perfil_id = perfil_map[nome_perfil].id
            atualizados += 1
        else:
            print(f'   [!] {c.nome}: perfil="{c.perfil}" não mapeado, pulando')

    db.session.commit()
    print(f'   {atualizados} colaborador(es) atualizados.')

    # 5. Gestores: popular colaborador_equipes com equipe atual
    print('\n5. Populando equipes gerenciadas para gestores...')
    gestores = Colaborador.query.filter(
        Colaborador.perfil.in_(['gestor', 'rh', 'diretoria']),
        Colaborador.ativo == 1,
    ).all()

    for g in gestores:
        if g.equipes_gerenciadas:
            print(f'   [-] {g.nome}: já tem {len(g.equipes_gerenciadas)} equipe(s) gerenciadas')
            continue
        if g.equipe_id:
            equipe = Equipe.query.get(g.equipe_id)
            if equipe:
                g.equipes_gerenciadas = [equipe]
                print(f'   [+] {g.nome} ({g.perfil}): equipe "{equipe.nome}"')

    db.session.commit()

    print('\n✔ Migração concluída.')
    print(f'   Perfis: {Perfil.query.count()}')
    print(f'   Permissões: {Permissao.query.count()}')
    print(f'   Colaboradores com perfil_id: {Colaborador.query.filter(Colaborador.perfil_id.isnot(None)).count()}')
