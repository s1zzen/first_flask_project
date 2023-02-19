# -*- coding: utf-8 -*-
from app import app, db
from flask import render_template, flash, redirect, url_for, request
from app.forms import LoginForm, RegistrationForm, EditProfileForm, PostForm, \
    ResetPasswordRequestForm, ResetPasswordForm
from flask_login import current_user, login_user, logout_user, login_required
from app.email import send_password_reset_email
from app.models import User, Post
from werkzeug.urls import url_parse
from datetime import datetime
from guess_language import guess_language

# [Название вкладки, текущаяя или нет, функции обработчики]
headersPages = [['База', False, 'index'], ['О Нас', False, 'about_us'],
                ['Новости', False, 'news'], ['Профиль', False, 'profile']]


@app.before_request
def before_request():
    if current_user.is_authenticated:  # type: ignore
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/')
@app.route('/about-us')
def about_us():
    headers = [x[:] for x in headersPages]
    headers[1][1] = True
    return render_template('about-us.html', headers=headers)


@app.route('/news', methods=['GET', 'POST'])
@login_required
def news():
    headers = [x[:] for x in headersPages]
    headers[2][1] = True
    form = PostForm()
    if form.validate_on_submit():
        language = guess_language(form.post.data)
        if language == 'UNKNOWN' or len(language) > 5:  # type: ignore
            language = ''
        post = Post(body=form.post.data, author=current_user, language=language)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        return redirect(url_for('news'))
    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(  # type: ignore
        page=page, per_page=app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('news', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('news', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template("news.html", form=form,
                           posts=posts.items, headers=headers, next_url=next_url,
                           prev_url=prev_url)


@app.route('/index')
@login_required
def index():
    headers = [x[:] for x in headersPages]
    headers[0][1] = True
    users = User.query.all()
    return render_template('index.html', headers=headers, users=users)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if current_user.is_authenticated:  # type: ignore
        return redirect(f'/profile/{current_user.username}')  # type: ignore
    headers = [x[:] for x in headersPages]
    headers[3][1] = True
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('profile'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('profile.html', headers=headers, form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():

    if current_user.is_authenticated:  # type: ignore
        return redirect(url_for('index'))
    headers = [x[:] for x in headersPages]
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)  # type: ignore
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('profile'))
    return render_template('register.html', title='Register', headers=headers, form=form)


@app.route('/profile/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page=page, per_page=app.config['POSTS_PER_PAGE'], error_out=False)
    headers = [x[:] for x in headersPages]
    next_url = url_for('user', username=current_user.username,  # type: ignore
                       page=posts.next_num) if posts.has_next else None
    prev_url = url_for('user', username=current_user.username,  # type: ignore
                       page=posts.prev_num) if posts.has_prev else None
    headers[3][1] = True
    return render_template('user.html', user=user, posts=posts.items,
                           headers=headers, next_url=next_url,
                           prev_url=prev_url)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    headers = [x[:] for x in headersPages]
    form = EditProfileForm(current_user.username)  # type: ignore
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username  # type: ignore
        form.about_me.data = current_user.about_me  # type: ignore
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form, headers=headers)


@app.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('user', username=username))
    current_user.follow(user)  # type: ignore
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('user', username=username))


@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('user', username=username))
    current_user.unfollow(user)  # type: ignore
    db.session.commit()
    flash('You are not following {}.'.format(username))
    return redirect(url_for('user', username=username))


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    headers = [x[:] for x in headersPages]
    if current_user.is_authenticated:  # type: ignore
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('profile'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form, headers=headers)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    headers = [x[:] for x in headersPages]
    if current_user.is_authenticated:  # type: ignore
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('profile'))
    return render_template('reset_password.html', form=form, headers=headers)
