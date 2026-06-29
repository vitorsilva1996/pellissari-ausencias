"""
Normaliza campos de texto no banco existente.
  - nome: Title Case
  - funcao: UPPER CASE
  - comentarios: strip() (remove espaços nas pontas)
Idempotente — pode ser executado múltiplas vezes sem efeito colateral.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Colaborador, Ferias, DayOff

app = create_app()

with app.app_context():
    alteracoes = 0

    # ── Colaboradores: nome → Title Case, funcao → UPPER CASE ────────────────
    print('\n── Colaboradores ──')
    for c in Colaborador.query.all():
        changed = []

        nome_norm = c.nome.strip().title() if c.nome else c.nome
        if nome_norm != c.nome:
            changed.append(f'nome: "{c.nome}" → "{nome_norm}"')
            c.nome = nome_norm

        funcao_norm = c.funcao.strip().upper() if c.funcao else c.funcao
        if funcao_norm != c.funcao:
            changed.append(f'funcao: "{c.funcao}" → "{funcao_norm}"')
            c.funcao = funcao_norm

        if changed:
            print(f'  [~] {", ".join(changed)}')
            alteracoes += len(changed)
        else:
            print(f'  [-] OK: {c.nome}')

    # ── Férias: comentarios → strip() ────────────────────────────────────────
    print('\n── Férias (comentários) ──')
    for f in Ferias.query.all():
        changed = []

        if f.comentario_gestor and f.comentario_gestor != f.comentario_gestor.strip():
            f.comentario_gestor = f.comentario_gestor.strip()
            changed.append('comentario_gestor')

        if f.comentario_rh and f.comentario_rh != f.comentario_rh.strip():
            f.comentario_rh = f.comentario_rh.strip()
            changed.append('comentario_rh')

        if changed:
            print(f'  [~] Férias id={f.id}: strip em {", ".join(changed)}')
            alteracoes += len(changed)

    # ── Day Off: comentarios → strip() ───────────────────────────────────────
    print('\n── Day Off (comentários) ──')
    for d in DayOff.query.all():
        if d.comentario_gestor and d.comentario_gestor != d.comentario_gestor.strip():
            d.comentario_gestor = d.comentario_gestor.strip()
            print(f'  [~] DayOff id={d.id}: strip em comentario_gestor')
            alteracoes += 1

    db.session.commit()
    print(f'\n✔ Normalização concluída. {alteracoes} campo(s) atualizado(s).')
