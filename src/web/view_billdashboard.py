# import codecs
# import os
#
from flask import render_template
from flask_login import login_required

from . import app
from .model import Reply
# from core.finance import BillConfig
from core.connect import FKrx
from core.finance import StockItemDB, StockQuery


@app.route('/bill/dashboard')
@login_required
def bill_dashboard():
    return render_template('pages/bill_dashboard.html')


@app.route('/ajax/stock/list', methods=['GET', 'POST'])
@login_required
def ajax_stock_list():
    return Reply.Success(value=FKrx.get_chunk('list'))


@app.route('/ajax/stock/item/<code>/investor/<month>', methods=['GET', 'POST'])
@login_required
def ajax_stock_item_investor(code, month):
    sidb = StockItemDB.factory(code)
    tradedata = StockQuery.get_investor_trading_trand(sidb, months=int(month))
    return Reply.Success(value=Reply.Data(tradedata.to_dict()))
