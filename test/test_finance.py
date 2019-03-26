# -*- coding: utf-8 -*-

import datetime
import unittest

from pysp.sbasic import SSingleton

from core.cache import FileCache
from core.finance import StockItemDB, DataCollection, BillConfig, StockQuery
from core.model import ServiceProvider


class TestFinance(unittest.TestCase):
    spd = ServiceProvider(name='daum', codename='카카오', code='035720')
    spn = ServiceProvider(name='naver', codename='카카오', code='035720')
    spk = ServiceProvider(name='krx', codename='카카오', code='035720')

    def test_collect_data(self):
        # FNaver.DEBUG = True

        f = DataCollection()
        # f.collect_candle(self.spd)
        f.collect_candle(self.spn)
        f.collect_investor(self.spn)
        f.collect_shortstock(self.spk)

        sp = DataCollection.factory_provider('035720', 'naver')
        self.assertTrue(sp.name == 'naver')
        self.assertTrue(sp.codename == '카카오')
        print(sp)
        sp = DataCollection.factory_provider('030200', 'naver')
        print(sp)

        f.collect('035720')
        f.collect('030200')
        del SSingleton._instances[FileCache]

    def test_billconfig(self):
        bconfig = BillConfig()
        cvalue = bconfig.get_value('folder.user_config')
        self.assertTrue(cvalue == '/var/pybill/config/')
        self.assertTrue(bconfig is BillConfig())

    def test_stockquery(self):
        sq = StockQuery()
        date1_forms = ['2019.3.4',  '2019-03-04', '20190304']
        date2_forms = ['2019.3.14', '2019-03-14', '20190314']
        date1_expected = StockQuery.to_strfdate(datetime.datetime(2019, 3, 4))
        date2_expected = StockQuery.to_strfdate(datetime.datetime(2019, 3, 14))
        for form in date1_forms:
            rv = sq.to_strfdate(sq.to_datetime(form))
            self.assertEqual(rv, date1_expected)
        for form in date2_forms:
            rv = sq.to_strfdate(sq.to_datetime(form))
            self.assertEqual(rv, date2_expected)
        # Generate data
        code = '030200'
        sidb = StockItemDB.factory(code)
        tdata = StockQuery.raw_data(sidb, months=3)
        print('ColNames:', tdata.colnames)
        print('SQL:', tdata.sql)
        self.assertTrue(len(tdata.fields) > 10)
        for i, field in enumerate(tdata.fields):
            self.assertTrue(len(field) == len(tdata.colnames))
