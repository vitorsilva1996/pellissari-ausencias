import secrets
import string
from datetime import date

from dateutil.relativedelta import relativedelta
from flask import render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from app.colaboradores import colaboradores
from app.models import Colaborador, Equipe, PeriodoAquisitivo, Ferias, DayOff, Perfil, Funcao
from app import db
from app.auth.permissions import has_permission, require_permission, get_user_equipes

# Mapeamento nome-do-perfil → string de compatibilidade
_PERFIL_STR = {
    'Colaborador': 'colaborador',
    'Gestor': 'gestor',
    'RH': 'rh',
    'Diretoria': 'diretoria',
    'Administrador': 'rh',
}


def _pode_ver_perfil(colab):
    if has_permission(current_user, 'colaboradores.editar'):
        return True
    if has_permission(current_user, 'colaboradores.ver'):
        equipe_ids = get_user_equipes(current_user)
        return colab.equipe_id in equipe_ids
    return current_user.id == colab.id


def _gerar_senha(length=8):
    alfabeto = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alfabeto) for _ in range(length))


def _equipes_e_gestores():
    equipes = Equipe.query.filter_by(ativo=1).order_by(Equipe.nome).all()
    gestores = (
        Colaborador.query
        .filter(Colaborador.perfil.in_(['gestor', 'rh', 'diretoria']), Colaborador.ativo == 1)
        .order_by(Colaborador.nome)
        .all()
    )
    return equipes, gestores


def _perfis_disponiveis():
    return Perfil.query.filter_by(ativo=1).order_by(Perfil.nome).all()


def _funcoes_disponiveis():
    return Funcao.query.filter_by(ativo=1).order_by(Funcao.nome).all()


# ── Listagem ──────────────────────────────────────────────────────────────────

@colaboradores.route('/')
@require_permission('colaboradores.ver')
def index():
    mostrar_inativos = request.args.get('inativos', '0') == '1'
    busca = request.args.get('q', '').strip()

    q = Colaborador.query.join(Equipe)
    if not mostrar_inativos:
        q = q.filter(Colaborador.ativo == 1)
    if busca:
        termo = f'%{busca}%'
        q = q.filter(
            db.or_(
                Colaborador.nome.ilike(termo),
                Colaborador.email.ilike(termo),
                Colaborador.funcao.ilike(termo),
                Equipe.nome.ilike(termo),
            )
        )

    lista = q.order_by(Colaborador.nome).all()
    return render_template('colaboradores/index.html',
                           lista=lista,
                           mostrar_inativos=mostrar_inativos,
                           busca=busca)


# ── Cadastro ──────────────────────────────────────────────────────────────────

@colaboradores.route('/novo', methods=['GET', 'POST'])
@require_permission('colaboradores.cadastrar')
def novo():
    equipes, gestores = _equipes_e_gestores()
    perfis = _perfis_disponiveis()
    funcoes = _funcoes_disponiveis()

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip().title()
        email = request.form.get('email', '').strip().lower()
        equipe_id = request.form.get('equipe_id', type=int)
        gestor_id = request.form.get('gestor_id', type=int) or None
        admissao_s = request.form.get('data_admissao', '').strip()
        perfil_id = request.form.get('perfil_id', type=int)
        funcao_id = request.form.get('funcao_id', type=int)

        erros = []
        if not nome:
            erros.append('Nome é obrigatório.')
        if not email:
            erros.append('E-mail é obrigatório.')
        elif Colaborador.query.filter_by(email=email).first():
            erros.append('E-mail já cadastrado.')
        if not equipe_id:
            erros.append('Equipe é obrigatória.')
        if not admissao_s:
            erros.append('Data de admissão é obrigatória.')

        funcao_obj = None
        funcao_str = ''
        if funcao_id:
            funcao_obj = db.session.get(Funcao, funcao_id)
            if funcao_obj:
                funcao_str = funcao_obj.nome
            else:
                erros.append('Função inválida.')
        else:
            erros.append('Função é obrigatória.')

        perfil_obj = None
        perfil_str = 'colaborador'
        if perfil_id:
            perfil_obj = db.session.get(Perfil, perfil_id)
            if perfil_obj:
                perfil_str = _PERFIL_STR.get(perfil_obj.nome, 'colaborador')
            else:
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
                                   perfis=perfis, funcoes=funcoes, form=request.form)

        senha_temp = _gerar_senha()
        c = Colaborador(
            nome=nome,
            email=email,
            funcao=funcao_str,
            funcao_id=funcao_id,
            equipe_id=equipe_id,
            gestor_id=gestor_id,
            data_admissao=data_admissao,
            perfil=perfil_str,
            perfil_id=perfil_id,
            ativo=1,
        )
        c.set_senha(senha_temp)

        equipe_ids = request.form.getlist('equipes_gerenciadas', type=int)
        if equipe_ids:
            c.equipes_gerenciadas = Equipe.query.filter(Equipe.id.in_(equipe_ids)).all()

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
                           perfis=perfis, funcoes=funcoes, form={})


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
@require_permission('colaboradores.editar')
def editar(id):
    colab = Colaborador.query.get_or_404(id)
    equipes, gestores = _equipes_e_gestores()
    perfis = _perfis_disponiveis()
    funcoes = _funcoes_disponiveis()

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip().title()
        email = request.form.get('email', '').strip().lower()
        equipe_id = request.form.get('equipe_id', type=int)
        gestor_id = request.form.get('gestor_id', type=int) or None
        admissao_s = request.form.get('data_admissao', '').strip()
        perfil_id = request.form.get('perfil_id', type=int)
        funcao_id = request.form.get('funcao_id', type=int)

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
        if not equipe_id:
            erros.append('Equipe é obrigatória.')

        funcao_obj = None
        if funcao_id:
            funcao_obj = db.session.get(Funcao, funcao_id)
            if not funcao_obj:
                erros.append('Função inválida.')
        else:
            erros.append('Função é obrigatória.')

        perfil_obj = None
        if perfil_id:
            perfil_obj = db.session.get(Perfil, perfil_id)
            if not perfil_obj:
                erros.append('Perfil inválido.')

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
                                   perfis=perfis, funcoes=funcoes, form=request.form)

        colab.nome = nome
        colab.email = email
        colab.equipe_id = equipe_id
        colab.gestor_id = gestor_id
        colab.data_admissao = data_admissao

        if funcao_obj:
            colab.funcao_id = funcao_obj.id
            colab.funcao = funcao_obj.nome

        if perfil_obj:
            colab.perfil_id = perfil_obj.id
            colab.perfil = _PERFIL_STR.get(perfil_obj.nome, 'colaborador')

        equipe_ids = request.form.getlist('equipes_gerenciadas', type=int)
        colab.equipes_gerenciadas = (
            Equipe.query.filter(Equipe.id.in_(equipe_ids)).all() if equipe_ids else []
        )

        db.session.commit()
        flash('Dados atualizados com sucesso.', 'success')
        return redirect(url_for('colaboradores.perfil', id=colab.id))

    return render_template('colaboradores/form.html',
                           colab=colab, equipes=equipes, gestores=gestores,
                           perfis=perfis, funcoes=funcoes, form={})


# ── Desativação ───────────────────────────────────────────────────────────────

@colaboradores.route('/<int:id>/desativar', methods=['POST'])
@require_permission('colaboradores.desativar')
def desativar(id):
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
@require_permission('colaboradores.desativar')
def reativar(id):
    colab = Colaborador.query.get_or_404(id)
    colab.ativo = 1
    db.session.commit()
    flash(f'{colab.nome} foi reativado.', 'success')
    return redirect(url_for('colaboradores.perfil', id=id))


# ── Reset de senha ────────────────────────────────────────────────────────────

@colaboradores.route('/<int:id>/reset-senha', methods=['POST'])
@require_permission('colaboradores.editar')
def reset_senha(id):
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
@require_permission('colaboradores.periodos')
def periodos(id):
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
@require_permission('colaboradores.periodos')
def periodo_novo(id):
    colab = Colaborador.query.get_or_404(id)

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

    sugestao_fim = sugestao_inicio + relativedelta(years=1) - relativedelta(days=1)
    sugestao_limite = sugestao_fim + relativedelta(months=11)

    if request.method == 'POST':
        inicio_s = request.form.get('data_inicio', '').strip()
        fim_s = request.form.get('data_fim', '').strip()
        limite_s = request.form.get('data_limite_saida', '').strip()
        dias = request.form.get('dias_direito', type=int, default=30)

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
