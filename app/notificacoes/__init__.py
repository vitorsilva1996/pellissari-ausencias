from flask import Blueprint

notificacoes = Blueprint('notificacoes', __name__)

from app.notificacoes import routes  # noqa: F401, E402
