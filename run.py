import os
from app import create_app, db
from app.models import Colaborador, Equipe, PeriodoAquisitivo, Ferias, DayOff, Notificacao

app = create_app(os.environ.get('FLASK_ENV', 'development'))


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'Colaborador': Colaborador,
        'Equipe': Equipe,
        'PeriodoAquisitivo': PeriodoAquisitivo,
        'Ferias': Ferias,
        'DayOff': DayOff,
        'Notificacao': Notificacao,
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
