import random, string

from flask import abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from ..models import Assignment, Class, ClassStudent, Page, Permission, Question, Quiz, StudentAssignment, User, db
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
    if not data["name"]:
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
    class_ = Class.query.get_or_404(id)
    if class_.teacher_id != current_user.id:
        abort(403)
    page = request.args.get('assignments_page', 1, int)
    session["usernames"] = []
    form = AssignmentForm(id)
    objects = []
    if form.validate_on_submit():
        # Merging them into one list
        items = session.get("assigned_pages", [])
        items.append('change-to-quiz')
        items.extend(session.get("assigned_quizzes", []))
        items.extend(session.get("assigned_chapter_quizzes", []))

        item_type = "page"
        for item in items:
            if item == "change-to-quiz":
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
                if student and (student in class_.students.all()):
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
        objects.append(-2)
        objects.extend(session.get("assigned_chapter_quizzes", []))
    assignment_pagination = class_.assignments.order_by(Assignment.due_date.desc()).paginate(page, per_page=8)
    return render_template('teacher/class.html', title="JCCoder - " + class_.name, class_=class_, form=form, objects=objects, assignments_pagination=assignment_pagination)

@teacher.route('/class/assignment-page', methods=["GET", "POST"])
def assignment_page():
    if request.method == "GET":
        abort(404)
    data = request.get_json()
    page = int(data["page"])
    class_ = Class.query.get(int(data["class_id"]))
    if not class_:
        abort(400)
    elif class_.teacher_id != current_user.id:
        abort(400)
    assignments_pagination = class_.assignments.order_by(Assignment.due_date.desc()).paginate(page + data["direction"], per_page=8)
    html = render_template('teacher/_assignment.html', class_=class_, assignments_pagination=assignments_pagination, moment=moment.create)
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
    quizzes = data["quizzes"]
    quizzes.extend(data["chapter_quizzes"])
    for quiz in quizzes:
        if not Quiz.query.get(quiz):
            abort(400)
    session["assigned_pages"] = data["pages"]
    session["assigned_quizzes"] = data["quizzes"]
    session["assigned_chapter_quizzes"] = data["chapter_quizzes"]
    return jsonify(success=True)

@teacher.route('/delete/class/<int:id>')
def delete_class(id):
    class_ = Class.query.get_or_404(id)
    if class_.teacher_id != current_user.id:
        abort(403)
    students_ids = [student.id for student in class_.students]
    assignments_ids = [assignment.id for assignment in class_.assignments]
    for class_student in ClassStudent.query.filter(db.and_(ClassStudent.class_id==class_.id, ClassStudent.student_id.in_(students_ids))).all():
        db.session.delete(class_student)
    for student_assignment in StudentAssignment.query.filter(db.and_(StudentAssignment.student_id.in_(students_ids), StudentAssignment.assignment_id.in_(assignments_ids))):
        db.session.delete(student_assignment)
    db.session.delete(class_)
    return redirect(url_for('.dashboard'))

@teacher.route('/generate-username', methods=['GET', 'POST'])
def generate_username():
    if request.method == 'GET':
        abort(404)
    data = request.get_json()
    try:
        name = data['name']
    except KeyError:
        abort(400)
    else:
        if not name.strip():
            return jsonify(success=True, username='')
        name = name.split()
        first_name = name[0].lower()
        if len(name) == 1:
            username = first_name
        else:
            last_name = ''.join(name[1:]).lower()
            username = first_name[0] + last_name
        new_username = username
        i = 1
        while User.query.filter_by(username=new_username).first() or new_username in session["usernames"]: # Prevent duplicates
            i += 1
            new_username = username + str(i)
        usernames = session['usernames']
        usernames.append(new_username)
        session['usernames'] = usernames
        return jsonify(success=True, username=new_username)

@teacher.route('/create-accounts', methods=['GET', 'POST'])
def create_accounts():
    if request.method == 'GET':
        abort(404)
    data = request.get_json()
    students = data["students"]
    class_id = int(data["class_id"])
    if current_user.id != Class.query.get(class_id).teacher_id:
        abort(403)
    for student_object in students:
        username = student_object["username"]
        password = student_object["password"]
        if User.query.filter_by(username=username).first():
            # Not unique username - Problem!
            abort(400)
        else:
            student = User(username=username, password=password, under_13=True)
            db.session.add(student)
            db.session.commit()
            class_student = ClassStudent(student_id=student.id, class_id=class_id)
            db.session.add(class_student)
    return jsonify(success=True)

@teacher.route('/class/<int:class_id>/delete/student/<int:student_id>')
def delete_student_from_class(class_id, student_id):
    if current_user.id != Class.query.get(class_id).teacher_id:
        abort(403)
    class_student = ClassStudent.query.filter_by(class_id=class_id, student_id=student_id).first()
    class_student.student_status = False
    db.session.add(class_student)
    return redirect(url_for('.display_class', id=class_id))

@teacher.route('/edit/student/', methods=["GET", "POST"])
def edit_student():
    if request.method == 'GET':
        abort(404)

    data = request.get_json()
    class_ = Class.query.get(int(data["class_id"]))
    if current_user.id != class_.teacher_id:
        abort(403)

    student = User.query.get(int(data["student_id"]))
    if not ClassStudent.query.filter_by(class_id=class_.id, student_id=student.id).first().student_status:
        # Student is not taught by this teacher
        abort(403)
    
    new_username = data["new_username"]
    if User.query.filter_by(username=new_username).first():
        # Username already exists
        return jsonify(success=True, unique_username=False)
    student.username = new_username
    db.session.add(student)
    return jsonify(success=True, unique_username=True)

@teacher.route('/edit/class/', methods=["GET", "POST"])
def edit_class():
    if request.method == 'GET':
        abort(404)
    
    data = request.get_json()
    class_ = Class.query.get(int(data["class_id"]))
    if current_user.id != class_.teacher_id:
        abort(403)
    
    class_.name = data["name"]
    db.session.add(class_)
    return jsonify(success=True)

@teacher.route('/progress/assignment/<int:assignment_id>', defaults={'student_username': None})
@teacher.route('/progress/assignment/<int:assignment_id>/student/<student_username>')
def assignment_progress(assignment_id, student_username):
    assignment = Assignment.query.get_or_404(assignment_id)
    if current_user.id != assignment.teacher_id:
        abort(403)
    if not assignment.is_quiz():
        abort(404)
    students = assignment.class_.students.filter(ClassStudent.student_status)
    if student_username:
        students = User.query.filter_by(username=student_username)
        if not students.first():
            abort(404)
    title = 'JCCoder - Assignment Progress - '
    if student_username:
        title += student_username
    else:
        title += 'All Students'
    return render_template('teacher/assignment_progress.html', title=title, assignment=assignment, students=students)

@teacher.route('/progress/assignment/<int:id>/reveal-answer', methods=['GET', 'POST'])
def assignment_progress_reveal_answer(id):
    if request.method == 'GET':
        abort(404)
    
    assignment = Assignment.query.get_or_404(id)
    if current_user.id != assignment.teacher_id:
        abort(403)
    if not assignment.is_quiz():
        abort(404)
    data = request.get_json()
    question = Question.query.get_or_404(int(data["question_id"]))
    return jsonify(success=True, answer=question.correct_answer())