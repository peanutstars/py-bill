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


class QueryData(dict):
    def __init__(self, **kwargs):
        super(QueryData, self).__init__()
        self['colnames'] = kwargs.get('colnames', [])
        self['fields'] = kwargs.get('fields', [])
        self['sql'] = kwargs.get('sql', None)

    def __getattr__(self, name):
        return self[name]
