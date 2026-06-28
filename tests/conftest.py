"""Fixtures compartilhadas entre todos os módulos de teste."""
import pytest
from datetime import date
from dateutil.relativedelta import relativedelta

from app import create_app, db as _db
from app.models import Equipe, Colaborador, PeriodoAquisitivo


# ── Aplicação e banco ─────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def app():
    """Cria a aplicação de teste uma única vez por sessão."""
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
def isolated_db(app):  # noqa: F811
    """
    Isolamento de sessão por teste.

    Antes do teste: expira o identity map para não herdar estado da sessão anterior.
    Depois do teste: rollback de transações pendentes, deleta todos os dados,
    expira o identity map e remove a sessão — o próximo teste começa sem rastros.

    Esse padrão evita ObjectDeletedError causado por objetos de um teste
    ficando marcados como 'deleted' no identity map quando o próximo teste roda.
    """
    _db.session.expire_all()
    yield _db.session
    _db.session.rollback()
    try:
        # Remove FK auto-referencial antes de deletar colaboradores
        _db.session.execute(
            Colaborador.__table__.update().values(gestor_id=None)
        )
        _db.session.commit()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()
    except Exception:
        _db.session.rollback()
    finally:
        # Expira todos os objetos do identity map para o próximo teste não ver
        # objetos marcados como deleted
        _db.session.expire_all()
        # Remove a sessão do registry — próximo acesso cria sessão limpa
        _db.session.remove()


# ── Dados de suporte ──────────────────────────────────────────────────────────

@pytest.fixture
def equipe():
    e = Equipe(nome='Equipe Teste', descricao='Equipe para testes automatizados')
    _db.session.add(e)
    _db.session.commit()
    _db.session.refresh(e)
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
    _db.session.refresh(g)
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
    _db.session.refresh(c)
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
    _db.session.refresh(c)
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
    _db.session.refresh(r)
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
    _db.session.refresh(p)
    return p


# ── Helper de login ───────────────────────────────────────────────────────────

@pytest.fixture
def login_as(client):  # noqa: F811
    """Retorna função que faz login via POST e devolve a resposta final."""
    def _login(user, senha='senha123'):
        # Lê email antes de qualquer potencial expiração de sessão
        email = user.email
        return client.post(
            '/login',
            data={'email': email, 'senha': senha},
            follow_redirects=True,
        )
    return _login
