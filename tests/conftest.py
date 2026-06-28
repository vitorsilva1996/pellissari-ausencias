"""Fixtures compartilhadas entre todos os módulos de teste."""
import pytest
from datetime import date
from dateutil.relativedelta import relativedelta

from app import create_app, db as _db
from app.models import Equipe, Colaborador, PeriodoAquisitivo


# ── Aplicação e banco ─────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def app():
    """Cria a aplicação de teste uma vez por sessão."""
    _app = create_app('testing')
    ctx = _app.app_context()
    ctx.push()
    _db.create_all()
    yield _app
    _db.drop_all()
    ctx.pop()


@pytest.fixture
def client(app):  # noqa: F811
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_tables():
    """Limpa todas as linhas entre testes; mantém o schema intacto."""
    yield
    _db.session.rollback()
    # Nulifica FK auto-referencial antes de deletar colaboradores
    _db.session.execute(
        Colaborador.__table__.update().values(gestor_id=None)
    )
    _db.session.commit()
    for table in reversed(_db.metadata.sorted_tables):
        _db.session.execute(table.delete())
    _db.session.commit()


# ── Dados de suporte ──────────────────────────────────────────────────────────

@pytest.fixture
def equipe():
    e = Equipe(nome='Equipe Teste', descricao='Equipe para testes automatizados')
    _db.session.add(e)
    _db.session.commit()
    return e


@pytest.fixture
def gestor(equipe):
    g = Colaborador(
        nome='Kleber Gestor',
        email='gestor@test.com',
        data_admissao=date.today() - relativedelta(years=3),
        funcao='Gerente de TI',
        equipe_id=equipe.id,
        perfil='gestor',
    )
    g.set_senha('senha123')
    _db.session.add(g)
    _db.session.commit()
    return g


@pytest.fixture
def colaborador(equipe, gestor):
    """Colaborador admitido há 2 anos — elegível para day off e férias."""
    c = Colaborador(
        nome='João Colaborador',
        email='joao@test.com',
        data_admissao=date.today() - relativedelta(years=2),
        funcao='Desenvolvedor',
        equipe_id=equipe.id,
        gestor_id=gestor.id,
        perfil='colaborador',
    )
    c.set_senha('senha123')
    _db.session.add(c)
    _db.session.commit()
    return c


@pytest.fixture
def colaborador_novo(equipe, gestor):
    """Colaborador admitido há 6 meses — inelegível para day off."""
    c = Colaborador(
        nome='Ana Novata',
        email='ana@test.com',
        data_admissao=date.today() - relativedelta(months=6),
        funcao='Analista',
        equipe_id=equipe.id,
        gestor_id=gestor.id,
        perfil='colaborador',
    )
    c.set_senha('senha123')
    _db.session.add(c)
    _db.session.commit()
    return c


@pytest.fixture
def rh(equipe):
    r = Colaborador(
        nome='Carla RH',
        email='rh@test.com',
        data_admissao=date.today() - relativedelta(years=4),
        funcao='Analista de RH',
        equipe_id=equipe.id,
        perfil='rh',
    )
    r.set_senha('senha123')
    _db.session.add(r)
    _db.session.commit()
    return r


@pytest.fixture
def periodo(colaborador):
    """Período aquisitivo com 30 dias disponíveis para o colaborador."""
    hoje = date.today()
    p = PeriodoAquisitivo(
        colaborador_id=colaborador.id,
        data_inicio=hoje - relativedelta(years=1),
        data_fim=hoje - relativedelta(days=1),
        dias_direito=30,
        data_limite_saida=hoje + relativedelta(months=11),
    )
    _db.session.add(p)
    _db.session.commit()
    return p


# ── Helper de login ───────────────────────────────────────────────────────────

@pytest.fixture
def login_as(client):  # noqa: F811
    """Retorna função que faz login via POST e devolve a resposta final."""
    def _login(user, senha='senha123'):
        return client.post(
            '/login',
            data={'email': user.email, 'senha': senha},
            follow_redirects=True,
        )
    return _login
