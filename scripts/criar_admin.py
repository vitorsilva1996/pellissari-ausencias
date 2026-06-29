import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Colaborador, Equipe
from datetime import date

app = create_app()

with app.app_context():
    equipe = db.session.get(Equipe, 1)
    if equipe is None:
        equipe = Equipe(id=1, nome='Administrativo')
        db.session.add(equipe)
        db.session.flush()
        print('Equipe "Administrativo" criada.')

    existente = Colaborador.query.filter_by(email='vitor@pellissari.com.br').first()
    if existente:
        print('Usuário já existe:', existente.email)
        sys.exit(0)

    admin = Colaborador(
        nome='Vitor Silva',
        email='vitor@pellissari.com.br',
        data_admissao=date.today(),
        funcao='ADMINISTRADOR',
        equipe_id=1,
        perfil='rh',
        ativo=1,
    )
    admin.set_senha('admin123')

    db.session.add(admin)
    db.session.commit()
    print(f'Usuário criado com sucesso: {admin.nome} <{admin.email}> perfil={admin.perfil}')
