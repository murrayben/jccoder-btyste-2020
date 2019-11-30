from flask import Flask, redirect, render_template, request, session, url_for
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_moment import Moment
from elasticsearch import Elasticsearch
from config import Config

# Flask-Bootstrap
bootstrap = Bootstrap()

# SQLAlchemy
db = SQLAlchemy()

# Flask-Migrate
migrate = Migrate()

# Flask-Moment
moment = Moment()

login = LoginManager()
login.session_protection = 'strong'
login.login_view = 'auth.login'
login.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask-Bootstrap, SQLAlchemy, Flask-Login, Flask-Migrate and Flask-Moment
    bootstrap.init_app(app)
    db.init_app(app)
    login.init_app(app)
    migrate.init_app(app, db)
    moment.init_app(app)

    # Elasticsearch
    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
        if app.config['ELASTICSEARCH_URL'] else None


    # Register blueprints
    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from .announcements import announcements as announcements_blueprint
    app.register_blueprint(announcements_blueprint, url_prefix='/announcements')

    from .teacher import teacher as teacher_blueprint
    app.register_blueprint(teacher_blueprint, url_prefix='/teacher')

    from .teacher_blog import teacher_blog as teacher_blog_blueprint
    app.register_blueprint(teacher_blog_blueprint, url_prefix='/blog')

    # Return app
    return app

from app import models