"""Funções de envio de e-mail para cada evento do sistema."""
import logging
from datetime import datetime
from flask import render_template
from flask_mail import Message

from app import mail
from app.auth.permissions import usuarios_com_permissao

log = logging.getLogger(__name__)


def _enviar(assunto, destinatarios, template, **ctx):
    """Envia e-mail HTML; nunca lança exceção para o chamador."""
    if not destinatarios:
        return
    ctx.setdefault('now', datetime.utcnow())
    try:
        html = render_template(template, **ctx)
        msg = Message(subject=assunto, recipients=destinatarios, html=html)
        mail.send(msg)
    except Exception:
        log.exception('Falha ao enviar e-mail "%s" para %s', assunto, destinatarios)


# ── Férias ────────────────────────────────────────────────────────────────────

def enviar_notificacao_ferias_gestor(ferias):
    gestor = ferias.colaborador.gestor
    if not gestor or not gestor.email:
        return
    _enviar(
        assunto=f'Nova solicitação de férias — {ferias.colaborador.nome}',
        destinatarios=[gestor.email],
        template='emails/ferias_solicitada.html',
        ferias=ferias,
        destinatario=gestor,
    )


def enviar_notificacao_ferias_rh(ferias):
    rhs = usuarios_com_permissao('ferias.aprovar_2')
    emails = [c.email for c in rhs if c.email]
    if not emails:
        return
    _enviar(
        assunto=f'Férias aguardando validação — {ferias.colaborador.nome}',
        destinatarios=emails,
        template='emails/ferias_solicitada.html',
        ferias=ferias,
        destinatario=None,
        para_rh=True,
    )


def enviar_notificacao_ferias_colaborador(ferias):
    if not ferias.colaborador.email:
        return
    aprovada = ferias.status == 'aprovada'
    _enviar(
        assunto='Resultado da sua solicitação de férias',
        destinatarios=[ferias.colaborador.email],
        template='emails/ferias_resultado.html',
        ferias=ferias,
        aprovada=aprovada,
    )


# ── Day Off ───────────────────────────────────────────────────────────────────

def enviar_notificacao_dayoff_gestor(dayoff):
    gestor = dayoff.colaborador.gestor
    if not gestor or not gestor.email:
        return
    _enviar(
        assunto=f'Nova solicitação de day off — {dayoff.colaborador.nome}',
        destinatarios=[gestor.email],
        template='emails/dayoff_solicitado.html',
        dayoff=dayoff,
        destinatario=gestor,
    )


def enviar_notificacao_dayoff_colaborador(dayoff):
    if not dayoff.colaborador.email:
        return
    aprovado = dayoff.status == 'aprovado'
    _enviar(
        assunto='Resultado da sua solicitação de day off',
        destinatarios=[dayoff.colaborador.email],
        template='emails/dayoff_resultado.html',
        dayoff=dayoff,
        aprovado=aprovado,
    )


# ── Lembretes e alertas ───────────────────────────────────────────────────────

def enviar_lembrete_aprovacao(solicitacao, tipo):
    """Lembrete para o aprovador após 3 dias úteis sem resposta."""
    if tipo == 'ferias':
        aprovador = solicitacao.colaborador.gestor
        if solicitacao.status == 'aguardando_rh':
            rhs = usuarios_com_permissao('ferias.aprovar_2')
            emails = [c.email for c in rhs if c.email]
            if emails:
                _enviar(
                    assunto=f'Lembrete: férias de {solicitacao.colaborador.nome} aguardando RH',
                    destinatarios=emails,
                    template='emails/lembrete_aprovacao.html',
                    solicitacao=solicitacao,
                    tipo='ferias',
                    papel='RH',
                )
            return
    else:
        aprovador = solicitacao.colaborador.gestor

    if not aprovador or not aprovador.email:
        return

    papel = 'gestor'
    assunto = (
        f'Lembrete: solicitação de {"férias" if tipo == "ferias" else "day off"} '
        f'de {solicitacao.colaborador.nome} aguarda sua resposta'
    )
    _enviar(
        assunto=assunto,
        destinatarios=[aprovador.email],
        template='emails/lembrete_aprovacao.html',
        solicitacao=solicitacao,
        tipo=tipo,
        papel=papel,
    )


def enviar_alerta_vencimento(colaborador, periodo, dias_restantes):
    """Alerta de vencimento de período aquisitivo."""
    if not colaborador.email:
        return
    _enviar(
        assunto=f'Atenção: seu período de férias vence em {dias_restantes} dias',
        destinatarios=[colaborador.email],
        template='emails/alerta_vencimento.html',
        colaborador=colaborador,
        periodo=periodo,
        dias_restantes=dias_restantes,
    )
