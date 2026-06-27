from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.notificacoes import notificacoes
from app.models import Notificacao
from app import db

_TIPOS_LABEL = {
    'ferias_solicitada':      'Férias solicitadas',
    'ferias_aprovada_gestor': 'Férias aprovadas pelo gestor',
    'ferias_aguardando_rh':   'Férias aguardando RH',
    'ferias_aprovada':        'Férias aprovadas',
    'ferias_reprovada':       'Férias reprovadas',
    'ferias_cancelada':       'Férias canceladas',
    'dayoff_solicitado':      'Day off solicitado',
    'dayoff_aprovado':        'Day off aprovado',
    'dayoff_reprovado':       'Day off reprovado',
    'dayoff_cancelado':       'Day off cancelado',
}

_TIPOS_ICONE = {
    'ferias_solicitada':      '🏖',
    'ferias_aprovada_gestor': '✅',
    'ferias_aguardando_rh':   '⏳',
    'ferias_aprovada':        '✅',
    'ferias_reprovada':       '❌',
    'ferias_cancelada':       '🚫',
    'dayoff_solicitado':      '☀️',
    'dayoff_aprovado':        '✅',
    'dayoff_reprovado':       '❌',
    'dayoff_cancelado':       '🚫',
}


@notificacoes.route('/')
@login_required
def index():
    todas = (
        Notificacao.query
        .filter_by(colaborador_id=current_user.id)
        .order_by(Notificacao.criado_em.desc())
        .all()
    )
    nao_lidas = [n for n in todas if not n.lida]
    lidas = [n for n in todas if n.lida]

    return render_template(
        'notificacoes/index.html',
        nao_lidas=nao_lidas,
        lidas=lidas,
        labels=_TIPOS_LABEL,
        icones=_TIPOS_ICONE,
    )


@notificacoes.route('/<int:id>/marcar-lida', methods=['POST'])
@login_required
def marcar_lida(id):
    n = Notificacao.query.filter_by(
        id=id, colaborador_id=current_user.id
    ).first_or_404()
    n.lida = 1
    db.session.commit()
    # Volta para a página anterior se for seguro, caso contrário lista de notificações
    next_url = request.referrer
    return redirect(next_url or url_for('notificacoes.index'))


@notificacoes.route('/marcar-todas-lidas', methods=['POST'])
@login_required
def marcar_todas_lidas():
    Notificacao.query.filter_by(
        colaborador_id=current_user.id, lida=0
    ).update({'lida': 1})
    db.session.commit()
    flash('Todas as notificações foram marcadas como lidas.', 'success')
    return redirect(url_for('notificacoes.index'))
