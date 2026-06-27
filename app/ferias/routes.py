from datetime import date, timedelta, datetime

from flask import render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from app.ferias import ferias
from app.models import Ferias, PeriodoAquisitivo, Notificacao, Colaborador
from app import db


def _criar_notificacao(colaborador_id, tipo, mensagem):
    db.session.add(Notificacao(
        colaborador_id=colaborador_id,
        tipo=tipo,
        mensagem=mensagem,
    ))


def _conflitos_equipe(colaborador, data_inicio, data_retorno, excluir_id=None):
    """Retorna colegas da mesma equipe com férias sobrepostas ao período."""
    colegas = Colaborador.query.filter(
        Colaborador.equipe_id == colaborador.equipe_id,
        Colaborador.id != colaborador.id,
        Colaborador.ativo == 1,
    ).all()

    conflitos = []
    for colega in colegas:
        q = Ferias.query.filter(
            Ferias.colaborador_id == colega.id,
            Ferias.status.in_(['aguardando_gestor', 'aguardando_rh', 'aprovada']),
            Ferias.data_inicio < data_retorno,
            Ferias.data_retorno > data_inicio,
        )
        if excluir_id:
            q = q.filter(Ferias.id != excluir_id)
        if q.first():
            conflitos.append(colega)
    return conflitos


def _pode_aprovar(f):
    """Verifica se o usuário atual pode agir nesta solicitação."""
    if current_user.perfil == 'gestor':
        return (
            f.status == 'aguardando_gestor'
            and f.colaborador.gestor_id == current_user.id
        )
    if current_user.perfil in ('rh', 'diretoria'):
        return f.status in ('aguardando_gestor', 'aguardando_rh')
    return False


# ── Listagem ──────────────────────────────────────────────────────────────────

@ferias.route('/')
@login_required
def index():
    minhas = (
        Ferias.query
        .filter_by(colaborador_id=current_user.id)
        .order_by(Ferias.solicitado_em.desc())
        .all()
    )

    pendentes = []
    if current_user.perfil in ('gestor', 'rh', 'diretoria'):
        q = Ferias.query.join(Colaborador)
        if current_user.perfil == 'gestor':
            q = q.filter(
                Colaborador.gestor_id == current_user.id,
                Ferias.status == 'aguardando_gestor',
            )
        else:
            q = q.filter(Ferias.status.in_(['aguardando_gestor', 'aguardando_rh']))
        pendentes = q.order_by(Ferias.solicitado_em.asc()).all()

    return render_template('ferias/index.html', minhas=minhas, pendentes=pendentes)


# ── Solicitação ───────────────────────────────────────────────────────────────

@ferias.route('/solicitar', methods=['GET', 'POST'])
@login_required
def solicitar():
    periodos = (
        PeriodoAquisitivo.query
        .filter_by(colaborador_id=current_user.id)
        .order_by(PeriodoAquisitivo.data_inicio.desc())
        .all()
    )
    periodos_disponiveis = [p for p in periodos if p.dias_restantes() > 0]

    if request.method == 'POST':
        periodo_id = request.form.get('periodo_aquisitivo_id', type=int)
        data_inicio_str = request.form.get('data_inicio', '').strip()
        dias = request.form.get('dias', type=int)

        erro = None
        periodo = None

        if not all([periodo_id, data_inicio_str, dias]):
            erro = 'Preencha todos os campos obrigatórios.'
        elif dias not in (15, 30):
            erro = 'A quantidade de dias deve ser 15 ou 30.'
        else:
            periodo = PeriodoAquisitivo.query.filter_by(
                id=periodo_id, colaborador_id=current_user.id
            ).first()
            if not periodo:
                erro = 'Período aquisitivo inválido.'
            else:
                try:
                    data_inicio = date.fromisoformat(data_inicio_str)
                except ValueError:
                    erro = 'Data de início inválida.'

        if not erro:
            if data_inicio < date.today():
                erro = 'A data de início não pode ser no passado.'
            elif dias > periodo.dias_restantes():
                erro = f'Dias insuficientes. Disponível: {periodo.dias_restantes()} dia(s).'
            else:
                ferias_ativas = Ferias.query.filter(
                    Ferias.periodo_aquisitivo_id == periodo.id,
                    Ferias.status.notin_(['reprovada', 'cancelada']),
                ).count()
                if ferias_ativas >= 2:
                    erro = 'Limite de 2 períodos de férias por período aquisitivo já atingido.'

        if erro:
            flash(erro, 'danger')
            return render_template('ferias/solicitar.html', periodos=periodos_disponiveis,
                           today=date.today().isoformat())

        data_retorno = data_inicio + timedelta(days=dias)

        nova = Ferias(
            colaborador_id=current_user.id,
            periodo_aquisitivo_id=periodo.id,
            data_inicio=data_inicio,
            dias=dias,
            data_retorno=data_retorno,
            status='aguardando_gestor',
        )
        db.session.add(nova)

        gestor = current_user.gestor
        if gestor:
            _criar_notificacao(
                gestor.id,
                'ferias_solicitada',
                f'{current_user.nome} solicitou {dias} dias de férias '
                f'a partir de {data_inicio.strftime("%d/%m/%Y")}.',
            )

        db.session.commit()

        conflitos = _conflitos_equipe(current_user, data_inicio, data_retorno)
        if conflitos:
            nomes = ', '.join(c.nome.split()[0] for c in conflitos)
            flash(
                f'Solicitação enviada! Atenção: {nomes} da sua equipe '
                f'também têm férias nesse período.',
                'warning',
            )
        else:
            flash('Solicitação de férias enviada com sucesso!', 'success')

        return redirect(url_for('ferias.index'))

    return render_template('ferias/solicitar.html', periodos=periodos_disponiveis,
                           today=date.today().isoformat())


# ── Aprovação / Reprovação ────────────────────────────────────────────────────

@ferias.route('/aprovar/<int:id>', methods=['GET', 'POST'])
@login_required
def aprovar(id):
    if current_user.perfil not in ('gestor', 'rh', 'diretoria'):
        abort(403)

    f = Ferias.query.get_or_404(id)

    if not _pode_aprovar(f):
        flash('Você não tem permissão para agir nesta solicitação.', 'warning')
        return redirect(url_for('ferias.index'))

    conflitos = _conflitos_equipe(f.colaborador, f.data_inicio, f.data_retorno, excluir_id=f.id)

    if request.method == 'POST':
        acao = request.form.get('acao')
        comentario = request.form.get('comentario', '').strip()
        agora = datetime.utcnow()

        if acao not in ('aprovar', 'reprovar'):
            flash('Ação inválida.', 'danger')
            return render_template('ferias/aprovar.html', f=f, conflitos=conflitos)

        if current_user.perfil == 'gestor':
            if acao == 'aprovar':
                f.status = 'aguardando_rh'
                f.comentario_gestor = comentario
                f.aprovado_gestor_em = agora
                _criar_notificacao(
                    f.colaborador_id,
                    'ferias_aprovada_gestor',
                    f'Suas férias de {f.data_inicio.strftime("%d/%m/%Y")} foram aprovadas '
                    f'pelo gestor e seguem para análise do RH.',
                )
                for rh in Colaborador.query.filter_by(perfil='rh', ativo=1).all():
                    _criar_notificacao(
                        rh.id,
                        'ferias_aguardando_rh',
                        f'Férias de {f.colaborador.nome} aprovadas pelo gestor, '
                        f'aguardando validação do RH.',
                    )
                flash('Férias aprovadas e encaminhadas ao RH.', 'success')
            else:
                f.status = 'reprovada'
                f.comentario_gestor = comentario
                _criar_notificacao(
                    f.colaborador_id,
                    'ferias_reprovada',
                    f'Suas férias de {f.data_inicio.strftime("%d/%m/%Y")} foram reprovadas '
                    f'pelo gestor.' + (f' Motivo: {comentario}' if comentario else ''),
                )
                flash('Solicitação reprovada.', 'info')

        else:  # rh / diretoria
            if f.status == 'aguardando_gestor':
                f.aprovado_gestor_em = agora

            if acao == 'aprovar':
                f.status = 'aprovada'
                f.comentario_rh = comentario
                f.aprovado_rh_em = agora
                _criar_notificacao(
                    f.colaborador_id,
                    'ferias_aprovada',
                    f'Suas férias de {f.data_inicio.strftime("%d/%m/%Y")} a '
                    f'{f.data_retorno.strftime("%d/%m/%Y")} foram aprovadas!',
                )
                flash('Férias aprovadas com sucesso!', 'success')
            else:
                f.status = 'reprovada'
                f.comentario_rh = comentario
                _criar_notificacao(
                    f.colaborador_id,
                    'ferias_reprovada',
                    f'Suas férias de {f.data_inicio.strftime("%d/%m/%Y")} foram reprovadas '
                    f'pelo RH.' + (f' Motivo: {comentario}' if comentario else ''),
                )
                flash('Solicitação reprovada.', 'info')

        db.session.commit()
        return redirect(url_for('ferias.index'))

    return render_template('ferias/aprovar.html', f=f, conflitos=conflitos)


# ── Cancelamento ──────────────────────────────────────────────────────────────

@ferias.route('/cancelar/<int:id>', methods=['POST'])
@login_required
def cancelar(id):
    f = Ferias.query.filter_by(id=id, colaborador_id=current_user.id).first_or_404()

    if f.status != 'aguardando_gestor':
        flash('Só é possível cancelar solicitações ainda aguardando o gestor.', 'warning')
        return redirect(url_for('ferias.index'))

    f.status = 'cancelada'
    gestor = current_user.gestor
    if gestor:
        _criar_notificacao(
            gestor.id,
            'ferias_cancelada',
            f'{current_user.nome} cancelou a solicitação de férias '
            f'de {f.data_inicio.strftime("%d/%m/%Y")}.',
        )

    db.session.commit()
    flash('Solicitação cancelada.', 'info')
    return redirect(url_for('ferias.index'))


# ── Histórico ─────────────────────────────────────────────────────────────────

@ferias.route('/historico')
@login_required
def historico():
    if current_user.perfil in ('rh', 'diretoria'):
        lista = (
            Ferias.query
            .join(Colaborador)
            .order_by(Ferias.solicitado_em.desc())
            .all()
        )
    elif current_user.perfil == 'gestor':
        lista = (
            Ferias.query
            .join(Colaborador)
            .filter(Colaborador.gestor_id == current_user.id)
            .order_by(Ferias.solicitado_em.desc())
            .all()
        )
    else:
        lista = (
            Ferias.query
            .filter_by(colaborador_id=current_user.id)
            .order_by(Ferias.solicitado_em.desc())
            .all()
        )

    return render_template('ferias/historico.html', lista=lista)
