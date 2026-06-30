from flask import render_template, redirect, url_for, request, flash

from app.configuracoes import configuracoes
from app.models import Perfil, Permissao, Colaborador, Funcao, Equipe
from app import db
from app.auth.permissions import require_permission


def _permissoes_por_modulo():
    perms = Permissao.query.order_by(Permissao.modulo, Permissao.codigo).all()
    grupos = {}
    for p in perms:
        grupos.setdefault(p.modulo, []).append(p)
    return grupos


# ═══════════════════════════════════════════════════════════════
# PERFIS
# ═══════════════════════════════════════════════════════════════

@configuracoes.route('/perfis')
@require_permission('configuracoes.perfis')
def perfis():
    lista = Perfil.query.order_by(Perfil.nome).all()
    user_counts = {
        p.id: Colaborador.query.filter_by(perfil_id=p.id, ativo=1).count()
        for p in lista
    }
    return render_template('configuracoes/perfis.html',
                           perfis=lista, user_counts=user_counts)


@configuracoes.route('/perfis/novo', methods=['GET', 'POST'])
@require_permission('configuracoes.perfis')
def perfil_novo():
    permissoes_por_modulo = _permissoes_por_modulo()

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        perm_ids = request.form.getlist('permissoes', type=int)

        if not nome:
            flash('Nome é obrigatório.', 'danger')
        elif Perfil.query.filter_by(nome=nome).first():
            flash('Já existe um perfil com este nome.', 'danger')
        else:
            p = Perfil(nome=nome, descricao=descricao or None)
            if perm_ids:
                p.permissoes = Permissao.query.filter(Permissao.id.in_(perm_ids)).all()
            db.session.add(p)
            db.session.commit()
            flash(f'Perfil "{nome}" criado com sucesso.', 'success')
            return redirect(url_for('configuracoes.perfis'))

    return render_template('configuracoes/perfil_form.html',
                           perfil=None,
                           permissoes_por_modulo=permissoes_por_modulo,
                           perfil_permissao_ids=set(),
                           form=request.form if request.method == 'POST' else {})


@configuracoes.route('/perfis/<int:id>/editar', methods=['GET', 'POST'])
@require_permission('configuracoes.perfis')
def perfil_editar(id):
    perfil = Perfil.query.get_or_404(id)
    permissoes_por_modulo = _permissoes_por_modulo()

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        perm_ids = request.form.getlist('permissoes', type=int)

        if not nome:
            flash('Nome é obrigatório.', 'danger')
        elif Perfil.query.filter(Perfil.nome == nome, Perfil.id != id).first():
            flash('Já existe um perfil com este nome.', 'danger')
        else:
            perfil.nome = nome
            perfil.descricao = descricao or None
            perfil.permissoes = (
                Permissao.query.filter(Permissao.id.in_(perm_ids)).all()
                if perm_ids else []
            )
            db.session.commit()
            flash('Perfil atualizado.', 'success')
            return redirect(url_for('configuracoes.perfis'))

    return render_template('configuracoes/perfil_form.html',
                           perfil=perfil,
                           permissoes_por_modulo=permissoes_por_modulo,
                           perfil_permissao_ids={p.id for p in perfil.permissoes},
                           form={})


@configuracoes.route('/perfis/<int:id>/excluir', methods=['POST'])
@require_permission('configuracoes.perfis')
def perfil_excluir(id):
    perfil = Perfil.query.get_or_404(id)
    count = Colaborador.query.filter_by(perfil_id=id).count()
    if count > 0:
        flash(
            f'Este perfil está associado a {count} colaborador(es). '
            'Reatribua-os antes de excluir.',
            'danger',
        )
        return redirect(url_for('configuracoes.perfis'))

    nome = perfil.nome
    db.session.delete(perfil)
    db.session.commit()
    flash(f'Perfil "{nome}" excluído.', 'info')
    return redirect(url_for('configuracoes.perfis'))


# ═══════════════════════════════════════════════════════════════
# FUNÇÕES
# ═══════════════════════════════════════════════════════════════

@configuracoes.route('/funcoes')
@require_permission('configuracoes.equipes')
def funcoes():
    lista = Funcao.query.order_by(Funcao.nome).all()
    colab_counts = {
        f.id: Colaborador.query.filter_by(funcao_id=f.id, ativo=1).count()
        for f in lista
    }
    return render_template('configuracoes/funcoes.html',
                           funcoes=lista, colab_counts=colab_counts)


@configuracoes.route('/funcoes/nova', methods=['GET', 'POST'])
@require_permission('configuracoes.equipes')
def funcao_nova():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip().upper()
        if not nome:
            flash('Nome é obrigatório.', 'danger')
        elif Funcao.query.filter_by(nome=nome).first():
            flash('Já existe uma função com este nome.', 'danger')
        else:
            db.session.add(Funcao(nome=nome))
            db.session.commit()
            flash(f'Função "{nome}" criada.', 'success')
            return redirect(url_for('configuracoes.funcoes'))

    return render_template('configuracoes/funcao_form.html', funcao=None,
                           form=request.form if request.method == 'POST' else {})


@configuracoes.route('/funcoes/<int:id>/editar', methods=['GET', 'POST'])
@require_permission('configuracoes.equipes')
def funcao_editar(id):
    funcao = Funcao.query.get_or_404(id)
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip().upper()
        if not nome:
            flash('Nome é obrigatório.', 'danger')
        elif Funcao.query.filter(Funcao.nome == nome, Funcao.id != id).first():
            flash('Já existe uma função com este nome.', 'danger')
        else:
            funcao.nome = nome
            # sincroniza campo texto nos colaboradores vinculados
            for c in funcao.colaboradores:
                c.funcao = nome
            db.session.commit()
            flash('Função atualizada.', 'success')
            return redirect(url_for('configuracoes.funcoes'))

    return render_template('configuracoes/funcao_form.html', funcao=funcao, form={})


@configuracoes.route('/funcoes/<int:id>/toggle', methods=['POST'])
@require_permission('configuracoes.equipes')
def funcao_toggle(id):
    funcao = Funcao.query.get_or_404(id)
    funcao.ativo = 0 if funcao.ativo else 1
    db.session.commit()
    estado = 'ativada' if funcao.ativo else 'desativada'
    flash(f'Função "{funcao.nome}" {estado}.', 'info')
    return redirect(url_for('configuracoes.funcoes'))


# ═══════════════════════════════════════════════════════════════
# EQUIPES
# ═══════════════════════════════════════════════════════════════

@configuracoes.route('/equipes')
@require_permission('configuracoes.equipes')
def equipes():
    lista = Equipe.query.order_by(Equipe.nome).all()
    colab_counts = {
        e.id: Colaborador.query.filter_by(equipe_id=e.id, ativo=1).count()
        for e in lista
    }
    return render_template('configuracoes/equipes.html',
                           equipes=lista, colab_counts=colab_counts)


@configuracoes.route('/equipes/nova', methods=['GET', 'POST'])
@require_permission('configuracoes.equipes')
def equipe_nova():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        if not nome:
            flash('Nome é obrigatório.', 'danger')
        else:
            db.session.add(Equipe(nome=nome, descricao=descricao or None))
            db.session.commit()
            flash(f'Equipe "{nome}" criada.', 'success')
            return redirect(url_for('configuracoes.equipes'))

    return render_template('configuracoes/equipe_form.html', equipe=None,
                           form=request.form if request.method == 'POST' else {})


@configuracoes.route('/equipes/<int:id>/editar', methods=['GET', 'POST'])
@require_permission('configuracoes.equipes')
def equipe_editar(id):
    equipe = Equipe.query.get_or_404(id)
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        if not nome:
            flash('Nome é obrigatório.', 'danger')
        else:
            equipe.nome = nome
            equipe.descricao = descricao or None
            db.session.commit()
            flash('Equipe atualizada.', 'success')
            return redirect(url_for('configuracoes.equipes'))

    return render_template('configuracoes/equipe_form.html', equipe=equipe, form={})


@configuracoes.route('/equipes/<int:id>/toggle', methods=['POST'])
@require_permission('configuracoes.equipes')
def equipe_toggle(id):
    equipe = Equipe.query.get_or_404(id)
    ativos = Colaborador.query.filter_by(equipe_id=id, ativo=1).count()
    if ativos and equipe.ativo:
        flash(f'Equipe possui {ativos} colaborador(es) ativo(s). Transfira-os antes de desativar.', 'danger')
        return redirect(url_for('configuracoes.equipes'))
    equipe.ativo = 0 if equipe.ativo else 1
    db.session.commit()
    estado = 'ativada' if equipe.ativo else 'desativada'
    flash(f'Equipe "{equipe.nome}" {estado}.', 'info')
    return redirect(url_for('configuracoes.equipes'))
