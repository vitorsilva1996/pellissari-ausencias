"""
Popula o banco com dados de teste baseados na Pellissari.
Seguro para re-executar: ignora registros já existentes e atualiza o Vitor.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date
from dateutil.relativedelta import relativedelta

from app import create_app, db
from app.models import Colaborador, Equipe, PeriodoAquisitivo

app = create_app()

SENHA_PADRAO = 'pellissari@2024'


# ── helpers ───────────────────────────────────────────────────────────────────

def get_ou_criar_equipe(nome):
    eq = Equipe.query.filter_by(nome=nome).first()
    if not eq:
        eq = Equipe(nome=nome)
        db.session.add(eq)
        db.session.flush()
        print(f'  [+] Equipe criada: {nome}')
    else:
        print(f'  [=] Equipe já existe: {nome}')
    return eq


def get_ou_criar_colaborador(nome, email, funcao, equipe, admissao, perfil,
                              gestor=None):
    c = Colaborador.query.filter_by(email=email).first()
    if not c:
        c = Colaborador(
            nome=nome,
            email=email,
            funcao=funcao,
            equipe_id=equipe.id,
            gestor_id=gestor.id if gestor else None,
            data_admissao=admissao,
            perfil=perfil,
            ativo=1,
        )
        c.set_senha(SENHA_PADRAO)
        db.session.add(c)
        db.session.flush()
        print(f'  [+] Colaborador criado: {nome} <{email}>')
    else:
        print(f'  [=] Colaborador já existe: {nome} <{email}>')
    return c


def criar_periodo(colaborador, data_inicio, data_fim, dias=30, limite=None):
    """Cria período aquisitivo se não existir (checa por colaborador+data_inicio)."""
    existente = PeriodoAquisitivo.query.filter_by(
        colaborador_id=colaborador.id,
        data_inicio=data_inicio,
    ).first()
    if existente:
        print(f'    [=] Período aquisitivo já existe: {data_inicio} – {data_fim}')
        return existente

    if limite is None:
        # CLT: colaborador deve sair até 11 meses após fim do período
        limite = data_fim + relativedelta(months=11)

    p = PeriodoAquisitivo(
        colaborador_id=colaborador.id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        dias_direito=dias,
        data_limite_saida=limite,
    )
    db.session.add(p)
    db.session.flush()
    print(f'    [+] Período aquisitivo: {data_inicio} – {data_fim} ({dias}d, limite {limite})')
    return p


def periodos_por_admissao(colaborador, admissao):
    """Gera todos os períodos aquisitivos desde a admissão até hoje."""
    hoje = date.today()
    inicio = admissao
    while inicio <= hoje:
        fim = inicio + relativedelta(years=1) - relativedelta(days=1)
        criar_periodo(colaborador, inicio, fim)
        inicio = fim + relativedelta(days=1)


# ── script principal ──────────────────────────────────────────────────────────

with app.app_context():
    print('\n=== Equipes ===')
    eq_debian = get_ou_criar_equipe('Debian')
    eq_kali   = get_ou_criar_equipe('Kali')

    # ── Gestores (criados antes dos subordinados) ─────────────────────────────
    print('\n=== Gestores ===')

    kleber = get_ou_criar_colaborador(
        nome='Kleber Pedroso',
        email='kleber.pedroso@pellissari.com.br',
        funcao='Gestor de TI',
        equipe=eq_debian,
        admissao=date(2025, 3, 25),
        perfil='gestor',
    )

    adilson = get_ou_criar_colaborador(
        nome='Adilson Ferreira',
        email='adilson.ferreira@pellissari.com.br',
        funcao='Gestor de TI',
        equipe=eq_kali,
        admissao=date(2024, 1, 1),
        perfil='gestor',
    )

    # ── Colaboradores ─────────────────────────────────────────────────────────
    print('\n=== Colaboradores ===')

    marco = get_ou_criar_colaborador(
        nome='Marco Aurelio',
        email='marco.aurelio@pellissari.com.br',
        funcao='Especialista em TI',
        equipe=eq_debian,
        admissao=date(2024, 9, 2),
        perfil='colaborador',
        gestor=kleber,
    )

    tarcisio = get_ou_criar_colaborador(
        nome='Tarcisio Mazur',
        email='tarcisio.mazur@pellissari.com.br',
        funcao='Técnico em TI',
        equipe=eq_debian,
        admissao=date(2024, 7, 4),
        perfil='colaborador',
        gestor=kleber,
    )

    breno = get_ou_criar_colaborador(
        nome='Breno Macyszyn',
        email='breno.macyszyn@pellissari.com.br',
        funcao='Técnico em TI',
        equipe=eq_kali,
        admissao=date(2024, 3, 6),
        perfil='colaborador',
        gestor=adilson,
    )

    # ── Atualiza o Vitor (já existente) ───────────────────────────────────────
    print('\n=== Vitor (atualização) ===')
    vitor = Colaborador.query.filter_by(email='vitor@pellissari.com.br').first()
    if vitor:
        vitor.equipe_id   = eq_debian.id
        vitor.gestor_id   = kleber.id
        vitor.data_admissao = date(2024, 2, 29)
        db.session.flush()
        print(f'  [~] Vitor atualizado: equipe=Debian, gestor=Kleber, admissão=29/02/2024')
    else:
        print('  [!] Vitor não encontrado — rode criar_admin.py primeiro.')
        vitor = None

    # ── Períodos aquisitivos ──────────────────────────────────────────────────
    print('\n=== Períodos aquisitivos ===')

    if vitor:
        print(f'  {vitor.nome}:')
        criar_periodo(
            vitor,
            data_inicio=date(2024, 2, 29),
            data_fim=date(2025, 2, 28),
            dias=30,
            limite=date(2026, 1, 28),
        )

    print(f'  {kleber.nome}:')
    periodos_por_admissao(kleber, date(2025, 3, 25))

    print(f'  {adilson.nome}:')
    periodos_por_admissao(adilson, date(2024, 1, 1))

    print(f'  {marco.nome}:')
    periodos_por_admissao(marco, date(2024, 9, 2))

    print(f'  {tarcisio.nome}:')
    periodos_por_admissao(tarcisio, date(2024, 7, 4))

    print(f'  {breno.nome}:')
    periodos_por_admissao(breno, date(2024, 3, 6))

    db.session.commit()

    # ── Resumo ────────────────────────────────────────────────────────────────
    print('\n=== Resumo ===')
    print(f'  Equipes:       {Equipe.query.count()}')
    print(f'  Colaboradores: {Colaborador.query.count()}')
    print(f'  Períodos aq.:  {PeriodoAquisitivo.query.count()}')
    print('\nCredenciais de acesso:')
    for c in Colaborador.query.order_by(Colaborador.nome).all():
        print(f'  {c.email:45s}  senha: {SENHA_PADRAO}  perfil: {c.perfil}')
    print()
