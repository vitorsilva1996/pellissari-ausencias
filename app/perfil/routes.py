from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app import db
from app.perfil import perfil
from app.models import Colaborador


@perfil.route('/', methods=['GET', 'POST'])
@login_required
def index():
    colaborador = db.session.get(Colaborador, current_user.id)

    if request.method == 'POST':
        senha_atual = request.form.get('senha_atual', '')
        nova_senha = request.form.get('nova_senha', '')
        confirmar = request.form.get('confirmar_senha', '')

        if not colaborador.check_senha(senha_atual):
            flash('Senha atual incorreta.', 'danger')
        elif len(nova_senha) < 6:
            flash('A nova senha deve ter pelo menos 6 caracteres.', 'danger')
        elif nova_senha != confirmar:
            flash('A confirmação não confere com a nova senha.', 'danger')
        else:
            colaborador.set_senha(nova_senha)
            db.session.commit()
            flash('Senha alterada com sucesso.', 'success')
            return redirect(url_for('perfil.index'))

    return render_template('perfil/index.html', colaborador=colaborador)
