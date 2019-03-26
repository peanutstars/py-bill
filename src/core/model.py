# -*- coding: utf-8 -*-

import collections


ServiceProvider = collections.namedtuple(
                    'ServiceProvider',
                    'name codename code')
StockDay = collections.namedtuple(
                    'StockDay',
                    'finance stamp start end high low volume')
StockDayInvestor = collections.namedtuple(
                    'StockDayInvestor',
                    'stamp foreigner frate institute person')
StockDayShort = collections.namedtuple(
                    'StockDayShort',
                    'stamp short shortamount')


class TableData:
    def __init__(self, **kwargs):
        self.colnames = kwargs.get('colnames', None)
        self.fields = kwargs.get('fields', None)
        self.sql = kwargs.get('sql', None)
