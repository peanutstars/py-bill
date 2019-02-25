import os

from flask import render_template, session, jsonify
from pysp.sconf import SYAML

from . import app
from .model import Reply


@app.route('/')
def index():
    return render_template('pages/index.html')

@app.route('/ajax/bookmark')
def ajax_bookmark():
    folder = os.path.dirname(os.path.abspath(__file__))
    bmfile = f'{folder}/../config/bookmark.yml'
    # return ReplyJSON.success(success=True, value=SYAML().load(bmfile))
    return Reply.Success(success=True, value=SYAML().load(bmfile))
