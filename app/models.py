from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class Permission:
    ASK_QUESTIONS = 0x01
    ANSWER_QUESTIONS = 0x02
    SAVE_HISTORY = 0x04
    MANAGE_CLASS = 0x08
    MODERATE_QUESTIONS = 0x10
    ADMINISTRATOR = 0xff

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'Student': (Permission.ASK_QUESTIONS |
                        Permission.ANSWER_QUESTIONS |
                        Permission.SAVE_HISTORY, True),
            'Teacher': (Permission.ASK_QUESTIONS |
                        Permission.ANSWER_QUESTIONS |
                        Permission.SAVE_HISTORY |
                        Permission.MANAGE_CLASS, False),
            'Moderator': (Permission.ASK_QUESTIONS |
                          Permission.ANSWER_QUESTIONS |
                          Permission.SAVE_HISTORY |
                          Permission.MODERATE_QUESTIONS, False),
            'Administrator': (0xff, False)
        }

        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    password_hash = db.Column(db.String(128))
    email = db.Column(db.String(120), unique=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    @property
    def password(self):
        raise AttributeError('Password is a write-only attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            self.role = Role.query.filter_by(default=True).first()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.can(Permission.ADMINISTRATOR)
    
    def can(self, permissions):
        return self.role is not None and (self.role.permissions & permissions) == permissions

    def __repr__(self):
        return '<User {}>'.format(self.username)