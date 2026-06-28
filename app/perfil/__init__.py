from flask import Blueprint

perfil = Blueprint('perfil', __name__)

from app.perfil import routes  # noqa: E402, F401
