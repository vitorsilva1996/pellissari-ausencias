from flask import render_template, redirect, url_for, request, flash

from app.configuracoes import configuracoes
from app.models import Perfil, Permissao, Colaborador
from app import db
from app.auth.permissions import require_permission


def _permissoes_por_modulo():
    perms = Permissao.query.order_by(Permissao.modulo, Permissao.codigo).all()
    grupos = {}
    for p in perms:
        grupos.setdefault(p.modulo, []).append(p)
    return grupos


# ── Listagem ──────────────────────────────────────────────────────────────────

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


# ── Criar ─────────────────────────────────────────────────────────────────────

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


# ── Editar ────────────────────────────────────────────────────────────────────

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


# ── Excluir ───────────────────────────────────────────────────────────────────

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
