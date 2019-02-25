import datetime

from flask import jsonify
from flask_login import UserMixin
from . import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True)
    username = db.Column(db.String(32))
    password = db.Column(db.String(100))
    registered_date = db.Column(db.DateTime, default=datetime.datetime.now)


class Reply:

    @classmethod
    def Success(cls, **kwargs):
        success = kwargs.get('success', True)
        errmsg = kwargs.get('errmsg', None)
        value = kwargs.get('value', None)
        return jsonify(success=success, errmsg=errmsg, value=value)

    @classmethod
    def Fail(cls, **kwargs):
        success = kwargs.get('success', False)
        errmsg = kwargs.get('emsg', 'Failed')
        value = kwargs.get('value', None)
        return jsonify(success=success, errmsg=errmsg, value=value)
