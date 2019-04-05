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
