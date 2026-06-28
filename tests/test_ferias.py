"""Testes do módulo de férias."""
from datetime import date, timedelta

from app import db
from app.models import Ferias


def _data_futura(dias=10):
    return (date.today() + timedelta(days=dias)).isoformat()


# ── test_solicitar_ferias_sem_periodo_aquisitivo ──────────────────────────────

def test_solicitar_ferias_sem_periodo_aquisitivo(client, colaborador, login_as):
    """POST sem período aquisitivo deve retornar erro de validação."""
    login_as(colaborador)

    # Envia um periodo_id inexistente
    resp = client.post('/ferias/solicitar', data={
        'periodo_aquisitivo_id': '9999',
        'data_inicio': _data_futura(15),
        'dias': '15',
    }, follow_redirects=True)

    assert resp.status_code == 200
    body = resp.data.decode('utf-8')
    # Espera mensagem de erro de período inválido ou campos obrigatórios
    assert 'inválido' in body or 'obrigatório' in body or 'Período' in body


# ── test_solicitar_ferias_com_periodo_valido ──────────────────────────────────

def test_solicitar_ferias_com_periodo_valido(client, colaborador, periodo, login_as):
    """Solicitação com dados válidos deve criar registro aguardando gestor."""
    login_as(colaborador)

    resp = client.post('/ferias/solicitar', data={
        'periodo_aquisitivo_id': str(periodo.id),
        'data_inicio': _data_futura(15),
        'dias': '15',
    }, follow_redirects=True)

    assert resp.status_code == 200

    ferias = Ferias.query.filter_by(colaborador_id=colaborador.id).first()
    assert ferias is not None
    assert ferias.status == 'aguardando_gestor'
    assert ferias.dias == 15
    assert ferias.periodo_aquisitivo_id == periodo.id


# ── test_aprovacao_gestor ─────────────────────────────────────────────────────

def test_aprovacao_gestor(client, colaborador, gestor, periodo, login_as):
    """Gestor aprova → status passa para aguardando_rh."""
    hoje = date.today()
    f = Ferias(
        colaborador_id=colaborador.id,
        periodo_aquisitivo_id=periodo.id,
        data_inicio=hoje + timedelta(days=15),
        dias=15,
        data_retorno=hoje + timedelta(days=30),
        status='aguardando_gestor',
    )
    db.session.add(f)
    db.session.commit()

    login_as(gestor)
    resp = client.post(f'/ferias/aprovar/{f.id}', data={
        'acao': 'aprovar',
        'comentario': 'Aprovado pelo gestor',
    }, follow_redirects=True)

    assert resp.status_code == 200
    updated = db.session.get(Ferias, f.id)
    assert updated.status == 'aguardando_rh'
    assert updated.aprovado_gestor_em is not None


# ── test_aprovacao_rh ─────────────────────────────────────────────────────────

def test_aprovacao_rh(client, colaborador, rh, periodo, login_as):
    """RH aprova solicitação → status passa para aprovada."""
    hoje = date.today()
    f = Ferias(
        colaborador_id=colaborador.id,
        periodo_aquisitivo_id=periodo.id,
        data_inicio=hoje + timedelta(days=20),
        dias=15,
        data_retorno=hoje + timedelta(days=35),
        status='aguardando_rh',
    )
    db.session.add(f)
    db.session.commit()

    login_as(rh)
    resp = client.post(f'/ferias/aprovar/{f.id}', data={
        'acao': 'aprovar',
        'comentario': '',
    }, follow_redirects=True)

    assert resp.status_code == 200
    updated = db.session.get(Ferias, f.id)
    assert updated.status == 'aprovada'
    assert updated.aprovado_rh_em is not None
