import codecs
import os

from flask import render_template, session, request
from pysp.sconf import SYAML

from . import app
from .model import Reply
from core.finance import BillConfig


@app.route('/bill/dashboard')
def bill_dashboard():
    return render_template('pages/bill_dashboard.html')
