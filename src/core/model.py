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
        self.colnames = kwargs.get('colnames', [])
        self.fields = kwargs.get('fields', [])
        self.sql = kwargs.get('sql', None)

    def to_dict(self):
        return {
            'colnames': self.colnames,
            'fields': self.fields,
            'sql': self.sql
        }
