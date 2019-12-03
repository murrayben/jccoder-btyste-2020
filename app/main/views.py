from random import shuffle
from flask import abort, current_app, flash, jsonify, redirect, render_template, url_for, session, request, g
from flask_login import current_user, login_required
from sqlalchemy.sql.expression import func
from datetime import datetime
from ..models import (db, AnswerStatus, Assignment, Chapter, Class,
                      ClassStudent, Hint, Lesson, Page, PageAnswer,
                      PageQuestion, Permission, ProblemMistake,
                      ProblemMistakeType, Project, Quiz, StudentAssignment,
                      TeacherNote, UserAnswer, Question, QuizAttempt)
from .. import moment
from .forms import NewPageQuestion, NewPageAnswer, EditPageAnswer, SearchForm
from . import main

@main.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
    g.search_form = SearchForm()

@main.route('/')
def index():
    upcoming_assignments = None
    past_assignments = None
    title = "JCCoder"
    if current_user.is_authenticated:
        if current_user.can(Permission.MANAGE_CLASS) and not current_user.is_admin():
            return redirect(url_for('teacher.dashboard'))
        upcoming_page = request.args.get('upcoming_page', 1, int)
        past_page = request.args.get('past_page', 1, int)
        upcoming_assignments = current_user.upcoming_assignments()
        past_assignments = current_user.past_assignments()
        title = "JCCoder - Dashboard"
    return render_template('index_new.html', title=title, upcoming_assignments=upcoming_assignments, past_assignments=past_assignments)

@main.route('/assignment-table', methods=['GET', 'POST'])
def assignment_table():
    if request.method == 'GET':
        abort(400)
    data = request.get_json()
    page = int(data["page"])
    assignments_type = data["type"]
    pagination = current_user.assignments
    if assignments_type == 'upcoming':
        pagination = pagination.filter(Assignment.due_date > datetime.now())
    else:
        pagination = pagination.filter(Assignment.due_date < datetime.now())
    pagination = pagination.paginate(page + data["direction"], per_page=10)
    html = render_template('_upcoming_past_assignments.html', type=assignments_type, pagination=pagination, assignments=pagination.items)
    return jsonify(success=True, html=html)


@main.route('/content')
def chapters():
    return render_template('chapters.html', title="JCCoder - Content")

@main.route('/about')
def about():
    return render_template('about.html', title="JCCoder - About")

@main.route('/lesson/page/<int:id>', methods=['GET', 'POST'])
def lesson_page(id):
    page = Page.query.get_or_404(id)
    if not page.is_unlocked():
        flash('You have not unlocked that page yet!', 'warning')
        return redirect(url_for('.chapter', id=page.lesson.chapter.id))
    new_question_form = NewPageQuestion()
    new_answer_form = NewPageAnswer()
    if new_question_form.submit_question.data and new_question_form.validate():
        question = PageQuestion(author=current_user._get_current_object(), text=new_question_form.text.data, page=page)
        db.session.add(question)
        return redirect(url_for('main.lesson_page', id=id))
    if new_answer_form.submit_answer.data and new_answer_form.validate():
        answer = PageAnswer(author=current_user._get_current_object(), text=new_answer_form.answer.data, question_id=int(new_answer_form.question_id.data))
        return redirect(url_for('main.lesson_page', id=id))
    return render_template('lesson_page.html', title="JCCoder - Lesson Pages", page=page, new_question_form=new_question_form, new_answer_form=new_answer_form, page_html=page.html)

@main.route('/edit/lesson-page/question/<int:id>', methods=['GET', 'POST'])
def edit_page_question(id):
    page_question = PageQuestion.query.get_or_404(id)
    form = NewPageQuestion()
    if form.validate_on_submit():
        page_question.text = form.text.data
        db.session.add(page_question)
        return redirect(url_for('main.lesson_page', id=page_question.page_id))
    form.text.data = page_question.text
    return render_template('edit_page_question.html', title="JCCoder - Edit Question", form=form)

@main.route('/edit/lesson-page/answer/<int:id>', methods=['GET', 'POST'])
def edit_page_answer(id):
    page_answer = PageAnswer.query.get_or_404(id)
    form = EditPageAnswer()
    if form.validate_on_submit():
        page_answer.text = form.answer.data
        db.session.add(page_answer)
        return redirect(url_for('main.lesson_page', id=page_answer.question.page_id))
    form.answer.data = page_answer.text
    return render_template('edit_page_answer.html', title="JCCoder - Edit Answer", form=form)

@main.route('/take-quiz/<int:id>')
def take_quiz(id):
    quiz = Quiz.query.get_or_404(id)
    #questions = quiz.questions.all()
    if not quiz.is_unlocked():
        return 'Locked'
    if quiz.type.code == 'P':
        questions = quiz.questions.order_by(func.rand()).limit(quiz.no_questions).all()
    else:
        questions = []
        for skill in quiz.tested_skills:
            question = skill.questions.order_by(func.rand()).first()
            if question:
                questions.append(question)
        shuffle(questions)
    session["attempt_no"] = 0
    try:
        session["questions"] = [question.id for question in questions]
    except AttributeError:
        # If all skills have no questions
        session["questions"] = []
    session["user_results"] = []
    session["no_attempts"] = []
    session["scores"] = []
    session["explanations"] = []
    session["num_hints_used"] = 0
    return render_template('take_quiz.html', title="JCCoder - Take Quiz", quiz=quiz, questions=questions)

@main.route('/submit-mistake', methods=["GET", "POST"])
def submit_mistake():
    # AJAX url for reporting mistake in a problem
    if request.method == 'GET':
        abort(404)

    data = request.get_json()
    mistake_type_id = data["mistake_type_id"]
    description = data["mistake_description"]
    question_id = data["problem_id"]
    if not ProblemMistakeType.query.get(mistake_type_id):
        abort(400)
    if not Question.query.get(question_id):
        abort(400)
    user_id = current_user.id if current_user.is_authenticated else None
    mistake = ProblemMistake(description=description, problem_mistake_type_id=mistake_type_id, user_id=user_id, question_id=question_id)
    db.session.add(mistake)
    return jsonify(success=True)

@main.route('/chapter/<int:id>')
def chapter(id):
    chapter = Chapter.query.get_or_404(id)
    lessons = []
    def append_lessons(lesson):
        lessons.append(lesson)
        if lesson.next_lesson:
            append_lessons(lesson.next_lesson)
    first_lesson = chapter.lessons.filter_by(prev_lesson=None).first()
    if first_lesson:
        append_lessons(first_lesson)
    return render_template('display_chapter.html', title="JCCoder - " + chapter.title, chapter=chapter, lessons=lessons)

@main.route('/page-content/', methods=['GET', 'POST'])
def page_content():
    # AJAX url for page
    if request.method == 'GET':
        abort(404)
    
    # Get page id
    data = request.get_json()
    is_quiz = data["is_quiz"]
    if is_quiz:
        if not current_user.can(Permission.MANAGE_CLASS):
            abort(403)
        quiz_id = int(data['id'])
        quiz = Quiz.query.get(quiz_id)

        if not quiz:
            # Return error as id is invalid
            abort(400)

        if not quiz.is_unlocked():
            abort(403)

        questions = quiz.questions
        title = quiz.title()
        html = render_template('teacher/_quiz_preview.html', quiz=quiz, questions=questions)
        html += """<style type="text/css" class="css-extra">
    .undraggable-btn {
        min-width: 100px;
        min-height: 46px;
        border: 1px solid #000000;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
</style>
"""
        return jsonify(success=True, page_title=title, page_html=html, page_type='')
    else:
        page_id = int(data['id'])

        # Get page
        page = Page.query.get(page_id)
        if not page:
            # Return error as id is invalid
            abort(400)

        if not page.is_unlocked():
            abort(403)
        
        page_title = page.title
        page_html = page.html
        if page.next_page:
            page_type = page.next_page.page_type.description
        else:
            page_type = ''

        notes_html = ''
        if current_user.is_admin():
            notes = page.notes.group_by(TeacherNote.teacher).all()
            notes_html = "<hr /><h3>Added Notes</h3>"
            for note in notes:
                notes_html += '<hr />{0}<p>Added by {1} to their class {2}'.format(note.body_html, note.teacher.username, note.class_.name)
        elif current_user.can(Permission.MANAGE_CLASS):
            notes = page.notes.filter_by(teacher_id=current_user.id).group_by(TeacherNote.class_id).all()
            notes_html = "<hr /><h3>You added</h3>"
            current_class = None
            for note in notes:
                if note.class_id != current_class:
                    notes_html += '<hr /><h5>Class: ' + note.class_.name + '</h5>'
                    current_class = note.class_id 
                notes_html += '<hr />{0}'.format(note.body_html)
        else:
            notes = page.notes.filter(TeacherNote.class_.has(Class.students.contains(current_user._get_current_object()))).all()
            notes_html = "<hr /><h3>Added by your teacher</h3>"
            for note in notes:
                notes_html += '<hr />{0}'.format(note.body_html)
                
        page_html += notes_html
        # css, js, stripped_lines = parsePageContent(page_html)
        # page_html = '\n'.join(stripped_lines)
        # return jsonify(success=True, page_title=page_title, page_html=page_html, page_type=page_type, css=css, js=js)
        return jsonify(success=True, page_title=page_title, page_html=page_html, page_type=page_type)

@main.route('/check', methods=['GET', 'POST'])
def check():
    if request.method == "GET":
        abort(404)
    attempt_no = session.get('attempt_no')
    attempt_no += 1
    session["attempt_no"] += 1
    data = request.get_json()
    # if data.get('hint_used_mark_incorrect', False):
    #     session["user_results"].append("Used hint")
    #     session["no_attempts"].append("N/A")
    #     return jsonify(success=True)
    answer = data['answer']
    if not type(answer) == list:
        answer = answer.strip()
    question = Question.query.get(data['question_id'])
    if not question:
        # Return error as id is invalid
        abort(400)

    hints_used = int(session.get("num_hints_used", 0))
    total_num_hints = Hint.query.filter_by(question_id=question.id).count()
    try:
        score = round(100 - ((hints_used / total_num_hints) * 100), 0)
    except ZeroDivisionError:
        # No hints available (shouldn't happen)
        print('No hints')
        score = 100
    
    # Get QuestionAnswer object then QuestionOption and then the text
    status = question.check(answer)
    try_again = False
    if status:
        answer_status = AnswerStatus.query.get(1) # Correct
        session["attempt_no"] = 0 # For the next question
        session["num_hints_used"] = 0
    else:
        answer_status = AnswerStatus.query.get(2) # Incorrect
        if attempt_no == question.max_attempts:
            session["attempt_no"] = 0 # For the next question
            session["num_hints_used"] = 0
        else:
            try_again = True
    

    if (not status) and (not try_again):
        # Got it wrong
        score = 0
        solution_html = question.get_explanation()
    else:
        solution_html = ""

    if not try_again:
        session["scores"].append(score)
        # if not data.get("used_hint", False):
        session["user_results"].append(answer)
        session["no_attempts"].append(attempt_no)
        session["explanations"].append(question.get_explanation())
    if current_user.is_authenticated:
        keyed_answer = answer
        if type(answer) == list:
            keyed_answer = ", ".join(answer)
        user_answer = UserAnswer(keyed_answer=keyed_answer, answer_status=answer_status, score=score, user=current_user._get_current_object(),
                                question=question, attempt_no=attempt_no)
    return jsonify(success=True, answer_status=status, try_again=try_again, solution_html=solution_html)

@main.route('/summary', methods=['GET', 'POST'])
def summary():
    if request.method == "GET":
        abort(404)
    data = request.get_json()
    question_ids = []
    questions = []
    correct_answers = []
    user_ans_status = []
    i = 0
    # for question in Quiz.query.filter_by(id=data['id']).first().questions:
    for question in [Question.query.get(question_id) for question_id in session["questions"]]:
        question_ids.append(question.id)
        questions.append((question.html or question.text))
        questions.append(question)
        correct_answers.append(question.correct_answer())
        user_ans_status.append(question.check(session["user_results"][i]))
        i += 1

    overall_score = sum(session["scores"]) / len(session["scores"])
    if current_user.is_authenticated:
        quiz_attempt = QuizAttempt(user_id=current_user.id, quiz_id=data['id'], percent=overall_score)
        #UserAnswer.query.filter_by(user_id=current_user.id).delete()
        db.session.add(quiz_attempt)
        assignments = Assignment.query.filter_by(quiz_id=data['id']).all()
        for assignment in assignments:
            if assignment.students.filter_by(username=current_user.username).first():
                #student_assignment = StudentAssignment(assignment_id=assignment.id, student_id=current_user.id, score=overall_score)
                student_assignments = StudentAssignment.query.filter_by(assignment_id=assignment.id, student_id=current_user.id).all()
                for student_assignment in student_assignments:
                    if not student_assignment.score or (student_assignment.score < overall_score):
                        student_assignment.score = overall_score
                        db.session.add(student_assignment)


    return jsonify(success=True, question_ids=question_ids, questions=session["questions"], no_attempts=session["no_attempts"],
            last_attempts=session["user_results"], scores=session["scores"],
            correct_answers=correct_answers, user_ans_status=user_ans_status,
            explanations=session["explanations"], overall_score=overall_score)

@main.route('/update-quiz-attempts', methods=["GET", "POST"])
def update_quiz_attempts():
    if request.method == "GET":
        abort(404)
    data = request.get_json()
    quiz_id = data["id"]
    quiz = Quiz.query.get(quiz_id)

    if not quiz:
        abort(400)  # Abort as id is invalid
    if current_user.is_authenticated:
        quiz_attempt = QuizAttempt.query.filter_by(quiz_id=data["id"], user_id=current_user.id).order_by(QuizAttempt.datetime.desc()).first()
        attempt_time = moment.create(quiz_attempt.datetime)
        formatted_time = attempt_time.format('YYYY-MM-DD hh:mm:ss')
        return jsonify(success=True, authenticated=True, overall_score=quiz_attempt.percent, datetime_string=attempt_time.fromNow(), formatted_datetime=formatted_time)
    else:
        return jsonify(success=True, authenticated=False)

@main.route('/get-hint', methods=["GET", "POST"])
def get_hint():
    if request.method == "GET":
        abort(404)
    data = request.get_json()
    hint = Hint.query.filter_by(hint_no=data["hint_no"], question_id=data["question_id"]).first()
    if not hint:
        # Return error as data is invalid (possibly user tried to change values through browser Inspector)
        abort(400)
    hint_count = Hint.query.filter_by(question_id=data["question_id"]).count()
    session["num_hints_used"] = int(session.get("num_hints_used", 0)) + 1
    is_last_hint = int(data["hint_no"]) == hint_count
    return jsonify(success=True, hint_html=hint.html, is_last_hint=is_last_hint)

@main.route('/project/<int:id>')
def project(id):
    project = Project.query.get_or_404(id)
    return render_template('project.html', title="JCCoder - Project - " + project.title, project=project)

@main.route('/search')
def search():
    if not g.search_form.validate():
        abort(404)
    q = g.search_form.q.data
    page = request.args.get('page', 1, type=int)
    pages, total = Page.search(q, page, current_app.config["POSTS_PER_PAGE"])
    next_url = url_for('main.search', q=q, page=page + 1) \
        if total > page * current_app.config["POSTS_PER_PAGE"] else None
    prev_url = url_for('main.search', q=q, page=page - 1) \
        if page > 1 else None
    return render_template('search_results.html', title="Search results for \"{0}\"".format(q), q=q, pages=pages.all(), total=total, prev_url=prev_url, next_url=next_url)

@main.route('/join', methods=["GET", "POST"])
@login_required
def join_class():
    if request.method == "GET":
        abort(404)
    data = request.get_json()
    class_id = int(data["class_id"])
    if not Class.query.get(class_id):
        abort(400)
    if ClassStudent.query.filter_by(student_id=current_user.id, class_id=class_id, student_status=True).first():
        # Can't join a class twice
        abort(400)
    class_student = ClassStudent(student_id=current_user.id, class_id=class_id)
    db.session.add(class_student)
    db.session.commit()
    return jsonify(success=True)


@main.route('/join/<code>')
@login_required
def join_class_confirm(code):
    if current_user.can(Permission.MANAGE_CLASS):
        # Teachers can't join classes
        return redirect(url_for('.index'))
    
    class_ = Class.query.filter_by(code=code).first_or_404()
    if ClassStudent.query.filter_by(student_id=current_user.id, class_id=class_.id, student_status=True).first():
        # Can't join a class twice
        flash('You have already joined that class.', 'info')
        return redirect(url_for('.index'))
    return render_template('join_class.html', title="JCCoder - Join class {0}".format(code), class_=class_)