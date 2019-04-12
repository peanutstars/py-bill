import datetime

from flask import jsonify, request
from flask_login import UserMixin
from . import db


class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True)
    username = db.Column(db.String(32))
    password = db.Column(db.String(100))
    registered_date = db.Column(db.DateTime, default=datetime.datetime.now)
    stocks = db.relationship('MStock', backref='author', lazy=True)


class MStock(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8))
    name = db.Column(db.String(32))
    atime = db.Column(db.DateTime, default=datetime.datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    __table_args__ = (db.UniqueConstraint('user_id', 'code',
                                          name='_user_id_code'),)


class Reply:
    @classmethod
    def Success(cls, **kwargs):
        data = {}
        data['success'] = kwargs.get('success', True)
        data['message'] = kwargs.get('message', None)
        data['value'] = kwargs.get('value', None)
        return jsonify(data)

    @classmethod
    def Fail(cls, **kwargs):
        data = {}
        data['success'] = kwargs.get('success', False)
        data['message'] = kwargs.get('message', 'Failed')
        data['value'] = kwargs.get('value', None)
        return jsonify(data)

    @classmethod
    def Data(cls, data):
        if isinstance(data, dict):
            data['request'] = {}
            data['request']['url'] = request.url
            data['request']['path'] = request.path
            data['request']['method'] = request.method
        return data
