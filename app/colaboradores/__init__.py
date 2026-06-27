from flask import Blueprint

colaboradores = Blueprint('colaboradores', __name__)

from app.colaboradores import routes  # noqa: F401, E402
