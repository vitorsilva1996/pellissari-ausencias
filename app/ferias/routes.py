from datetime import date, timedelta, datetime

from flask import render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from app.ferias import ferias
from app.models import Ferias, PeriodoAquisitivo, Notificacao, Colaborador, Equipe
from app import db
from app.auth.permissions import (
    has_permission, require_permission, require_any_permission,
    get_user_equipes, usuarios_com_permissao,
)
from app.utils import ler_ordenacao
from app.notificacoes.email import (
    enviar_notificacao_ferias_gestor,
    enviar_notificacao_ferias_rh,
    enviar_notificacao_ferias_colaborador,
)


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
    if has_permission(current_user, 'ferias.aprovar_2'):
        return f.status in ('aguardando_gestor', 'aguardando_rh')
    if has_permission(current_user, 'ferias.aprovar_1'):
        equipe_ids = get_user_equipes(current_user)
        return (
            f.status == 'aguardando_gestor'
            and f.colaborador.equipe_id in equipe_ids
        )
    return False


# ── Listagem ──────────────────────────────────────────────────────────────────

_STATUS_EQUIPE_FILTROS = frozenset({'todos', 'aguardando', 'aprovada', 'reprovada', 'cancelada'})

_SORT_MINHAS = {
    'solicitado_em': Ferias.solicitado_em,
    'inicio':        Ferias.data_inicio,
    'status':        Ferias.status,
}

_SORT_EQUIPE = {
    'solicitado_em': Ferias.solicitado_em,
    'nome':          Colaborador.nome,
    'equipe':        Equipe.nome,
    'inicio':        Ferias.data_inicio,
    'status':        Ferias.status,
}


def _solicitacoes_equipe(status_filtro, sort_col, sort_dir):
    """Todas as férias visíveis para o aprovador (gestor: equipes gerenciadas;
    RH/Administrador: todas), com o status filtrado, ordenadas, e a
    permissão de agir por item."""
    pode_aprovar_2 = has_permission(current_user, 'ferias.aprovar_2')
    pode_aprovar_1 = has_permission(current_user, 'ferias.aprovar_1')
    if not (pode_aprovar_1 or pode_aprovar_2):
        return None

    q = Ferias.query.join(Colaborador).join(Equipe, Colaborador.equipe_id == Equipe.id)
    if not pode_aprovar_2:
        equipe_ids = get_user_equipes(current_user)
        q = q.filter(Colaborador.equipe_id.in_(equipe_ids))

    if status_filtro == 'aguardando':
        q = q.filter(Ferias.status.in_(['aguardando_gestor', 'aguardando_rh']))
    elif status_filtro in ('aprovada', 'reprovada', 'cancelada'):
        q = q.filter(Ferias.status == status_filtro)

    coluna = _SORT_EQUIPE[sort_col]
    q = q.order_by(coluna.desc() if sort_dir == 'desc' else coluna.asc())

    lista = q.all()
    return [{'ferias': f, 'pode_aprovar': _pode_aprovar(f)} for f in lista]


@ferias.route('/')
@login_required
def index():
    sort_minhas_col, sort_minhas_dir = ler_ordenacao('minhas', _SORT_MINHAS, 'solicitado_em')
    coluna_minhas = _SORT_MINHAS[sort_minhas_col]
    minhas = (
        Ferias.query
        .filter_by(colaborador_id=current_user.id)
        .order_by(coluna_minhas.desc() if sort_minhas_dir == 'desc' else coluna_minhas.asc())
        .all()
    )

    pendentes = []
    pode_aprovar_2 = has_permission(current_user, 'ferias.aprovar_2')
    pode_aprovar_1 = has_permission(current_user, 'ferias.aprovar_1')

    if pode_aprovar_2:
        pendentes = (
            Ferias.query
            .filter(Ferias.status.in_(['aguardando_gestor', 'aguardando_rh']))
            .order_by(Ferias.solicitado_em.asc())
            .all()
        )
    elif pode_aprovar_1:
        equipe_ids = get_user_equipes(current_user)
        pendentes = (
            Ferias.query
            .join(Colaborador)
            .filter(
                Colaborador.equipe_id.in_(equipe_ids),
                Ferias.status == 'aguardando_gestor',
            )
            .order_by(Ferias.solicitado_em.asc())
            .all()
        )

    status_equipe_filtro = request.args.get('status_equipe', 'todos')
    if status_equipe_filtro not in _STATUS_EQUIPE_FILTROS:
        status_equipe_filtro = 'todos'
    sort_equipe_col, sort_equipe_dir = ler_ordenacao('equipe', _SORT_EQUIPE, 'solicitado_em')
    solicitacoes_equipe = _solicitacoes_equipe(status_equipe_filtro, sort_equipe_col, sort_equipe_dir)

    hoje = date.today()
    periodos = (
        PeriodoAquisitivo.query
        .filter_by(colaborador_id=current_user.id)
        .order_by(PeriodoAquisitivo.data_inicio.desc())
        .all()
    )
    periodos_info = []
    for p in periodos:
        usados = p.dias_usados()
        restantes = p.dias_restantes()
        pct = min(100, int(usados / p.dias_direito * 100)) if p.dias_direito else 0
        periodos_info.append({
            'periodo': p,
            'usados': usados,
            'restantes': restantes,
            'pct': pct,
            'vencido': p.data_limite_saida < hoje,
            'dias_limite': (p.data_limite_saida - hoje).days,
        })

    return render_template('ferias/index.html',
                           minhas=minhas,
                           pendentes=pendentes,
                           periodos_info=periodos_info,
                           solicitacoes_equipe=solicitacoes_equipe,
                           status_equipe_filtro=status_equipe_filtro)


# ── Solicitação ───────────────────────────────────────────────────────────────

@ferias.route('/solicitar', methods=['GET', 'POST'])
@require_permission('ferias.solicitar')
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
            return render_template('ferias/solicitar.html',
                                   periodos=periodos_disponiveis,
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
        enviar_notificacao_ferias_gestor(nova)

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
@require_any_permission('ferias.aprovar_1', 'ferias.aprovar_2')
def aprovar(id):
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

        _acao_gestor = None
        if not has_permission(current_user, 'ferias.aprovar_2'):
            # Aprovador de 1º nível (gestor)
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
                for rh in usuarios_com_permissao('ferias.aprovar_2'):
                    _criar_notificacao(
                        rh.id,
                        'ferias_aguardando_rh',
                        f'Férias de {f.colaborador.nome} aprovadas pelo gestor, '
                        f'aguardando validação do RH.',
                    )
                flash('Férias aprovadas e encaminhadas ao RH.', 'success')
                _acao_gestor = 'aprovada_rh'
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
                _acao_gestor = 'reprovada'

        else:
            # Aprovador de 2º nível (RH / administrador)
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

        if not has_permission(current_user, 'ferias.aprovar_2') and _acao_gestor:
            if _acao_gestor == 'aprovada_rh':
                enviar_notificacao_ferias_rh(f)
            else:
                enviar_notificacao_ferias_colaborador(f)
        else:
            enviar_notificacao_ferias_colaborador(f)

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
    if has_permission(current_user, 'ferias.aprovar_2'):
        lista = (
            Ferias.query
            .join(Colaborador)
            .order_by(Ferias.solicitado_em.desc())
            .all()
        )
    elif has_permission(current_user, 'ferias.aprovar_1'):
        equipe_ids = get_user_equipes(current_user)
        lista = (
            Ferias.query
            .join(Colaborador)
            .filter(Colaborador.equipe_id.in_(equipe_ids))
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
