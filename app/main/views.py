from flask import abort, current_app, jsonify, redirect, render_template, url_for, session, request, g
from flask_login import current_user, login_required
from datetime import datetime
from ..models import db, Chapter, Page, PageAnswer, PageQuestion, Project, Quiz, Lesson, UserAnswer, Question, AnswerStatus, Hint, QuizAttempt
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
    return render_template('index.html', title="JCCoder")

@main.route('/content')
def chapters():
    return render_template('chapters.html', title="JCCoder - Content")

@main.route('/about')
def about():
    return render_template('about.html', title="JCCoder - About")

@main.route('/lesson/page/<int:id>', methods=['GET', 'POST'])
def lesson_page(id):
    page = Page.query.get_or_404(id)
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
    questions = quiz.questions.all()
    session["attempt_no"] = 0
    session["user_results"] = []
    session["no_attempts"] = []
    session["scores"] = []
    return render_template('take_quiz.html', title="JCCoder - Take Quiz", quiz=quiz, questions=questions)

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
    page_id = int(data['id'])

    # Get page
    page = Page.query.get(page_id)
    if not page:
        # Return error as id is invalid
        abort(400)
    
    page_title = page.title
    page_html = page.html
    if page.next_page:
        page_type = page.next_page.page_type.description
    else:
        page_type = ''

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

    answer = data['answer'].strip()
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
    else:
        print(hints_used)
        print(total_num_hints)
    
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
        solution_html = question.solution_html
    else:
        solution_html = ""

    if not try_again:
        session["scores"].append(score)
        # if not data.get("used_hint", False):
        session["user_results"].append(answer)
        session["no_attempts"].append(attempt_no)
    if current_user.is_authenticated:
        user_answer = UserAnswer(keyed_answer=answer, answer_status=answer_status, score=score, user=current_user._get_current_object(),
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
    for question in Quiz.query.filter_by(id=data['id']).first().questions:
        question_ids.append(question.id)
        questions.append((question.html or question.text))
        correct_answers.append(question.correct_answer())
        user_ans_status.append(question.check(session["user_results"][i]))
        i += 1

    overall_score = sum(session["scores"]) / len(session["scores"])
    if current_user.is_authenticated:
        quiz_attempt = QuizAttempt(user_id=current_user.id, quiz_id=data['id'], percent=overall_score)
        UserAnswer.query.filter_by(user_id=current_user.id).delete()
        db.session.add(quiz_attempt)

    return jsonify(success=True, question_ids=question_ids, questions=questions, no_attempts=session["no_attempts"],
            last_attempts=session["user_results"], scores=session["scores"],
            correct_answers=correct_answers, user_ans_status=user_ans_status,
            overall_score=overall_score)

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
        return jsonify(success=True, authenticated=True, overall_score=quiz_attempt.percent, datetime_string=attempt_time.utc(), formatted_datetime=formatted_time)
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