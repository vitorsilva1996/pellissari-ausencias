"""Testes do módulo de day off."""
import calendar
from datetime import date

import pytest

from app import db
from app.models import DayOff


def _data_futura_no_mes():
    """Retorna o primeiro dia disponível no mês atual após hoje."""
    hoje = date.today()
    ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
    if hoje.day >= ultimo_dia:
        return None  # sem dia disponível no mês (último dia do mês)
    return date(hoje.year, hoje.month, hoje.day + 1).isoformat()


# ── test_dayoff_colaborador_inelegivel ────────────────────────────────────────

def test_dayoff_colaborador_inelegivel(client, colaborador_novo, login_as):
    """Colaborador com menos de 1 ano não pode solicitar day off."""
    login_as(colaborador_novo)

    data_str = _data_futura_no_mes()
    if data_str is None:
        pytest.skip('Sem data futura disponível no mês atual')

    resp = client.post('/dayoff/solicitar', data={
        'data_solicitada': data_str,
    }, follow_redirects=True)

    assert resp.status_code == 200
    body = resp.data.decode('utf-8')
    assert 'elegibilidade' in body.lower() or 'elegível' in body.lower()


# ── test_dayoff_saldo_esgotado ────────────────────────────────────────────────

def test_dayoff_saldo_esgotado(client, colaborador, login_as):
    """Colaborador que já usou o day off do mês não pode solicitar outro."""
    hoje = date.today()
    # Cria um dayoff pendente para o mês atual
    db.session.add(DayOff(
        colaborador_id=colaborador.id,
        data_solicitada=hoje,
        mes_referencia=date(hoje.year, hoje.month, 1),
        status='aguardando_gestor',
    ))
    db.session.commit()

    login_as(colaborador)

    data_str = _data_futura_no_mes()
    if data_str is None:
        pytest.skip('Sem data futura disponível no mês atual')

    resp = client.post('/dayoff/solicitar', data={
        'data_solicitada': data_str,
    }, follow_redirects=True)

    assert resp.status_code == 200
    body = resp.data.decode('utf-8')
    assert 'já utilizou' in body or 'saldo' in body.lower()
    # Garante que não foi criado um segundo dayoff
    assert DayOff.query.filter_by(colaborador_id=colaborador.id).count() == 1


# ── test_solicitar_dayoff_valido ──────────────────────────────────────────────

def test_solicitar_dayoff_valido(client, colaborador, login_as):
    """Colaborador elegível pode solicitar day off para data futura no mês."""
    data_str = _data_futura_no_mes()
    if data_str is None:
        pytest.skip('Sem data futura disponível no mês atual')

    login_as(colaborador)

    resp = client.post('/dayoff/solicitar', data={
        'data_solicitada': data_str,
    }, follow_redirects=True)

    assert resp.status_code == 200

    dayoff = DayOff.query.filter_by(colaborador_id=colaborador.id).first()
    assert dayoff is not None
    assert dayoff.status == 'aguardando_gestor'
    assert dayoff.data_solicitada.isoformat() == data_str
