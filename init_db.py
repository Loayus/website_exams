from models import db, Role, User, QCM, Question, Answer, UserAttempt, UserAnswer
from app import app

def init_database():
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
        else:
            print("Le compte admin existe déjà")

        print("\n Base de données initialisée avec succès !")

if __name__ == '__main__':
    init_database()
