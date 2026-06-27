from flask import Blueprint

painel = Blueprint('painel', __name__)

from app.painel import routes  # noqa: F401, E402
