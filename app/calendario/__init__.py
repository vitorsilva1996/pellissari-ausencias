from flask import Blueprint

calendario = Blueprint('calendario', __name__)

from app.calendario import routes  # noqa: F401, E402
