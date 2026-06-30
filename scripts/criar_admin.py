import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Colaborador, Equipe
from datetime import date

app = create_app()

with app.app_context():
    equipe = Equipe.query.filter_by(nome='Kali').first()
    if equipe is None:
        print('Equipe "Kali" não encontrada — execute importacao_final.py primeiro.')
        sys.exit(1)

    existente = Colaborador.query.filter_by(email='vitor.silva@pellissari.com.br').first()
    if existente:
        print('Usuário já existe:', existente.email)
        sys.exit(0)

    admin = Colaborador(
        nome='Vitor Silva',
        email='vitor.silva@pellissari.com.br',
        data_admissao=date(2023, 12, 11),
        funcao='SUPERVISOR IV',
        equipe_id=equipe.id,
        perfil='rh',
        ativo=1,
    )
    admin.set_senha('admin123')

    db.session.add(admin)
    db.session.commit()
    print(f'Usuário criado: {admin.nome} <{admin.email}> perfil={admin.perfil}')
