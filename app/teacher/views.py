import random, string

from flask import abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from ..models import Assignment, Class, Page, Permission, Quiz, StudentAssignment, User, db
from .. import moment
from .forms import AssignmentForm, NewClass
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

@teacher.route('/class/<int:id>', methods=["GET", "POST"])
def display_class(id):
    _class = Class.query.get_or_404(id)
    if _class.teacher_id != current_user.id:
        abort(403)
    page = request.args.get('assignments_page', 1, int)
    form = AssignmentForm(id)
    objects = []
    if form.validate_on_submit():
        # Merging them into one list
        items = session.get("assigned_pages", [])
        items.append('change')
        items.extend(session.get("assigned_quizzes", []))

        item_type = "page"
        for item in items:
            if item == "change":
                item_type = "quiz"
                continue
            assignment = Assignment(class_id=id, teacher_id=current_user.id, due_date=form.due_date.data)
            if item_type == "page":
                assignment.page_id = item
            else:
                assignment.quiz_id = item
            db.session.add(assignment)
            db.session.commit()
            for student_id in form.students.data:
                # Confirming that student is a real user and in the class.
                student = User.query.get(student_id)
                if student and (student in _class.students.all()):
                    student_assignment = StudentAssignment(student_id=student_id, assignment_id=assignment.id)
                    db.session.add(student_assignment)
                else:
                    flash('Invalid student id(s)', 'warning')
                    db.session.delete(assignment)
                    db.session.commit()
        return redirect(url_for('.display_class', id=id))
    elif form.is_submitted() and not form.validate():
        objects = session.get("assigned_pages", [])
        objects.append(-1)
        objects.extend(session.get("assigned_quizzes", []))
    assignment_pagination = _class.assignments.paginate(page, per_page=8)
    return render_template('teacher/class.html', title="JCCoder - " + _class.name, _class=_class, form=form, objects=objects, assignments_pagination=assignment_pagination)

@teacher.route('/class/assignment-page', methods=["GET", "POST"])
def assignment_page():
    if request.method == "GET":
        abort(404)
    data = request.get_json()
    page = int(data["page"])
    _class = Class.query.get(int(data["class_id"]))
    if not _class:
        abort(400)
    elif _class.teacher_id != current_user.id:
        abort(400)
    assignments_pagination = _class.assignments.paginate(page + data["direction"], per_page=8)
    html = render_template('teacher/_assignment.html', _class=_class, assignments_pagination=assignments_pagination, moment=moment.create)
    return jsonify(success=True, html=html)

@teacher.route('/save-items', methods=["GET", "POST"])
def save_items():
    if request.method == "GET":
        abort(404)
    data = request.get_json()
    # Check if all ids are valid
    for page in data["pages"]:
        if not Page.query.get(page):
            abort(400)
    for quiz in data["quizzes"]:
        if not Quiz.query.get(quiz):
            abort(400)
    session["assigned_pages"] = data["pages"]
    session["assigned_quizzes"] = data["quizzes"]
    return jsonify(success=True)