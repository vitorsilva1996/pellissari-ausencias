from datetime import datetime
from flask_login import UserMixin
from app import db, bcrypt


# ── Tabelas de associação ─────────────────────────────────────────────────────

perfil_permissoes = db.Table(
    'perfil_permissoes',
    db.Column('perfil_id',    db.Integer, db.ForeignKey('perfis.id'),    primary_key=True),
    db.Column('permissao_id', db.Integer, db.ForeignKey('permissoes.id'), primary_key=True),
)

colaborador_equipes = db.Table(
    'colaborador_equipes',
    db.Column('colaborador_id', db.Integer, db.ForeignKey('colaboradores.id'), primary_key=True),
    db.Column('equipe_id',      db.Integer, db.ForeignKey('equipes.id'),       primary_key=True),
)


# ── Permissao ─────────────────────────────────────────────────────────────────

class Permissao(db.Model):
    __tablename__ = 'permissoes'

    id      = db.Column(db.Integer, primary_key=True)
    codigo  = db.Column(db.String(60),  unique=True, nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    modulo  = db.Column(db.String(60),  nullable=False)

    def __repr__(self):
        return f'<Permissao {self.codigo}>'


# ── Perfil ────────────────────────────────────────────────────────────────────

class Perfil(db.Model):
    __tablename__ = 'perfis'

    id        = db.Column(db.Integer, primary_key=True)
    nome      = db.Column(db.String(60), unique=True, nullable=False)
    descricao = db.Column(db.String(200), nullable=True)
    ativo     = db.Column(db.SmallInteger, nullable=False, default=1)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    permissoes = db.relationship(
        'Permissao', secondary=perfil_permissoes, backref='perfis', lazy='select',
    )

    @property
    def codigos(self):
        return frozenset(p.codigo for p in self.permissoes)

    def __repr__(self):
        return f'<Perfil {self.nome}>'


# ── Equipe ────────────────────────────────────────────────────────────────────

class Equipe(db.Model):
    __tablename__ = 'equipes'

    id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome     = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(255), nullable=True)

    colaboradores = db.relationship(
        'Colaborador', back_populates='equipe', lazy='dynamic',
        foreign_keys='Colaborador.equipe_id',
    )

    def __repr__(self):
        return f'<Equipe {self.nome}>'


# ── Colaborador ───────────────────────────────────────────────────────────────

class Colaborador(UserMixin, db.Model):
    __tablename__ = 'colaboradores'

    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome         = db.Column(db.String(150), nullable=False)
    email        = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash   = db.Column(db.String(255), nullable=False)
    data_admissao = db.Column(db.Date, nullable=False)
    funcao       = db.Column(db.String(100), nullable=False)
    equipe_id    = db.Column(db.Integer, db.ForeignKey('equipes.id'), nullable=False)
    gestor_id    = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=True)
    perfil       = db.Column(
        db.Enum('colaborador', 'gestor', 'rh', 'diretoria'),
        nullable=False, default='colaborador',
    )
    perfil_id    = db.Column(db.Integer, db.ForeignKey('perfis.id'), nullable=True)
    ad_login     = db.Column(db.String(150), nullable=True)
    ativo        = db.Column(db.SmallInteger, nullable=False, default=1)
    criado_em    = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    equipe = db.relationship(
        'Equipe', back_populates='colaboradores', foreign_keys=[equipe_id],
    )
    gestor = db.relationship('Colaborador', remote_side=[id], backref='subordinados')
    perfil_obj = db.relationship('Perfil', foreign_keys=[perfil_id])
    equipes_gerenciadas = db.relationship(
        'Equipe', secondary=colaborador_equipes, backref='gestores',
    )
    periodos_aquisitivos = db.relationship(
        'PeriodoAquisitivo', back_populates='colaborador', lazy='dynamic',
    )
    ferias       = db.relationship('Ferias',     back_populates='colaborador', lazy='dynamic')
    dayoffs      = db.relationship('DayOff',     back_populates='colaborador', lazy='dynamic')
    notificacoes = db.relationship('Notificacao', back_populates='colaborador', lazy='dynamic')

    @staticmethod
    def normalizar_nome(v):
        return v.strip().title() if v else v

    @staticmethod
    def normalizar_funcao(v):
        return v.strip().upper() if v else v

    def set_senha(self, senha):
        self.senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

    def check_senha(self, senha):
        return bcrypt.check_password_hash(self.senha_hash, senha)

    def is_active(self):
        return bool(self.ativo)

    def pode_solicitar_dayoff(self):
        from datetime import date
        from dateutil.relativedelta import relativedelta
        return self.data_admissao <= date.today() - relativedelta(years=1)

    def __repr__(self):
        return f'<Colaborador {self.nome}>'


# ── PeriodoAquisitivo ─────────────────────────────────────────────────────────

class PeriodoAquisitivo(db.Model):
    __tablename__ = 'periodos_aquisitivos'

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    colaborador_id  = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    data_inicio     = db.Column(db.Date, nullable=False)
    data_fim        = db.Column(db.Date, nullable=False)
    dias_direito    = db.Column(db.Integer, nullable=False, default=30)
    data_limite_saida = db.Column(db.Date, nullable=False)

    colaborador = db.relationship('Colaborador', back_populates='periodos_aquisitivos')
    ferias      = db.relationship('Ferias', back_populates='periodo_aquisitivo', lazy='dynamic')

    def dias_usados(self):
        return sum(
            f.dias for f in self.ferias
            if f.status not in ('reprovada', 'cancelada')
        )

    def dias_restantes(self):
        return self.dias_direito - self.dias_usados()

    def __repr__(self):
        return f'<PeriodoAquisitivo {self.colaborador_id} {self.data_inicio}~{self.data_fim}>'


# ── Ferias ────────────────────────────────────────────────────────────────────

class Ferias(db.Model):
    __tablename__ = 'ferias'

    id                   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    colaborador_id       = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    periodo_aquisitivo_id = db.Column(db.Integer, db.ForeignKey('periodos_aquisitivos.id'), nullable=False)
    data_inicio          = db.Column(db.Date, nullable=False)
    dias                 = db.Column(db.Integer, nullable=False)
    data_retorno         = db.Column(db.Date, nullable=False)
    status               = db.Column(
        db.Enum('aguardando_gestor', 'aguardando_rh', 'aprovada', 'reprovada', 'cancelada'),
        nullable=False, default='aguardando_gestor',
    )
    comentario_gestor  = db.Column(db.Text, nullable=True)
    comentario_rh      = db.Column(db.Text, nullable=True)
    aprovado_gestor_em = db.Column(db.DateTime, nullable=True)
    aprovado_rh_em     = db.Column(db.DateTime, nullable=True)
    solicitado_em      = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    colaborador       = db.relationship('Colaborador', back_populates='ferias')
    periodo_aquisitivo = db.relationship('PeriodoAquisitivo', back_populates='ferias')

    def __repr__(self):
        return f'<Ferias {self.colaborador_id} {self.data_inicio} {self.status}>'


# ── DayOff ────────────────────────────────────────────────────────────────────

class DayOff(db.Model):
    __tablename__ = 'dayoff'

    id               = db.Column(db.Integer, primary_key=True, autoincrement=True)
    colaborador_id   = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    data_solicitada  = db.Column(db.Date, nullable=False)
    mes_referencia   = db.Column(db.Date, nullable=False)
    status           = db.Column(
        db.Enum('aguardando_gestor', 'aprovado', 'reprovado', 'cancelado'),
        nullable=False, default='aguardando_gestor',
    )
    comentario_gestor = db.Column(db.Text, nullable=True)
    decidido_em       = db.Column(db.DateTime, nullable=True)
    solicitado_em     = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    colaborador = db.relationship('Colaborador', back_populates='dayoffs')

    def __repr__(self):
        return f'<DayOff {self.colaborador_id} {self.data_solicitada} {self.status}>'


# ── Notificacao ───────────────────────────────────────────────────────────────

class Notificacao(db.Model):
    __tablename__ = 'notificacoes'

    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    tipo           = db.Column(db.String(60), nullable=False)
    mensagem       = db.Column(db.Text, nullable=False)
    lida           = db.Column(db.SmallInteger, nullable=False, default=0)
    enviado_email  = db.Column(db.SmallInteger, nullable=False, default=0)
    criado_em      = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    colaborador = db.relationship('Colaborador', back_populates='notificacoes')

    def __repr__(self):
        return f'<Notificacao {self.tipo} -> colaborador {self.colaborador_id}>'
