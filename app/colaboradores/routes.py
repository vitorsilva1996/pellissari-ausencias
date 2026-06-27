import secrets
import string
from datetime import date

from dateutil.relativedelta import relativedelta
from flask import render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from app.colaboradores import colaboradores
from app.models import Colaborador, Equipe, PeriodoAquisitivo, Ferias, DayOff
from app import db


def _somente_rh():
    if current_user.perfil not in ('rh', 'diretoria'):
        abort(403)


def _pode_ver_perfil(colab):
    if current_user.perfil in ('rh', 'diretoria'):
        return True
    if current_user.perfil == 'gestor' and colab.gestor_id == current_user.id:
        return True
    return current_user.id == colab.id


def _gerar_senha(length=8):
    alfabeto = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alfabeto) for _ in range(length))


def _equipes_e_gestores():
    equipes = Equipe.query.order_by(Equipe.nome).all()
    gestores = (
        Colaborador.query
        .filter(Colaborador.perfil.in_(['gestor', 'rh', 'diretoria']), Colaborador.ativo == 1)
        .order_by(Colaborador.nome)
        .all()
    )
    return equipes, gestores


# ── Listagem ──────────────────────────────────────────────────────────────────

@colaboradores.route('/')
@login_required
def index():
    _somente_rh()
    mostrar_inativos = request.args.get('inativos', '0') == '1'
    q = Colaborador.query
    if not mostrar_inativos:
        q = q.filter_by(ativo=1)
    lista = q.order_by(Colaborador.nome).all()
    return render_template('colaboradores/index.html',
                           lista=lista, mostrar_inativos=mostrar_inativos)


# ── Cadastro ──────────────────────────────────────────────────────────────────

@colaboradores.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    _somente_rh()
    equipes, gestores = _equipes_e_gestores()

    if request.method == 'POST':
        nome       = request.form.get('nome', '').strip()
        email      = request.form.get('email', '').strip().lower()
        funcao     = request.form.get('funcao', '').strip()
        equipe_id  = request.form.get('equipe_id', type=int)
        gestor_id  = request.form.get('gestor_id', type=int) or None
        admissao_s = request.form.get('data_admissao', '').strip()
        perfil     = request.form.get('perfil', 'colaborador')

        erros = []
        if not nome:
            erros.append('Nome é obrigatório.')
        if not email:
            erros.append('E-mail é obrigatório.')
        elif Colaborador.query.filter_by(email=email).first():
            erros.append('E-mail já cadastrado.')
        if not funcao:
            erros.append('Função é obrigatória.')
        if not equipe_id:
            erros.append('Equipe é obrigatória.')
        if not admissao_s:
            erros.append('Data de admissão é obrigatória.')
        if perfil not in ('colaborador', 'gestor', 'rh', 'diretoria'):
            erros.append('Perfil inválido.')

        data_admissao = None
        if admissao_s:
            try:
                data_admissao = date.fromisoformat(admissao_s)
            except ValueError:
                erros.append('Data de admissão inválida.')

        if erros:
            for e in erros:
                flash(e, 'danger')
            return render_template('colaboradores/form.html',
                                   colab=None, equipes=equipes, gestores=gestores,
                                   form=request.form)

        senha_temp = _gerar_senha()
        c = Colaborador(
            nome=nome,
            email=email,
            funcao=funcao,
            equipe_id=equipe_id,
            gestor_id=gestor_id,
            data_admissao=data_admissao,
            perfil=perfil,
            ativo=1,
        )
        c.set_senha(senha_temp)
        db.session.add(c)
        db.session.commit()

        flash(
            f'Colaborador <strong>{nome}</strong> cadastrado com sucesso! '
            f'Senha temporária: <code>{senha_temp}</code>',
            'success',
        )
        return redirect(url_for('colaboradores.perfil', id=c.id))

    return render_template('colaboradores/form.html',
                           colab=None, equipes=equipes, gestores=gestores,
                           form={})


# ── Perfil ────────────────────────────────────────────────────────────────────

@colaboradores.route('/<int:id>')
@login_required
def perfil(id):
    colab = Colaborador.query.get_or_404(id)
    if not _pode_ver_perfil(colab):
        abort(403)

    periodos = (
        PeriodoAquisitivo.query
        .filter_by(colaborador_id=id)
        .order_by(PeriodoAquisitivo.data_inicio.desc())
        .all()
    )
    ferias_lista = (
        Ferias.query
        .filter_by(colaborador_id=id)
        .order_by(Ferias.solicitado_em.desc())
        .limit(10)
        .all()
    )
    dayoffs_lista = (
        DayOff.query
        .filter_by(colaborador_id=id)
        .order_by(DayOff.solicitado_em.desc())
        .limit(10)
        .all()
    )
    return render_template('colaboradores/perfil.html',
                           colab=colab, periodos=periodos,
                           ferias_lista=ferias_lista, dayoffs_lista=dayoffs_lista,
                           today=date.today(), relativedelta=relativedelta)


# ── Edição ────────────────────────────────────────────────────────────────────

@colaboradores.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    _somente_rh()
    colab = Colaborador.query.get_or_404(id)
    equipes, gestores = _equipes_e_gestores()

    if request.method == 'POST':
        nome       = request.form.get('nome', '').strip()
        email      = request.form.get('email', '').strip().lower()
        funcao     = request.form.get('funcao', '').strip()
        equipe_id  = request.form.get('equipe_id', type=int)
        gestor_id  = request.form.get('gestor_id', type=int) or None
        admissao_s = request.form.get('data_admissao', '').strip()
        perfil_val = request.form.get('perfil', 'colaborador')

        erros = []
        if not nome:
            erros.append('Nome é obrigatório.')
        if not email:
            erros.append('E-mail é obrigatório.')
        else:
            duplicado = Colaborador.query.filter(
                Colaborador.email == email,
                Colaborador.id != colab.id,
            ).first()
            if duplicado:
                erros.append('E-mail já usado por outro colaborador.')
        if not funcao:
            erros.append('Função é obrigatória.')
        if not equipe_id:
            erros.append('Equipe é obrigatória.')

        data_admissao = colab.data_admissao
        if admissao_s:
            try:
                data_admissao = date.fromisoformat(admissao_s)
            except ValueError:
                erros.append('Data de admissão inválida.')

        if erros:
            for e in erros:
                flash(e, 'danger')
            return render_template('colaboradores/form.html',
                                   colab=colab, equipes=equipes, gestores=gestores,
                                   form=request.form)

        colab.nome         = nome
        colab.email        = email
        colab.funcao       = funcao
        colab.equipe_id    = equipe_id
        colab.gestor_id    = gestor_id
        colab.data_admissao = data_admissao
        colab.perfil       = perfil_val
        db.session.commit()

        flash('Dados atualizados com sucesso.', 'success')
        return redirect(url_for('colaboradores.perfil', id=colab.id))

    return render_template('colaboradores/form.html',
                           colab=colab, equipes=equipes, gestores=gestores,
                           form={})


# ── Desativação ───────────────────────────────────────────────────────────────

@colaboradores.route('/<int:id>/desativar', methods=['POST'])
@login_required
def desativar(id):
    _somente_rh()
    colab = Colaborador.query.get_or_404(id)
    if colab.id == current_user.id:
        flash('Você não pode desativar seu próprio cadastro.', 'danger')
        return redirect(url_for('colaboradores.perfil', id=id))

    colab.ativo = 0
    db.session.commit()
    flash(f'{colab.nome} foi desativado.', 'info')
    return redirect(url_for('colaboradores.index'))


# ── Reativação ────────────────────────────────────────────────────────────────

@colaboradores.route('/<int:id>/reativar', methods=['POST'])
@login_required
def reativar(id):
    _somente_rh()
    colab = Colaborador.query.get_or_404(id)
    colab.ativo = 1
    db.session.commit()
    flash(f'{colab.nome} foi reativado.', 'success')
    return redirect(url_for('colaboradores.perfil', id=id))


# ── Reset de senha ────────────────────────────────────────────────────────────

@colaboradores.route('/<int:id>/reset-senha', methods=['POST'])
@login_required
def reset_senha(id):
    _somente_rh()
    colab = Colaborador.query.get_or_404(id)
    nova = _gerar_senha()
    colab.set_senha(nova)
    db.session.commit()
    flash(
        f'Senha redefinida para <strong>{colab.nome}</strong>. '
        f'Nova senha temporária: <code>{nova}</code>',
        'success',
    )
    return redirect(url_for('colaboradores.perfil', id=id))


# ── Períodos aquisitivos ──────────────────────────────────────────────────────

@colaboradores.route('/<int:id>/periodos')
@login_required
def periodos(id):
    _somente_rh()
    colab = Colaborador.query.get_or_404(id)
    lista = (
        PeriodoAquisitivo.query
        .filter_by(colaborador_id=id)
        .order_by(PeriodoAquisitivo.data_inicio.desc())
        .all()
    )
    return render_template('colaboradores/periodos.html',
                           colab=colab, periodos=lista, form={},
                           sugestao_inicio=None, sugestao_fim=None, sugestao_limite=None,
                           today=date.today())


@colaboradores.route('/<int:id>/periodos/novo', methods=['GET', 'POST'])
@login_required
def periodo_novo(id):
    _somente_rh()
    colab = Colaborador.query.get_or_404(id)

    # Sugere próximo período a partir do último existente ou da admissão
    ultimo = (
        PeriodoAquisitivo.query
        .filter_by(colaborador_id=id)
        .order_by(PeriodoAquisitivo.data_inicio.desc())
        .first()
    )
    if ultimo:
        sugestao_inicio = ultimo.data_fim + relativedelta(days=1)
    else:
        sugestao_inicio = colab.data_admissao

    sugestao_fim    = sugestao_inicio + relativedelta(years=1) - relativedelta(days=1)
    sugestao_limite = sugestao_fim + relativedelta(months=11)

    if request.method == 'POST':
        inicio_s  = request.form.get('data_inicio', '').strip()
        fim_s     = request.form.get('data_fim', '').strip()
        limite_s  = request.form.get('data_limite_saida', '').strip()
        dias      = request.form.get('dias_direito', type=int, default=30)

        erros = []
        data_inicio = data_fim = data_limite = None

        for label, s, attr in [
            ('Data de início', inicio_s, 'data_inicio'),
            ('Data de fim', fim_s, 'data_fim'),
            ('Data limite de saída', limite_s, 'data_limite_saida'),
        ]:
            try:
                val = date.fromisoformat(s)
                if attr == 'data_inicio':
                    data_inicio = val
                elif attr == 'data_fim':
                    data_fim = val
                else:
                    data_limite = val
            except ValueError:
                erros.append(f'{label} inválida.')

        if data_inicio and data_fim and data_fim <= data_inicio:
            erros.append('Data de fim deve ser posterior à data de início.')
        if data_fim and data_limite and data_limite <= data_fim:
            erros.append('Data limite deve ser posterior à data de fim.')
        if dias < 1 or dias > 30:
            erros.append('Dias de direito deve estar entre 1 e 30.')

        # Verifica sobreposição com períodos existentes
        if data_inicio and data_fim and not erros:
            overlap = PeriodoAquisitivo.query.filter(
                PeriodoAquisitivo.colaborador_id == id,
                PeriodoAquisitivo.data_inicio <= data_fim,
                PeriodoAquisitivo.data_fim >= data_inicio,
            ).first()
            if overlap:
                erros.append('Este período se sobrepõe a um período aquisitivo já existente.')

        lista = (
            PeriodoAquisitivo.query
            .filter_by(colaborador_id=id)
            .order_by(PeriodoAquisitivo.data_inicio.desc())
            .all()
        )

        if erros:
            for e in erros:
                flash(e, 'danger')
            return render_template('colaboradores/periodos.html',
                                   colab=colab, periodos=lista,
                                   form=request.form,
                                   sugestao_inicio=sugestao_inicio,
                                   sugestao_fim=sugestao_fim,
                                   sugestao_limite=sugestao_limite,
                                   today=date.today())

        p = PeriodoAquisitivo(
            colaborador_id=id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            dias_direito=dias,
            data_limite_saida=data_limite,
        )
        db.session.add(p)
        db.session.commit()
        flash('Período aquisitivo cadastrado com sucesso.', 'success')
        return redirect(url_for('colaboradores.periodos', id=id))

    lista = (
        PeriodoAquisitivo.query
        .filter_by(colaborador_id=id)
        .order_by(PeriodoAquisitivo.data_inicio.desc())
        .all()
    )
    return render_template('colaboradores/periodos.html',
                           colab=colab, periodos=lista, form={},
                           sugestao_inicio=sugestao_inicio,
                           sugestao_fim=sugestao_fim,
                           sugestao_limite=sugestao_limite,
                           today=date.today())
