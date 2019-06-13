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


    def test_fetch_finance_data(self):
        stockcode = '030200'
        # stockcode = '001800'
        # stockcode = '009150'
        sidb = StockItemDB.factory(stockcode)
        colnames = ['stamp', 'start', 'low', 'high', 'end', 'volume']
        qdata = StockQuery.raw_data_of_each_colnames(sidb, colnames, months=60)
        
        # it = IterAlgo()
        # sim = it.run(qdata)
        # data_folder = f'STalk_{stockcode}'
        # if not os.path.exists(data_folder):
        #     os.mkdir(data_folder)

        # for i, v in enumerate(sim.too_much):
        #     sfile = f'{data_folder}/too_much{i+1:03d}.log'
        #     self.as_file(sfile, v)

        # for i, v in enumerate(sim.per_day):
        #     sfile = f'{data_folder}/per_day{i+1:03d}.log'
        #     self.as_file(sfile, v)

        # for i, v in enumerate(sim.ecount):
        #     sfile = f'{data_folder}/ecount{i+1:03d}.log'
        #     self.as_file(sfile, v)

        algo = AlgoTable(qdata)
        pdata = algo.process()

        pd = pickle.dumps(pdata)
        pickle.loads(pd)

        # print('Report', pdata.report)
        # print(json.dumps(pdata))      