from flask import abort, jsonify, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from markdown import markdown
from ..models import AnswerStatus, Topic, Strand, Module, Lesson, LearningOutcome, Glossary, Page, UserAnswer, Question, QuestionAnswer, QuestionOption, QuestionType, Quiz, PageType, Project, ProjectStep
from .forms import NewQuestion, NewTopic, NewStrand, NewModule, NewLesson, EditLessonContent, NewLearningOutcome, NewQuiz, NewGlossary, NewPage, NewProject
from .. import db
from . import admin
import json

@admin.before_request
def check_for_admin():
    if not current_user.is_authenticated or not current_user.is_admin():
        abort(403)

@admin.route('/new/question', methods=['GET', 'POST'])
@login_required
def new_question():
    form = NewQuestion()
    if form.validate_on_submit():
        question_type = form.type.data
        question_type_id = QuestionType.query.filter(QuestionType.id == question_type).first().id
        quiz = Quiz.query.get(form.quiz.data)
        question = Question(text=form.text.data, question_type_id=question_type_id, max_attempts=form.max_attempts.data, quiz=quiz)
        db.session.add(question)
        db.session.commit()
        question_type = question.question_type
        question_answer = None
        if question_type == QuestionType.query.filter_by(code='C').first(): # Multiple Choice
            options = request.form.getlist('options1')
            for option in options:
                db.session.add(QuestionOption(text=option, question_id=question.id))
            db.session.commit()
            question_answer = QuestionAnswer(option=QuestionOption.query.filter_by(text=options[form.answer.data-1]).first(), question=question)
        
        elif question_type == QuestionType.query.filter_by(code='S').first(): # Single Answer
            question_option = QuestionOption(text=form.answer.data, question_id=question.id)
            db.session.add(question_option)
            db.session.commit()
            question_answer = QuestionAnswer(option=QuestionOption.query.filter_by(text=form.answer.data).first(), question=question)
        db.session.add(question_answer)
        return redirect(url_for('admin.all_questions'))
    return render_template('admin/new_question.html', title="JCCoder - New Question", form=form, QuestionType=QuestionType)

@admin.route('/new/topic', methods=['GET', 'POST'])
@login_required
def new_topic():
    form = NewTopic()
    if form.validate_on_submit():
        topic = Topic(name=form.name.data)
        db.session.add(topic)
        return redirect(url_for('admin.all_topics'))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Topic", new_thing="Topic", form=form)

@admin.route('/new/strand', methods=['GET', 'POST'])
@login_required
def new_strand():
    form = NewStrand()
    if form.validate_on_submit():
        number = 1
        if len(Strand.query.all()) > 0:
            number = Strand.query.all()[-1].number + 1
        strand = Strand(title=form.title.data, description=form.description.data, 
                        topic=Topic.query.get(form.topic.data), number=number)
        strand.next_strand_id = form.next_strand.data
        if not form.next_strand.data == 0:
            Strand.query.get(form.next_strand.data).prev_strand = strand
        else:
            strand.next_strand_id = None # MySQL doesn't like 0
        db.session.add(strand)
        return redirect(url_for('admin.all_strands'))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Strand", new_thing="Strand", form=form)

@admin.route('/new/module', methods=['GET', 'POST'])
@login_required
def new_module():
    form = NewModule()
    if form.validate_on_submit():
        module = Module(title=form.title.data, description=form.description.data,
                        strand=Strand.query.get(form.strand.data))
        module.next_module_id = form.next_module.data
        if not form.next_module.data == 0:
            Module.query.get(form.next_module.data).prev_module = module
        else:
            module.next_module = None # MySQL doesn't like 0
        db.session.add(module)
        return redirect(url_for('admin.all_modules'))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Module", new_thing="Module", form=form)

@admin.route('/new/lesson', methods=['GET', 'POST'])
@login_required
def new_lesson():
    form = NewLesson()
    if form.validate_on_submit():
        lesson = Lesson(title=form.title.data, overview=form.overview.data, icon=form.icon.data,
                        module=Module.query.get(form.module.data))
        number = 1
        lessons_in_module = Lesson.query.filter_by(module=lesson.module).all()
        if len(lessons_in_module) > 1:
            number = lessons_in_module[-2].sequence_no + 1
        lesson.sequence_no = number
        lesson.next_lesson_id = form.next_lesson.data
        if not form.next_lesson.data == 0:
            Lesson.query.get(form.next_lesson.data).prev_lesson = lesson
        else:
            lesson.next_lesson = None # MySQL doesn't like 0
        db.session.add(lesson)
        return redirect(url_for('admin.all_lessons'))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Lesson", new_thing="Lesson", form=form)

@admin.route('/new/learning-outcome', methods=['GET', 'POST'])
@login_required
def new_learning_outcome():
    form = NewLearningOutcome()
    if form.validate_on_submit():
        learning_outcome = LearningOutcome(description=form.description.data,
                                           lesson=Lesson.query.get(form.lesson.data))
        db.session.add(learning_outcome)
        return redirect(url_for('admin.all_lessons'))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Learning Outcome", new_thing="Learning Outcome", form=form)

@admin.route('/new/quiz', methods=['GET', 'POST'])
@login_required
def new_quiz():
    form = NewQuiz()
    if form.validate_on_submit():
        quiz = Quiz(description=form.description.data, page=Page.query.get(form.page.data))
        db.session.add(quiz)
        return redirect(url_for('admin.all_quizzes'))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Quiz", new_thing="Quiz", form=form)

@admin.route('/new/glossary', methods=['GET', 'POST'])
@login_required
def new_glossary():
    form = NewGlossary()
    if form.validate_on_submit():
        glossary = Glossary(title=form.title.data, text=form.content.data, lesson_id=form.lesson.data)
        db.session.add(glossary)
        return redirect(url_for('admin.all_glossaries'))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Glossary", new_thing="Glossary", form=form)

@admin.route('/new/page', methods=['GET', 'POST'])
@login_required
def new_page():
    form = NewPage()
    if form.validate_on_submit():
        if form.next_page.data == 0:
            next_page_id = None
        else:
            next_page_id = form.next_page.data
        page_type = PageType.query.get(form.page_type.data)
        page = Page(title=form.title.data, page_type=page_type,
                        next_page_id=next_page_id,
                        lesson_id=form.lesson.data)
        db.session.add(page)
        db.session.commit()
        page.text = form.content.data

        db.session.add(page)
        return redirect(url_for('admin.all_pages'))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Page", new_thing="Page", form=form)

@admin.route('/new/project', methods=['GET', 'POST'])
@login_required
def new_project():
    form = NewProject()
    if form.validate_on_submit():
        project = Project(title=form.title.data, description=form.description.data, thumbnail=form.thumbnail.data,
                              lesson_id=form.lesson.data, status=bool(form.status.data))
        db.session.add(project)
        return redirect(url_for('main.index'))
    return render_template('admin/new_project.html', title="JCCoder - New Project", form=form)

@admin.route('/save-step', methods=['GET', 'POST'])
def save_step():
    if request.method == 'GET':
        abort(404)
    data = request.get_json()
    if data.get('editing'):
        step = ProjectStep.query.get(data.get('step_id'))
        if not step:
            abort(400)
        step.title = data.get('title')
        step.content = data.get('content')
        db.session.add(step)
        db.session.commit()
    else:
        if data.get('prev_step_id'):
            prev_step = ProjectStep.query.get(data.get('prev_step_id'))
        else:
            prev_step = None
        step = ProjectStep(title=data.get('title'), content=data.get('content'), project_id=data.get('project_id'), prev_step=prev_step)
        db.session.add(step)
        db.session.commit()
    step_id = step.id
    return jsonify(success=True, stepID=step_id)

@admin.route('/all/topic/')
@login_required
def all_topics():
    topics = Topic.query.all()
    return render_template('admin/all_something.html', title="JCCoder - All Topics", list_items="Topics", items=topics)

@admin.route('/all/strand/')
@login_required
def all_strands():
    strands = Strand.query.all()
    groups = Topic.query.all()
    return render_template('admin/all_something.html', title="JCCoder - All Strands", list_items="Strands", items=strands, groups=groups)

@admin.route('/all/module/')
@login_required
def all_modules():
    modules = Module.query.all()
    groups = []
    for topic in Topic.query.all():
        groups.extend(topic.all_ordered_children())
    return render_template('admin/all_something.html', title="JCCoder - All Modules", list_items="Modules", items=modules, groups=groups)

@admin.route('/all/lesson/')
@login_required
def all_lessons():
    lessons = Lesson.query.all()
    groups = []
    for topic in Topic.query.all():
        for strand in topic.all_ordered_children():
            groups.extend(strand.all_ordered_children())
    return render_template('admin/all_something.html', title="JCCoder - All Lessons", list_items="Lessons", items=lessons, groups=groups)

@admin.route('/all/quiz/')
@login_required
def all_quizzes():
    quizzes = Quiz.query.all()
    return render_template('admin/all_something.html', title="JCCoder - All Quizzes", list_items="Quizzes", items=quizzes)

@admin.route('/all/question/')
@login_required
def all_questions():
    questions = Question.query.all()
    return render_template('admin/all_something.html', title="JCCoder - All Questions", list_items="Questions", items=questions)

@admin.route('/all/glossary/')
@login_required
def all_glossaries():
    glossaries = Glossary.query.all()
    return render_template('admin/all_something.html', title="JCCoder - All Glossaries", list_items="Glossaries", items=glossaries)

@admin.route('/all/page/')
@login_required
def all_pages():
    pages = Page.query.all()
    groups = []
    for topic in Topic.query.all():
        for strand in topic.all_ordered_children():
            for lesson in strand.all_ordered_children():
                groups.extend(lesson.all_ordered_children())
    return render_template('admin/all_something.html', title="JCCoder - All Pages", list_items="Pages", items=pages, groups=groups)

@admin.route('/all/project/')
@login_required
def all_projects():
    projects = Project.query.all()
    groups = []
    for topic in Topic.query.all():
        for strand in topic.all_ordered_children():
            for lesson in strand.all_ordered_children():
                groups.extend(lesson.all_ordered_children())
    return render_template('admin/all_something.html', title="JCCoder - All Projects", list_items="Projects", items=projects, groups=groups)

@admin.route('/all/strand/<int:id>')
@login_required
def topics_strands(id):
    topic = Topic.query.get_or_404(id)
    strands = topic.all_ordered_children()
    return render_template('admin/somethings_things.html', title="JCCoder - All Strands in Topic " + topic.name, owner_of_things="Topic", thing_type="Strands", things=strands, owner=topic)

@admin.route('/all/module/<int:id>')
@login_required
def strands_modules(id):
    strand = Strand.query.get_or_404(id)
    modules = strand.all_ordered_children()
    return render_template('admin/somethings_things.html', title="JCCoder - All Modules in Strand " + strand.title, owner_of_things="Strand", thing_type="Modules", things=modules, owner=strand)

@admin.route('/all/lesson/<int:id>')
@login_required
def modules_lessons(id):
    module = Module.query.get_or_404(id)
    lessons = module.all_ordered_children()
    return render_template('admin/somethings_things.html', title="JCCoder - All Lessons in Module " + module.title, owner_of_things="Module", thing_type="Lessons", things=lessons, owner=module)

@admin.route('/all/pages/<int:id>')
@login_required
def lessons_pages(id):
    lesson = Lesson.query.get_or_404(id)
    pages = lesson.all_ordered_children()
    return render_template('admin/somethings_things.html', title="JCCoder - All Pages in Lesson " + lesson.title, owner_of_things="Lesson", thing_type="Pages", things=pages, owner=lesson)

@admin.route('/all/questions/<int:id>')
@login_required
def quizzes_questions(id):
    quiz = Quiz.query.get_or_404(id)
    questions = Question.query.filter_by(quiz=quiz).all()
    return render_template('admin/somethings_things.html', title="JCCoder - All Question in Quiz (in page: " + quiz.page.title + ")", owner_of_things="Quiz", thing_type="Questions", things=questions, owner=quiz)

@admin.route('/edit/topic/<int:id>', methods=["GET", "POST"])
@login_required
def edit_topic(id):
    topic = Topic.query.get_or_404(id)
    form = NewTopic()
    if form.validate_on_submit():
        topic.name = form.name.data
        db.session.add(topic)
        return redirect(url_for('.all_topics'))
    form.name.data = topic.name
    return render_template('admin/edit_topic.html', title="JCCoder - Edit Topic " + topic.name, form=form, topic=topic)

@admin.route('/edit/strand/<int:id>', methods=["GET", "POST"])
@login_required
def edit_strand(id):
    strand = Strand.query.get_or_404(id)
    form = NewStrand()
    if form.validate_on_submit():
        strand.title = form.title.data
        strand.description = form.description.data
        strand.topic_id = form.topic.data
        strand.next_strand_id = form.next_strand.data
        if not form.next_strand.data == 0:
            Strand.query.get(form.next_strand.data).prev_strand = strand
        else:
            strand.next_strand_id = None # MySQL doesn't like 0
        db.session.add(strand)
        return redirect(url_for('.all_strands'))
    form.title.data = strand.title
    form.description.data = strand.description
    form.topic.data = strand.topic_id
    try:
        form.next_strand.data = strand.next_strand_id
    except:
        form.next_strand.data = 0
    return render_template('admin/edit_not_learn_out_topic.html', title="JCCoder - Edit Strand " + strand.title, form=form, thing=strand)

@admin.route('/edit/module/<int:id>', methods=["GET", "POST"])
@login_required
def edit_module(id):
    module = Module.query.get_or_404(id)
    form = NewModule()
    if form.validate_on_submit():
        module.title = form.title.data
        module.description = form.description.data
        module.strand_id = form.strand.data
        module.next_module_id = form.next_module.data
        if not form.next_module.data == 0:
            Module.query.get(form.next_module.data).prev_module = module
        else:
            module.next_module = None # MySQL doesn't like 0
        db.session.add(module)
        return redirect(url_for('.all_modules'))
    form.title.data = module.title
    form.description.data = module.description
    form.strand.data = module.strand_id
    try:
        form.next_module.data = module.next_module_id
    except:
        form.next_module.data = 0
    return render_template('admin/edit_not_learn_out_topic.html', title="JCCoder - Edit Module " + module.title, form=form, thing=module)

@admin.route('/edit/lesson/<int:id>', methods=["GET", "POST"])
@login_required
def edit_lesson(id):
    lesson = Lesson.query.get_or_404(id)
    form = NewLesson()
    if form.validate_on_submit():
        lesson.title = form.title.data
        lesson.overview = form.overview.data
        lesson.icon = form.icon.data
        lesson.module_id = form.module.data
        lesson.next_lesson_id = form.next_lesson.data
        if not form.next_lesson.data == 0:
            Lesson.query.get(form.next_lesson.data).prev_lesson = lesson
        else:
            lesson.next_lesson = None # MySQL doesn't like 0
        db.session.add(lesson)
        return redirect(url_for('.all_lessons'))
    form.title.data = lesson.title
    form.overview.data = lesson.overview
    form.icon.data = lesson.icon
    form.module.data = lesson.module_id
    try:
        form.next_lesson.data = lesson.next_lesson_id
    except:
        form.next_lesson.data = 0
    return render_template('admin/edit_not_learn_out_topic.html', title="JCCoder - Edit Lesson " + lesson.title, form=form, thing=lesson)

@admin.route('/edit/lesson/<int:id>/content', methods=["GET", "POST"])
@login_required
def edit_lesson_content(id):
    lesson = Lesson.query.get_or_404(id)
    form = EditLessonContent()
    return render_template('admin/edit_lesson_content.html', title="JCCoder - Edit Lesson " + lesson.title + "'s Content", form=form,lesson=lesson)

@admin.route('/edit/learning-outcome/<int:id>', methods=["GET", "POST"])
@login_required
def edit_learning_outcome(id):
    learning_outcome = LearningOutcome.query.get_or_404(id)
    form = NewLearningOutcome()
    if form.validate_on_submit():
        learning_outcome.description = form.description.data
        learning_outcome.lesson_id = form.lesson.data
        db.session.add(learning_outcome)
        return redirect(url_for('.all_lessons'))
    form.description.data = learning_outcome.description
    form.lesson.data = learning_outcome.lesson_id
    return render_template('admin/edit_learning_outcome.html', title="JCCoder - Edit Learning Outcome " + learning_outcome.description, form=form, learning_outcome=learning_outcome)

@admin.route('/edit/glossary/<int:id>', methods=["GET", "POST"])
@login_required
def edit_glossary(id):
    glossary = Glossary.query.get_or_404(id)
    form = NewGlossary()
    if form.validate_on_submit():
        glossary.title = form.title.data
        glossary.text = form.content.data
        glossary.lesson_id = form.lesson.data
        db.session.add(glossary)
        return redirect(url_for('.all_glossaries'))
    form.title.data = glossary.title
    form.content.data = glossary.text
    form.lesson.data = glossary.lesson_id
    return render_template('admin/edit_not_learn_out_topic.html', title="JCCoder - Edit Glossary " + glossary.title, form=form, thing=glossary)

@admin.route('/edit/page/<int:id>', methods=["GET", "POST"])
@login_required
def edit_page(id):
    page = Page.query.get_or_404(id)
    form = NewPage()
    if form.validate_on_submit():
        page.page_type_id = form.page_type.data
        page.title = form.title.data
        page.text = form.content.data
        page.next_page_id = form.next_page.data
        if not form.next_page.data == 0:
            Page.query.get(form.next_page.data).prev_page = page
        else:
            page.next_page_id = None # MySQL doesn't like 0
        page.lesson_id = form.lesson.data
        db.session.add(page)
        return redirect(url_for('.all_pages'))
    form.page_type.data = page.page_type_id
    form.title.data = page.title
    form.content.data = page.text
    try:
        form.next_page.data = page.next_page_id
    except:
        form.next_page.data = 0
    form.lesson.data = page.lesson_id
    return render_template('admin/edit_not_learn_out_topic.html', title="JCCoder - Edit Glossary " + page.title, form=form, thing=page)

@admin.route('/edit/quiz/<int:id>', methods=["GET", "POST"])
@login_required
def edit_quiz(id):
    quiz = Quiz.query.get_or_404(id)
    form = NewQuiz()
    if form.validate_on_submit():
        quiz.description = form.description.data
        quiz.page_id = form.page.data
        db.session.add(quiz)
        return redirect(url_for('.all_quizzes'))
    form.description.data = quiz.description
    form.page.data = quiz.page_id
    return render_template('admin/edit_quiz.html', title="JCCoder - Edit Quiz in Page " + quiz.page.title, form=form, quiz=quiz)

@admin.route('/edit/question/<int:id>', methods=["GET", "POST"])
@login_required
def edit_question(id):
    question = Question.query.get_or_404(id)
    form = NewQuestion()
    if form.validate_on_submit():
        question.question_type_id = form.type.data
        question.text = form.text.data
        question.max_attempts = form.max_attempts.data
        question.answer.first().option.text = form.answer.data
        question.quiz_id = form.quiz.data
        db.session.add(question)
        return redirect(url_for('.all_questions'))
    form.type.data = question.question_type_id
    form.text.data = question.text
    form.answer.data = question.correct_answer()
    form.max_attempts.data = question.max_attempts
    form.quiz.data = question.quiz_id
    return render_template('admin/edit_question.html', title="JCCoder - Edit Question", form=form, question=question)

@admin.route('/edit/project/<int:id>', methods=["GET", "POST"])
@login_required
def edit_project(id):
    project = Project.query.get_or_404(id)
    form = NewProject()
    if form.validate_on_submit():
        project.status = bool(form.status.data)
        project.title = form.title.data
        project.description = form.description.data
        project.thumbnail = form.thumbnail.data
        project.lesson_id = form.lesson.data
        return redirect(url_for('.all_projects'))
    form.status.data = int(project.status)
    form.title.data = project.title
    form.description.data = project.description
    form.thumbnail.data = project.thumbnail
    form.lesson.data = project.lesson_id
    steps = {}
    for i, step in enumerate(project.steps, 1):
        steps['step_' + str(i)] = {}
        step_dict = steps['step_' + str(i)]
        step_dict['id'] = step.id
        step_dict['title'] = step.title
        step_dict['content'] = step.content.replace('"', '\\"')
        
    steps = json.dumps(steps, sort_keys=True).replace('    ', '\t')
    return render_template('admin/edit_project.html', title="JCCoder - Edit Project", form=form, project=project, steps=steps)

@admin.route('/preview-project', methods=["GET", "POST"])
def preview_project():
    if request.method == "GET":
        abort(404)
    data = request.get_json()
    description = data['description']
    steps = data['steps']

    preview_html = """<div class="well">
    {0}
</div>""".format(markdown(description))
    
    for step in steps:
        preview_html += """<h3 class="text-success">{0}</h3>
<div class="well">
    {1}
</div>""".format(step.get('title', 'None'), markdown(step.get('content', 'None')))

    return jsonify(success=True, previewHTML=preview_html)