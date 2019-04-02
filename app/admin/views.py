from flask import abort, jsonify, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from ..models import customTagMarkdown, AnswerStatus, Strand, Module, Chapter, Lesson, Skill, Glossary, Page, UserAnswer, Question, QuestionAnswer, QuestionOption, QuestionType, Quiz, PageType, Project, ProjectStep, Hint
from .forms import NewQuestion, NewStrand, NewModule, NewChapter, NewLesson, EditLessonContent, NewSkill, NewQuiz, NewGlossary, NewPage, NewProject
from .. import db
from . import admin
import json

@admin.before_request
def check_for_admin():
    if not current_user.is_authenticated or not current_user.is_admin():
        abort(403)

def parseSkillIDs(ids):
    return_list = []

    # Iterate through whole list of ids
    for i in ids:
        # Turn id into an object
        skill = Skill.query.filter_by(id=i).first()

        # Add that on to the list of Tag objects
        return_list.append(skill)
    
    # Return the list of objects back to the caller
    return return_list

# Do the reverse of the above
def unparseSkillObjects(quiz):
    return_list = []

    # Iterate through the list of objects
    for i in quiz.tested_skills:
        # Add the id of the tag to the list of ids
        return_list.append(i.id)
    
    # Return the list of ids back to the caller
    return return_list

@admin.route('/new/question', methods=['GET', 'POST'])
@login_required
def new_question():
    form = NewQuestion()
    if form.validate_on_submit():
        question_type = form.type.data
        question_type_id = QuestionType.query.filter(QuestionType.id == question_type).first().id
        quiz = Quiz.query.get(form.quiz.data)
        question = Question(text=form.text.data, question_type_id=question_type_id, max_attempts=form.max_attempts.data,
                                quiz=quiz, solution=form.solution.data)
        db.session.add(question)
        db.session.commit()

        for i, hint_text in enumerate(form.hints.data.split('::sep::'), 1):
            hint = Hint(text=hint_text.strip(), hint_no=i, question_id=question.id)
            db.session.add(hint)
        question_type = question.question_type
        question_answer = None
        if question_type == QuestionType.query.filter_by(code='C').first(): # Multiple Choice
            options = request.form.getlist('options1')
            for option in options:
                db.session.add(QuestionOption(text=option, question_id=question.id))
            db.session.commit()
            question_answer = QuestionAnswer(option=QuestionOption.query.filter_by(text=options[int(form.answer.data)-1]).first(), question=question)
        elif question_type == QuestionType.query.filter_by(code='D').first(): # Drag and drop
            options = request.form.getlist('options1')
            for option in options:
                if option.startswith('img:'):
                    option = option[4:]
                    option = '<img src="{0}" />'.format(option)
                db.session.add(QuestionOption(text=option, question_id=question.id))
            question_answer_option = QuestionOption(text=form.answer.data, question_id=question.id)
            db.session.add(question_answer_option)
            db.session.commit()
            question_answer = QuestionAnswer(option=QuestionOption.query.filter_by(text=form.answer.data).first(), question=question)
        elif question_type == QuestionType.query.filter_by(code='S').first(): # Single Answer
            question_option = QuestionOption(text=form.answer.data, question_id=question.id)
            db.session.add(question_option)
            db.session.commit()
            question_answer = QuestionAnswer(option=QuestionOption.query.filter_by(text=form.answer.data).first(), question=question)
        db.session.add(question_answer)
        return redirect(url_for('admin.all_questions'))
    return render_template('admin/new_question.html', title="JCCoder - New Question", form=form, QuestionType=QuestionType)

@admin.route('/new/strand', methods=['GET', 'POST'])
@login_required
def new_strand():
    form = NewStrand()
    if form.validate_on_submit():
        strand = Strand(name=form.name.data)
        db.session.add(strand)
        return redirect(url_for('admin.all_strands'))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Strand", new_thing="Strand", form=form)

@admin.route('/new/module', methods=['GET', 'POST'])
@login_required
def new_module():
    form = NewModule()
    if form.validate_on_submit():
        number = 1
        if len(Module.query.all()) > 0:
            number = Module.query.all()[-1].number + 1
        module = Module(title=form.title.data, description=form.description.data, 
                        strand=Strand.query.get(form.strand.data), number=number)
        module.next_module_id = form.next_module.data
        if not form.next_module.data == 0:
            Module.query.get(form.next_module.data).prev_module = module
        else:
            module.next_module_id = None # MySQL doesn't like 0
        db.session.add(module)
        return redirect(url_for('admin.all_modules'))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Module", new_thing="Module", form=form)

@admin.route('/new/chapter', methods=['GET', 'POST'])
@login_required
def new_chapter():
    form = NewChapter()
    if form.validate_on_submit():
        chapter = Chapter(title=form.title.data, description=form.description.data,
                        module=Module.query.get(form.module.data))
        chapter.next_chapter_id = form.next_chapter.data
        if not form.next_chapter.data == 0:
            Chapter.query.get(form.next_chapter.data).prev_chapter = chapter
        else:
            chapter.next_chapter = None # MySQL doesn't like 0
        db.session.add(chapter)
        return redirect(url_for('admin.all_chapters'))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Chapter", new_thing="Chapter", form=form)

@admin.route('/new/lesson', methods=['GET', 'POST'])
@login_required
def new_lesson():
    form = NewLesson()
    if form.validate_on_submit():
        lesson = Lesson(title=form.title.data, overview=form.overview.data, icon=form.icon.data,
                        chapter=Chapter.query.get(form.chapter.data))
        number = 1
        lessons_in_chapter = Lesson.query.filter_by(chapter=lesson.chapter).all()
        if len(lessons_in_chapter) > 1:
            number = lessons_in_chapter[-2].sequence_no + 1
        lesson.sequence_no = number
        lesson.next_lesson_id = form.next_lesson.data
        if not form.next_lesson.data == 0:
            Lesson.query.get(form.next_lesson.data).prev_lesson = lesson
        else:
            lesson.next_lesson = None # MySQL doesn't like 0
        db.session.add(lesson)
        return redirect(url_for('admin.all_lessons'))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Lesson", new_thing="Lesson", form=form)

@admin.route('/new/skill', methods=['GET', 'POST'])
@login_required
def new_skill():
    form = NewSkill()
    if form.validate_on_submit():
        skill = Skill(description=form.description.data,
                                           lesson=Lesson.query.get(form.lesson.data))
        db.session.add(skill)
        return redirect(url_for('admin.all_skills'))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Skill", new_thing="Skill", form=form)

@admin.route('/new/quiz', methods=['GET', 'POST'])
@login_required
def new_quiz():
    form = NewQuiz()
    if form.validate_on_submit():
        skills = parseSkillIDs(form.tested_skills.data)
        quiz = Quiz(description=form.description.data, lesson=Lesson.query.get(form.lesson.data), tested_skills=skills)
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
    if data.get('prev_step_id'):
        prev_step = ProjectStep.query.get(data.get('prev_step_id'))
    else:
        prev_step = None
    if data.get('editing'):
        step = ProjectStep.query.get(data.get('step_id'))
        if not step:
            abort(400)
        step.title = data.get('title')
        step.content = data.get('content')
        step.prev_step = prev_step
        db.session.add(step)
        db.session.commit()
    else:
        step = ProjectStep(title=data.get('title'), content=data.get('content'), project_id=data.get('project_id'), prev_step=prev_step)
        db.session.add(step)
        db.session.commit()
    step_id = step.id
    return jsonify(success=True, stepID=step_id)

@admin.route('/all/strand/')
@login_required
def all_strands():
    strands = Strand.query.all()
    return render_template('admin/all_something.html', title="JCCoder - All Strands", list_items="Strands", items=strands)

@admin.route('/all/module/')
@login_required
def all_modules():
    modules = Module.query.all()
    groups = Strand.query.all()
    return render_template('admin/all_something.html', title="JCCoder - All Modules", list_items="Modules", items=modules, groups=groups)

@admin.route('/all/chapter/')
@login_required
def all_chapters():
    chapters = Chapter.query.all()
    groups = []
    for strand in Strand.query.all():
        groups.extend(strand.all_ordered_children())
    return render_template('admin/all_something.html', title="JCCoder - All Chapters", list_items="Chapters", items=chapters, groups=groups)

@admin.route('/all/lesson/')
@login_required
def all_lessons():
    lessons = Lesson.query.all()
    groups = []
    for strand in Strand.query.all():
        for module in strand.all_ordered_children():
            groups.extend(module.all_ordered_children())
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
    for strand in Strand.query.all():
        for module in strand.all_ordered_children():
            for lesson in module.all_ordered_children():
                groups.extend(lesson.all_ordered_children())
    return render_template('admin/all_something.html', title="JCCoder - All Pages", list_items="Pages", items=pages, groups=groups)

@admin.route('/all/skill/')
@login_required
def all_skills():
    skills = Skill.query.all()
    groups = []
    for strand in Strand.query.all():
        for module in strand.all_ordered_children():
            for lesson in module.all_ordered_children():
                groups.extend(lesson.all_ordered_children())
    return render_template('admin/all_something.html', title="JCCoder - All Skills", list_items="Skills", items=skills, groups=groups)

@admin.route('/all/project/')
@login_required
def all_projects():
    projects = Project.query.all()
    groups = []
    for strand in Strand.query.all():
        for module in strand.all_ordered_children():
            for lesson in module.all_ordered_children():
                groups.extend(lesson.all_ordered_children())
    return render_template('admin/all_something.html', title="JCCoder - All Projects", list_items="Projects", items=projects, groups=groups)

@admin.route('/all/module/<int:id>')
@login_required
def strands_modules(id):
    strand = Strand.query.get_or_404(id)
    modules = strand.all_ordered_children()
    return render_template('admin/somethings_things.html', title="JCCoder - All Modules in Strand " + strand.name, owner_of_things="Strand", thing_type="Modules", things=modules, owner=strand)

@admin.route('/all/chapter/<int:id>')
@login_required
def modules_chapters(id):
    module = Module.query.get_or_404(id)
    chapters = module.all_ordered_children()
    return render_template('admin/somethings_things.html', title="JCCoder - All Chapters in Module " + module.title, owner_of_things="Module", thing_type="Chapters", things=chapters, owner=module)

@admin.route('/all/lesson/<int:id>')
@login_required
def chapters_lessons(id):
    chapter = Chapter.query.get_or_404(id)
    lessons = chapter.all_ordered_children()
    return render_template('admin/somethings_things.html', title="JCCoder - All Lessons in Chapter " + chapter.title, owner_of_things="Chapter", thing_type="Lessons", things=lessons, owner=chapter)

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
    return render_template('admin/somethings_things.html', title="JCCoder - All Questions in Quiz (in lesson: " + quiz.lesson.title + ")", owner_of_things="Quiz", thing_type="Questions", things=questions, owner=quiz)

@admin.route('/edit/strand/<int:id>', methods=["GET", "POST"])
@login_required
def edit_strand(id):
    strand = Strand.query.get_or_404(id)
    form = NewStrand()
    if form.validate_on_submit():
        strand.name = form.name.data
        db.session.add(strand)
        return redirect(url_for('.all_strands'))
    form.name.data = strand.name
    return render_template('admin/edit_strand.html', title="JCCoder - Edit Strand " + strand.name, form=form, strand=strand)

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
            module.next_module_id = None # MySQL doesn't like 0
        db.session.add(module)
        return redirect(url_for('.all_modules'))
    form.title.data = module.title
    form.description.data = module.description
    form.strand.data = module.strand_id
    try:
        form.next_module.data = module.next_module_id
    except:
        form.next_module.data = 0
    return render_template('admin/edit_not_learn_out_strand.html', title="JCCoder - Edit Module " + module.title, form=form, thing=module)

@admin.route('/edit/chapter/<int:id>', methods=["GET", "POST"])
@login_required
def edit_chapter(id):
    chapter = Chapter.query.get_or_404(id)
    form = NewChapter()
    if form.validate_on_submit():
        chapter.title = form.title.data
        chapter.description = form.description.data
        chapter.module_id = form.module.data
        chapter.next_chapter_id = form.next_chapter.data
        if not form.next_chapter.data == 0:
            Chapter.query.get(form.next_chapter.data).prev_chapter = chapter
        else:
            chapter.next_chapter = None # MySQL doesn't like 0
        db.session.add(chapter)
        return redirect(url_for('.all_chapters'))
    form.title.data = chapter.title
    form.description.data = chapter.description
    form.module.data = chapter.module_id
    try:
        form.next_chapter.data = chapter.next_chapter_id
    except:
        form.next_chapter.data = 0
    return render_template('admin/edit_not_learn_out_strand.html', title="JCCoder - Edit Chapter " + chapter.title, form=form, thing=chapter)

@admin.route('/edit/lesson/<int:id>', methods=["GET", "POST"])
@login_required
def edit_lesson(id):
    lesson = Lesson.query.get_or_404(id)
    form = NewLesson()
    if form.validate_on_submit():
        lesson.title = form.title.data
        lesson.overview = form.overview.data
        lesson.icon = form.icon.data
        lesson.chapter_id = form.chapter.data
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
    form.chapter.data = lesson.chapter_id
    try:
        form.next_lesson.data = lesson.next_lesson_id
    except:
        form.next_lesson.data = 0
    return render_template('admin/edit_not_learn_out_strand.html', title="JCCoder - Edit Lesson " + lesson.title, form=form, thing=lesson)

@admin.route('/edit/lesson/<int:id>/content', methods=["GET", "POST"])
@login_required
def edit_lesson_content(id):
    lesson = Lesson.query.get_or_404(id)
    form = EditLessonContent()
    return render_template('admin/edit_lesson_content.html', title="JCCoder - Edit Lesson " + lesson.title + "'s Content", form=form,lesson=lesson)

@admin.route('/edit/skill/<int:id>', methods=["GET", "POST"])
@login_required
def edit_skill(id):
    skill = Skill.query.get_or_404(id)
    form = NewSkill()
    if form.validate_on_submit():
        skill.description = form.description.data
        skill.lesson_id = form.lesson.data
        db.session.add(skill)
        return redirect(url_for('.all_skills'))
    form.description.data = skill.description
    form.lesson.data = skill.lesson_id
    return render_template('admin/edit_skill.html', title="JCCoder - Edit Skill " + skill.description, form=form, skill=skill)

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
    return render_template('admin/edit_not_learn_out_strand.html', title="JCCoder - Edit Glossary " + glossary.title, form=form, thing=glossary)

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
    return render_template('admin/edit_not_learn_out_strand.html', title="JCCoder - Edit Glossary " + page.title, form=form, thing=page)

@admin.route('/edit/quiz/<int:id>', methods=["GET", "POST"])
@login_required
def edit_quiz(id):
    quiz = Quiz.query.get_or_404(id)
    form = NewQuiz()
    if form.validate_on_submit():
        quiz.description = form.description.data
        quiz.tested_skills = parseSkillIDs(form.tested_skills.data)
        quiz.lesson_id = form.lesson.data
        db.session.add(quiz)
        return redirect(url_for('.all_quizzes'))
    form.description.data = quiz.description
    form.tested_skills.data = unparseSkillObjects(quiz)
    form.lesson.data = quiz.lesson_id
    return render_template('admin/edit_quiz.html', title="JCCoder - Edit Quiz in Lesson " + quiz.lesson.title, form=form, quiz=quiz)

@admin.route('/edit/question/<int:id>', methods=["GET", "POST"])
@login_required
def edit_question(id):
    question = Question.query.get_or_404(id)
    form = NewQuestion()
    if form.validate_on_submit():
        question.question_type_id = form.type.data
        question.text = form.text.data
        question.max_attempts = form.max_attempts.data
        question.solution = form.solution.data
        if question.question_type_id == QuestionType.query.filter_by(code='C').first().id:
            question.answer.first().option_id = question.options.all()[int(form.answer.data) - 1].id
        else:
            question.answer.first().option.text = form.answer.data

        for i, hint_text in enumerate(form.hints.data.split('::sep::'), 1):
            hint_text = hint_text.strip()   # Remove extra whitespace such as the newline character
            existing_hint = Hint.query.filter_by(hint_no=i, question_id=question.id).first()
            if not existing_hint:
                hint = Hint(text=hint_text, hint_no=i, question_id=question.id)
                db.session.add(hint)
            elif existing_hint.text != hint_text:
                existing_hint.text = hint_text
                db.session.add(existing_hint)
        
        question.quiz_id = form.quiz.data
        db.session.add(question)
        return redirect(url_for('.all_questions'))
    form.type.data = question.question_type_id
    form.text.data = question.text

    options = question.options.all()
    for i, option in enumerate(options):
        options[i] = option.text
    if question.question_type_id == QuestionType.query.filter_by(code='C').first().id:
        form.answer.data = options.index(question.correct_answer()) + 1
    else:
        form.answer.data = question.correct_answer()

    hint_text = ""
    for hint in question.hints:
        hint_text += hint.text + "\n::sep::\n"
    form.hints.data = hint_text[:-8] # [:-8] gets rid of extra ::sep:: at the end (the 8th char is a newline)
    form.max_attempts.data = question.max_attempts
    form.quiz.data = question.quiz_id
    form.solution.data = question.solution

    if question.question_type_id == QuestionType.query.filter_by(code='S').first().id:
        options = [None]

    options = json.dumps(options)
    return render_template('admin/edit_question.html', title="JCCoder - Edit Question", form=form, question=question, options=options)

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

    preview_html = """<div class="card">
    <div class="card-body">
        {0}
    </div>
</div>""".format(customTagMarkdown(description))
    
    for step in steps:
        preview_html += """<h3 class="text-success mt-4">{0}</h3>
<div class="card">
    <div class="card-body">
        {1}
    </div>
</div>""".format(step.get('title', 'None'), customTagMarkdown(step.get('content', 'None')))

    return jsonify(success=True, previewHTML=preview_html)