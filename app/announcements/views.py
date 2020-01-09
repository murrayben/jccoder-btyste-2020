from flask import abort, current_app, flash, g, render_template, redirect, request, url_for
from flask_login import current_user, login_required
from datetime import datetime
from ..models import db, Announcement, Tag
from .forms import AnnouncementForm, SearchForm
from . import announcements

@announcements.before_request
def addSearchForm():
    if not current_user.is_authenticated:  
        return current_app.login_manager.unauthorized()
    g.announcement_search_form = SearchForm()

# Get Tag objects from a list of Tag ids
def parseMultipleAnnouncement(form):
    # Gather ids
    num_list = form.tags.data

    # Set initial value of list of Tag objects
    return_list = []

    # Iterate through whole list of ids
    for i in num_list:
        # Turn id into an object
        tag = Tag.query.filter_by(id=i).first()

        # Add that on to the list of Tag objects
        return_list.append(tag)
    
    # Return the list of objects back to the caller
    return return_list

# Do the reverse of the above
def unparseMultipleAnnouncement(announcement):
    # Set initial value of list of Tag ids
    return_list = []

    # Iterate through the list of objects
    for i in announcement.tags:
        # Add the id of the tag to the list of ids
        return_list.append(i.id)
    
    # Return the list of ids back to the caller
    return return_list

@announcements.route('/', methods=['GET', 'POST'])
def index():
    # Get the pagination page. If no page is specified the default page number (1) is used.
    page = request.args.get("page", 1, type=int)
    form = AnnouncementForm()

    announcements = Announcement.query.filter(db.or_(Announcement.published == True, Announcement.author_id == current_user.id, current_user.is_admin())).order_by(Announcement.date_posted.desc())

    pagination = announcements.paginate(
        page, per_page=current_app.config["POSTS_PER_PAGE"],
        error_out=True)

    announcements = pagination.items

    if form.validate_on_submit():
        # Get the actual tag objects by parsing the ids using a function that I defined earlier
        tags = parseMultipleAnnouncement(form)

        # Create a announcement object
        announcement = Announcement(title=form.title.data, body=form.body.data, summary=form.summary.data, author=current_user._get_current_object(), tags=tags, published=form.published.data)

        # Add the announcement to the database session
        db.session.add(announcement)

        # Commit the database session to write the announcement to the database
        db.session.commit()

        # Issue a redirect to the home page
        return redirect(url_for('.index'))
    
    # Render the announcements/index.html template
    return render_template("announcements/index.html", title="Announcements", form=form, announcements=announcements, pagination=pagination)

# Render a full announcement/announcement on its own
@announcements.route('/<int:id>', methods=['GET', 'POST'])
def permalink(id):
    # Retrieve the announcement and if id doesn't exist yet, return a 404 status code.
    announcement = Announcement.query.get_or_404(id)
    
    # If the announcement isn't public and the author is not the current user
    if announcement.published == False and announcement.author != current_user and not current_user.is_admin():
        # Return a 403 status code (forbidden)
        abort(403)

    # Render template
    return render_template("announcements/permalink.html", title="Announcement - " + announcement.title, announcement=announcement)

@announcements.route('/tag/<int:id>')
def tag(id):
    # Get the pagination page. If no page is specified the default page number (1) is used.
    page = request.args.get("page", 1, type=int)

    tag = Tag.query.get_or_404(id)
    announcements = tag.announcements.filter(db.or_(Announcement.published == True, Announcement.author_id == current_user.id,
                current_user.is_admin())).order_by(Announcement.date_posted.desc())

    pagination = announcements.paginate(
        page, per_page=current_app.config["POSTS_PER_PAGE"],
        error_out=True)

    announcements = pagination.items

    return render_template("announcements/tag.html", title="Tag - " + tag.name, tag=tag, announcements=announcements, pagination=pagination)

# Make a announcement public
@announcements.route('/public/<int:id>')
def public(id):
    # Retrieve announcement from database (issue 404 error is announcement doesn't exist)
    announcement = Announcement.query.get_or_404(id)

    # Issue a 403 (forbidden) error if announcement author is not the logged in user
    if announcement.author.username != current_user.username and not current_user.is_admin():
        abort(403)

    # Change status of announcement
    announcement.published = True

    # Flash a message that says that the announcement is public.
    flash("Your announcement is now public.", 'info')

    return redirect(url_for('.index'))

# Make a announcement private or a draft
@announcements.route('/draft/<int:id>')
def draft(id):
    # Retrieve announcement from database (issue 404 error is announcement doesn't exist)
    announcement = Announcement.query.get_or_404(id)

    # Issue a 403 (forbidden) error if announcement author is not the logged in user
    if announcement.author.username != current_user.username and not current_user.is_admin():
        abort(403)

    # Change status of announcement
    announcement.published = False

    # Flash a message that says that the announcement is a draft
    flash("Your announcement is now a draft.", 'info')

    return redirect(url_for('.index'))

# Editing a announcement
@announcements.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    # Retrieve announcement from database (issue 404 error is announcement doesn't exist)
    announcement = Announcement.query.get_or_404(id)

    # Create form object
    form = AnnouncementForm()

    # Issue a 403 (forbidden) error if announcement author is not the logged in user
    if current_user.username != announcement.author.username and not current_user.is_admin():
        abort(403)

    # If request method is POST (a form was submitted)
    if form.validate_on_submit():
        announcement.title = form.title.data
        announcement.body = form.body.data
        announcement.summary = form.summary.data
        announcement.tags = parseMultipleAnnouncement(form)
        announcement.published = form.published.data
        announcement.date_posted = datetime.utcnow()

        # Redirect the user to the page with the announcement in it
        return redirect(url_for('.permalink', id=id))
    
    # Set initial values of the fields with the announcement data
    form.title.data = announcement.title
    form.body.data = announcement.body
    form.summary.data = announcement.summary

    # Get list of tag ids by calling the unparseMultipleAnnouncement function (it was defined earlier)
    form.tags.data = unparseMultipleAnnouncement(announcement)
    form.published.data = announcement.published

    # Render edit page template
    return render_template("announcements/edit.html", title="Edit Announcement - " + announcement.title, announcement=announcement, form=form)

@announcements.route('/search')
def search():
    if not g.announcement_search_form.validate():
        abort(404)
    q = g.announcement_search_form.q.data
    g.search_form.q.data = ""
    page = request.args.get('page', 1, type=int)
    announcements, total = Announcement.search(q, page, current_app.config["POSTS_PER_PAGE"])
    next_url = url_for('.search', q=q, page=page + 1) \
        if total > page * current_app.config["POSTS_PER_PAGE"] else None
    prev_url = url_for('.search', q=q, page=page - 1) \
        if page > 1 else None
    return render_template('announcements/search_results.html', title="Search results for \"{0}\"".format(q), q=q, announcements=announcements.all(), total=total, prev_url=prev_url, next_url=next_url)