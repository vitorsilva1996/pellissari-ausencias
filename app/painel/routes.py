from flask import render_template
from flask_login import login_required

from app.painel import painel


@painel.route('/')
@login_required
def index():
    return render_template('painel/index.html')
