from flask import render_template
from app import db
from . import main

@main.app_errorhandler(404)
def not_found(error):
    return render_template('404.html', title="JCCoder - Not found"), 404

@main.app_errorhandler(500)
def internal_server_error(error):
    db.session.rollback()
    return render_template('500.html', title="JCCoder - Error"), 500