from flask import Blueprint

dayoff = Blueprint('dayoff', __name__)

from app.dayoff import routes  # noqa: F401, E402
