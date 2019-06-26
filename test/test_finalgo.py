# -*- coding: utf-8 -*-

import codecs
import json
import os
import pickle
import unittest

from core.finance import StockItemDB, StockQuery
from core.finalgo import AlgoTable, IterAlgo


class TestAlgorithm(unittest.TestCase):

    def as_file(self, path, data):
        with codecs.open(path, 'w', encoding='utf-8') as fd:
            fd.write(IterAlgo.dump(data))
            fd.write(json.dumps(data))


    def test_AlgoTable(self):
        stockcode = '030200'
        # stockcode = '001800'
        # stockcode = '009150'
        sidb = StockItemDB.factory(stockcode)
        colnames = ['stamp', 'start', 'low', 'high', 'end', 'volume']
        qdata = StockQuery.raw_data_of_each_colnames(sidb, colnames, months=60)
        
        algo = AlgoTable(qdata)
        pdata = algo.process()

        pd = pickle.dumps(pdata)
        pickle.loads(pd)
    
    def test_IterAlgo(self):
        stockcode = '030200'
        index = 0
        
        data = IterAlgo.compute_index(stockcode, index)
        pd = pickle.dumps(data)
        pickle.loads(pd)

    # def test_adjust_split_stock(self):
    #     stockcode = '001800'
    #     rate = 20
    #     sdate = '2017-07-06'
    #     sidb = StockItemDB.factory(stockcode)
    #     rv = sidb.adjust_split_stock(rate, sdate)
    #     print('-----------------', rv)
    #     del sidb

    def test_load_brief(self):
        stockcode = '030200'
        data = IterAlgo.load_brief(stockcode, folder='./algo')
        # print(json.dumps(data))