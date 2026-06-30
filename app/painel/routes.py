from datetime import date, timedelta

from flask import render_template, request, abort, send_file, Response
from flask_login import login_required, current_user

from app import db
from app.painel import painel
from app.models import (
    Colaborador, Equipe, PeriodoAquisitivo, Ferias, DayOff
)
from app.auth.permissions import has_permission, require_permission, get_user_equipes

# Ordem de prioridade: quanto maior, mais crítico
_STATUS_PRIO = {
    'sem_periodo': -1,
    'concluido':    0,
    'programado':   1,
    'pendente':     2,
    'atencao':      3,
    'vencido':      4,
}


def _status_periodo(periodo, hoje):
    """Classifica um PeriodoAquisitivo conforme as regras de negócio."""
    restantes = periodo.dias_restantes()
    if restantes == 0:
        return 'concluido'
    if periodo.data_limite_saida < hoje:
        return 'vencido'
    dias_ate_limite = (periodo.data_limite_saida - hoje).days
    ferias_futuras = [
        f for f in periodo.ferias
        if f.status == 'aprovada' and f.data_retorno > hoje
    ]
    dias_programados = sum(f.dias for f in ferias_futuras)
    if dias_ate_limite <= 60 and dias_programados < restantes:
        return 'atencao'
    if ferias_futuras:
        return 'programado'
    return 'pendente'


def _equipes_visiveis():
    if has_permission(current_user, 'painel.exportar'):
        return Equipe.query.order_by(Equipe.nome).all()
    ids = get_user_equipes(current_user)
    return Equipe.query.filter(Equipe.id.in_(ids)).order_by(Equipe.nome).all()


def _dados_painel(equipe_ids, hoje):
    """Compila todos os dados para o dashboard gerencial."""
    mes_ref = date(hoje.year, hoje.month, 1)

    colaboradores = (
        Colaborador.query
        .filter(Colaborador.equipe_id.in_(equipe_ids), Colaborador.ativo == 1)
        .order_by(Colaborador.nome)
        .all()
    )
    colab_ids = [c.id for c in colaboradores]

    colab_rows = []
    alertas_vencidos = []
    alertas_30 = []
    alertas_60 = []
    alertas_90 = []
    n_vencidos_atencao = 0

    for c in colaboradores:
        periodos = (
            PeriodoAquisitivo.query
            .filter_by(colaborador_id=c.id)
            .order_by(PeriodoAquisitivo.data_inicio.desc())
            .all()
        )

        periodos_rel = []
        for p in periodos:
            restantes = p.dias_restantes()
            if restantes == 0 and p.data_limite_saida < hoje - timedelta(days=90):
                continue
            s = _status_periodo(p, hoje)
            dias_limite = (p.data_limite_saida - hoje).days
            periodos_rel.append({
                'periodo':    p,
                'status':     s,
                'restantes':  restantes,
                'dias_limite': dias_limite,
            })

        status_geral = max(
            (pr['status'] for pr in periodos_rel),
            key=lambda s: _STATUS_PRIO.get(s, -1),
            default='sem_periodo',
        )

        periodo_principal = max(
            periodos_rel,
            key=lambda pr: _STATUS_PRIO.get(pr['status'], -1),
            default=None,
        )

        colab_rows.append({
            'colaborador':     c,
            'status':          status_geral,
            'periodo_princ':   periodo_principal,
            'periodos':        periodos_rel,
        })

        if status_geral in ('vencido', 'atencao'):
            n_vencidos_atencao += 1

        for pr in periodos_rel:
            s = pr['status']
            d = pr['dias_limite']
            item = {'colaborador': c, **pr}
            if s == 'vencido':
                alertas_vencidos.append(item)
            elif s == 'atencao':
                if d <= 30:
                    alertas_30.append(item)
                else:
                    alertas_60.append(item)
            elif s in ('pendente', 'programado') and 60 < d <= 90:
                alertas_90.append(item)

    pendentes_ferias = (
        Ferias.query
        .join(Colaborador)
        .filter(
            Colaborador.id.in_(colab_ids),
            Ferias.status.in_(['aguardando_gestor', 'aguardando_rh']),
        )
        .order_by(Ferias.solicitado_em.asc())
        .all()
    )

    pendentes_dayoff = (
        DayOff.query
        .join(Colaborador)
        .filter(
            Colaborador.id.in_(colab_ids),
            DayOff.status == 'aguardando_gestor',
        )
        .order_by(DayOff.solicitado_em.asc())
        .all()
    )

    dayoff_sem_solicitacao = []
    for c in colaboradores:
        if not c.pode_solicitar_dayoff():
            continue
        tem = DayOff.query.filter(
            DayOff.colaborador_id == c.id,
            DayOff.mes_referencia == mes_ref,
            DayOff.status.notin_(['reprovado', 'cancelado']),
        ).count()
        if not tem:
            dayoff_sem_solicitacao.append(c)

    ferias_aprovadas = Ferias.query.filter(
        Ferias.colaborador_id.in_(colab_ids),
        Ferias.status == 'aprovada',
        Ferias.data_retorno >= hoje,
    ).count()

    _eq_map = {}
    for row in colab_rows:
        eq = row['colaborador'].equipe
        if eq.id not in _eq_map:
            _eq_map[eq.id] = {'nome': eq.nome, 'total': 0, 'ok': 0, 'atencao': 0, 'vencido': 0}
        _eq_map[eq.id]['total'] += 1
        s = row['status']
        if s == 'vencido':
            _eq_map[eq.id]['vencido'] += 1
        elif s == 'atencao':
            _eq_map[eq.id]['atencao'] += 1
        else:
            _eq_map[eq.id]['ok'] += 1
    resumo_equipes = sorted(_eq_map.values(), key=lambda x: x['nome'])

    alertas_criticos = sorted(
        alertas_vencidos + alertas_30 + alertas_60,
        key=lambda a: a['dias_limite'],
    )

    pendentes_aprovacao = []
    for f in pendentes_ferias:
        pendentes_aprovacao.append({
            'tipo': 'ferias',
            'colaborador': f.colaborador,
            'data': f.data_inicio,
            'status': f.status,
            'id': f.id,
            'dias': f.dias,
        })
    for d in pendentes_dayoff:
        pendentes_aprovacao.append({
            'tipo': 'dayoff',
            'colaborador': d.colaborador,
            'data': d.data_solicitada,
            'status': d.status,
            'id': d.id,
            'dias': 1,
        })
    pendentes_aprovacao.sort(key=lambda x: x['data'])

    return dict(
        colab_rows=colab_rows,
        totais=dict(
            colaboradores=len(colaboradores),
            ferias_aprovadas=ferias_aprovadas,
            pendentes=len(pendentes_ferias) + len(pendentes_dayoff),
            vencidos_atencao=n_vencidos_atencao,
            dayoff_sem_solicitacao=len(dayoff_sem_solicitacao),
        ),
        alertas=dict(
            vencidos=alertas_vencidos,
            dias_30=alertas_30,
            dias_60=alertas_60,
            dias_90=alertas_90,
        ),
        alertas_criticos=alertas_criticos,
        resumo_equipes=resumo_equipes,
        pendentes_aprovacao=pendentes_aprovacao,
        pendentes_ferias=pendentes_ferias,
        pendentes_dayoff=pendentes_dayoff,
        dayoff_sem_solicitacao=dayoff_sem_solicitacao,
        hoje=hoje,
    )


# ── Rotas ─────────────────────────────────────────────────────────────────────

@painel.route('/')
@login_required
def index():
    if not has_permission(current_user, 'painel.ver'):
        return render_template('painel/pessoal.html')

    hoje = date.today()
    equipes = _equipes_visiveis()
    equipe_ids = {e.id for e in equipes}

    equipe_filtro = request.args.get('equipe', 'todas')
    if equipe_filtro != 'todas' and has_permission(current_user, 'painel.exportar'):
        try:
            fid = int(equipe_filtro)
            if fid in equipe_ids:
                equipe_ids = {fid}
        except ValueError:
            pass

    dados = _dados_painel(equipe_ids, hoje)
    return render_template(
        'painel/index.html',
        equipes=equipes,
        equipe_filtro=equipe_filtro,
        equipe_detalhe=None,
        **dados,
    )


@painel.route('/equipe/<int:equipe_id>')
@require_permission('painel.ver')
def equipe(equipe_id):
    eq = Equipe.query.get_or_404(equipe_id)

    if not has_permission(current_user, 'painel.exportar'):
        equipe_ids = get_user_equipes(current_user)
        if equipe_id not in equipe_ids:
            abort(403)

    hoje = date.today()
    equipes = _equipes_visiveis()
    dados = _dados_painel({equipe_id}, hoje)

    return render_template(
        'painel/index.html',
        equipes=equipes,
        equipe_filtro=str(equipe_id),
        equipe_detalhe=eq,
        **dados,
    )


@painel.route('/colaboradores')
@require_permission('painel.ver')
def colaboradores():
    hoje = date.today()
    equipes = _equipes_visiveis()
    equipe_ids = {e.id for e in equipes}

    equipe_filtro = request.args.get('equipe', 'todas')
    if equipe_filtro != 'todas' and has_permission(current_user, 'painel.exportar'):
        try:
            fid = int(equipe_filtro)
            if fid in equipe_ids:
                equipe_ids = {fid}
        except ValueError:
            pass

    dados = _dados_painel(equipe_ids, hoje)
    return render_template(
        'painel/colaboradores.html',
        equipes=equipes,
        equipe_filtro=equipe_filtro,
        **dados,
    )


# ── Exportações ───────────────────────────────────────────────────────────────

def _resolver_equipe_ids():
    """Retorna (equipe_ids, equipe_label) com base no query param ?equipe=."""
    equipes = _equipes_visiveis()
    equipe_ids = {e.id for e in equipes}
    equipe_filtro = request.args.get('equipe', 'todas')

    if equipe_filtro != 'todas' and has_permission(current_user, 'painel.exportar'):
        try:
            fid = int(equipe_filtro)
            if fid in equipe_ids:
                equipe_ids = {fid}
                equipe_label = next(e.nome for e in equipes if e.id == fid)
                return equipe_ids, equipe_label
        except (ValueError, StopIteration):
            pass

    return equipe_ids, 'Todas as equipes'


@painel.route('/exportar/pdf')
@require_permission('painel.exportar')
def exportar_pdf():
    from app.painel.relatorios import gerar_pdf_ferias
    equipe_ids, equipe_label = _resolver_equipe_ids()
    dados = _dados_painel(equipe_ids, date.today())

    pdf = gerar_pdf_ferias(dados['colab_rows'], equipe_label)
    return Response(
        pdf,
        mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=ferias.pdf'},
    )


@painel.route('/exportar/excel')
@require_permission('painel.exportar')
def exportar_excel():
    from app.painel.relatorios import gerar_excel_ferias
    equipe_ids, equipe_label = _resolver_equipe_ids()
    dados = _dados_painel(equipe_ids, date.today())

    xlsx = gerar_excel_ferias(dados['colab_rows'], dados['alertas'], equipe_label)
    return Response(
        xlsx,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=ferias.xlsx'},
    )


@painel.route('/exportar/alertas/pdf')
@require_permission('painel.exportar')
def exportar_alertas_pdf():
    from app.painel.relatorios import gerar_pdf_alertas
    equipe_ids, equipe_label = _resolver_equipe_ids()
    dados = _dados_painel(equipe_ids, date.today())

    pdf = gerar_pdf_alertas(dados['alertas'], equipe_label)
    return Response(
        pdf,
        mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=alertas.pdf'},
    )
