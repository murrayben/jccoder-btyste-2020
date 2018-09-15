from flask import render_template
from app import app, db

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html', title="JCCoder - Not found"), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('500.html', title="JCCoder - Error"), 500