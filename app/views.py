from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user
from app.models import User
from app.forms import LoginForm
from app import app

@app.route('/')
def index():
    return render_template('index.html', title="JCCoder")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is not None and user.check_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('index'))
        flash('Invalid username or password!', 'warning')
    return render_template('login.html', title="JCCoder - Login", form=form)
