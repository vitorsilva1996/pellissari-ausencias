import importlib
import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_apscheduler import APScheduler

from config import config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
bcrypt = Bcrypt()
scheduler = APScheduler()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Faça login para acessar esta página.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    from app.models import Colaborador
    return db.session.get(Colaborador, int(user_id))


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    if hasattr(config[config_name], 'init_app'):
        config[config_name].init_app(app)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    bcrypt.init_app(app)

    if not app.config.get('TESTING') and not scheduler.running:
        scheduler.init_app(app)
        importlib.import_module('app.notificacoes.scheduler')
        scheduler.start()

    from app.auth import auth as auth_blueprint
    from app.colaboradores import colaboradores as colab_blueprint
    from app.ferias import ferias as ferias_blueprint
    from app.dayoff import dayoff as dayoff_blueprint
    from app.calendario import calendario as calendario_blueprint
    from app.painel import painel as painel_blueprint
    from app.notificacoes import notificacoes as notif_blueprint

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(colab_blueprint, url_prefix='/colaboradores')
    app.register_blueprint(ferias_blueprint, url_prefix='/ferias')
    app.register_blueprint(dayoff_blueprint, url_prefix='/dayoff')
    app.register_blueprint(calendario_blueprint, url_prefix='/calendario')
    app.register_blueprint(painel_blueprint, url_prefix='/painel')
    app.register_blueprint(notif_blueprint, url_prefix='/notificacoes')

    # ── Global timedelta para templates de e-mail ─────────────────────────────
    from datetime import timedelta
    app.jinja_env.globals['timedelta'] = timedelta

    # ── Filtro de data em português ──────────────────────────────────────────
    _MESES_BR = [
        '', 'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
        'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
    ]

    @app.template_filter('data_br')
    def data_br_filter(d):
        if d is None:
            return ''
        return f'{d.day} de {_MESES_BR[d.month]} de {d.year}'

    # ── Context processor: notificações não lidas ─────────────────────────────
    @app.context_processor
    def injetar_notificacoes():
        from flask_login import current_user
        from app.models import Notificacao
        count = 0
        if current_user.is_authenticated:
            count = Notificacao.query.filter_by(
                colaborador_id=current_user.id, lida=0
            ).count()
        return {'notificacoes_nao_lidas': count}

    @app.route('/')
    def index():
        return render_template('index.html')

    return app
