import codecs
import os

from flask import render_template, session, request
from pysp.sconf import SYAML

from . import app
from .model import Reply
from core.finance import BillConfig


@app.route('/')
def index():
    return render_template('pages/index.html')

@app.route('/ajax/bookmark', methods=['GET', 'POST'])
def ajax_bookmark():
    bcfg = BillConfig()
    bookmark = None
    if request.method == 'GET':
        if session and 'user_id' in session:
            bmfile = 'bookmark_userid_{uid:04d}.yml'
            _bookmark = bcfg.get_value('folder.bookmark')
            _bookmark += bmfile.format(uid=int(session['user_id']))
            if os.path.exists(_bookmark):
                bookmark = _bookmark
        if bookmark is None:
            _bookmark = bcfg.get_value('folder.bookmark')+'bookmark.yml'
            if os.path.exists(_bookmark):
                bookmark = _bookmark
        if bookmark is None:
            _bookmark = bcfg.get_value('folder.config')+'bookmark.yml'
            if os.path.exists(_bookmark):
                bookmark = _bookmark
        return Reply.Success(value=SYAML().load(bookmark))
        # return Reply.Fail(success=False, message='Fail Message Test')
    elif request.method == 'POST':
        content = request.get_json()
        if session and 'user_id' in session:
            bmfile = 'bookmark_userid_{uid:04d}.yml'
            _bookmark = bcfg.get_value('folder.bookmark')
            _bookmark += bmfile.format(uid=int(session['user_id']))
            with codecs.open(_bookmark, 'w', encoding='utf-8') as fd:
                fd.write(content['data'])
            msg = 'Stored to {}.'.format(os.path.basename(_bookmark))
            return Reply.Success(success=True, message=msg)
        return Reply.Fail(message='Need to log in.')
