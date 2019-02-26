import os

from flask import render_template, session
from pysp.sconf import SYAML

from . import app
from .model import Reply
from core.finance import BillConfig


@app.route('/')
def index():
    return render_template('pages/index.html')

@app.route('/ajax/bookmark', methods=['GET'])
def ajax_bookmark():
    bcfg = BillConfig()
    bookmark = None
    if session and 'user_id' in session:
        _bookmark = bcfg.get_value('folder.user_config')
        if session['user_id'] == '1':
            _bookmark += 'bookmark.yml'
        else:
            _bookmark += 'bookmark_userid_'+session['user_id']+'.yml'
        if os.path.exists(_bookmark):
            bookmark = _bookmark
    if bookmark is None:
        _bookmark = bcfg.get_value('folder.user_config')+'bookmark.yml'
        if os.path.exists(_bookmark):
            bookmark = _bookmark
    if bookmark is None:
        _bookmark = bcfg.get_value('folder.config')+'bookmark.yml'
        if os.path.exists(_bookmark):
            bookmark = _bookmark
    return Reply.Success(success=True, value=SYAML().load(bookmark))
    # return Reply.Fail(success=False, errmsg='Fail Message Test')
