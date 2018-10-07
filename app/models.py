from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from datetime import datetime
from markdown import markdown
from app import db, login
import bleach, re

def customTagMarkdown(original_mardown, extensions=None):
    lines = []
    for line in original_mardown.split('\n'):
        if ':video::' in line:
            arguments = line.split('::')
            video = """<div class="row" style="margin-bottom:20px">
    <div class="{0}">
        <div class="embed-responsive embed-responsive-{1}">
            <iframe class="embed-responsive-item" src="{2}" allowfullscreen></iframe>
        </div>
    </div>
</div>""".format(arguments[1], arguments[2], arguments[3])
            line = video
        lines.append(line)
    finished_markdown = '\n'.join(lines)
    
    html = markdown(finished_markdown, output_format='html', extensions=extensions or [])
    return html

post_tags = db.Table("post_tags",
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id')),
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id'))
)

class Permission:
    ASK_QUESTIONS = 0x01
    ANSWER_QUESTIONS = 0x02
    SAVE_HISTORY = 0x04
    MANAGE_CLASS = 0x08
    MODERATE_QUESTIONS = 0x10
    ADMINISTRATOR = 0xff

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'Student': (Permission.ASK_QUESTIONS |
                        Permission.ANSWER_QUESTIONS |
                        Permission.SAVE_HISTORY, True),
            'Teacher': (Permission.ASK_QUESTIONS |
                        Permission.ANSWER_QUESTIONS |
                        Permission.SAVE_HISTORY |
                        Permission.MANAGE_CLASS, False),
            'Moderator': (Permission.ASK_QUESTIONS |
                          Permission.ANSWER_QUESTIONS |
                          Permission.SAVE_HISTORY |
                          Permission.MODERATE_QUESTIONS, False),
            'Administrator': (0xff, False)
        }

        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    password_hash = db.Column(db.String(128))
    email = db.Column(db.String(120), unique=True)
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    under_13 = db.Column(db.Boolean, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    answers = db.relationship('UserAnswer', backref='user', lazy='dynamic')
    page_questions = db.relationship('PageQuestion', backref='author', lazy='dynamic')
    page_answers = db.relationship('PageAnswer', backref='author', lazy='dynamic')

    @property
    def password(self):
        raise AttributeError('Password is a write-only attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            self.role = Role.query.filter_by(default=True).first()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.can(Permission.ADMINISTRATOR)
    
    def can(self, permissions):
        return self.role is not None and (self.role.permissions & permissions) == permissions

    def __repr__(self):
        return '<User {}>'.format(self.username)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

    
class AnonymousUser(AnonymousUserMixin):
    id = 0

    def can(self, permissions):
        return False

    def is_admin(self):
        return False

login.anonymous_user = AnonymousUser

class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))

    def __repr__(self):
        return 'Tag <%s>' % self.name

class Post(db.Model):
    __tablename__ = 'posts'
    __searchable__ = ['title', 'body']

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    summary = db.Column(db.Text)
    summary_html = db.Column(db.Text)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    published = db.Column(db.Boolean, default=True)
    title = db.Column(db.String(64))
    tags = db.relationship('Tag', secondary=post_tags,
                           backref=db.backref('posts', lazy='dynamic'))

    @staticmethod
    def body_changed(target, value, oldvalue, initiator):
        target.body_html = markdown(value, output_format='html')

    @staticmethod
    def summary_changed(target, value, oldvalue, initiator):
        target.summary_html = markdown(value, output_format='html')

db.event.listen(Post.body, 'set', Post.body_changed)
db.event.listen(Post.summary, 'set', Post.summary_changed)

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    description = db.Column(db.Text)
    description_html = db.Column(db.Text)
    thumbnail = db.Column(db.String(100))
    status = db.Column(db.Boolean, default=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))
    steps = db.relationship('ProjectStep', backref='project', lazy='dynamic')

    @staticmethod
    def description_changed(target, value, oldvalue, initiator):
        target.description_html = customTagMarkdown(value, output_format='html')

    def what_model(self):
        return "Project"

db.event.listen(Project.description, 'set', Project.description_changed)

class ProjectStep(db.Model):
    __tablename__ = 'projectsteps'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    content = db.Column(db.Text)
    content_html = db.Column(db.Text)
    next_step_id = db.Column(db.Integer, db.ForeignKey('projectsteps.id'), nullable=True)
    next_step = db.relationship('ProjectStep', backref=db.backref('prev_step', uselist=False), remote_side=[id], uselist=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))

    @staticmethod
    def content_changed(target, value, oldvalue, initiator):
        target.content_html = customTagMarkdown(value)

db.event.listen(ProjectStep.content, 'set', ProjectStep.content_changed)

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text)
    html = db.Column(db.Text)
    image_url = db.Column(db.Text)
    max_attempts = db.Column(db.Integer)
    question_type_id = db.Column(db.Integer, db.ForeignKey('questiontypes.id'))
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'))
    options = db.relationship('QuestionOption', backref='question', lazy='dynamic')
    answer = db.relationship('QuestionAnswer', backref='question', lazy='dynamic')
    user_answer = db.relationship('UserAnswer', backref='question', lazy='dynamic')

    def what_model(self):
        return "Question"
    
    def show(self):
        return (self.html or self.text)

    def check(self, answer):
        if answer == self.correct_answer():
            return 1
        else:
            return 0
    
    def correct_answer(self):
        return self.answer.first().option.text

    def generate_new_html(target, value, oldvalue, initiator):
        # If the new question page is going to open to regular users
        # allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
        #                 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
        #                 'h1', 'h2', 'h3', 'p', 'img', 'footer', 'div', 'span']
        # target.html = bleach.linkify(bleach.clean(
        #     markdown(value, output_format='html'),
        #     tags=allowed_tags))
        # Otherwise:
        target.html = markdown(value, output_format='html')

    def __repr__(self):
        return '<Question> {0} Answer: {1}'.format(self.text, self.correct_answer())

db.event.listen(Question.text, 'set', Question.generate_new_html)

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'))
    questions = db.relationship('Question', backref='quiz', lazy='dynamic')

    def what_model(self):
        return "Quiz"

    def model_one_lower(self):
        return "Questions"

class Glossary(db.Model):
    __tablename__ = 'glossaries'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    text = db.Column(db.Text)
    html = db.Column(db.Text)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))

    def what_model(self):
        return "Glossary"

    def generate_new_html(target, value, oldvalue, initiator):
        # If the new glossary page is going to open to regular users
        # allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
        #                 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
        #                 'h1', 'h2', 'h3', 'p', 'img', 'footer', 'div', 'span']
        # target.html = bleach.linkify(bleach.clean(
        #     markdown(value, output_format='html'),
        #     tags=allowed_tags))
        # Otherwise:
        target.html = bleach.linkify(markdown(value, output_format='html'))
    
    def __repr__(self):
        return '<Glossary> {0}'.format(self.title)

db.event.listen(Glossary.text, 'set', Glossary.generate_new_html)

class QuestionOption(db.Model):
    __tablename__ = 'questionoptions'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))
    answers = db.relationship('QuestionAnswer', backref='option', lazy='dynamic')

    def __repr__(self):
        return self.text

class QuestionType(db.Model):
    __tablename__ = 'questiontypes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(1))
    description = db.Column(db.Text)
    questions = db.relationship('Question', backref='question_type', lazy='dynamic')

class QuestionAnswer(db.Model):
    __tablename__ = 'questionanswers'
    id = db.Column(db.Integer, primary_key=True)
    option_id = db.Column(db.Integer, db.ForeignKey('questionoptions.id'))
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))

    def __repr__(self):
        return self.option

class UserAnswer(db.Model):
    __tablename__ = 'useranswers'
    id = db.Column(db.Integer, primary_key=True)
    attempt_no = db.Column(db.Integer)
    datetime = db.Column(db.DateTime, default=datetime.utcnow)
    keyed_answer = db.Column(db.Text)
    answer_status_id = db.Column(db.Integer, db.ForeignKey('answerstatus.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))

class AnswerStatus(db.Model):
    __tablename__ = 'answerstatus'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(64))
    user_answer = db.relationship('UserAnswer', backref='answer_status', lazy='dynamic')

class Strand(db.Model):
    __tablename__ = 'strands'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    modules = db.relationship('Module', backref='strand', lazy='dynamic')

    def __repr__(self):
        return '<Strand %s>' % self.name

    def what_model(self):
        return "Strand"

    def model_one_lower(self):
        return "Modules"

    def all_ordered_children(self):
        ordered = []
        if len(self.modules.all()) > 0:
            def append_module(module):
                ordered.append(module)
                if module.next_module:
                    append_module(module.next_module)
            append_module(self.modules.filter_by(prev_module=None).first())
        return ordered

class Module(db.Model):
    __tablename__ = 'modules'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64))
    description = db.Column(db.Text)
    next_module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=True)
    next_module = db.relationship('Module', backref=db.backref('prev_module', uselist=False), remote_side=[id], uselist=False)
    number = db.Column(db.Integer)
    strand_id = db.Column(db.Integer, db.ForeignKey('strands.id'))
    chapters = db.relationship('Chapter', backref='module', lazy='dynamic')

    def __repr__(self):
        return '<Module %s>' % self.title

    def what_model(self):
        return "Module"

    def model_one_lower(self):
        return "Chapters"

    def all_ordered_children(self):
        ordered = []
        if len(self.chapters.all()) > 0:
            def append_chapter(chapter):
                ordered.append(chapter)
                if chapter.next_chapter:
                    append_chapter(chapter.next_chapter)
            append_chapter(self.chapters.filter_by(prev_chapter=None).first())
        return ordered

class Chapter(db.Model):
    __tablename__ = 'chapters'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64))
    description = db.Column(db.Text)
    icon = db.Column(db.Text)
    next_chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id'), nullable=True)
    next_chapter = db.relationship('Chapter', backref=db.backref('prev_chapter', uselist=False), remote_side=[id], uselist=False)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'))
    lessons = db.relationship('Lesson', backref='chapter', lazy='dynamic')

    def __repr__(self):
        return '<Chapter %s>' % self.title

    def what_model(self):
        return "Chapter"

    def model_one_lower(self):
        return "Lessons"

    def all_ordered_children(self):
        ordered = []
        if len(self.lessons.all()) > 0:
            def append_lesson(lesson):
                ordered.append(lesson)
                if lesson.next_lesson:
                    append_lesson(lesson.next_lesson)
            append_lesson(self.lessons.filter_by(prev_lesson=None).first())
        return ordered

class Lesson(db.Model):
    __tablename__ = 'lessons'
    __searchable__ = ['title', 'overview']

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64))
    overview = db.Column(db.Text)
    overview_html = db.Column(db.Text)
    sequence_no = db.Column(db.Integer)
    icon = db.Column(db.Text)
    next_lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=True)
    next_lesson = db.relationship('Lesson', backref=db.backref('prev_lesson', uselist=False), remote_side=[id], uselist=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id'))
    learning_outcomes = db.relationship('LearningOutcome', backref='lesson', lazy='dynamic')
    pages = db.relationship('Page', backref='lesson', lazy='dynamic')
    projects = db.relationship('Project', backref='lesson', lazy='dynamic')

    def __repr__(self):
        return '<Lesson %s>' % self.title

    def what_model(self):
        return "Lesson"

    def model_one_lower(self):
        return "Pages"
    
    def generate_new_html(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p', 'img', 'footer', 'div', 'span']
        target.overview_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, attributes=['class', 'id', 'href', 'alt', 'title', 'style', 'src']))

    def all_ordered_children(self):
        ordered = []
        if len(self.pages.all()) > 0:
            def append_page(page):
                ordered.append(page)
                if page.next_page:
                    append_page(page.next_page)
            append_page(self.pages.filter_by(prev_page=None).first())
        return ordered

db.event.listen(Lesson.overview, 'set', Lesson.generate_new_html)

class Page(db.Model):
    __tablename__ = 'pages'
    __searchable__ = ['title', 'text']

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    text = db.Column(db.Text)
    html = db.Column(db.Text)
    page_type_id = db.Column(db.Integer, db.ForeignKey('pagetypes.id'))
    # prev_page_id = db.Column(db.Integer, db.ForeignKey('pages.id'), nullable=True)
    next_page_id = db.Column(db.Integer, db.ForeignKey('pages.id'), nullable=True)
    next_page = db.relationship('Page', backref=db.backref('prev_page', uselist=False), remote_side=[id], uselist=False)
    questions = db.relationship('PageQuestion', backref='page', lazy='dynamic')
    quiz = db.relationship('Quiz', backref='page', uselist=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))

    def what_model(self):
        return "Page"

    def generate_new_html(target, value, oldvalue, initiator):
        # allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
        #                 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
        #                 'h1', 'h2', 'h3', 'p', 'img', 'footer', 'div', 'span', 'iframe']
        
        if target.page_type.description == "Quiz":
            target.html = '<iframe src="{0}" width="100%" class="quiz" frameborder="0"></iframe>'.format(url_for('main.take_quiz', id=target.quiz.id))
        else:
            target.html = bleach.linkify(
                customTagMarkdown(value)
            )
    
    def __repr__(self):
        return '<Page %s>' % self.title

db.event.listen(Page.text, 'set', Page.generate_new_html)

class PageType(db.Model):
    __tablename__ = 'pagetypes'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(64))
    pages = db.relationship('Page', backref='page_type', lazy='dynamic')

    @staticmethod
    def insert_types():
        types = ['Article', 'Quiz', 'Glossary', 'Video']
        for page_type in types:
            if not PageType.query.filter_by(description=page_type).first():
                t = PageType(description=page_type)
                db.session.add(t)
        db.session.commit()

class PageQuestion(db.Model):
    __tablename__ = 'pagequestion'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    text = db.Column(db.Text)
    html = db.Column(db.Text)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'))
    answers = db.relationship('PageAnswer', backref='question', lazy='dynamic')

    def generate_new_html(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p', 'img', 'footer', 'div', 'span']
        target.html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, attributes=['class', 'id', 'href', 'alt', 'title', 'style', 'src']))

db.event.listen(PageQuestion.text, 'set', PageQuestion.generate_new_html)

class PageAnswer(db.Model):
    __tablename__ = 'pageanswers'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    text = db.Column(db.Text)
    html = db.Column(db.Text)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('pagequestion.id'))

    def generate_new_html(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p', 'img', 'footer', 'div', 'span']
        target.html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, attributes=['class', 'id', 'href', 'alt', 'title', 'style', 'src']))

db.event.listen(PageAnswer.text, 'set', PageAnswer.generate_new_html)

class LearningOutcome(db.Model):
    __tablename__ = 'learningoutcomes'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(64))
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))