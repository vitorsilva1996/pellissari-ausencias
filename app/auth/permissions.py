from functools import wraps

from flask import abort
from flask_login import current_user

_FALLBACK = {
    'colaborador': frozenset({
        'ferias.solicitar', 'dayoff.solicitar',
    }),
    'gestor': frozenset({
        'ferias.solicitar', 'ferias.aprovar_1',
        'dayoff.solicitar', 'dayoff.aprovar',
        'colaboradores.ver', 'painel.ver',
    }),
    'rh': frozenset({
        'ferias.solicitar', 'ferias.aprovar_1', 'ferias.aprovar_2', 'ferias.cancelar',
        'dayoff.solicitar', 'dayoff.aprovar',
        'colaboradores.ver', 'colaboradores.cadastrar', 'colaboradores.editar',
        'colaboradores.desativar', 'colaboradores.periodos',
        'painel.ver', 'painel.exportar',
        'configuracoes.perfis', 'configuracoes.equipes',
    }),
    'diretoria': frozenset({
        'colaboradores.ver', 'painel.ver', 'painel.exportar',
    }),
}

_ALL = frozenset({
    'ferias.solicitar', 'ferias.aprovar_1', 'ferias.aprovar_2', 'ferias.cancelar',
    'dayoff.solicitar', 'dayoff.aprovar',
    'colaboradores.ver', 'colaboradores.cadastrar', 'colaboradores.editar',
    'colaboradores.desativar', 'colaboradores.periodos',
    'painel.ver', 'painel.exportar',
    'configuracoes.perfis', 'configuracoes.equipes',
})


def has_permission(user, codigo: str) -> bool:
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'perfil_obj', None) is not None:
        return codigo in user.perfil_obj.codigos
    return codigo in _FALLBACK.get(getattr(user, 'perfil', ''), frozenset())


def require_permission(codigo: str):
    """Decorator: exige login + permissão específica."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                from flask import current_app
                return current_app.login_manager.unauthorized()
            if not has_permission(current_user, codigo):
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


def require_any_permission(*codigos: str):
    """Decorator: exige login + ao menos uma das permissões informadas."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                from flask import current_app
                return current_app.login_manager.unauthorized()
            if not any(has_permission(current_user, codigo) for codigo in codigos):
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


def get_user_equipes(user) -> list:
    """Retorna IDs das equipes que o usuário gerencia."""
    if getattr(user, 'equipes_gerenciadas', None):
        return [e.id for e in user.equipes_gerenciadas]
    return [user.equipe_id]


def usuarios_com_permissao(codigo: str) -> list:
    """Retorna colaboradores ativos que possuem a permissão informada
    (via perfil customizado ou fallback legado por enum `perfil`)."""
    from app.models import Colaborador
    return [
        c for c in Colaborador.query.filter_by(ativo=1).all()
        if has_permission(c, codigo)
    ]
