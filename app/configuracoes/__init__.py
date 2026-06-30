from flask import Blueprint

configuracoes = Blueprint('configuracoes', __name__)

from app.configuracoes import routes  # noqa: E402,F401
