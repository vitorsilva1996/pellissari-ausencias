from datetime import date, timedelta

from flask import render_template, request, abort
from flask_login import login_required, current_user

from app.painel import painel
from app.models import (
    Colaborador, Equipe, PeriodoAquisitivo, Ferias, DayOff
)

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
    # Soma dias de férias aprovadas que ainda não terminaram
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
    if current_user.perfil in ('rh', 'diretoria'):
        return Equipe.query.order_by(Equipe.nome).all()
    return [current_user.equipe]


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

    # ── Status de férias por colaborador ─────────────────────────────────────
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
            # Ignora períodos antigos 100% concluídos
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

        # Status "pior" do colaborador
        status_geral = max(
            (pr['status'] for pr in periodos_rel),
            key=lambda s: _STATUS_PRIO.get(s, -1),
            default='sem_periodo',
        )

        # Período mais crítico para exibir na tabela
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

        # Alertas por período
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

    # ── Solicitações pendentes ────────────────────────────────────────────────
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

    # ── Day offs não solicitados no mês ──────────────────────────────────────
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

    # ── Férias aprovadas vigentes ─────────────────────────────────────────────
    ferias_aprovadas = Ferias.query.filter(
        Ferias.colaborador_id.in_(colab_ids),
        Ferias.status == 'aprovada',
        Ferias.data_retorno >= hoje,
    ).count()

    return dict(
        colab_rows=colab_rows,
        totais=dict(
            colaboradores=len(colaboradores),
            ferias_aprovadas=ferias_aprovadas,
            pendentes=len(pendentes_ferias) + len(pendentes_dayoff),
            vencidos_atencao=n_vencidos_atencao,
        ),
        alertas=dict(
            vencidos=alertas_vencidos,
            dias_30=alertas_30,
            dias_60=alertas_60,
            dias_90=alertas_90,
        ),
        pendentes_ferias=pendentes_ferias,
        pendentes_dayoff=pendentes_dayoff,
        dayoff_sem_solicitacao=dayoff_sem_solicitacao,
        hoje=hoje,
    )


# ── Rotas ─────────────────────────────────────────────────────────────────────

@painel.route('/')
@login_required
def index():
    # Colaboradores veem o painel pessoal simplificado
    if current_user.perfil == 'colaborador':
        return render_template('painel/pessoal.html')

    hoje = date.today()
    equipes = _equipes_visiveis()
    equipe_ids = {e.id for e in equipes}

    # Filtro por equipe (só RH / diretoria podem escolher)
    equipe_filtro = request.args.get('equipe', 'todas')
    if equipe_filtro != 'todas' and current_user.perfil in ('rh', 'diretoria'):
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
@login_required
def equipe(equipe_id):
    if current_user.perfil == 'colaborador':
        abort(403)

    eq = Equipe.query.get_or_404(equipe_id)

    # Gestor só acessa a própria equipe
    if current_user.perfil == 'gestor' and current_user.equipe_id != equipe_id:
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
