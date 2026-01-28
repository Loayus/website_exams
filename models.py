from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Role(db.Model):
    """Table des rôles"""
    __tablename__ = 'role'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relation avec User
    users = db.relationship('User', backref='role', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'


class QCM(db.Model):
    """Table des QCMs"""
    __tablename__ = 'qcm'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relations
    creator = db.relationship('User', backref='qcms_created')
    questions = db.relationship('Question', backref='qcm', lazy=True, cascade='all, delete-orphan')
    user_attempts = db.relationship('UserAttempt', backref='qcm', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<QCM {self.title}>'


class Question(db.Model):
    """Table des questions"""
    __tablename__ = 'question'

    id = db.Column(db.Integer, primary_key=True)
    qcm_id = db.Column(db.Integer, db.ForeignKey('qcm.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    answers = db.relationship('Answer', backref='question', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Question {self.id}: {self.question_text[:50]}>'


class Answer(db.Model):
    """Table des réponses"""
    __tablename__ = 'answer'

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Answer {self.id}: {self.answer_text[:50]}>'


class UserAttempt(db.Model):
    """Table des tentatives des utilisateurs"""
    __tablename__ = 'user_attempt'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    qcm_id = db.Column(db.Integer, db.ForeignKey('qcm.id'), nullable=False)
    score = db.Column(db.Float)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref='attempts')
    user_answers = db.relationship('UserAnswer', backref='attempt', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<UserAttempt {self.id}: User {self.user_id} - QCM {self.qcm_id}>'


class UserAnswer(db.Model):
    """Table des réponses des utilisateurs"""
    __tablename__ = 'user_answer'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('user_attempt.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey('answer.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    question = db.relationship('Question')
    answer = db.relationship('Answer')

    def __repr__(self):
        return f'<UserAnswer {self.id}: Attempt {self.attempt_id}>'


class User(db.Model):
    """Table des utilisateurs"""
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    # Clé étrangère vers Role
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)

    def set_password(self, password):
        """Hache le mot de passe"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Vérifie le mot de passe"""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        """Vérifie si l'utilisateur est admin"""
        return self.role.name == 'admin'

    def __repr__(self):
        return f'<User {self.email}>'