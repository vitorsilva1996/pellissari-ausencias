from flask import Blueprint

ferias = Blueprint('ferias', __name__)

from app.ferias import routes  # noqa: F401, E402
