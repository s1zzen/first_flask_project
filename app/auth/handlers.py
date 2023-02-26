from app.auth import bp
from app import db, headersPages
from app.models import User
from app.auth.forms import EditProfileForm, LoginForm, RegistrationForm,\
    ResetPasswordForm, ResetPasswordRequestForm
from flask import flash, redirect, url_for, render_template, request
from flask_login import login_required, login_user, logout_user, current_user
from app.auth.email import send_password_reset_email
from werkzeug.urls import url_parse


@bp.route('/profile', methods=['GET', 'POST'])
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
            return redirect(url_for('main.profile'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)
    return render_template('auth/profile.html', headers=headers, form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():

    if current_user.is_authenticated:  # type: ignore
        return redirect(url_for('main.index'))
    headers = [x[:] for x in headersPages]
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)  # type: ignore
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('main.profile'))
    return render_template('auth/register.html',
                           title='Register', headers=headers, form=form)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    headers = [x[:] for x in headersPages]
    form = EditProfileForm(current_user.username)  # type: ignore
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('main.profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username  # type: ignore
        form.about_me.data = current_user.about_me  # type: ignore
    return render_template('auth/edit_profile.html', title='Edit Profile',
                           form=form, headers=headers)


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    headers = [x[:] for x in headersPages]
    if current_user.is_authenticated:  # type: ignore
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('main.profile'))
    return render_template('auth/reset_password_request.html',
                           title='Reset Password', form=form, headers=headers)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    headers = [x[:] for x in headersPages]
    if current_user.is_authenticated:  # type: ignore
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('main.profile'))
    return render_template('auth/reset_password.html', form=form, headers=headers)
