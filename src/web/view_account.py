import time

from flask import render_template, flash, redirect, url_for, session, request
from flask_login import login_user, login_required  # current_user
from wtforms import Form, StringField, PasswordField, HiddenField
from wtforms.validators import (InputRequired, Email, Length, EqualTo,
                                DataRequired)
from wtforms.csrf.session import SessionCSRF
from werkzeug.security import generate_password_hash, check_password_hash

from .account import role_required
from .model import Role, Notify, User, MStock, Reply
from . import app, db
from core.model import Dict


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


class PasswordForm(FormCSRF):
    passwd_cur = PasswordField('Current', [InputRequired(), Length(max=32)])
    passwd_new = PasswordField('New', [
                    DataRequired(),
                    Length(min=5, max=32),
                    EqualTo('passwd_confirm',
                            message='Do not match Password')])
    passwd_confirm = PasswordField('Confirm')


# @login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    session['username'] = user.username
    # session['role'] = user.role
    return user


# Register
@app.route('/account/register', methods=['GET', 'POST'])
def account_register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        email = form.email.data
        username = form.username.data
        password = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data,
                        email=email, password=password)
        try:
            db.session().add(new_user)
            db.session().commit()
        except Exception:
            flash('Already used E-mail address.', 'warning')
            return render_template('pages/account_register.html', form=form)
        flash(f'You, {username} are now registered and can log in', 'success')
        return redirect(url_for('account_login'))
    elif form.csrf_token.errors:
        flash('You have submitted an invalid CSRF token', 'danger')
    return render_template('pages/account_register.html', form=form)


@app.route('/account/login', methods=['GET', 'POST'])
def account_login():
    form = LoginForm(request.form)
    if request.method == 'GET':
        form.h_next.data = request.args.get('next')
    if request.method == 'POST' and form.validate():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                if login_user(user):
                    flash(f'Welcome, {user.username} !', 'success')
                else:
                    flash(f'Hi {user.username}, '
                          'Please wait for permitting by the administrator.',
                          'warning')
                next = form.h_next.data
                return redirect(next or url_for('index'))
        time.sleep(3)
        flash('Invalid E-mail Address or Password', 'warning')
    elif form.csrf_token.errors:
        time.sleep(3)
        flash('Invalid CSRF token', 'danger')
    return render_template('pages/account_login.html', form=form)


@app.route('/account/logout')
@login_required
def account_logout():
    username = session['username']
    session.clear()
    flash(f'Logged out - Bye {username} !', 'success')
    return redirect(url_for('index'))


@app.route('/account')
@login_required
def account():
    user = User.query.get(int(session['user_id']))
    users = User.query.all() if user.is_authorized('ADMIN') else None
    recent_stocks = MStock.list(session['user_id'])
    context = Dict()
    context.roles = Role.TYPE.keys()
    context.user = user 
    context.users = users
    context.notify = Notify.get_names(user.notify)
    context.notifications = Notify.NAMES
    context.recent_stocks = recent_stocks
    context.function.notify_names = Notify.get_names
    return render_template('pages/account.html', **context)


@app.route('/account/password', methods=['GET', 'POST'])
@login_required
def account_password():
    form = PasswordForm(request.form)
    if request.method == 'POST' and form.validate():
        user = User.query.get(int(session['user_id']))
        if user:
            if check_password_hash(user.password, form.passwd_cur.data):
                user.password = generate_password_hash(form.passwd_new.data)
                db.session().commit()
                flash('Changed Password', 'success')
                return redirect(url_for('account'))
            else:
                flash('Invalid the Current Password', 'danger')
    elif form.csrf_token.errors:
        flash('Invalid CSRF token', 'danger')
    recent_stocks = MStock.list(session['user_id'])
    return render_template('pages/account_password.html',
                           form=form, recent_stocks=recent_stocks)


@app.route('/ajax/account/user', methods=['GET', 'PATCH', 'DELETE'])
@login_required
@role_required('ADMIN')
def ajax_account_user():
    '''Supervisor manage user property.'''
    if int(session['user_id']) != 1:
        return Reply.Fail(message="Not Allow Permittion")

    if request.method == 'GET':
        params = dict(request.args)
    else:
        params = request.get_json()
    print('@@ ', request.method, params)

    if type(params) is not dict or 'id' not in params:
        return Reply.Fail(message="Invalid or Need Parameters")
    id = params.pop('id')
    try:
        if request.method == 'GET':
            return Reply.Success(value=User.info(id))
        if request.method == 'PATCH':
            return Reply.Success(value=User.update(id, **params))
        if request.method == 'DELETE':
            return Reply.Success(value=User.delete(id))
    except Exception as e:
        return Reply.Fail(message=str(e))


@app.route('/ajax/account/user/notify', methods=['PATCH'])
@login_required
def ajax_account_user_notify():
    '''Update user property yourself.'''
    user = User.query.get(int(session['user_id']))
    if user:
        nname = request.get_json().get('notify', 'NOT_USED')
        # print('B', nname, user.notify)
        op = request.get_json().get('operate').lower()
        if op == 'select':
            if nname == 'NOT_USED':
                user.notify = Notify.NAMES.get(nname)
            else:
                user.notify |= Notify.NAMES.get(nname)
        else:
            user.notify &= (Notify.ALL ^ Notify.NAMES.get(nname))
        db.session().commit()
        # print('A', user.notify)
        value = Dict()
        value.value = user.notify
        value.names = Notify.get_names(user.notify)
        # flash('Notify Email is Acceptance.', 'success')
        return Reply.Success(value=value)
    return Reply.Fail(message=f'No User: {session["user_id"]}')