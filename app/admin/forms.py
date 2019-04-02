from flask_wtf import FlaskForm
from wtforms import FileField, IntegerField, SelectMultipleField, PasswordField, RadioField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.widgets.html5 import NumberInput, URLInput
from wtforms.validators import DataRequired, Length, Optional
from ..models import QuestionType, Strand, Module, Chapter, Lesson, Quiz, Page, PageType, Skill

class NewQuestion(FlaskForm):
    def __init__(self, *args, **kwargs):
        super(NewQuestion, self).__init__(*args, **kwargs)
        self.type.choices = [(question_type.id, question_type.description)
                             for question_type in QuestionType.query.all()]
        self.quiz.choices = [(quiz.id, 'Quiz in lesson: {0}, Description: {1}'.format(quiz.lesson.title, quiz.description))
                             for quiz in Quiz.query.all()]

    type = SelectField('Question Type', validators=[DataRequired()], coerce=int)
    text = TextAreaField('Question', validators=[DataRequired()])
    options1 = StringField('Options', validators=[DataRequired()])
    answer = StringField('Answer (first option is 1, second option is 2, etc.)', validators=[DataRequired()])
    solution = TextAreaField('Solution Description', validators=[DataRequired()])
    hints = TextAreaField('Hints [seperate each hint with "::sep::" (without quotes)]', validators=[DataRequired()])
    max_attempts = IntegerField('Maximum attempts', widget=NumberInput(min=1, max=10), validators=[DataRequired()])
    quiz = SelectField('Quiz', coerce=int)
    submit = SubmitField('Submit Question')

class NewStrand(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(1, 64)])
    submit = SubmitField('Submit Changes')

class NewModule(FlaskForm):
    def __init__(self, *args, **kwargs):
        super(NewModule, self).__init__(*args, **kwargs)
        self.strand.choices = [(strand.id, strand.name)
                               for strand in Strand.query.all()]
        self.next_module.choices = [(0, '..........')]
        self.next_module.choices.extend([(module.id, module.title)
                                         for module in Module.query.all()])

    title = StringField('Title', validators=[DataRequired(), Length(1, 64)])
    description = TextAreaField('Description', validators=[DataRequired()])
    next_module = SelectField('Next Module', coerce=int)
    strand = SelectField('Strand', coerce=int)
    submit = SubmitField('Submit Changes')

class NewChapter(FlaskForm):
    def __init__(self, *args, **kwargs):
        super(NewChapter, self).__init__(*args, **kwargs)
        self.module.choices = [(module.id, module.title)
                               for module in Module.query.all()]
        self.next_chapter.choices = [(0, '..........')]
        self.next_chapter.choices.extend([(chapter.id, chapter.title)
                                         for chapter in Chapter.query.all()])
    
    title = StringField('Title', validators=[DataRequired(), Length(1, 64)])
    description = TextAreaField('Description', validators=[DataRequired()])
    next_chapter = SelectField('Next Chapter', coerce=int)
    module = SelectField('Module', coerce=int)
    submit = SubmitField('Submit Changes')

class NewLesson(FlaskForm):
    def __init__(self, *args, **kwargs):
        super(NewLesson, self).__init__(*args, **kwargs)
        self.chapter.choices = [(chapter.id, chapter.module.title + ' > ' + chapter.title)
                               for chapter in Chapter.query.all()]
        self.next_lesson.choices = [(0, '..........')]
        self.next_lesson.choices.extend([(lesson.id, lesson.title)
                                         for lesson in Lesson.query.all()])
    
    title = StringField('Title', validators=[DataRequired(), Length(1, 64)])
    overview = TextAreaField('Overview', validators=[DataRequired()])
    icon = StringField('Icon URL (don\'t forget the http://)', widget=URLInput(), validators=[DataRequired()], default="http://")
    next_lesson = SelectField('Next Lesson', coerce=int)
    chapter = SelectField('Chapter', coerce=int)
    markdown = "overview"
    submit = SubmitField('Submit Changes')

class EditLessonContent(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(1, 64)])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Submit Content')

class NewSkill(FlaskForm):
    def __init__(self, *args, **kwargs):
        super(NewSkill, self).__init__(*args, **kwargs)
        self.lesson.choices = [(lesson.id, lesson.chapter.module.title + ' > ' + lesson.chapter.title + ' > ' + lesson.title)
                               for lesson in Lesson.query.all()]

    description = TextAreaField('Description', validators=[DataRequired()])
    lesson = SelectField('Lesson', coerce=int)
    submit = SubmitField('Submit Changes')

class NewQuiz(FlaskForm):
    def __init__(self, *args, **kwargs):
        super(NewQuiz, self).__init__(*args, **kwargs)
        self.lesson.choices = [(lesson.id, lesson.chapter.module.title + ' > ' + lesson.chapter.title + ' > ' + lesson.title)
                               for lesson in Lesson.query.all()]
        self.tested_skills.choices = [(skill.id, skill.lesson.chapter.module.title + ' > '
                                + skill.lesson.chapter.title + ' > '
                                + skill.lesson.title + ' > '
                                + skill.description)
                                for skill in Skill.query.all()]

    description = TextAreaField('Description', validators=[DataRequired()])
    tested_skills = SelectMultipleField('Skills Tested', coerce=int)
    lesson = SelectField('Lesson', coerce=int)
    submit = SubmitField('Submit Quiz')

class NewGlossary(FlaskForm):
    def __init__(self, *args, **kwargs):
        super(NewGlossary, self).__init__(*args, **kwargs)
        self.lesson.choices = [(lesson.id, lesson.chapter.module.title + ' > ' + lesson.chapter.title + ' > ' + lesson.title)
                               for lesson in Lesson.query.all()]

    title = StringField('Title', validators=[DataRequired(), Length(1, 100)])
    content = TextAreaField('Content', validators=[DataRequired()])
    lesson = SelectField('Lesson', coerce=int)
    markdown = "content"
    submit = SubmitField('Submit Glossary')

class NewPage(FlaskForm):
    def __init__(self, *args, **kwargs):
        super(NewPage, self).__init__(*args, **kwargs)
        self.next_page.choices = [(0, '..........')]
        self.lesson.choices = [(lesson.id, lesson.chapter.module.title + ' > ' + lesson.chapter.title + ' > ' + lesson.title)
                               for lesson in Lesson.query.all()]
        self.next_page.choices.extend([(page.id, page.title)
                               for page in Page.query.all()])
        self.page_type.choices = [(page_type.id, page_type.description)
                                  for page_type in PageType.query.all()]
    
    page_type = SelectField('Type', coerce=int)
    title = StringField('Title', validators=[DataRequired(), Length(1, 100)])
    content = TextAreaField('Content', validators=[DataRequired()])
    next_page = SelectField(coerce=int, validators=[Optional()])
    lesson = SelectField(coerce=int)
    markdown = "content"
    submit = SubmitField('Submit Page')

class NewProject(FlaskForm):
    def __init__(self, *args, **kwargs):
        super(NewProject, self).__init__(*args, **kwargs)
        self.lesson.choices = [(lesson.id, lesson.chapter.module.title + ' > ' + lesson.chapter.title + ' > ' + lesson.title)
                               for lesson in Lesson.query.all()]
        self.status.choices = [(0, 'Draft'), (1, 'Final')]
    
    status = RadioField('Status', coerce=int, default=0)

    title = StringField('Title', validators=[DataRequired(), Length(1, 150, 'Title must be less than 150 characters.')])
    description = TextAreaField('Description', validators=[DataRequired()])
    thumbnail = StringField('Thumbnail', widget=URLInput(), validators=[DataRequired(),
                                                                        Length(1, 500, 'URL must be less than 500 characters.')])
    lesson = SelectField(coerce=int)

    step_title = StringField('Step Title', validators=[Length(max=150)])
    step_content = TextAreaField('Step Content')

    submit = SubmitField('Submit Project')
