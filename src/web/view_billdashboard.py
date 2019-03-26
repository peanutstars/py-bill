# import codecs
# import os
#
from flask import render_template  # session, request

from . import app
from .model import Reply
# from core.finance import BillConfig
from core.connect import FKrx


@app.route('/bill/dashboard')
def bill_dashboard():
    return render_template('pages/bill_dashboard.html')


@app.route('/ajax/stock/list', methods=['GET', 'POST'])
def ajax_stock_list():
    return Reply.Success(value=FKrx.get_chunk('list'))


@app.route('/ajax/stock/item/', defaults={'code': '035720'})
@app.route('/ajax/stock/item/<code>', methods=['GET', 'POST'])
def ajax_stock_item(code):
    return Reply.Success(value=code)
