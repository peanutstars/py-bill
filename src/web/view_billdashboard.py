# import codecs
# import os
#
from flask import render_template, abort
from flask_login import login_required

from . import app
from .model import Reply
# from core.finance import BillConfig
from core.connect import FKrx
from core.finance import DataCollection, StockItemDB, StockQuery


@app.route('/bill/dashboard')
@login_required
def bill_dashboard():
    return render_template('pages/bill_dashboard.html')


@app.route('/bill/stock/', defaults={"code": None})
@app.route('/bill/stock/<code>')
@login_required
def bill_stock(code):
    if code is None:
        return render_template('pages/bill_stock.html')
    try:
        provider = DataCollection.factory_provider(code, 'krx')
    except DataCollection.Error:
        abort(404)
    extra_info = {'code': code,
                  'codename': provider.codename}
    return render_template('pages/bill_stock_code.html', extra_info=extra_info)


@app.route('/ajax/stock/list', methods=['GET', 'POST'])
@login_required
def ajax_stock_list():
    return Reply.Success(value=FKrx.get_chunk('list'))


@app.route('/ajax/stock/item/<code>/investor/<month>', methods=['GET', 'POST'])
@login_required
def ajax_stock_item_investor(code, month):
    sidb = StockItemDB.factory(code)
    tradedata = StockQuery.get_investor_trading_trand(sidb, months=int(month))
    return Reply.Success(value=Reply.Data(tradedata))
