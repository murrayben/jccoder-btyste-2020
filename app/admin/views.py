"""admin/views.py

Views for the admin interface.
"""

import json

from flask import (abort, flash, jsonify, redirect, render_template, request,
                   session, url_for)
from flask_login import current_user, login_required

from .. import db
from ..models import (AnswerStatus, Chapter, Glossary, Hint, Lesson, Module,
                      Page, PageType, ProblemMistake, Project, ProjectStep,
                      Question, QuestionAnswer, QuestionOption, QuestionType,
                      Quiz, Skill, Strand, UserAnswer, customTagMarkdown)
from . import admin
from .forms import (EditLessonContent, NewChapter, NewGlossary, NewLesson,
                    NewModule, NewPage, NewProject, NewQuestion, NewQuiz,
                    NewSkill, NewStrand)


@admin.before_request
def check_for_admin():
    """Checks if the current user is admin or it returns a 403 code."""
    if not current_user.is_authenticated or not current_user.is_admin():
        abort(403)

def parseSkillIDs(ids):
    """Turns a list of Skill ids into a list of Skill object."""
    return_list = []

    for i in ids:
        skill = Skill.query.filter_by(id=i).first()
        return_list.append(skill)

    return return_list

def unparseSkillObjects(quiz):
    """Turns a list of Skill objects into a list of Skill ids."""
    return_list = []

    for i in quiz.tested_skills:
        return_list.append(i.id)

    return return_list

@admin.route('/new/question', methods=['GET', 'POST'])
@login_required
def new_question():
    """View for adding a new question."""
    form = NewQuestion()
    if form.validate_on_submit():
        # Figuring out the type of the question
        question_type = form.type.data
        question_type_id = QuestionType.query.filter(
            QuestionType.id == question_type
        ).first().id
        question = Question(text=form.text.data,
            question_type_id=question_type_id,
            max_attempts=form.max_attempts.data, skill_id=form.skill.data
        )
        db.session.add(question)
        db.session.commit() # Must commit the question now because its
                            # id is needed for hints and options

        # Split hints box by "::sep::"
        for i, hint_text in enumerate(form.hints.data.split('::sep::'), 1):
            hint = Hint(
                text=hint_text.strip(), hint_no=i, question_id=question.id
            )
            db.session.add(hint)
        question_type = question.question_type

        # Initialise option and answer variables
        question_answer = None
        options = request.form.getlist('options1')  # Returns list
                                                    # containing all
                                                    # the options
        if question_type == QuestionType.query.filter_by(code='C').first():
            # Multiple Choice
            for option in options:
                db.session.add(
                    QuestionOption(text=option, question_id=question.id)
                )
            # Must commit as correct answer requires id of the option
            db.session.commit()
            
            # This subtracts 1 from form data because the field in the
            # form is not zero-index based
            correct_option = QuestionOption.query.filter_by(
                text=options[int(form.answer.data) - 1], question=question
                ).first()
            question_answer = QuestionAnswer(
                option=correct_option, question=question
            )
        elif question_type == QuestionType.query.filter_by(code='D').first():
            # Drag and drop
            for option in options:
                if option.startswith('img:'):
                    # Replaces "img:"
                    option = option[4:]
                    option = '<img src="{0}" class="img-fluid" />'.format(
                        option)
                db.session.add(
                    QuestionOption(text=option, question_id=question.id)
                )
            # Adds a dummy option that contains the answer in format
            # "row=button number row=button number..."
            question_answer_option = QuestionOption(
                text=form.answer.data, question_id=question.id
            )
            db.session.add(question_answer_option)
            db.session.commit()
            question_answer = QuestionAnswer(
                option=question_answer_option, question=question
                )
        elif question_type == QuestionType.query.filter_by(code='S').first():
            # Single Answer
            # Adds a dummy option so answer can be recorded
            question_option = QuestionOption(
                text=form.answer.data, question_id=question.id
            )
            db.session.add(question_option)
            db.session.commit()
            question_answer = QuestionAnswer(
                option=QuestionOption.query.filter_by(
                    text=form.answer.data
                ).first(), question=question
            )
        else:
            # Multiple Answer
            for option in options:
                db.session.add(
                    QuestionOption(text=option, question_id=question.id)
                )
            db.session.commit()

            # Splits the answer by commas
            for answer in form.answer.data.split(','):
                question_answer = QuestionAnswer(
                    option=QuestionOption.query.filter_by(
                        text=options[int(answer) - 1]
                    ).first(), question=question
                )
        db.session.add(question_answer)
        db.session.commit()
        return redirect(url_for('admin.edit_question', id=question.id))
    return render_template('admin/new_question.html', title="JCCoder - New Question", form=form, QuestionType=QuestionType)

@admin.route('/new/strand', methods=['GET', 'POST'])
@login_required
def new_strand():
    """View for a new strand."""
    form = NewStrand()
    if form.validate_on_submit():
        strand = Strand(name=form.name.data)
        db.session.add(strand)
        db.session.commit()
        return redirect(url_for('admin.edit_strand', id=strand.id))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Strand", new_thing="Strand", form=form)

@admin.route('/new/module', methods=['GET', 'POST'])
@login_required
def new_module():
    """View for a new module."""
    form = NewModule()
    if form.validate_on_submit():
        number = 1
        if len(Module.query.all()) > 0:
            number = Module.query.all()[-1].number + 1
        module = Module(title=form.title.data,
            description=form.description.data,
            strand=Strand.query.get(form.strand.data), number=number)
        module.next_module_id = form.next_module.data
        if not form.next_module.data == 0:
            Module.query.get(form.next_module.data).prev_module = module
        else:
            module.next_module_id = None # MySQL doesn't like 0
        db.session.add(module)
        db.session.commit()
        return redirect(url_for('admin.edit_module', id=module.id))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Module", new_thing="Module", form=form)

@admin.route('/new/chapter', methods=['GET', 'POST'])
@login_required
def new_chapter():
    """View for a new chapter."""
    form = NewChapter()
    if form.validate_on_submit():
        chapter = Chapter(
            title=form.title.data, name=form.name.data,
            image_url=form.image_url.data, description=form.description.data,
            module=Module.query.get(form.module.data))
        chapter.next_chapter_id = form.next_chapter.data
        if not form.next_chapter.data == 0:
            Chapter.query.get(form.next_chapter.data).prev_chapter = chapter
        else:
            chapter.next_chapter_id = None # MySQL doesn't like 0
        db.session.add(chapter)
        db.session.commit()
        return redirect(url_for('admin.edit_chapter', id=chapter.id))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Chapter", new_thing="Chapter", form=form)

@admin.route('/new/lesson', methods=['GET', 'POST'])
@login_required
def new_lesson():
    """View for a new lesson."""
    form = NewLesson()
    if form.validate_on_submit():
        lesson = Lesson(title=form.title.data, overview=form.overview.data,
                        icon=form.icon.data,
                        chapter=Chapter.query.get(form.chapter.data),
                        type_id=form.lesson_type.data)
        # Add sequence number
        number = 1
        lessons_in_chapter = Lesson.query.filter_by(chapter=lesson.chapter).all()
        if len(lessons_in_chapter) > 1:
            # There is an extra lesson because of the new lesson
            number = lessons_in_chapter[-2].sequence_no + 1
        lesson.sequence_no = number
        lesson.next_lesson_id = form.next_lesson.data
        if not form.next_lesson.data == 0:
            Lesson.query.get(form.next_lesson.data).prev_lesson = lesson
        else:
            lesson.next_lesson_id = None # MySQL doesn't like 0
        db.session.add(lesson)
        db.session.commit()
        return redirect(url_for('admin.edit_lesson', id=lesson.id))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Lesson", new_thing="Lesson", form=form)

@admin.route('/new/skill', methods=['GET', 'POST'])
@login_required
def new_skill():
    """View for a new skill."""
    form = NewSkill()
    if form.validate_on_submit():
        skill = Skill(description=form.description.data,
                      lesson=Lesson.query.get(form.lesson.data))
        db.session.add(skill)
        db.session.commit()
        return redirect(url_for('admin.edit_skill', id=skill.id))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Skill", new_thing="Skill", form=form)

@admin.route('/new/quiz', methods=['GET', 'POST'])
@login_required
def new_quiz():
    """View for a new quiz."""
    form = NewQuiz()
    if form.validate_on_submit():
        skills = parseSkillIDs(form.tested_skills.data)
        quiz = Quiz(description=form.description.data,
                    lesson=Lesson.query.get(form.lesson.data),
                    no_questions=form.no_questions.data, tested_skills=skills,
                    type_id=form.quiz_type.data)
        quiz.next_quiz_id = form.next_quiz.data
        if not form.next_quiz.data == 0:
            Quiz.query.get(form.next_quiz.data).prev_quiz = quiz
        else:
            quiz.next_quiz_id = None # MySQL doesn't like 0
        db.session.add(quiz)
        db.session.commit()
        return redirect(url_for('admin.edit_quiz', id=quiz.id))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Quiz", new_thing="Quiz", form=form)

@admin.route('/new/glossary', methods=['GET', 'POST'])
@login_required
def new_glossary():
    """View for a new glossary (not currently used)."""
    form = NewGlossary()
    if form.validate_on_submit():
        glossary = Glossary(title=form.title.data, text=form.content.data, lesson_id=form.lesson.data)
        db.session.add(glossary)
        db.session.commit()
        return redirect(url_for('admin.edit_glossary', id=glossary.id))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Glossary", new_thing="Glossary", form=form)

@admin.route('/new/page', methods=['GET', 'POST'])
@login_required
def new_page():
    """View for a new page."""
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
        db.session.commit()
        return redirect(url_for('admin.edit_page', id=page.id))
    return render_template('admin/admin_new_something.html', title="JCCoder - New Page", new_thing="Page", form=form)

@admin.route('/new/project', methods=['GET', 'POST'])
@login_required
def new_project():
    """View for a new project."""
    form = NewProject()
    if form.validate_on_submit():
        project = Project(title=form.title.data, description=form.description.data, thumbnail=form.thumbnail.data,
                              lesson_id=form.lesson.data, status=bool(form.status.data))
        db.session.add(project)
        db.session.commit()
        return redirect(url_for('main.index'))
    return render_template('admin/new_project.html', title="JCCoder - New Project", form=form)

@admin.route('/save-step', methods=['GET', 'POST'])
def save_step():
    """View for the AJAX call of saving a step or creating a new step."""
    if request.method == 'GET':
        abort(404)
    data = request.get_json()
    if data.get('prev_step_id'):
        # Gets the previous step
        prev_step = ProjectStep.query.get(data.get('prev_step_id'))
    else:
        prev_step = None
    if data.get('editing'):
        # Update existing fields if step has already been saved
        step = ProjectStep.query.get(data.get('step_id'))
        if not step:
            # Something wrong has occured!
            abort(400)
        step.title = data.get('title')
        step.content = data.get('content')
        step.prev_step = prev_step
        db.session.add(step)
        db.session.commit()
    else:
        step = ProjectStep(title=data.get('title'),
                           content=data.get('content'),
                           project_id=data.get('project_id'),
                           prev_step=prev_step)
        db.session.add(step)
        db.session.commit()
    step_id = step.id
    # Return JSON object
    return jsonify(success=True, stepID=step_id)

@admin.route('/all/strand/')
@login_required
def all_strands():
    """View for displaying all strands."""
    strands = Strand.query.all()
    return render_template('admin/all_something.html', title="JCCoder - All Strands", list_items="Strands", items=strands)

@admin.route('/all/module/')
@login_required
def all_modules():
    """View for displaying all modules."""
    modules = Module.query.all()
    groups = Strand.query.all() # For displaying the modules grouped by strand
    return render_template('admin/all_something.html', title="JCCoder - All Modules", list_items="Modules", items=modules, groups=groups)

@admin.route('/all/chapter/')
@login_required
def all_chapters():
    """View for displaying all chapters."""
    chapters = Chapter.query.all()
    groups = []
    for strand in Strand.query.all():
        groups.extend(strand.all_ordered_children())    # Gets modules
                                                        # in order
    return render_template('admin/all_something.html', title="JCCoder - All Chapters", list_items="Chapters", items=chapters, groups=groups)

@admin.route('/all/lesson/')
@login_required
def all_lessons():
    """View for displaying all lessons."""
    lessons = Lesson.query.all()
    groups = []
    for strand in Strand.query.all():
        for module in strand.all_ordered_children(): # Returns ordered
                                                     # modules
            # Returns ordered chapters
            groups.extend(module.all_ordered_children())
    return render_template('admin/all_something.html', title="JCCoder - All Lessons", list_items="Lessons", items=lessons, groups=groups)

@admin.route('/all/quiz/')
@login_required
def all_quizzes():
    """View for displaying all quizzes."""
    quizzes = Quiz.query.all()
    return render_template('admin/all_something.html', title="JCCoder - All Quizzes", list_items="Quizzes", items=quizzes)

@admin.route('/all/question/')
@login_required
def all_questions():
    """View for displaying all questions."""
    groups = Skill.query.all()
    questions = Question.query.all()
    return render_template('admin/all_something.html', title="JCCoder - All Questions", list_items="Questions", items=questions, groups=groups)

@admin.route('/all/glossary/')
@login_required
def all_glossaries():
    """View for displaying all glossaries (not currently used)."""
    glossaries = Glossary.query.all()
    return render_template('admin/all_something.html', title="JCCoder - All Glossaries", list_items="Glossaries", items=glossaries)

@admin.route('/all/page/')
@login_required
def all_pages():
    """View for displaying all pages."""
    pages = Page.query.all()
    groups = []

    # Similar technique used to order all the lessons for grouping the
    # pages by lesson
    for strand in Strand.query.all():
        for module in strand.all_ordered_children():
            for lesson in module.all_ordered_children():
                groups.extend(lesson.all_ordered_children())
    return render_template('admin/all_something.html', title="JCCoder - All Pages", list_items="Pages", items=pages, groups=groups)

@admin.route('/all/skill/')
@login_required
def all_skills():
    """View for displaying all skills."""
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
    """View for displaying all projects."""
    projects = Project.query.all()

    groups = []
    for strand in Strand.query.all():
        for module in strand.all_ordered_children():
            for lesson in module.all_ordered_children():
                groups.extend(lesson.all_ordered_children())
    return render_template('admin/all_something.html', title="JCCoder - All Projects", list_items="Projects", items=projects, groups=groups)

@admin.route('/all/problem-mistakes')
@login_required
def all_problem_mistakes():
    """View for displaying all mistakes reported in questions."""
    open_problem_mistakes = ProblemMistake.query.filter_by(is_closed=False) \
        .order_by(ProblemMistake.datetime.desc()).all()
    closed_problem_mistakes = ProblemMistake.query.filter_by(is_closed=True) \
        .order_by(ProblemMistake.datetime.desc()).all()
    return render_template('admin/all_problem_mistakes.html', title="JCCoder - All Problem Mistakes", open_problem_mistakes=open_problem_mistakes, closed_problem_mistakes=closed_problem_mistakes)

@admin.route('/all/problem-mistakes/open')
@login_required
def open_problem_mistakes():
    """View for displaying all open mistakes reported in questions."""
    problem_mistakes = ProblemMistake.query.filter_by(is_closed=False).order_by(ProblemMistake.datetime.desc()).all()
    return render_template('admin/all_open_problem_mistakes.html', title="JCCoder - All Open Problem Mistakes", problem_mistakes=problem_mistakes)

@admin.route('/all/module/<int:id>')
@login_required
def strands_modules(id):
    """View for displaying all modules in a certain strand."""
    strand = Strand.query.get_or_404(id)
    modules = strand.all_ordered_children()
    return render_template('admin/somethings_things.html', title="JCCoder - All Modules in Strand " + strand.name, owner_of_things="Strand", thing_type="Modules", things=modules, owner=strand)

@admin.route('/all/chapter/<int:id>')
@login_required
def modules_chapters(id):
    """View for displaying all chapters in a certain module."""
    module = Module.query.get_or_404(id)
    chapters = module.all_ordered_children()
    return render_template('admin/somethings_things.html', title="JCCoder - All Chapters in Module " + module.title, owner_of_things="Module", thing_type="Chapters", things=chapters, owner=module)

@admin.route('/all/lesson/<int:id>')
@login_required
def chapters_lessons(id):
    """View for displaying all lessons in a certain chapter."""
    chapter = Chapter.query.get_or_404(id)
    lessons = chapter.all_ordered_children()
    return render_template('admin/somethings_things.html', title="JCCoder - All Lessons in Chapter " + chapter.title, owner_of_things="Chapter", thing_type="Lessons", things=lessons, owner=chapter)

@admin.route('/all/pages/<int:id>')
@login_required
def lessons_pages(id):
    """View for displaying all pages in a certain lesson."""
    lesson = Lesson.query.get_or_404(id)
    pages = lesson.all_ordered_children()
    return render_template('admin/somethings_things.html', title="JCCoder - All Pages in Lesson " + lesson.title, owner_of_things="Lesson", thing_type="Pages", things=pages, owner=lesson)

@admin.route('/all/questions/<int:id>')
@login_required
def quizzes_questions(id):
    """View for displaying all questions in a certain skill.
    
    Called `quizzes_questions` because questions used to be part of
    quizzes and this views name was not changed for
    backwards-compatibility.
    """
    quiz = Quiz.query.get_or_404(id)
    questions = Question.query.filter(Question.skill_id == quiz.tested_skills.first().id).all()
    return render_template('admin/somethings_things.html', title="JCCoder - All Questions in Quiz (in lesson: " + quiz.lesson.title + ")", owner_of_things="Quiz", thing_type="Questions", things=questions, owner=quiz)

@admin.route('/edit/strand/<int:id>', methods=["GET", "POST"])
@login_required
def edit_strand(id):
    """View for editing a strand."""
    strand = Strand.query.get_or_404(id)
    form = NewStrand()
    if form.validate_on_submit():
        strand.name = form.name.data
        db.session.add(strand)
        db.session.commit()
        return redirect(url_for('.edit_strand', id=strand.id))
    form.name.data = strand.name
    return render_template('admin/edit_strand.html', title="JCCoder - Edit Strand " + strand.name, form=form, strand=strand)

@admin.route('/edit/module/<int:id>', methods=["GET", "POST"])
@login_required
def edit_module(id):
    """View for editing a module."""
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
        db.session.commit()
        return redirect(url_for('.edit_module', id=module.id))
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
    """View for editing a chapter."""
    chapter = Chapter.query.get_or_404(id)
    form = NewChapter()
    if form.validate_on_submit():
        chapter.title = form.title.data
        chapter.name = form.name.data
        chapter.image_url = form.image_url.data
        chapter.description = form.description.data
        chapter.module_id = form.module.data
        chapter.next_chapter_id = form.next_chapter.data
        if not form.next_chapter.data == 0:
            Chapter.query.get(form.next_chapter.data).prev_chapter = chapter
        else:
            chapter.next_chapter_id = None # MySQL doesn't like 0
        db.session.add(chapter)
        db.session.commit()
        return redirect(url_for('.edit_chapter', id=chapter.id))
    form.title.data = chapter.title
    form.name.data = chapter.name
    form.image_url.data = chapter.image_url
    form.description.data = chapter.description
    form.module.data = chapter.module_id
    try:
        form.next_chapter.data = chapter.next_chapter_id
    except:
        form.next_chapter.data = 0 # If field is NULL
    return render_template('admin/edit_not_learn_out_strand.html', title="JCCoder - Edit Chapter " + chapter.title, form=form, thing=chapter)

@admin.route('/edit/lesson/<int:id>', methods=["GET", "POST"])
@login_required
def edit_lesson(id):
    """View for editing a lesson."""
    lesson = Lesson.query.get_or_404(id)
    form = NewLesson()
    if form.validate_on_submit():
        lesson.title = form.title.data
        lesson.type_id = form.lesson_type.data
        lesson.overview = form.overview.data    
        lesson.icon = form.icon.data
        lesson.chapter_id = form.chapter.data
        lesson.next_lesson_id = form.next_lesson.data
        if not form.next_lesson.data == 0:
            next_lesson = Lesson.query.get(form.next_lesson.data)
            next_lesson.chapter_id = form.chapter.data
            next_lesson.prev_lesson = lesson
        else:
            lesson.next_lesson_id = None # MySQL doesn't like 0
        db.session.add(lesson)
        db.session.commit()
        return redirect(url_for('.edit_lesson', id=lesson.id))
    form.title.data = lesson.title
    form.lesson_type.data = lesson.type_id
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
    """View for editing content of a lesson (not currently used)."""
    lesson = Lesson.query.get_or_404(id)
    form = EditLessonContent()
    return render_template('admin/edit_lesson_content.html', title="JCCoder - Edit Lesson " + lesson.title + "'s Content", form=form,lesson=lesson)

@admin.route('/edit/skill/<int:id>', methods=["GET", "POST"])
@login_required
def edit_skill(id):
    """View for editing a skill."""
    skill = Skill.query.get_or_404(id)
    form = NewSkill()
    if form.validate_on_submit():
        skill.description = form.description.data
        skill.lesson_id = form.lesson.data
        db.session.add(skill)
        db.session.commit()
        return redirect(url_for('.edit_skill', id=skill.id))
    form.description.data = skill.description
    form.lesson.data = skill.lesson_id
    return render_template('admin/edit_skill.html', title="JCCoder - Edit Skill " + skill.description, form=form, skill=skill)

@admin.route('/edit/glossary/<int:id>', methods=["GET", "POST"])
@login_required
def edit_glossary(id):
    """View for editing a glossary (not currently used)."""
    glossary = Glossary.query.get_or_404(id)
    form = NewGlossary()
    if form.validate_on_submit():
        glossary.title = form.title.data
        glossary.text = form.content.data
        glossary.lesson_id = form.lesson.data
        db.session.add(glossary)
        db.session.commit()
        return redirect(url_for('.edit_glossary', id=glossary.id))
    form.title.data = glossary.title
    form.content.data = glossary.text
    form.lesson.data = glossary.lesson_id
    return render_template('admin/edit_not_learn_out_strand.html', title="JCCoder - Edit Glossary " + glossary.title, form=form, thing=glossary)

@admin.route('/edit/page/<int:id>', methods=["GET", "POST"])
@login_required
def edit_page(id):
    """View for editing a page."""
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
        db.session.commit()
        return redirect(url_for('.edit_page', id=page.id))
    form.page_type.data = page.page_type_id
    form.title.data = page.title
    form.content.data = page.text
    try:
        form.next_page.data = page.next_page_id
    except:
        form.next_page.data = 0
    form.lesson.data = page.lesson_id
    return render_template('admin/edit_not_learn_out_strand.html', title="JCCoder - Edit Page " + page.title, form=form, thing=page)

@admin.route('/edit/quiz/<int:id>', methods=["GET", "POST"])
@login_required
def edit_quiz(id):
    """View for editing a quiz."""
    quiz = Quiz.query.get_or_404(id)
    form = NewQuiz(editing=True)
    if form.validate_on_submit():
        quiz.type_id = form.quiz_type.data
        quiz.description = form.description.data
        quiz.no_questions = form.no_questions.data
        quiz.tested_skills = parseSkillIDs(form.tested_skills.data)
        if not form.next_quiz.data == 0:
            Quiz.query.get(form.next_quiz.data).prev_quiz = quiz
        else:
            quiz.next_quiz_id = None # MySQL doesn't like 0
        quiz.lesson_id = form.lesson.data
        db.session.add(quiz)
        db.session.commit()
        return redirect(url_for('.edit_quiz', id=quiz.id))
    form.quiz_type.data = quiz.type_id
    form.description.data = quiz.description
    form.no_questions.data = quiz.no_questions
    form.tested_skills.data = unparseSkillObjects(quiz)
    try:
        form.next_quiz.data = quiz.next_quiz_id
    except:
        form.next_quiz.data = 0
    form.lesson.data = quiz.lesson_id
    return render_template('admin/edit_quiz.html', title="JCCoder - Edit Quiz in Lesson " + quiz.lesson.title, form=form, quiz=quiz)

@admin.route('/edit/question/<int:id>', methods=["GET", "POST"])
@login_required
def edit_question(id):
    """View for editing a question."""
    question = Question.query.get_or_404(id)
    form = NewQuestion()
    if form.validate_on_submit():
        question.question_type_id = form.type.data
        question.text = form.text.data
        question.max_attempts = form.max_attempts.data

        # Options
        options = request.form.getlist('options1')  # Get the options
        original_options = question.options.all()   # Store the
                                                    # original options

        if question.question_type_id == QuestionType.query.filter_by(code='D').first().id:
            # To add the extra option (the option that is a dummy
            # option) that contains the answer
            options.append(question.correct_answer())

        # Adding and deleting options from DB
        for option in options:
            try:
                if option != original_options[0].text:
                    # Text has changed
                    original_options[0].text = option
                    db.session.add(original_options[0])

                # Remove option from original options
                del original_options[0]
            except IndexError:
                # No original options left, so add new ones
                new_option = QuestionOption(text=option, question_id=question.id)
                db.session.add(new_option)
        
        for option in original_options:
            # Any left over original options should be deleted
            db.session.delete(option)
        
        db.session.commit()

        # Modifying the correct answer
        if question.question_type_id == QuestionType.query.filter_by(code='C').first().id:
            # Multiple Choice
            question.answer.first().option_id = question.options.all()[
                int(form.answer.data) - 1].id
        elif question.question_type_id == QuestionType.query.filter_by(code='M').first().id:
            # Multiple Answer

            # Like options, get answer(s) and original answer(s)
            answers = [
                QuestionOption.query.get(question.options.all()[
                    int(answer) - 1].id)
                for answer in form.answer.data.split(',')
            ]
            original_answers = [answer.option for answer in question.answer.all()]

            # Sort the answers to see if they have changed. Order does
            # not matter unless it is a drag and drop question where it
            # is stored in a single field.
            if not sorted([option.id for option in answers]) == sorted([option.id for option in original_answers]):
                # If answers have changed:
                for answer in answers:
                    if answer in original_answers:
                        # Unchanged answers
                        original_answers.pop(original_answers.index(answer))
                    else:
                        # New answers
                        question_answer = QuestionAnswer(option=answer, question=question)
                        db.session.add(question_answer)
                for answer in original_answers:
                    # Delete remaining
                    db.session.delete(answer.answer)
        else:
            # Drag and drop / Single Answer just updates the dummy
            # option
            question.answer.first().option.text = form.answer.data

        # Hints
        for i, hint_text in enumerate(form.hints.data.split('::sep::'), 1):
            hint_text = hint_text.strip()   # Remove extra whitespace
                                            # such as the newline
                                            # character
            
            existing_hint = Hint.query.filter_by(hint_no=i, question_id=question.id).first()
            if not existing_hint:
                # New hint
                hint = Hint(text=hint_text, hint_no=i, question_id=question.id)
                db.session.add(hint)
            elif existing_hint.text != hint_text:
                # Changed hint
                existing_hint.text = hint_text
                db.session.add(existing_hint)
        
        question.skill_id = form.skill.data
        db.session.add(question)
        db.session.commit()
        return redirect(url_for('.edit_question', id=question.id))
    form.type.data = question.question_type_id
    form.text.data = question.text

    options = question.options.all()
    for i, option in enumerate(options):
        # Replace option objects with just their text
        options[i] = option.text

    # Correct answer
    if question.question_type_id == QuestionType.query.filter_by(code='C').first().id:
        form.answer.data = options.index(question.correct_answer()) + 1
    elif question.question_type_id == QuestionType.query.filter_by(code='M').first().id:
        # Joins a comma between different options
        form.answer.data = ", ".join([
            str(question.options.all().index(answer.option) + 1)
            for answer in question.answer.all()])
    else:
        # Drag and drop / Single Answer
        form.answer.data = question.correct_answer()

    hint_text = ""
    for hint in question.hints:
        # Add "::sep::" between different hints
        hint_text += hint.text + "\n::sep::\n"
    form.hints.data = hint_text[:-8]    # [:-8] gets rid of extra
                                        # ::sep:: at the end (the 8th
                                        # char is a newline)
    form.max_attempts.data = question.max_attempts
    form.skill.data = question.skill_id

    if question.question_type_id == QuestionType.query.filter_by(code='S').first().id:
        # Single Answer has no real options, set to a list to avoid
        # type errors
        options = [None]

    # Options passed to template as JSON
    options = json.dumps(options)
    return render_template('admin/edit_question.html', title="JCCoder - Edit Question", form=form, question=question, options=options)

@admin.route('/edit/project/<int:id>', methods=["GET", "POST"])
@login_required
def edit_project(id):
    """View for editing a project."""
    project = Project.query.get_or_404(id)
    form = NewProject()
    if form.validate_on_submit():
        project.status = bool(form.status.data)
        project.title = form.title.data
        project.description = form.description.data
        project.thumbnail = form.thumbnail.data
        project.lesson_id = form.lesson.data
        db.session.commit()
        return redirect(url_for('.edit_project', id=project.id))
    form.status.data = int(project.status)
    form.title.data = project.title
    form.description.data = project.description
    form.thumbnail.data = project.thumbnail
    form.lesson.data = project.lesson_id

    # Creates dictionary containing steps
    steps = {}
    for i, step in enumerate(project.steps, 1):
        steps['step_' + str(i)] = {}    # Initialises key
        step_dict = steps['step_' + str(i)]
        step_dict['id'] = step.id
        step_dict['title'] = step.title

        # Escapes double quote
        step_dict['content'] = step.content.replace('"', '\\"')
        
    # Escapes tab
    steps = json.dumps(steps, sort_keys=True).replace('    ', '\t')
    return render_template('admin/edit_project.html', title="JCCoder - Edit Project", form=form, project=project, steps=steps)

@admin.route('/problem-mistake/<int:id>')
def view_problem_mistake(id):
    """View for reading a reported mistake in a question."""
    problem_mistake = ProblemMistake.query.get_or_404(id)
    return render_template('admin/view_problem_mistake.html', title="JCCoder - View Problem Mistake", problem_mistake=problem_mistake)

@admin.route('/problem-mistake/<int:id>/close')
def close_problem_mistake(id):
    """View for closing a reported mistake in a question."""
    problem_mistake = ProblemMistake.query.get_or_404(id)
    problem_mistake.is_closed = True
    db.session.add(problem_mistake)
    flash('The issue is now closed.', 'success')
    return redirect(url_for('.open_problem_mistakes'))

@admin.route('/problem-mistake/<int:id>/reopen')
def reopen_problem_mistake(id):
    """View for reopening a reported mistake in a question."""
    problem_mistake = ProblemMistake.query.get_or_404(id)
    problem_mistake.is_closed = False
    db.session.add(problem_mistake)
    flash('The issue has been reopened.', 'danger')
    return redirect(url_for('.open_problem_mistakes'))

@admin.route('/preview-project', methods=["GET", "POST"])
def preview_project():
    """View for previewing a project (AJAX view)."""
    if request.method == "GET":
        abort(404)
    data = request.get_json()
    description = data['description']
    steps = data['steps']

    # Adds Bootstrap 4 card with description
    # (converted from HTML to markdown)
    preview_html = """<div class="card">
    <div class="card-body">
        {0}
    </div>
</div>""".format(customTagMarkdown(description))
    
    for step in steps:
        # Each of the steps adds a card with title and content
        # (converted to HTML from markdown)
        preview_html += """<h3 class="text-success mt-4">{0}</h3>
<div class="card">
    <div class="card-body">
        {1}
    </div>
</div>""".format(step.get('title', 'None'), customTagMarkdown(step.get('content', 'None')))

    return jsonify(success=True, previewHTML=preview_html)
