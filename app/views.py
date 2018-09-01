from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from app.models import User
from app.forms import LoginForm, RegistrationForm
from app import app, db

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

@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    flash('<strong>Success!</strong> You have been logged out ' + username + '.', 'success')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user, False)
        flash('<strong>Success!</strong> You have been registered and logged in!', 'success')
        return redirect(url_for('index'))
    return render_template('register.html', title="JCCoder - Register", form=form)