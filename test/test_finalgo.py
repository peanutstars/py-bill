# -*- coding: utf-8 -*-

import json
import unittest

from core.finance import StockItemDB, StockQuery
from core.finalgo import AlgoTable


class TestAlgorithm(unittest.TestCase):

    def test_fetch_finance_data(self):
        stockcode = '030200'
        # stockcode = '001800'
        # stockcode = '009150'
        sidb = StockItemDB.factory(stockcode)
        colnames = ['stamp', 'start', 'low', 'high', 'end', 'volume']
        qdata = StockQuery.raw_data_of_each_colnames(sidb, colnames, months=60)
        
        algo = AlgoTable(qdata)
        pdata = algo.process()
        print('Report', pdata.report)
        print(json.dumps(pdata))

        
