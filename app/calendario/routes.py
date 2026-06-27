import calendar
from collections import defaultdict
from datetime import date, timedelta

from flask import render_template, request
from flask_login import login_required, current_user

from app.calendario import calendario
from app.models import Ferias, DayOff, Colaborador, Equipe

MESES_PT = [
    '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]
DIAS_SEMANA = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']


def _equipes_visiveis():
    """Equipes que o usuário atual pode visualizar."""
    if current_user.perfil in ('rh', 'diretoria'):
        return Equipe.query.order_by(Equipe.nome).all()
    # colaborador e gestor veem apenas a própria equipe
    return [current_user.equipe]


def _colaboradores_visiveis(equipe_ids):
    return (
        Colaborador.query
        .filter(Colaborador.equipe_id.in_(equipe_ids), Colaborador.ativo == 1)
        .all()
    )


def _construir_ausencias(ano, mes, colab_ids):
    """
    Retorna (ausencias_por_dia, conflito_por_dia).

    ausencias_por_dia: {dia_int: [{'nome', 'tipo', 'equipe_id'}]}
    conflito_por_dia:  set de dias com 2+ ausentes da mesma equipe
    """
    num_dias = calendar.monthrange(ano, mes)[1]
    primeiro_dia = date(ano, mes, 1)
    ultimo_dia = date(ano, mes, num_dias)

    ausencias = defaultdict(list)

    # ── Férias aprovadas que se sobrepõem ao mês ──────────────────────────────
    ferias_mes = (
        Ferias.query
        .filter(
            Ferias.colaborador_id.in_(colab_ids),
            Ferias.status == 'aprovada',
            Ferias.data_inicio <= ultimo_dia,
            Ferias.data_retorno > primeiro_dia,
        )
        .all()
    )

    for f in ferias_mes:
        # data_retorno é o dia de volta ao trabalho; [data_inicio, data_retorno)
        dia = max(f.data_inicio, primeiro_dia)
        fim = min(f.data_retorno, ultimo_dia + timedelta(days=1))
        while dia < fim:
            ausencias[dia.day].append({
                'nome': f.colaborador.nome,
                'nome_curto': f.colaborador.nome.split()[0],
                'tipo': 'ferias',
                'equipe_id': f.colaborador.equipe_id,
            })
            dia += timedelta(days=1)

    # ── Day offs aprovados no mês ─────────────────────────────────────────────
    dayoffs_mes = (
        DayOff.query
        .filter(
            DayOff.colaborador_id.in_(colab_ids),
            DayOff.status == 'aprovado',
            DayOff.data_solicitada >= primeiro_dia,
            DayOff.data_solicitada <= ultimo_dia,
        )
        .all()
    )

    for d in dayoffs_mes:
        ausencias[d.data_solicitada.day].append({
            'nome': d.colaborador.nome,
            'nome_curto': d.colaborador.nome.split()[0],
            'tipo': 'dayoff',
            'equipe_id': d.colaborador.equipe_id,
        })

    # ── Detectar conflitos (2+ ausentes da mesma equipe no mesmo dia) ─────────
    conflito_por_dia = set()
    for dia, lista in ausencias.items():
        contagem_por_equipe = defaultdict(int)
        for a in lista:
            contagem_por_equipe[a['equipe_id']] += 1
        if any(v >= 2 for v in contagem_por_equipe.values()):
            conflito_por_dia.add(dia)

    return dict(ausencias), conflito_por_dia


def _render(ano, mes):
    hoje = date.today()

    # Validação básica
    if not (1 <= mes <= 12):
        mes = hoje.month
        ano = hoje.year

    equipes_disponiveis = _equipes_visiveis()
    equipe_ids_disponiveis = {e.id for e in equipes_disponiveis}

    # Filtro por equipe via query string (apenas para quem vê mais de uma)
    equipe_filtro = request.args.get('equipe', 'todas')
    if equipe_filtro != 'todas':
        try:
            fid = int(equipe_filtro)
            equipe_ids_filtradas = {fid} & equipe_ids_disponiveis
        except ValueError:
            equipe_ids_filtradas = equipe_ids_disponiveis
    else:
        equipe_ids_filtradas = equipe_ids_disponiveis

    if not equipe_ids_filtradas:
        equipe_ids_filtradas = equipe_ids_disponiveis

    colab_ids = [c.id for c in _colaboradores_visiveis(equipe_ids_filtradas)]

    ausencias_por_dia, conflito_por_dia = _construir_ausencias(ano, mes, colab_ids)

    # Navegação mês anterior / próximo
    if mes == 1:
        prev_ano, prev_mes = ano - 1, 12
    else:
        prev_ano, prev_mes = ano, mes - 1

    if mes == 12:
        next_ano, next_mes = ano + 1, 1
    else:
        next_ano, next_mes = ano, mes + 1

    # Grade: lista de semanas, cada semana = lista de 7 ints (0 = fora do mês)
    semanas = calendar.monthcalendar(ano, mes)

    return render_template(
        'calendario/index.html',
        ano=ano,
        mes=mes,
        nome_mes=MESES_PT[mes],
        dias_semana=DIAS_SEMANA,
        semanas=semanas,
        hoje=hoje,
        ausencias_por_dia=ausencias_por_dia,
        conflito_por_dia=conflito_por_dia,
        equipes_disponiveis=equipes_disponiveis,
        equipe_filtro=equipe_filtro,
        prev_ano=prev_ano, prev_mes=prev_mes,
        next_ano=next_ano, next_mes=next_mes,
    )


# ── Rotas ─────────────────────────────────────────────────────────────────────

@calendario.route('/')
@login_required
def index():
    hoje = date.today()
    return _render(hoje.year, hoje.month)


@calendario.route('/<int:ano>/<int:mes>')
@login_required
def mes_especifico(ano, mes):
    return _render(ano, mes)
