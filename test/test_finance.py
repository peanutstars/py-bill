# -*- coding: utf-8 -*-

import unittest

from pysp.sbasic import SSingleton
from pysp.serror import SDebug

from core.cache import FCache
from core.finance import StockItemDB, DataCollection, BillConfig, StockQuery
from core.model import ServiceProvider, QueryData


class TestFinance(unittest.TestCase):
    spd = ServiceProvider(name='daum', codename='카카오', code='035720')
    spn = ServiceProvider(name='naver', codename='카카오', code='035720')
    spk = ServiceProvider(name='krx', codename='카카오', code='035720')

    def test_collect_data(self):
        log = SDebug()
        log.DEBUG = True

        f = DataCollection()
        # f.collect_candle(self.spd)
        f.collect_candle(self.spn)
        f.collect_investor(self.spn)
        f.collect_shortstock(self.spk)

        sp = DataCollection.factory_provider('035720', 'naver')
        self.assertTrue(sp.name == 'naver')
        self.assertTrue(sp.codename == '카카오')
        log.dprint(str(sp))
        sp = DataCollection.factory_provider('030200', 'naver')
        log.dprint(str(sp))

        f.collect('035720')
        f.collect('030200')
        f.collect('009150')
        del SSingleton._instances[FCache]

    def test_billconfig(self):
        bconfig = BillConfig()
        cvalue = bconfig.get_value('folder.user_config')
        self.assertTrue(cvalue == '/var/pybill/config/')
        self.assertTrue(bconfig is BillConfig())

    def test_stockquery(self):
        log = SDebug()
        log.DEBUG = True

        # get raw data
        code = '035720'
        sidb = StockItemDB.factory(code)
        tdata = StockQuery.raw_data(sidb, months=3)
        log.dprint(f'ColNames: {tdata.colnames}')
        log.dprint(f'SQL: {tdata.sql}')
        self.assertTrue(len(tdata.fields) > 10)
        for i, field in enumerate(tdata.fields):
            self.assertTrue(len(field) == len(tdata.colnames))
        # get raw date - start_date and end_date
        start_date = '2019.2.28'
        end_date = '2019.1.28'
        qda = StockQuery.raw_data(sidb, sdate=start_date, edate=end_date)
        qdb = StockQuery.raw_data(sidb, sdate=end_date, edate=start_date)
        self.assertTrue(len(qda.colnames), len(qdb.colnames))
        self.assertTrue(qda.sql == qdb.sql)
        self.assertTrue(len(qda.fields), len(qdb.fields))
        for x, field in enumerate(qda.fields):
            # log.dprint(f'{x} {field}')
            for y, c in enumerate(field):
                self.assertTrue(c == qdb.fields[x][y])
        # StockQuery.TradingAccumulator
        expected = [
            ['2019-01-28', 11366, -2969, -8397, None],
            ['2019-01-29', -10310, 29683, -19373, -25903],
            ['2019-01-30', -84400, -108169, 192569, -5184],
            ['2019-01-31', -156676, -256854, 413530, 19046],
            ['2019-02-01', -150096, -322488, 472584, -45847],
            ['2019-02-07', -184875, -350506, 535381, -58635],
            ['2019-02-08', -252447, -374938, 627385, -89576],
            ['2019-02-11', -467146, -541110, 1008256, -16089],
            ['2019-02-12', -553039, -580190, 1133229, -42115],
            ['2019-02-13', -523722, -595680, 1119402, -66656],
            ['2019-02-14', -412993, -459841, 872834, -138018],
            ['2019-02-15', -351215, -374411, 725626, -172396],
            ['2019-02-18', -362054, -344239, 706293, -190908],
            ['2019-02-19', -376019, -363627, 739646, -187127],
            ['2019-02-20', -401052, -428104, 829156, -155548],
            ['2019-02-21', -411358, -499224, 910582, -142351],
            ['2019-02-22', -451380, -499416, 950796, -114175],
            ['2019-02-25', -525672, -551588, 1077260, -55688],
            ['2019-02-26', -390375, -213506, 603881, -51690],
            ['2019-02-27', -300261, -139224, 439485, -96192],
            ['2019-02-28', -198527, -60789, 259316, -142114]
        ]
        expected_change_columns = [
            ['2019-01-28', 11366, -2969, -8397, None, 102000],
            ['2019-01-29', -10310, 29683, -19373, -25903, 102000],
            ['2019-01-30', -84400, -108169, 192569, -5184, 99900],
            ['2019-01-31', -156676, -256854, 413530, 19046, 99300],
            ['2019-02-01', -150096, -322488, 472584, -45847, 99600],
            ['2019-02-07', -184875, -350506, 535381, -58635, 99000],
            ['2019-02-08', -252447, -374938, 627385, -89576, 98200],
            ['2019-02-11', -467146, -541110, 1008256, -16089, 95600],
            ['2019-02-12', -553039, -580190, 1133229, -42115, 96000],
            ['2019-02-13', -523722, -595680, 1119402, -66656, 98100],
            ['2019-02-14', -412993, -459841, 872834, -138018, 100500],
            ['2019-02-15', -351215, -374411, 725626, -172396, 101500],
            ['2019-02-18', -362054, -344239, 706293, -190908, 102000],
            ['2019-02-19', -376019, -363627, 739646, -187127, 100000],
            ['2019-02-20', -401052, -428104, 829156, -155548, 99700],
            ['2019-02-21', -411358, -499224, 910582, -142351, 98900],
            ['2019-02-22', -451380, -499416, 950796, -114175, 99300],
            ['2019-02-25', -525672, -551588, 1077260, -55688, 98300],
            ['2019-02-26', -390375, -213506, 603881, -51690, 103500],
            ['2019-02-27', -300261, -139224, 439485, -96192, 105000],
            ['2019-02-28', -198527, -60789, 259316, -142114, 103500]
        ]

        # Case 1, StockQuery.TradingAccumulator
        items = ['stamp', 'foreigner', 'institute', 'person', 'shortamount']
        trandata = QueryData(colnames=items)
        # for x, field in enumerate(trandata.fields):
        #     log.dprint(f'{x} {field}')
        tacc = StockQuery.TradingAccumulator(items, qda.colnames)
        for field in qda.fields:
            trandata.fields.append(tacc.update(field))
        for x, field in enumerate(expected):
            # log.dprint(f'{x} {field}')
            for y, row in enumerate(field):
                self.assertTrue(row == trandata.fields[x][y])

        # Case 2, StockQuery.TradingAccumulator
        items = ['stamp', 'foreigner', 'institute', 'person', 'shortamount']
        trandata = QueryData(colnames=items)
        # for x, field in enumerate(trandata.fields):
        #     log.dprint(f'{x} {field}')
        tacc = StockQuery.TradingAccumulator(items, qda.colnames,
                                             amount_colname='shortamount')
        for field in qda.fields:
            trandata.fields.append(tacc.update(field))
        for x, field in enumerate(expected):
            log.dprint(f'{x} {field}')
            for y, row in enumerate(field):
                self.assertTrue(row == trandata.fields[x][y])

        # Case 3, StockQuery.TradingAccumulator
        items = ['stamp', 'foreigner', 'institute', 'person',
                 'shortamount', 'end']
        qda = StockQuery.raw_data(sidb, colnames=items,
                                  sdate=start_date, edate=end_date)
        trandata = QueryData(colnames=items)
        tacc = StockQuery.TradingAccumulator(items, qda.colnames,
                                             amount_colname='shortamount')
        for field in qda.fields:
            trandata.fields.append(tacc.update(field))
        # for x, field in enumerate(trandata.fields):
        #     log.dprint(f'{x} {field}')
        for x, field in enumerate(expected_change_columns):
            log.dprint(f'{x} {field}')
            for y, row in enumerate(field):
                self.assertTrue(row == trandata.fields[x][y])

        # get investor trading trand
        # Case 1
        trandata = StockQuery.get_investor_trading_trand(
                                sidb, sdate=start_date, edate=end_date)
        for x, field in enumerate(expected):
            # log.dprint(f'{x} {field}')
            for y, row in enumerate(field):
                self.assertTrue(row == trandata.fields[x][y])
        # Case 2
        trandata = StockQuery.get_investor_trading_trand(
                                sidb, sdate=start_date, months=1)
        for x, field in enumerate(expected):
            # log.dprint(f'{x} {field}')
            for y, row in enumerate(field):
                self.assertTrue(row == trandata.fields[x][y])
