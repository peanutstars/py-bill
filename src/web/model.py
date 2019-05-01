import datetime

from flask import jsonify, request
from flask_login import UserMixin
from . import db


class Role:
    TYPE = {
        'ADMIN':    100,
        'STOCK':    300,
        'BOOKMARK': 600,
        'NONE':     900,
    }

    @classmethod
    def is_permission(cls, required, user):
        return cls.TYPE.get(required, 'NONE') >= cls.TYPE.get(user)


class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True)
    username = db.Column(db.String(32))
    password = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=False)
    # role = db.Column(db.String(32), default="BOOKMARK")
    registered_date = db.Column(db.DateTime, default=datetime.datetime.now)
    stocks = db.relationship('MStock', backref='author', lazy=True)

    @property
    def is_active(self):
        return self.active

    # def is_permission(self, required):
    #     return Role.is_permission(required, self.role)

    @classmethod
    def info(cls, id):
        user = User.query.get(int(id))
        if user:
            info = {}
            for k, v in vars(user).items():
                if k[0] == '_' or k == 'password':
                    continue
                info[k] = v
            return info
        raise KeyError(f'ID={id} Is Not Exist.')

    @classmethod
    def update(cls, id, **kwargs):
        id = int(id)
        if id == 1:
            raise KeyError(f'Permission Error')
        user = User.query.get(int(id))
        for k, v in kwargs.items():
            if k in ['password', 'email']:
                KeyError(f'"{k}" Column Is Not Allowed.')
            if hasattr(user, k):
                setattr(user, k, v)
                continue
            raise KeyError(f'"{k}" Is Not Member.')
        db.session.commit()

    @classmethod
    def delete(cls, id):
        id = int(id)
        if id == 1:
            raise KeyError(f'Permission Error.')
        user = User.query.get(int(id))
        if user:
            db.session.delete(user)
            db.session.commit()
            return
        raise KeyError(f'ID={id} Is Not Exist.')


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
