"""Jobs agendados para lembretes e alertas automáticos."""
import logging
from datetime import date, timedelta

from app import scheduler
from app.models import Colaborador, Ferias, DayOff, PeriodoAquisitivo

log = logging.getLogger(__name__)

_DIAS_UTEIS_LEMBRETE = 3


def _dias_uteis_entre(inicio, fim):
    """Conta dias úteis (seg-sex) no intervalo [inicio, fim)."""
    count = 0
    delta = (fim - inicio).days
    for i in range(delta):
        if (inicio + timedelta(days=i)).weekday() < 5:
            count += 1
    return count


@scheduler.task('cron', id='lembrete_aprovacao', hour=8, minute=0)
def job_lembrete_aprovacao():
    """Lembrete quando solicitação aguarda resposta há 3+ dias úteis."""
    with scheduler.app.app_context():
        from app.notificacoes.email import enviar_lembrete_aprovacao
        hoje = date.today()

        for f in Ferias.query.filter(
            Ferias.status.in_(['aguardando_gestor', 'aguardando_rh'])
        ).all():
            try:
                if _dias_uteis_entre(f.solicitado_em.date(), hoje) >= _DIAS_UTEIS_LEMBRETE:
                    enviar_lembrete_aprovacao(f, 'ferias')
            except Exception:
                log.exception('Erro ao enviar lembrete férias id=%s', f.id)

        for d in DayOff.query.filter_by(status='aguardando_gestor').all():
            try:
                if _dias_uteis_entre(d.solicitado_em.date(), hoje) >= _DIAS_UTEIS_LEMBRETE:
                    enviar_lembrete_aprovacao(d, 'dayoff')
            except Exception:
                log.exception('Erro ao enviar lembrete dayoff id=%s', d.id)


@scheduler.task('cron', id='alerta_vencimento', hour=7, minute=30)
def job_alerta_vencimento():
    """Alerta colaboradores sobre períodos aquisitivos próximos do vencimento."""
    with scheduler.app.app_context():
        from app.notificacoes.email import enviar_alerta_vencimento
        hoje = date.today()
        limites = {90, 60, 30}

        for periodo in (
            PeriodoAquisitivo.query
            .join(Colaborador)
            .filter(Colaborador.ativo == 1, PeriodoAquisitivo.data_limite_saida >= hoje)
            .all()
        ):
            if periodo.dias_restantes() <= 0:
                continue
            try:
                dias_ate = (periodo.data_limite_saida - hoje).days
                if dias_ate in limites:
                    enviar_alerta_vencimento(periodo.colaborador, periodo, dias_ate)
            except Exception:
                log.exception('Erro ao enviar alerta vencimento periodo id=%s', periodo.id)


@scheduler.task('cron', id='lembrete_dayoff_mensal', day=20, hour=9, minute=0)
def job_lembrete_dayoff_mensal():
    """No dia 20: avisa elegíveis que ainda não solicitaram day off no mês."""
    with scheduler.app.app_context():
        from app.notificacoes.email import _enviar
        hoje = date.today()
        mes_ref = date(hoje.year, hoje.month, 1)

        for c in Colaborador.query.filter_by(ativo=1).all():
            try:
                if not c.pode_solicitar_dayoff():
                    continue
                ja_solicitou = DayOff.query.filter(
                    DayOff.colaborador_id == c.id,
                    DayOff.mes_referencia == mes_ref,
                    DayOff.status.notin_(['reprovado', 'cancelado']),
                ).first()
                if not ja_solicitou and c.email:
                    _enviar(
                        assunto='Lembrete: você ainda não solicitou seu day off este mês',
                        destinatarios=[c.email],
                        template='emails/lembrete_dayoff_mensal.html',
                        colaborador=c,
                        mes_ref=mes_ref,
                    )
            except Exception:
                log.exception('Erro ao enviar lembrete dayoff mensal colab id=%s', c.id)
