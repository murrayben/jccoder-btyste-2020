from flask import Flask, redirect, render_template, request, session, url_for
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

# Flask-Bootstrap
bootstrap = Bootstrap()

# SQLAlchemy
db = SQLAlchemy()

login = LoginManager()
login.session_protection = 'strong'
login.login_view = 'auth.login'
login.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask-Bootstrap, SQLAlchemy and Flask-Login
    bootstrap.init_app(app)
    db.init_app(app)
    login.init_app(app)

    # Register blueprints
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Return app
    return app
