"""app/models.py

Module containing all the models in the application. Contains functions
for rendering markdown.
"""

import hashlib
import re
from datetime import datetime

import bleach
from flask import request, url_for
from flask_login import AnonymousUserMixin, UserMixin, current_user
from markdown import markdown
from mdx_gfm import GithubFlavoredMarkdownExtension
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login
from app.search import add_to_index, query_index, remove_from_index


def customTagMarkdown(original_mardown, object_id=None, extensions=None):
    """Renders markdown to HTML with modified custom Markdown syntax.
    
    Paramaters
    ----------
    original_markdown : str
        Markdown to be converted
    object_id : int
        ID of the model that is converting the markdown (default None)
    extensions : list
        Any additional extensions to be added to markdown converter
        (default None)

    Returns
    -------
    Converted HTML : str
    """

    # Initialising variables
    lines = []  # Markdown split into individual lines
    hint_counter = 0    # Stores what hint # the program is at
    collapse_counter = 1    # Stores what collapse no the program is at
    hints = []  # List of hints
    drag_and_drop_options = []  # Options in a drag and drop question
    recording_hint = False  # If a hint tag is in progress
    recording_collapse = False  # If a collapse tag is in progress
    recording_drag_and_drop = False # If a drag and drop tag is in progress
    add_line = True # If the program should add the current line to the
                    # end HTML
    for line in original_mardown.split('\n'):   # Splits markdown by newline
        if ':video::' in line:  # Video (also used for Scratch embed)
            # Splits arguments and creates HTML
            arguments = line.split('::')

            # arguments[0] = "video" from tag (not used)
            # arguments[1] = Bootstrap grid class
            # arguments[2] = Aspect ratio
            # arguments[3] = Embed link
            video = """<div class="row" style="margin-bottom:20px">
    <div class="{0}">
        <div class="embed-responsive embed-responsive-{1}">
            <iframe class="embed-responsive-item" src="{2}" allowfullscreen></iframe>
        </div>
    </div>
</div>""".format(arguments[1], arguments[2], arguments[3])

            # Replaces line with entire HTML
            line = video
        
        # Hints
        elif '::hints::' in line:   # Opening tag
            # Initial HTML (object_id ensures unique ids if two hint
            # objects occur within the same step)
            hint_html = """<div class="card border-info mb-3">
    <div class="card-header bg-info p-2">
        <h5 class="mb-0">
            <button class="btn btn-link text-white" data-toggle="collapse" data-target="#step{0}-hints" aria-expanded="true" aria-controls="step{0}-hints" style="text-decoration: none;">
                <i class="fas fa-2x fa-question-circle"></i>
                <span style="position: relative; bottom: 5px; left: 5px;">I need a hint</span>
            </button>
        </h5>
    </div>

    <div id="step{0}-hints" class="collapse">
        <div class="card-body">\n""".format(object_id)  # BS4 card
            add_line = False    # "::hints::" should not be added
        elif '::/hint::' in line:   # End of one individual hint
            # Stop recording HTML of the hint
            # "::hint::" should not be added to HTML
            recording_hint = False
            add_line = False
        elif recording_hint:    # Add current line to list containing
                                # all hints
            try:
                # Adding line to current hint
                hints[hint_counter - 1] = hints[hint_counter - 1] + '\n' + line
            except IndexError:
                # First line so index currently doesn't exist
                hints.append(line)
            # Do not add line to HTML as it will be added later
            add_line = False
        elif '::hint::' in line:    # Start recording HTML for a hint
            hint_counter += 1
            recording_hint = True
            add_line = False
        elif '::/hints::' in line:  # End of hints
            hint_counter = 1    # Is reused as loop counter
            # Put everything together

            # BS4 navigation pills
            hint_html += """<ul class="nav nav-pills" role="tablist">\n"""
            for hint in hints:
                if hint:    # In case of a blank line
                    hint_html += """<li class="nav-item">
    <a class="nav-link"""
                    # First hint should be visible
                    hint_html += ' active show"' if hint_counter == 1 else '"'
                    hint_html += """ id="step{0}-hint{1}-tab" data-toggle="pill" href="#step{0}-hint{1}" role="tab" aria-controls="lesson{0}-hint{1}">Hint {1}</a>
</li>\n""".format(object_id, hint_counter)
                    hint_counter += 1
            # Reset counter and close navigation pills HTML
            hint_counter = 1
            hint_html += """</ul>
<div class="tab-content mt-2 border rounded px-3 pt-3">"""
            
            # BS4 pill/tab content
            for hint in hints:
                if hint:
                    # Similar to above
                    hint_html += '<div class="tab-pane fade'
                    hint_html += ' show active"' if hint_counter == 1 else '"'
                    hint_html += """ id="step{0}-hint{1}" role="tabpanel" aria-labelledby="step{0}-hint{1}">{2}</div>\n""".format(object_id, hint_counter, markdown(hint, output_format='html'))
                    hint_counter += 1
            # Close all open HTML tags and reset variables
            hint_html += '</div></div></div></div>'
            hint_counter = 1
            hints = []

            # Replace line with all the HTML
            line = hint_html
        
        # CSS & JS specific to a page
        elif ':css::' in line:
            line = '<link rel="stylesheet" href="{0}" class="css-extra" />'.format(line.split('::')[1].strip())
        elif ':js::' in line:
            line = '<script type="text/javascript" src="{0}" class="js-extra"></script>'.format(line.split('::')[1].strip())

        # Drag and Drop quiz
        elif '::drag-and-drop::' in line:
            recording_drag_and_drop = True
            line = ''   # Or `add_line = False` could be used
        elif '::/drag-and-drop::' in line:  # Turn options into a table
            table = """<table class="table bg-secondary table-bordered text-white">\n"""
            for option in drag_and_drop_options:
                # Uses BS4 table
                table += """    <tr>
        <td>{0}</td>
        <td class="blank bg-info"></td>
    </tr>""".format(option)
            table += "\n</table>"
            line = table
            recording_drag_and_drop = False
            drag_and_drop_options = []
        elif recording_drag_and_drop:
            # Add options to the list
            drag_and_drop_options.append(line)
            line = ''
        

        # Collapse (similar to drag and drop)
        elif ':collapse::' in line:
            collapse_title = line.split('::')[1].strip()

            # Add BS4 collapsible card (collapse_counter ensured unique
            # IDs)
            line = """<div class="card border-info mb-3">
    <div class="card-header bg-info p-2">
        <h5 class="mb-0">
            <button class="btn btn-link text-white" data-toggle="collapse" data-target="#step{0}-collapse{1}" aria-expanded="true" aria-controls="step{0}-hints" style="text-decoration: none;">
                <i class="fas fa-2x fa-info-circle"></i>
                <span style="position: relative; bottom: 5px; left: 5px;">{2}</span>
            </button>
        </h5>
    </div>

    <div id="step{0}-collapse{1}" class="collapse">
        <div class="card-body">\n""".format(object_id, collapse_counter, collapse_title)
            recording_collapse = True   # Not really required
        elif '::/collapse::' in line:   # Close open HTML tags
            line = "</div></div></div>"
            recording_collapse = False
            collapse_counter += 1

        # Glossary items
        elif ':glossary-item::' in line:    
            glossary_item = line.split('::')[1].strip()
            line = """<div class="card mb-3">
    <h5 class="card-header">{0}</h5>
    <div class="card-body pb-1">""".format(glossary_item)
            recording_collapse = True
        
        elif '::/glossary-item::' in line:
            line = "</div></div>"
            recording_collapse = False
        
        elif recording_collapse:    # Does nothing extra
            line = markdown(line, output_format='html')
        if add_line:
            lines.append(line)
        add_line = True
    
    # Join up the lines
    finished_markdown = '\n'.join(lines)

    # Add GFM extension and any extras passed as arguments
    extensions_list = [GithubFlavoredMarkdownExtension()]
    extensions_list.extend(extensions or [])
    html = markdown(finished_markdown, output_format='html', extensions=extensions_list)
    return html

# Following three tables are association tables for many-to-many
# relationships
announcement_tags = db.Table("announcement_tags",
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id')),
    db.Column('announcement_id', db.Integer, db.ForeignKey('announcements.id'))
)

post_tags = db.Table("post_tags",
    db.Column('post_category_id', db.Integer, db.ForeignKey('postcategories.id')),
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id'))
)

quiz_skills = db.Table("quiz_skills",
    db.Column('quiz_id', db.Integer, db.ForeignKey('quizzes.id')),
    db.Column('skill_id', db.Integer, db.ForeignKey('skills.id'))
)


class Permission:
    """Contains the binary values for actions a user can or cannot do."""
    ASK_QUESTIONS = 0x01
    ANSWER_QUESTIONS = 0x02
    SAVE_HISTORY = 0x04
    MANAGE_CLASS = 0x08
    MODERATE_QUESTIONS = 0x10
    ADMINISTRATOR = 0xff


class SearchableMixin(object):
    """Incorporates the `search.py` functions and returns a list of
    objects rather than IDs. Should be inherited from and not used
    directly.

    Contains classmethods only.

    Based from the Flask-Mega Tutorial by Miguel Grinberg.
    """

    @classmethod
    def search(cls, expression, page, per_page):
        """Searches using `search.py` `query_index` function and
        returns a list of SQLAlchemy objects, not IDs.

        Returns
        -------
        Objects found : SQLAlchemy.BaseQuery
        
        Total objects found : int
        """

        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            # Return a blank query
            return cls.query.filter_by(id=0), 0
        
        # Used in a SQL WHEN statement to order objects in the same order the search returned
        when = []   
        for i in range(len(ids)):   # enumerate() could also be used
            when.append((ids[i], i))

        # Filter: IF object id IN ids (above)
        # ORDER BY: when list
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        """Adds any changes to DB in a dictionary."""
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        """Checks the changes and either adds, modifies or deletes from
        the indices.
        """
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        """Utility method to reindex all objects."""
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)

# Add events for automatic addition or deletion of the indices
db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        """Inserts the roles for the application."""
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
    avatar_hash = db.Column(db.String(32))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    announcements = db.relationship('Announcement', backref='author',
                                    lazy='dynamic')
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    comments = db.relationship('PostComment', backref='author',
                               lazy='dynamic')
    answers = db.relationship('UserAnswer', backref='user', lazy='dynamic')
    notes = db.relationship('TeacherNote', backref='teacher', lazy='dynamic')
    page_questions = db.relationship('PageQuestion', backref='author',
                                     lazy='dynamic')
    page_answers = db.relationship('PageAnswer', backref='author',
                                   lazy='dynamic')
    reported_problem_mistakes = db.relationship('ProblemMistake',
                                                backref='user',
                                                lazy='dynamic')
    quizzes_attempted = db.relationship('Quiz', secondary='quizattempts',
                        backref=db.backref('users_attempted', lazy='dynamic'),
                        lazy='dynamic') # For quiz results

    @property
    def password(self):
        """Password attribute, write-only. Raises `AttributeError` if
        read.
        """
        raise AttributeError('Password is a write-only attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            self.role = Role.query.filter_by(default=True).first()
        self.avatar_hash = hashlib.md5(self.username.encode("utf-8")).hexdigest()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.can(Permission.ADMINISTRATOR)
    
    def can(self, permissions):
        return self.role is not None and (self.role.permissions & permissions) == permissions

    def upcoming_assignments(self):
        return self.assignments.filter(Assignment.due_date > datetime.now())
    
    def past_assignments(self):
        return self.assignments.filter(Assignment.due_date < datetime.now())
    
    def getAvatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            base_url = 'https://secure.gravatar.com/avatar'
        else:
            base_url = 'http://www.gravatar.com/avatar'
        if self.avatar_hash:
            hash = self.avatar_hash
        else:
            hash = hashlib.md5(self.username.encode('utf-8')).hexdigest()
            self.avatar_hash = hash
        full_url = "%s/%s?s=%i&d=%s&?r=%s" % (base_url, hash, size, default, rating)
        return full_url

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

    @property
    def assignments(self):
        return Assignment.query.filter_by(id=0)

    def upcoming_assignments(self):
        return []
    
    def past_assignments(self):
        return []

login.anonymous_user = AnonymousUser

class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))

    def __repr__(self):
        return 'Tag <%s>' % self.name

class Announcement(db.Model, SearchableMixin):
    __tablename__ = 'announcements'
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
    tags = db.relationship('Tag', secondary=announcement_tags,
                           backref=db.backref('announcements', lazy='dynamic'))

    @staticmethod
    def body_changed(target, value, oldvalue, initiator):
        target.body_html = customTagMarkdown(value)

    @staticmethod
    def summary_changed(target, value, oldvalue, initiator):
        target.summary_html = customTagMarkdown(value)

db.event.listen(Announcement.body, 'set', Announcement.body_changed)
db.event.listen(Announcement.summary, 'set', Announcement.summary_changed)

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    description = db.Column(db.Text)
    description_html = db.Column(db.Text)
    thumbnail = db.Column(db.String(500))
    status = db.Column(db.Boolean, default=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))
    steps = db.relationship('ProjectStep', backref='project', lazy='dynamic')

    @staticmethod
    def description_changed(target, value, oldvalue, initiator):
        target.description_html = customTagMarkdown(value)

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
        target.content_html = customTagMarkdown(value, target.id)

db.event.listen(ProjectStep.content, 'set', ProjectStep.content_changed)

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text)
    html = db.Column(db.Text)
    image_url = db.Column(db.Text)
    max_attempts = db.Column(db.Integer)
    question_type_id = db.Column(db.Integer, db.ForeignKey('questiontypes.id'))
    # quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'))
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'))
    options = db.relationship('QuestionOption', backref='question', lazy='dynamic')
    answer = db.relationship('QuestionAnswer', backref='question', lazy='dynamic')
    user_answer = db.relationship('UserAnswer', backref='question', lazy='dynamic')
    hints = db.relationship('Hint', backref='question', lazy='dynamic')
    reported_mistakes = db.relationship('ProblemMistake', backref='question', lazy='dynamic')

    def what_model(self):
        return "Question"
    
    def show(self):
        return (self.html or self.text)

    def check(self, answer):
        if answer == self.correct_answer():
            return True
        else:
            return False
    
    def correct_answer(self):
        if self.question_type == QuestionType.query.filter_by(code='M').first():
            return [answer.option.text for answer in self.answer.all()]
        return self.answer.first().option.text

    def get_explanation(self):
        explanation = ""
        for hint in self.hints.all():
            explanation += hint.html
        return explanation

    def generate_new_html(target, value, oldvalue, initiator):
        # If the new question page is going to open to regular users
        # allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
        #                 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
        #                 'h1', 'h2', 'h3', 'p', 'img', 'footer', 'div', 'span']
        # target.html = bleach.linkify(bleach.clean(
        #     customTagMarkdown(value),
        #     tags=allowed_tags))
        # Otherwise:
        target.html = customTagMarkdown(value)

    def drag_and_drop_answers(self, response=None, use_correct_answer=False):
        if not response and not use_correct_answer:
            raise TypeError(
                'drag_and_drop_answers() takes at least 1 argument (0 given)'
            )
        
        if use_correct_answer:
            response = self.correct_answer()
        
        options = []
        for pair in response.split(' '):
            char = pair.split('=')[1]
            options.append(self.options.offset(int(char) - 1).first())

        if self.question_type != QuestionType.query.filter_by(code='D').first():
            return ""

        spaces = self.html.split('<td class="blank bg-info"></td>')
        html = []
        for i, space in enumerate(spaces):
            html.append(space)
            try:
                option = """<span class="draggable-btn bg-white mr-3 mt-2 d-flex p-2" data-position="{0}">
    <span class="m-auto text-dark">{1}
</span>""".format(i + 1, options[i])
            except IndexError:
                # Last space containg closing table tag (</table>)
                pass
            else:
                # Add option
                html.append('<td class="blank bg-info">{0}</td>'.format(option))
        html = ''.join(html)
        return html

    def __repr__(self):
        return '<Question> {0} Answer: {1}'.format(self.text, self.correct_answer())

db.event.listen(Question.text, 'set', Question.generate_new_html)

class Hint(db.Model):
    __tablename__ = 'hints'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text)
    html = db.Column(db.Text)
    hint_no = db.Column(db.Integer)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))

    def generate_new_html(target, value, oldvalue, initiator):
        # allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
        #                 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
        #                 'h1', 'h2', 'h3', 'p', 'img', 'footer', 'div', 'span']
        # target.html = bleach.linkify(bleach.clean(
        #     customTagMarkdown(value),
        #     tags=allowed_tags))
        target.html = customTagMarkdown(value)
    
db.event.listen(Hint.text, 'set', Hint.generate_new_html)

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    no_questions = db.Column(db.Integer)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))
    next_quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=True)
    type_id = db.Column(db.Integer, db.ForeignKey('quiztypes.id'))
    next_quiz = db.relationship('Quiz', backref=db.backref('prev_quiz', uselist=False), remote_side=[id], uselist=False)
    # questions = db.relationship('Question', backref='quiz', lazy='dynamic')
    assignments = db.relationship('Assignment', backref='quiz', lazy='dynamic')
    tested_skills = db.relationship('Skill', secondary=quiz_skills,
                        backref=db.backref('quizzes_tested', lazy='dynamic'),
                        lazy='dynamic')

    @property
    def questions(self):
        if self.type.code == 'P':
            return self.tested_skills.first().questions # NOTE: Returns BaseQuery object and not list
        else:
            return None

    def title(self):
        if self.type == QuizType.query.filter_by(code='P').first():
            return self.tested_skills.first().description
        else:
            return self.lesson.title + ' - Chapter ' + self.lesson.chapter.title 

    def what_model(self):
        return "Quiz"

    def model_one_lower(self):
        return "Questions"

    def is_unlocked(self):
        return current_user.assignments.filter_by(quiz_id=self.id).first() or current_user.can(Permission.MANAGE_CLASS)

class QuizType(db.Model):
    __tablename__ = 'quiztypes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(1))
    description = db.Column(db.Text)
    quizzes = db.relationship('Quiz', backref='type', lazy='dynamic')

    @staticmethod
    def insert_types():
        types = [('P', 'Practice'), ('Q', 'Regular Quiz'), ('U', 'Unit Test')]
        for code, quiz_type in types:
            if not QuizType.query.filter_by(description=quiz_type).first():
                t = QuizType(code=code, description=quiz_type)
                db.session.add(t)
        db.session.commit()

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
        #     customTagMarkdown(value),
        #     tags=allowed_tags))
        # Otherwise:
        target.html = bleach.linkify(customTagMarkdown(value))
    
    def __repr__(self):
        return '<Glossary> {0}'.format(self.title)

db.event.listen(Glossary.text, 'set', Glossary.generate_new_html)

class QuestionOption(db.Model):
    __tablename__ = 'questionoptions'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))
    answer = db.relationship('QuestionAnswer', backref='option', uselist=False)

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
    score = db.Column(db.Integer)   # Score is out of 100
    answer_status_id = db.Column(db.Integer, db.ForeignKey('answerstatus.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))

    def __repr__(self):
        return '<User Answer (%s, %i, %s)>' % (self.keyed_answer, self.score, self.user)

class QuizAttempt(db.Model):
    __tablename__ = 'quizattempts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'))
    percent = db.Column(db.Integer) # Overall score of quiz (mean of all question scores)
    datetime = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('quizattempts',
                cascade='all, delete-orphan', lazy='dynamic'))
    quiz = db.relationship('Quiz', backref=db.backref('quizattempts',
                cascade='all, delete-orphan', lazy='dynamic'))

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
    image_url = db.Column(db.Text)
    name = db.Column(db.Text)
    active = db.Column(db.Boolean)
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

    def student_progress(self, student):
        quiz_scores = []
        for lesson in self.lessons:
            for quiz in lesson.quizzes:
                best_score = QuizAttempt.query.filter_by(quiz_id=quiz.id, user_id=student.id).order_by(QuizAttempt.percent.desc()).first()
                if not best_score:
                    best_score = 0
                else:
                    best_score = best_score.percent
                quiz_scores.append(best_score)
        try:
            average = (sum(quiz_scores) / len(quiz_scores)) # Mean of all scores
        except ZeroDivisionError:
            return 0
        else:
            return round(average)

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
    type_id = db.Column(db.Integer, db.ForeignKey('lessontypes.id'))
    skills = db.relationship('Skill', backref='lesson', lazy='dynamic')
    pages = db.relationship('Page', backref='lesson', lazy='dynamic')
    quizzes = db.relationship('Quiz', backref='lesson', lazy='dynamic')
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
            customTagMarkdown(value),
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

    def all_ordered_quizzes(self):
        ordered = []
        if len(self.quizzes.all()) > 0:
            def append_quiz(quiz):
                ordered.append(quiz)
                if quiz.next_quiz:
                    append_quiz(quiz.next_quiz)
            append_quiz(self.quizzes.filter_by(prev_quiz=None).first())
        return ordered

db.event.listen(Lesson.overview, 'set', Lesson.generate_new_html)

class LessonType(db.Model):
    __tablename__ = 'lessontypes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(1))
    description = db.Column(db.Text)
    lessons = db.relationship('Lesson', backref='type', lazy='dynamic')

    @staticmethod
    def insert_types():
        types = [('L', 'Learn'), ('Q', 'Quiz'), ('U', 'Unit Test')]
        for code, lesson_type in types:
            if not LessonType.query.filter_by(description=lesson_type).first():
                t = LessonType(code=code, description=lesson_type)
                db.session.add(t)
        db.session.commit()

class Page(SearchableMixin, db.Model):
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
    assignments = db.relationship('Assignment', backref='page', lazy='dynamic')
    notes = db.relationship('TeacherNote', backref='page', lazy='dynamic')
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))

    def what_model(self):
        return "Page"

    def generate_new_html(target, value, oldvalue, initiator):
        # allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
        #                 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
        #                 'h1', 'h2', 'h3', 'p', 'img', 'footer', 'div', 'span', 'iframe']
        
        target.html = customTagMarkdown(value)
    
    def is_unlocked(self):
        return current_user.assignments.filter_by(page_id=self.id).first() or current_user.can(Permission.MANAGE_CLASS)

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
        types = ['Article', 'Glossary', 'Video']
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
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'br', 'blockquote', 'code',
                        'del', 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p', 'img', 'footer', 'div', 'span',
                        'table', 'tbody', 'thead', 'td', 'tr', 'th']
        target.html = bleach.linkify(bleach.clean(
            customTagMarkdown(value),
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
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'br', 'blockquote', 'code',
                        'del', 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p', 'img', 'footer', 'div', 'span',
                        'table', 'tbody', 'thead', 'td', 'tr', 'th']
        target.html = bleach.linkify(bleach.clean(
            customTagMarkdown(value),
            tags=allowed_tags, attributes=['class', 'id', 'href', 'alt', 'title', 'style', 'src']))

db.event.listen(PageAnswer.text, 'set', PageAnswer.generate_new_html)

class Skill(db.Model):
    __tablename__ = 'skills'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'))
    questions = db.relationship('Question', backref='skill', lazy='dynamic')

    def what_model(self):
        return "Skill"
    
    @property
    def practice_quiz(self):
        return self.quizzes_tested.filter(Quiz.type_id == QuizType.query.filter_by(code='P').first().id).first()

class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8), unique=True)
    name = db.Column(db.String(50))
    description = db.Column(db.Text)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    assignments = db.relationship('Assignment', backref='class_', lazy='dynamic', cascade='all')
    notes = db.relationship('TeacherNote', backref='class_', lazy='dynamic')
    students = db.relationship('User', secondary='class_students',
        backref=db.backref('classes', lazy='dynamic', cascade='all'), lazy='dynamic')

    def __repr__(self):
        return "<Class, Name: %s Code: %s>" % (self.name, self.code)

class ClassStudent(db.Model):
    __tablename__ = 'class_students'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    student_status = db.Column(db.Boolean, default=True)

class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    due_date = db.Column(db.DateTime)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'))    # One will be null because pages
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'))  # and quizzes are different model
    students = db.relationship('User', secondary='student_assignments', 
        backref=db.backref('assignments', lazy='dynamic', cascade='all'), lazy='dynamic')

    def is_quiz(self):
        if self.quiz_id is not None:
            return True
        else:
            return False
    
    def assigned_item(self):
        if not self.page_id or self.quiz_id:
            return None
        return self.quiz if self.is_quiz else self.page

class StudentAssignment(db.Model):
    __tablename__ = 'student_assignments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'))
    datetime = db.Column(db.DateTime, default=datetime.utcnow)
    score = db.Column(db.Integer)

class ProblemMistake(db.Model):
    __tablename__ = 'problemmistakes'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    datetime = db.Column(db.DateTime, default=datetime.utcnow)
    is_closed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))
    problem_mistake_type_id = db.Column(db.Integer, db.ForeignKey('problemmistaketypes.id'))

class ProblemMistakeType(db.Model):
    __tablename__ = 'problemmistaketypes'
    id = db.Column(db.Integer, primary_key=True)
    mistake_type = db.Column(db.Text)
    description = db.Column(db.Text)
    problem_mistakes = db.relationship('ProblemMistake', backref='problem_mistake_type', lazy='dynamic')

    @staticmethod
    def insert_types():
        types = [('The answer is not correct.', 'What should be the correct answer and what are the steps to get to that answer?'), 
                 ('There is a typo.', 'What does the incorrect text say and what should it be instead?'),
                 ('The question or hints are confusing or unclear.', 'What exactly confused you and how would you reword the question?'),
                 ('Something isn\'t working or something seems broken.', 'What exactly happened and what had you expected to happen instead?')]
        for mistake_type, description in types:
            if not ProblemMistakeType.query.filter_by(mistake_type=mistake_type).first():
                t = ProblemMistakeType(mistake_type=mistake_type, description=description)
                db.session.add(t)
        db.session.commit()

class Post(db.Model, SearchableMixin):
    __tablename__ = 'posts'
    __searchable__ = ['title', 'body']

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    summary = db.Column(db.Text)
    summary_html = db.Column(db.Text)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    published = db.Column(db.Boolean, default=True)
    title = db.Column(db.String(64))
    categories = db.relationship('PostCategory', secondary=post_tags,
                           backref=db.backref('posts', lazy='dynamic'))
    comments = db.relationship('PostComment', backref='post', lazy='dynamic')

    @staticmethod
    def body_changed(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'br', 'blockquote', 'code',
                        'del', 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p', 'img', 'footer', 'div', 'span',
                        'table', 'tbody', 'thead', 'td', 'tr', 'th']
        target.body_html = bleach.linkify(bleach.clean(
            customTagMarkdown(value),
            tags=allowed_tags, attributes=['class', 'id', 'href', 'alt', 'title', 'style', 'src']))
        new_summary = value
        new_summary = new_summary.split(' ')
        new_summary = new_summary[:80]
        new_summary = ' '.join(new_summary)
        if not new_summary == value:
            new_summary += '&hellip;'
        target.summary = new_summary

    @staticmethod
    def summary_changed(target, value, oldvalue, initiator):
        target.summary_html = customTagMarkdown(value)

db.event.listen(Post.body, 'set', Post.body_changed)
db.event.listen(Post.summary, 'set', Post.summary_changed)

class PostComment(db.Model):
    __tablename__ = 'postcomments'

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @staticmethod
    def body_changed(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'br', 'blockquote', 'code',
                        'del', 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p', 'img', 'footer', 'div', 'span',
                        'table', 'tbody', 'thead', 'td', 'tr', 'th']
        target.body_html = bleach.linkify(bleach.clean(
            customTagMarkdown(value),
            tags=allowed_tags, attributes=['class', 'id', 'href', 'alt', 'title', 'style', 'src']))

db.event.listen(PostComment.body, 'set', PostComment.body_changed)

class PostCategory(db.Model):
    __tablename__ = 'postcategories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))

    def __repr__(self):
        return 'Post Category <%s>' % self.name

def set_target(attrs, new=False):
    attrs[(None, 'target')] = '_blank'
    attrs[(None, 'rel')] = 'noopener noreferrer'
    return attrs

class TeacherNote(db.Model):
    __tablename__ = 'teachernotes'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'))

    @staticmethod
    def body_changed(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'br', 'blockquote', 'code',
                        'del', 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p', 'img', 'footer', 'div', 'span',
                        'table', 'tbody', 'thead', 'td', 'tr', 'th']
        target.body_html = bleach.linkify(bleach.clean(
            customTagMarkdown(value),
            tags=allowed_tags, attributes=['class', 'id', 'href', 'alt', 'title', 'style', 'src']), callbacks=[set_target])

db.event.listen(TeacherNote.body, 'set', TeacherNote.body_changed)
