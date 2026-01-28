from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from datetime import datetime, UTC
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'votre_cle_secrete_a_changer_en_production')

# Configuration de la base de données
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///exam_website.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Importer les modèles et initialiser la DB
from models import db, User, Role, QCM, Question, Answer, UserAttempt, UserAnswer

db.init_app(app)

# Initialiser la base de données au démarrage
def initialize_database():
    """Initialise la base de données avec les rôles et l'admin par défaut"""
    with app.app_context():
        # Créer toutes les tables
        db.create_all()

        # Vérifier si les rôles existent déjà
        if Role.query.count() == 0:
            # Créer les rôles
            admin_role = Role(name='admin', description='Administrateur du système')
            people_role = Role(name='people', description='Utilisateur standard')

            db.session.add(admin_role)
            db.session.add(people_role)
            db.session.commit()

            print("Rôles créés : admin et people")

        # Vérifier si l'admin existe déjà
        admin_user = User.query.filter_by(email='oceane.camus14@gmail.com').first()
        if not admin_user:
            # Créer l'utilisateur admin par défaut
            admin_role = Role.query.filter_by(name='admin').first()
            admin_user = User(
                email='oceane.camus14@gmail.com',
                first_name='Oceane',
                last_name='Camus',
                role_id=admin_role.id
            )
            admin_user.set_password('Doody123!')

            db.session.add(admin_user)
            db.session.commit()
            print("Compte admin créé avec succès")
        else:
            print("Le compte admin existe déjà")

        print("Base de données initialisée avec succès !")

# Appeler l'initialisation au démarrage
initialize_database()

# Décorateur pour protéger les routes nécessitant une connexion
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'error')
            return redirect(url_for('connexion'))
        return f(*args, **kwargs)
    return decorated_function

# Décorateur pour protéger les routes admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'error')
            return redirect(url_for('connexion'))

        user = User.query.get(session['user_id'])
        if not user or not user.is_admin():
            flash('Accès refusé. Cette page est réservée aux administrateurs.', 'error')
            return redirect(url_for('main_page'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def main_page():
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    return render_template('index.html', user=user)

@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    # Si déjà connecté, rediriger vers l'accueil
    if 'user_id' in session:
        return redirect(url_for('main_page'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Vérifier les identifiants dans la base de données
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_active:
                return render_template('connexion.html', error='Votre compte est désactivé.')

            # Connexion réussie
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['user_role'] = user.role.name

            # Mettre à jour la date de dernière connexion
            user.last_login = datetime.now(UTC)
            db.session.commit()

            flash(f'Bienvenue {user.first_name} !', 'success')

            # Rediriger vers la page de gestion si admin
            if user.is_admin():
                return redirect(url_for('gestion'))
            return redirect(url_for('main_page'))
        else:
            return render_template('connexion.html', error='Email ou mot de passe incorrect')

    return render_template('connexion.html')

@app.route('/inscription', methods=['GET', 'POST'])
def inscription():
    # Si déjà connecté, rediriger vers l'accueil
    if 'user_id' in session:
        return redirect(url_for('main_page'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')

        # Validations
        if not all([email, password, confirm_password, first_name, last_name]):
            return render_template('inscription.html', error='Tous les champs sont obligatoires')

        if password != confirm_password:
            return render_template('inscription.html', error='Les mots de passe ne correspondent pas')

        if len(password) < 8:
            return render_template('inscription.html', error='Le mot de passe doit contenir au moins 8 caractères')

        # Vérifier si l'email existe déjà
        if User.query.filter_by(email=email).first():
            return render_template('inscription.html', error='Cet email est déjà utilisé')

        # Créer le nouvel utilisateur avec le rôle "people"
        people_role = Role.query.filter_by(name='people').first()
        new_user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role_id=people_role.id
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Compte créé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('connexion'))

    return render_template('inscription.html')

@app.route('/gestion')
@admin_required
def gestion():
    """Page de gestion réservée aux administrateurs"""
    users = User.query.all()
    roles = Role.query.all()
    user = User.query.get(session['user_id'])

    return render_template('gestion.html', users=users, roles=roles, user=user)

@app.route('/deconnexion')
def deconnexion():
    """Déconnexion de l'utilisateur"""
    session.clear()
    flash('Vous avez été déconnecté avec succès.', 'success')
    return redirect(url_for('connexion'))

@app.route('/api/user/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """API pour activer/désactiver un utilisateur"""
    user = User.query.get_or_404(user_id)

    # Empêcher de désactiver son propre compte
    if user.id == session['user_id']:
        return {'success': False, 'message': 'Vous ne pouvez pas désactiver votre propre compte'}, 400

    user.is_active = not user.is_active
    db.session.commit()

    status = 'activé' if user.is_active else 'désactivé'
    return {'success': True, 'message': f'Utilisateur {status}', 'is_active': user.is_active}

@app.route('/api/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """API pour supprimer un utilisateur"""
    user = User.query.get_or_404(user_id)

    # Empêcher de supprimer son propre compte
    if user.id == session['user_id']:
        return {'success': False, 'message': 'Vous ne pouvez pas supprimer votre propre compte'}, 400

    db.session.delete(user)
    db.session.commit()

    return {'success': True, 'message': 'Utilisateur supprimé avec succès'}

@app.route('/creer-qcm', methods=['GET', 'POST'])
@admin_required
def creer_qcm():
    """Page de création de QCM réservée aux administrateurs"""
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        import json

        # Récupérer les données du formulaire
        title = request.form.get('title')
        description = request.form.get('description')
        questions_data = request.form.get('questions_data')

        if not title:
            flash('Le titre du QCM est obligatoire', 'error')
            return render_template('creer_qcm.html', user=user)

        # Créer le QCM
        new_qcm = QCM(
            title=title,
            description=description,
            created_by=user.id
        )
        db.session.add(new_qcm)
        db.session.flush()  # Pour obtenir l'ID du QCM

        # Parser les questions
        if questions_data:
            questions = json.loads(questions_data)

            for idx, q_data in enumerate(questions):
                question = Question(
                    qcm_id=new_qcm.id,
                    question_text=q_data['text'],
                    order=idx
                )
                db.session.add(question)
                db.session.flush()

                # Ajouter les réponses
                for ans_idx, ans_data in enumerate(q_data['answers']):
                    answer = Answer(
                        question_id=question.id,
                        answer_text=ans_data['text'],
                        is_correct=ans_data['is_correct'],
                        order=ans_idx
                    )
                    db.session.add(answer)

        db.session.commit()
        flash('QCM créé avec succès !', 'success')
        return redirect(url_for('liste_qcm_admin'))

    return render_template('creer_qcm.html', user=user)

@app.route('/mes-qcm')
@admin_required
def liste_qcm_admin():
    """Liste des QCM pour les admins"""
    user = User.query.get(session['user_id'])
    qcms = QCM.query.order_by(QCM.created_at.desc()).all()
    return render_template('qcm/liste_qcm_admin.html', user=user, qcms=qcms)

@app.route('/qcm')
@login_required
def liste_qcm():
    """Liste des QCM disponibles pour tous les utilisateurs connectés"""
    user = User.query.get(session['user_id'])
    qcms = QCM.query.filter_by(is_active=True).order_by(QCM.created_at.desc()).all()

    # Récupérer les scores des tentatives de l'utilisateur
    attempts = {}
    for qcm in qcms:
        user_attempt = UserAttempt.query.filter_by(
            user_id=user.id,
            qcm_id=qcm.id
        ).order_by(UserAttempt.completed_at.desc()).first()

        if user_attempt:
            attempts[qcm.id] = {
                'score': user_attempt.score,
                'date': user_attempt.completed_at
            }

    return render_template('qcm/liste_qcm.html', user=user, qcms=qcms, attempts=attempts)

@app.route('/qcm/<int:qcm_id>')
@login_required
def passer_qcm(qcm_id):
    """Page pour passer un QCM"""
    user = User.query.get(session['user_id'])
    qcm = QCM.query.get_or_404(qcm_id)

    if not qcm.is_active:
        flash('Ce QCM n\'est plus disponible', 'error')
        return redirect(url_for('liste_qcm'))

    return render_template('qcm/passer_qcm.html', user=user, qcm=qcm)

@app.route('/qcm/<int:qcm_id>/soumettre', methods=['POST'])
@login_required
def soumettre_qcm(qcm_id):
    """Soumettre les réponses d'un QCM"""
    user = User.query.get(session['user_id'])
    qcm = QCM.query.get_or_404(qcm_id)

    # Créer une tentative
    attempt = UserAttempt(
        user_id=user.id,
        qcm_id=qcm.id
    )
    db.session.add(attempt)
    db.session.flush()

    # Enregistrer les réponses et calculer le score par question
    total_questions = len(qcm.questions)
    total_score = 0

    for question in qcm.questions:
        # Récupérer toutes les réponses sélectionnées pour cette question
        selected_answer_ids = request.form.getlist(f'question_{question.id}')

        # Enregistrer chaque réponse sélectionnée
        for answer_id in selected_answer_ids:
            answer_id = int(answer_id)
            user_answer = UserAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                answer_id=answer_id
            )
            db.session.add(user_answer)

        # Calculer le score pour cette question
        question_score = calculate_question_score(question, selected_answer_ids)
        total_score += question_score

    # Calculer le score en pourcentage
    score = (total_score / total_questions * 100) if total_questions > 0 else 0
    attempt.score = score

    db.session.commit()

    return redirect(url_for('resultat_qcm', attempt_id=attempt.id))

def calculate_question_score(question, selected_answer_ids):
    """
    Calcule le score pour une question avec pénalités
    Format: Bonnes cochées / Mauvaises cochées / Score

    Le score dépend du nombre de bonnes réponses dans la question,
    du nombre de bonnes réponses cochées, et du nombre de mauvaises réponses cochées
    """
    selected_ids = set(int(aid) for aid in selected_answer_ids) if selected_answer_ids else set()

    # Récupérer les réponses correctes et incorrectes
    correct_answer_ids = set(answer.id for answer in question.answers if answer.is_correct)
    incorrect_answer_ids = set(answer.id for answer in question.answers if not answer.is_correct)

    # Calculer le nombre de bonnes et mauvaises réponses cochées
    correct_checked = len(selected_ids & correct_answer_ids)  # Intersection
    incorrect_checked = len(selected_ids & incorrect_answer_ids)  # Intersection

    # Nombre total de bonnes réponses dans la question
    total_correct = len(correct_answer_ids)

    # Tables de notation selon le nombre de bonnes réponses
    scoring_tables = {
        1: {  # Si une bonne réponse est la bonne
            (1, 0): 1.0,
            (1, 1): 0.5,
            (1, 2): 0.0,
        },
        2: {  # Si deux bonnes réponses sont les bonnes
            (2, 0): 1.0,
            (2, 1): 0.66,
            (2, 2): 0.5,
            (2, 3): 0.4,
            (1, 0): 0.5,
            (1, 1): 0.25,
            (1, 2): 0.0,
        },
        3: {  # Si trois bonnes réponses sont les bonnes
            (3, 0): 1.0,
            (3, 1): 0.66,
            (3, 2): 0.33,
            (2, 0): 0.66,
            (2, 1): 0.33,
            (2, 2): 0.0,
            (1, 0): 0.33,
            (1, 1): 0.0,
        },
        4: {  # Si quatre bonnes réponses sont les bonnes
            (4, 0): 1.0,
            (4, 1): 0.75,
            (3, 0): 0.75,
            (3, 1): 0.5,
            (2, 0): 0.5,
            (2, 1): 0.25,
            (1, 0): 0.2,
            (1, 1): 0.0,
        },
        5: {  # Si cinq bonnes réponses sont les bonnes
            (5, 0): 1.0,
            (4, 0): 0.8,
            (3, 0): 0.6,
            (2, 0): 0.4,
            (1, 0): 0.2,
            (0, 0): 0.0,
        }
    }

    # Récupérer la table de notation appropriée
    if total_correct not in scoring_tables:
        # Cas imprévu, retour au système strict
        return 1.0 if (correct_checked == total_correct and incorrect_checked == 0) else 0.0

    scoring_table = scoring_tables[total_correct]

    # Chercher le score correspondant
    # Pour les cas avec "2 ou +" ou "1 ou +", on vérifie les conditions
    key = (correct_checked, incorrect_checked)

    if key in scoring_table:
        return scoring_table[key]

    # Gérer les cas "2 ou +" et "1 ou +"
    if total_correct == 1:
        if correct_checked == 1 and incorrect_checked >= 2:
            return 0.0
    elif total_correct == 2:
        if correct_checked == 1 and incorrect_checked >= 2:
            return 0.0
    elif total_correct == 3:
        if correct_checked == 2 and incorrect_checked >= 2:
            return 0.0
        if correct_checked == 1 and incorrect_checked >= 1:
            return 0.0
    elif total_correct == 5:
        # Pour 5 bonnes réponses, si on coche des mauvaises, score = 0
        if incorrect_checked > 0:
            return 0.0

    # Par défaut, si combinaison non prévue, score = 0
    return 0.0

@app.route('/resultat/<int:attempt_id>')
@login_required
def resultat_qcm(attempt_id):
    """Afficher le résultat d'une tentative"""
    user = User.query.get(session['user_id'])
    attempt = UserAttempt.query.get_or_404(attempt_id)

    # Vérifier que c'est bien la tentative de l'utilisateur
    if attempt.user_id != user.id:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('liste_qcm'))

    return render_template('qcm/resultat_qcm.html', user=user, attempt=attempt)

@app.route('/api/qcm/<int:qcm_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_qcm_status(qcm_id):
    """API pour activer/désactiver un QCM"""
    qcm = QCM.query.get_or_404(qcm_id)
    qcm.is_active = not qcm.is_active
    db.session.commit()

    status = 'activé' if qcm.is_active else 'désactivé'
    return {'success': True, 'message': f'QCM {status}', 'is_active': qcm.is_active}

@app.route('/api/qcm/<int:qcm_id>/delete', methods=['POST'])
@admin_required
def delete_qcm(qcm_id):
    """API pour supprimer un QCM"""
    qcm = QCM.query.get_or_404(qcm_id)
    db.session.delete(qcm)
    db.session.commit()

    return {'success': True, 'message': 'QCM supprimé avec succès'}

if __name__ == '__main__':
    app.run(debug=True, port=5001)
