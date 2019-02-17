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
