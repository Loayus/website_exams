"""
Point d'entrée WSGI pour l'application Flask
Utilisé par Gunicorn pour démarrer l'application
"""
from app import app

if __name__ == "__main__":
    app.run()
