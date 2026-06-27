from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from app.auth import auth
from app.models import Colaborador


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('painel.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        remember = request.form.get('remember') == 'on'

        colaborador = Colaborador.query.filter_by(email=email, ativo=1).first()

        if colaborador and colaborador.check_senha(senha):
            login_user(colaborador, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('painel.index'))

        flash('E-mail ou senha incorretos.', 'danger')

    return render_template('auth/login.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('auth.login'))
