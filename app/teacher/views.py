import random, string

from flask import abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from ..models import Class, Permission, db
from .forms import NewClass
from . import teacher

@teacher.before_request
def teacher_before_request():
    if not current_user.is_authenticated or not current_user.can(Permission.MANAGE_CLASS):
        abort(403)

@teacher.route('/dashboard')
def dashboard():
    classes = Class.query.filter_by(teacher_id=current_user.id).all()
    form = NewClass()
    if form.validate_on_submit():
        random_code = ''
        while random_code == '' or (Class.query.filter_by(code=random_code).count() > 0):
            random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        new_class = Class(name=form.name.data, code=random_code, description=form.description.data, teacher_id=current_user.id)
        db.session.add(new_class)
        return redirect(url_for('.dashboard'))
    return render_template('teacher/dashboard.html', title="JCCoder - Teacher Dashboard", form=form, classes=classes)

@teacher.route('/new/class', methods=['GET', 'POST'])
def new_class():
    if request.method == 'GET' or not current_user.is_authenticated:
        abort(404)
    data = request.get_json()
    if not data["name"] or not data["description"]:
        abort(400)
    random_code = ''
    while random_code == '' or (Class.query.filter_by(code=random_code).count() > 0):
        random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    new_class = Class(name=data["name"], code=random_code, description=data["description"], teacher_id=current_user.id)
    db.session.add(new_class)
    db.session.commit()
    return jsonify(success=True, code=random_code)

@teacher.route('/class/<int:id>')
def display_class(id):
    _class = Class.query.get_or_404(id)
    if _class.teacher_id != current_user.id:
        abort(403)
    return render_template('teacher/class.html', title="JCCoder - " + _class.name, _class=_class)