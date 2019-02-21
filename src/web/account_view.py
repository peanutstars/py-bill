from flask import render_template, flash, redirect, url_for, session, request
from flask_login import login_user, login_required, logout_user, current_user
from wtforms import Form, StringField, TextAreaField, PasswordField, HiddenField
from wtforms.validators import InputRequired, Email, Length, EqualTo, DataRequired
from wtforms.csrf.session import SessionCSRF
from werkzeug.security import generate_password_hash, check_password_hash

from .model import User
from . import app, db, login_manager



class FormCSRF(Form):
    class Meta:
        csrf = True
        csrf_class = SessionCSRF
        csrf_secret = b'Key@CSRF'

        @property
        def csrf_context(self):
            return session


class RegisterForm(FormCSRF):
    email = StringField('E-mail Address', [
                InputRequired(), Length(min=5, max=64),
                Email("Invalid Email Address")])
    username = StringField('Username', [
                InputRequired(), Length(min=4, max=32)])
    password = PasswordField('Password', [
                DataRequired(),
                Length(min=5, max=32),
                EqualTo('confirm', message='Passwords do not match')])
    confirm = PasswordField('Confirm Password')

class LoginForm(FormCSRF):
    email = StringField('E-mail Address', [
                InputRequired(), Length(min=5, max=64)])
    password = PasswordField('Password', [
                InputRequired(), Length(max=32)])
    h_next = HiddenField()


# @login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    session['username'] = user.username
    return user


# Register
@app.route('/account/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        email = form.email.data
        username = form.username.data
        password = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data,
                        email=form.email.data, password=password)
        try:
            db.session().add(new_user)
            db.session().commit()
        except Exception as e:
            flash('Already used E-mail address.', 'warning')
            return render_template('pages/register.html', form=form)
        flash(f'You, {username} are now registered and can log in', 'success')
        return redirect(url_for('login'))
    elif form.csrf_token.errors:
        flash('You have submitted an invalid CSRF token', 'danger')
    return render_template('pages/register.html', form=form)

@app.route('/account/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'GET':
        form.h_next.data = request.args.get('next')
    if request.method == 'POST' and form.validate():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                flash(f'Welcome, {user.username} !', 'success')
                next = form.h_next.data
                return redirect(next or url_for('index'))
        flash('Invalid E-mail Address or Password', 'warning')
    elif form.csrf_token.errors:
        flash('Invalid CSRF token', 'danger')
    return render_template('pages/login.html', form=form)

@app.route('/account/logout')
@login_required
def logout():
    username = session['username']
    session.clear()
    flash(f'Logged out - Bye {username} !', 'success')
    return redirect(url_for('index'))

@app.route('/account')
@login_required
def account():
    user = User.query.get(int(session['user_id']))
    return render_template('pages/account.html', user=user)
