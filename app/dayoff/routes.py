import calendar
from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from flask import render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from app.dayoff import dayoff
from app.models import DayOff, Notificacao, Colaborador, Equipe
from app import db
from app.auth.permissions import has_permission, require_permission, get_user_equipes
from app.utils import ler_ordenacao
from app.notificacoes.email import (
    enviar_notificacao_dayoff_gestor,
    enviar_notificacao_dayoff_colaborador,
)


def _criar_notificacao(colaborador_id, tipo, mensagem):
    db.session.add(Notificacao(
        colaborador_id=colaborador_id,
        tipo=tipo,
        mensagem=mensagem,
    ))


def _mes_ref(referencia=None):
    """Primeiro dia do mês de referência (padrão: mês atual)."""
    d = referencia or date.today()
    return date(d.year, d.month, 1)


def _saldo_mes(colaborador_id, mes=None):
    """Retorna (usado, saldo) para o mês. Saldo máximo = 1."""
    usado = DayOff.query.filter(
        DayOff.colaborador_id == colaborador_id,
        DayOff.mes_referencia == _mes_ref(mes),
        DayOff.status.notin_(['reprovado', 'cancelado']),
    ).count()
    return usado, max(0, 1 - usado)


def _conflitos_equipe(colaborador, data_solicitada, excluir_id=None):
    """Colegas da mesma equipe com dayoff no mesmo dia (pendente ou aprovado)."""
    colegas = Colaborador.query.filter(
        Colaborador.equipe_id == colaborador.equipe_id,
        Colaborador.id != colaborador.id,
        Colaborador.ativo == 1,
    ).all()

    conflitos = []
    for colega in colegas:
        q = DayOff.query.filter(
            DayOff.colaborador_id == colega.id,
            DayOff.data_solicitada == data_solicitada,
            DayOff.status.in_(['aguardando_gestor', 'aprovado']),
        )
        if excluir_id:
            q = q.filter(DayOff.id != excluir_id)
        if q.first():
            conflitos.append(colega)
    return conflitos


def _pode_aprovar(d):
    """Verifica se o usuário atual pode agir neste day off."""
    if not has_permission(current_user, 'dayoff.aprovar'):
        return False
    if d.status != 'aguardando_gestor':
        return False
    if not has_permission(current_user, 'ferias.aprovar_2'):
        return d.colaborador.equipe_id in get_user_equipes(current_user)
    return True


_STATUS_EQUIPE_FILTROS = frozenset({'todos', 'aguardando', 'aprovado', 'reprovado', 'cancelado'})

_SORT_MEUS = {
    'solicitado_em':   DayOff.solicitado_em,
    'data_solicitada': DayOff.data_solicitada,
    'status':          DayOff.status,
}

_SORT_EQUIPE = {
    'solicitado_em':   DayOff.solicitado_em,
    'nome':            Colaborador.nome,
    'equipe':          Equipe.nome,
    'data_solicitada': DayOff.data_solicitada,
    'status':          DayOff.status,
}


def _solicitacoes_equipe(status_filtro, sort_col, sort_dir):
    """Todos os day offs visíveis para o aprovador (gestor: equipes gerenciadas;
    RH/Administrador: todos), com o status filtrado, ordenados, e a
    permissão de agir por item."""
    if not has_permission(current_user, 'dayoff.aprovar'):
        return None

    q = DayOff.query.join(Colaborador).join(Equipe, Colaborador.equipe_id == Equipe.id)
    if not has_permission(current_user, 'ferias.aprovar_2'):
        equipe_ids = get_user_equipes(current_user)
        q = q.filter(Colaborador.equipe_id.in_(equipe_ids))

    if status_filtro == 'aguardando':
        q = q.filter(DayOff.status == 'aguardando_gestor')
    elif status_filtro in ('aprovado', 'reprovado', 'cancelado'):
        q = q.filter(DayOff.status == status_filtro)

    coluna = _SORT_EQUIPE[sort_col]
    q = q.order_by(coluna.desc() if sort_dir == 'desc' else coluna.asc())

    lista = q.all()
    return [{'dayoff': d, 'pode_aprovar': _pode_aprovar(d)} for d in lista]


# ── Listagem ──────────────────────────────────────────────────────────────────

@dayoff.route('/')
@login_required
def index():
    hoje = date.today()
    usado, saldo = _saldo_mes(current_user.id)

    sort_meus_col, sort_meus_dir = ler_ordenacao('meus', _SORT_MEUS, 'solicitado_em')
    coluna_meus = _SORT_MEUS[sort_meus_col]
    meus = (
        DayOff.query
        .filter_by(colaborador_id=current_user.id)
        .order_by(coluna_meus.desc() if sort_meus_dir == 'desc' else coluna_meus.asc())
        .all()
    )

    pendentes = []
    if has_permission(current_user, 'dayoff.aprovar'):
        q = DayOff.query.join(Colaborador).filter(DayOff.status == 'aguardando_gestor')
        if not has_permission(current_user, 'ferias.aprovar_2'):
            equipe_ids = get_user_equipes(current_user)
            q = q.filter(Colaborador.equipe_id.in_(equipe_ids))
        pendentes = q.order_by(DayOff.solicitado_em.asc()).all()

    status_equipe_filtro = request.args.get('status_equipe', 'todos')
    if status_equipe_filtro not in _STATUS_EQUIPE_FILTROS:
        status_equipe_filtro = 'todos'
    sort_equipe_col, sort_equipe_dir = ler_ordenacao('equipe', _SORT_EQUIPE, 'solicitado_em')
    solicitacoes_equipe = _solicitacoes_equipe(status_equipe_filtro, sort_equipe_col, sort_equipe_dir)

    data_elegibilidade = None
    if not current_user.pode_solicitar_dayoff():
        data_elegibilidade = current_user.data_admissao + relativedelta(years=1)

    return render_template(
        'dayoff/index.html',
        meus=meus,
        pendentes=pendentes,
        saldo=saldo,
        usado=usado,
        mes_atual=hoje,
        data_elegibilidade=data_elegibilidade,
        solicitacoes_equipe=solicitacoes_equipe,
        status_equipe_filtro=status_equipe_filtro,
    )


# ── Solicitação ───────────────────────────────────────────────────────────────

@dayoff.route('/solicitar', methods=['GET', 'POST'])
@require_permission('dayoff.solicitar')
def solicitar():
    hoje = date.today()
    elegivel = current_user.pode_solicitar_dayoff()
    data_elegibilidade = None
    if not elegivel:
        data_elegibilidade = current_user.data_admissao + relativedelta(years=1)

    usado, saldo = _saldo_mes(current_user.id)

    if request.method == 'POST':
        if not elegivel:
            flash('Você ainda não tem elegibilidade para solicitar day off.', 'danger')
            return redirect(url_for('dayoff.solicitar'))

        data_str = request.form.get('data_solicitada', '').strip()

        if not data_str:
            flash('Informe a data desejada.', 'danger')
            return render_template('dayoff/solicitar.html',
                                   elegivel=elegivel,
                                   data_elegibilidade=data_elegibilidade,
                                   saldo=saldo, hoje=hoje)

        try:
            data_solicitada = date.fromisoformat(data_str)
        except ValueError:
            flash('Data inválida.', 'danger')
            return render_template('dayoff/solicitar.html',
                                   elegivel=elegivel,
                                   data_elegibilidade=data_elegibilidade,
                                   saldo=saldo, hoje=hoje)

        erro = None
        if data_solicitada <= hoje:
            erro = 'A data do day off deve ser futura.'
        elif saldo == 0:
            erro = 'Você já utilizou o day off deste mês.'
        elif data_solicitada.month != hoje.month or data_solicitada.year != hoje.year:
            erro = 'O day off deve ser solicitado para o mês atual.'

        if erro:
            flash(erro, 'danger')
            return render_template('dayoff/solicitar.html',
                                   elegivel=elegivel,
                                   data_elegibilidade=data_elegibilidade,
                                   saldo=saldo, hoje=hoje)

        novo = DayOff(
            colaborador_id=current_user.id,
            data_solicitada=data_solicitada,
            mes_referencia=_mes_ref(),
            status='aguardando_gestor',
        )
        db.session.add(novo)

        gestor = current_user.gestor
        if gestor:
            _criar_notificacao(
                gestor.id,
                'dayoff_solicitado',
                f'{current_user.nome} solicitou day off para '
                f'{data_solicitada.strftime("%d/%m/%Y")}.',
            )

        db.session.commit()
        enviar_notificacao_dayoff_gestor(novo)

        conflitos = _conflitos_equipe(current_user, data_solicitada)
        if conflitos:
            nomes = ', '.join(c.nome.split()[0] for c in conflitos)
            flash(
                f'Solicitação enviada! Atenção: {nomes} da sua equipe '
                f'também tem day off neste dia.',
                'warning',
            )
        else:
            flash('Solicitação de day off enviada com sucesso!', 'success')

        return redirect(url_for('dayoff.index'))

    ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
    data_min = date(hoje.year, hoje.month, min(hoje.day + 1, ultimo_dia)).isoformat()
    data_max = date(hoje.year, hoje.month, ultimo_dia).isoformat()

    return render_template('dayoff/solicitar.html',
                           elegivel=elegivel,
                           data_elegibilidade=data_elegibilidade,
                           saldo=saldo, hoje=hoje,
                           data_min=data_min, data_max=data_max)


# ── Aprovação ─────────────────────────────────────────────────────────────────

@dayoff.route('/aprovar/<int:id>', methods=['GET', 'POST'])
@require_permission('dayoff.aprovar')
def aprovar(id):
    d = DayOff.query.get_or_404(id)

    # Aprovadores de 1º nível só podem agir em equipes que gerenciam
    if not has_permission(current_user, 'ferias.aprovar_2'):
        equipe_ids = get_user_equipes(current_user)
        if d.colaborador.equipe_id not in equipe_ids:
            abort(403)

    if d.status != 'aguardando_gestor':
        flash('Esta solicitação já foi processada.', 'warning')
        return redirect(url_for('dayoff.index'))

    conflitos = _conflitos_equipe(d.colaborador, d.data_solicitada, excluir_id=d.id)

    if request.method == 'POST':
        acao = request.form.get('acao')
        comentario = request.form.get('comentario', '').strip()

        if acao not in ('aprovar', 'reprovar'):
            flash('Ação inválida.', 'danger')
            return render_template('dayoff/aprovar.html', d=d, conflitos=conflitos)

        d.comentario_gestor = comentario
        d.decidido_em = datetime.utcnow()

        if acao == 'aprovar':
            d.status = 'aprovado'
            _criar_notificacao(
                d.colaborador_id,
                'dayoff_aprovado',
                f'Seu day off de {d.data_solicitada.strftime("%d/%m/%Y")} foi aprovado!',
            )
            flash('Day off aprovado.', 'success')
        else:
            d.status = 'reprovado'
            _criar_notificacao(
                d.colaborador_id,
                'dayoff_reprovado',
                f'Seu day off de {d.data_solicitada.strftime("%d/%m/%Y")} foi reprovado.'
                + (f' Motivo: {comentario}' if comentario else ''),
            )
            flash('Solicitação reprovada.', 'info')

        db.session.commit()
        enviar_notificacao_dayoff_colaborador(d)
        return redirect(url_for('dayoff.index'))

    return render_template('dayoff/aprovar.html', d=d, conflitos=conflitos)


# ── Cancelamento ──────────────────────────────────────────────────────────────

@dayoff.route('/cancelar/<int:id>', methods=['POST'])
@login_required
def cancelar(id):
    d = DayOff.query.filter_by(id=id, colaborador_id=current_user.id).first_or_404()

    if d.status != 'aguardando_gestor':
        flash('Só é possível cancelar solicitações aguardando aprovação.', 'warning')
        return redirect(url_for('dayoff.index'))

    d.status = 'cancelado'
    gestor = current_user.gestor
    if gestor:
        _criar_notificacao(
            gestor.id,
            'dayoff_cancelado',
            f'{current_user.nome} cancelou o day off de '
            f'{d.data_solicitada.strftime("%d/%m/%Y")}.',
        )

    db.session.commit()
    flash('Solicitação cancelada.', 'info')
    return redirect(url_for('dayoff.index'))
