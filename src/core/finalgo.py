#!/usr/bin/env python3

import codecs
import hashlib
import itertools
import json
import multiprocessing
import os

from collections import namedtuple

from pysp.serror import SDebug

from core.model import Dict
from core.finance import StockItemDB, StockQuery


StepParam = namedtuple('StepParam', 'gradnames stepname')


class Algo:
    class Error(Exception):
        pass

    def _fill_data(self, idxs, values, field):
        if len(field) == idxs[0]:
            [field.append(x) for x in values]
            return
        for i, ix in enumerate(idxs):
            field[ix] = values[i]


class AlgoOp(Algo):
    def generate(self, idx, fields):
        raise NotImplementedError(f'{self.__class__.__name__}.generate')


class AlgoProc(Algo):
    def process(self, idx, fields):
        raise NotImplementedError(f'{self.__class__.__name__}.process')

    def _check_array(self, idxs, values, field):
        if len(idxs) != len(values):
            raise Algo.Error('Not Enough each Count of Parameter.')
        return [field[x] for x in idxs]

    def is_all(self, idxs, values, field, **kwargs):
        fvalues = self._check_array(idxs, values, field)
        return all([x==y for x, y in zip(fvalues, values) if y is not None])

    def is_any(self, idxs, values, field, **kwargs):
        none_skip = kwargs.get('none_skip', True)
        fvalues = self._check_array(idxs, values, field)
        if none_skip:
            return any([x==y for x, y in zip(fvalues, values) if y is not None])
        return any([x==y for x, y in zip(fvalues, values)])

    def is_le_all(self, idxs, values, field):
        fvalues = self._check_array(idxs, values, field)
        return all([x<=y for x, y in zip(fvalues, values) if y is not None])

    def is_ge_all(self, idxs, values, field):
        fvalues = self._check_array(idxs, values, field)
        return all([x>=y for x, y in zip(fvalues, values) if y is not None])

    def is_ge_any(self, idxs, values, field):
        fvalues = self._check_array(idxs, values, field)
        return any([x>=y for x, y in zip(fvalues, values) if y is not None])

    def is_or(self, cmds, idxs, array, field):
        _cmds = cmds
        if type(cmds) is str:
            _cmds = [cmds] * len(array)
        if type(array) is list and type(array[0]) is list:
            for i, a in enumerate(array):
                cmd = _cmds[i]
                if not hasattr(self, cmd):
                    raise Algo.Error(f'"{cmd}" Is Not Exist.')
                _cmd = getattr(self, cmd)
                _v = _cmd(idxs, a, field)
                if _v:
                    return _v
            return False
        raise Algo.Error('It Is Not A Double-List.')


class OpPrice(AlgoOp):
    TRADE_UNIT = {
        1000: 1,
        5000: 5,
        10000: 10,
        50000: 50,
        100000: 100,
        500000: 500,
        10000000: 1000
    }

    # def __init__(self, refcolname, buy, sell, colnames):
    def __init__(self, cfg, colnames):
        colnames.append(cfg.price.buy.colname)
        colnames.append(cfg.price.sell.colname)
        self.ilow = colnames.index(cfg.price.ref_colname.low)
        self.ihigh = colnames.index(cfg.price.ref_colname.high)
        self.ibprice = colnames.index(cfg.price.buy.colname)
        self.isprice = colnames.index(cfg.price.sell.colname)
        self.bpercent = cfg.price.buy.percent
        self.spercent = cfg.price.sell.percent

    @classmethod
    def to_unit_price(cls, price, roundup):
        uprice = price
        for k, v in cls.TRADE_UNIT.items():
            if price < k:
                mod = price % v
                # print('@', k, v)
                if (mod) == 0:
                    break
                uprice = (price-mod+v) if roundup else (price-mod)
                break
        # print('@', roundup, price, uprice)
        return uprice

    def generate(self, idx, fields):
        buyprice = None
        sellprice = None
        field = fields[idx]
        lowprice = field[self.ilow]
        highprice = field[self.ihigh]
        if lowprice is not None and highprice is not None:
            buyprice = lowprice + int((highprice-lowprice)*self.bpercent/100)
            buyprice = self.to_unit_price(buyprice, roundup=True)
            sellprice = lowprice + int((highprice-lowprice)*self.spercent/100)
            sellprice = self.to_unit_price(sellprice, roundup=False)
        indexes = [self.ibprice, self.isprice]
        values =[buyprice, sellprice]
        self._fill_data(indexes, values, field)


class OpSumAvg(AlgoOp):
    def __init__(self, accum, colnames):
        super(OpSumAvg, self).__init__()
        self.name = f's{accum}Av'
        colnames.append(self.name)
        self.iend = colnames.index('end')
        self.iself = colnames.index(self.name)
        self.accum = accum
        self.items = []
    
    def generate(self, idx, fields):
        avg = None
        data = fields[idx][self.iend]
        if len(self.items) == self.accum:
            avg = int(sum(self.items)/self.accum)
            self.items.pop(0)
        self.items.append(data)
        self._fill_data([self.iself], [avg], fields[idx])


class OpGradient(AlgoOp):
    def __init__(self, cfg, colname, colnames):
        super(OpGradient, self).__init__()
        self.name = f'{colname}Gt'
        colnames.append(self.name)
        self.icolname = colnames.index(colname)
        self.iself = colnames.index(self.name)
        self.accum = cfg.gradient.accum
        self.items = []
    
    def generate(self, idx, fields):
        gradient = None
        data = fields[idx][self.icolname]
        if data:
            if len(self.items) == self.accum:
                gradient = int((self.items[-1] - self.items[0])/(self.accum-1))
                self.items.pop(0)
            self.items.append(data)
        self._fill_data([self.iself], [gradient], fields[idx])


class Curve:
    HIGH = 3
    UP =   2
    LOW =  1
    DOWN = 0

    STEP = {
        HIGH: 'HH',
        UP:   'UP',
        LOW:  'LW',
        DOWN: 'DN'
    }


class OpCurveStep(AlgoOp):
    STEP = [Curve.DOWN, Curve.HIGH, Curve.LOW, Curve.UP]

    def __init__(self, std_colnames, stepname, colnames):
        super(OpCurveStep, self).__init__()
        self.name = f'{stepname}'
        self.stepname = f'{stepname}Md'
        colnames.append(self.name)
        colnames.append(self.stepname)
        self.igradients = [colnames.index(x) for x in std_colnames]
        self.istep = colnames.index(self.name)
        self.istepname = colnames.index(self.stepname)
    
    def generate(self, idx, fields):
        step = None
        stepname = None
        gt1st = fields[idx][self.igradients[0]]
        gt2nd = fields[idx][self.igradients[1]]
        if gt1st is not None and gt2nd is not None:
            step = self.STEP[(gt1st>0)*2 + (gt2nd>0)*1]
            stepname = Curve.STEP.get(step)

        # print('@', idx, len(fields[idx]), self.istep, self.name, self.stepname)
        self._fill_data([self.istep, self.istepname], [step, stepname], fields[idx])


class OpMinMax(AlgoOp):
    COLNAME_PERCENT = 'pct{}m'

    def __init__(self, accum, colnames):
        super(OpMinMax, self).__init__()
        self.minname = f'min{accum}m'
        self.maxname = f'max{accum}m'
        self.pctname = self.COLNAME_PERCENT.format(accum)  # f'pct{accum}m'
        colnames.append(self.minname)
        colnames.append(self.maxname)
        colnames.append(self.pctname)
        self.iend = colnames.index('end')
        self.imin = colnames.index(self.minname)
        self.imax = colnames.index(self.maxname)
        self.ipct = colnames.index(self.pctname)
        self.accum = accum*5*4
        self.items = []
    
    def generate(self, idx, fields):
        minvalue = None
        maxvalue = None
        percent = None
        data = fields[idx][self.iend]
        if len(self.items) == self.accum:
            minvalue = min(self.items)
            maxvalue = max(self.items)
            # print('@', self.pctname, minvalue, maxvalue, data)
            if minvalue == maxvalue:
                percent = 0 if data < minvalue else 100
            else:
                percent = int((data-minvalue)/(maxvalue-minvalue)*100)
            self.items.pop(0)
        self.items.append(data)
        self._fill_data([self.imin, self.imax, self.ipct], 
                        [minvalue, maxvalue, percent], fields[idx])


class CondBuy(AlgoProc):
    COLNAME_BUYCNT =        'buycnt'
    COLNAME_BUYREASON =     'breason'
    COLNAME_AFTER_HHUPUP =  'afhuu'
    HERE_IT_GO =            15

    def __init__(self, cfg, colnames):
        super(CondBuy, self).__init__()
        accums = cfg.sum.accums
        colnames.append(self.COLNAME_AFTER_HHUPUP)
        colnames.append(self.COLNAME_BUYCNT)
        colnames.append(self.COLNAME_BUYREASON)
        self.istamp = colnames.index('stamp')
        self.ihhupup = colnames.index(self.COLNAME_AFTER_HHUPUP)
        self.ibcnt = colnames.index(self.COLNAME_BUYCNT)
        self.ibreason = colnames.index(self.COLNAME_BUYREASON)
        _curve_step = AlgoTable.get_curve_step_colname
        self.steps = [f'{_curve_step(x, accums)}Md' for x in range(len(accums))]
        self.isteps = [colnames.index(x) for x in self.steps]
        _minmax_percent = OpMinMax.COLNAME_PERCENT.format
        self.percents = [_minmax_percent(x) for x in cfg.minmax.accums]
        self.ipercents = [colnames.index(x) for x in self.percents]
        self.after_hhupup = 0
        self.start = False

    def init_extra_columns(self, cfg, colnames):
        self.ibprice = colnames.index(cfg.price.buy.colname)
        self.ibaverage = colnames.index(CalBuy.COLNAME_BUY_AVERAGE)

    def is_skipped(self, field):
        if self.is_any(self.isteps, [None]*len(self.isteps), field, none_skip=False):
            return True
        if self.is_any(self.ipercents, [None]*len(self.ipercents), field, none_skip=False):
            return True
        return False

    def process(self, cfg, idx, fields):
        buycnt = 0
        buyreason = ''

        field = fields[idx]
        fg_skip = self.is_skipped(field)
        
        while True:
            if fg_skip:
                break
            # Check Starting Condition
            if self.start is False and self.is_all(self.isteps, ['DN','DN','DN'], field):
                self.start = True
                cfg.algo.start.stamp = field[self.istamp]

            if self.is_or('is_all', self.isteps, [['HH','UP','UP']], field):
                if self.after_hhupup <= 0:
                    self.after_hhupup = cfg.buy.after.hhupup.begin 
                else:
                    self.after_hhupup += cfg.buy.after.hhupup.append
            elif self.is_or('is_all', self.isteps,
                            [['HH','UP',None], ['LW','HH',None]], field):
                if self.after_hhupup <= 0:
                    self.after_hhupup = cfg.buy.after.hhupup.hhup_lwhh.begin
                else:
                    self.after_hhupup += cfg.buy.after.hhupup.hhup_lwhh.append
            else:
                self.after_hhupup -= 1
                if self.after_hhupup < 0:
                    self.after_hhupup = 0

            if self.is_or(['is_all','is_any'], self.isteps, 
                          [['UP','UP','UP'], ['HH','HH','HH']], field):
                break

            if self.is_or('is_any', self.isteps, [['DN','DN','DN']], field):
                if self.is_or('is_all', self.isteps, [['LW','DN','DN']], field):
                    buycnt = self.HERE_IT_GO
            elif self.is_or('is_all', self.isteps, [['HH','UP',None]], field):
                pass
            else:
                buycnt = self.HERE_IT_GO

            if self.is_or('is_ge_any', self.ipercents, [[90,80,None,60,60,None]], field):
                buycnt = 0
                break
            elif self.is_or('is_le_all', self.ipercents, 
                            [[0,0,0,0,0,0], [10,10,10,10,10,25]], field):
                buycnt = self.HERE_IT_GO

            if buycnt > 0:
                if self.start is False or self.after_hhupup > cfg.buy.after.hhupup.thresholds:
                    buycnt = 0

            # Additional purchase
            prevfield = fields[idx-1]
            baverage = prevfield[self.ibaverage]
            if baverage and baverage > field[self.ibprice]:
                buycnt = self.HERE_IT_GO

            break  # End of While

        if not fg_skip:
            buyreason += ':'.join([str(field[x]) for x in self.isteps])
            buyreason += '@'+':'.join([str(field[x]) for x in self.ipercents])
            
        indexes = [self.ihhupup, self.ibcnt, self.ibreason]
        values = [self.after_hhupup, buycnt, buyreason]
        self._fill_data(indexes, values, field)


class CalBuy(AlgoProc):
    COLNAME_BUY_VOLUME =    'bvolume'
    COLNAME_BUY_AMOUNT =    'bamount'
    COLNAME_BUY_AVERAGE =   'bavg'

    def __init__(self, cfg, colnames):
        super(CalBuy, self).__init__()
        colnames.append(self.COLNAME_BUY_VOLUME)
        colnames.append(self.COLNAME_BUY_AMOUNT)
        colnames.append(self.COLNAME_BUY_AVERAGE)
        self.ibcnt = colnames.index(CondBuy.COLNAME_BUYCNT)
        self.ibprice = colnames.index(cfg.price.buy.colname)
        self.ivolume = colnames.index(self.COLNAME_BUY_VOLUME)
        self.iamount = colnames.index(self.COLNAME_BUY_AMOUNT)
        self.iaverage = colnames.index(self.COLNAME_BUY_AVERAGE)
        self.reset()

    def reset(self, **kwargs):
        self.volume = kwargs.get('volume',0)
        self.amount = kwargs.get('amount',0)
        self.average = kwargs.get('average',0)
        field = kwargs.get('field', None)
        if field:
            indexes = [self.ivolume, self.iamount, self.iaverage]
            values = [self.volume, self.amount, self.average]
            self._fill_data(indexes, values, field)

    def process(self, cfg, idx, fields):
        field = fields[idx]
        indexes = [self.ivolume, self.iamount, self.iaverage]

        buy_count = field[self.ibcnt]
        bprice = field[self.ibprice]
        if buy_count > 0 and bprice > 0:
            self.volume += 1
            self.amount += (1 * field[self.ibprice])
            self.average = int(self.amount / self.volume)

        values = [self.volume, self.amount, self.average]
        self._fill_data(indexes, values, field)


class CondSell(AlgoProc):
    COLNAME_SELL_POINT =    'sellcnt'
    COLNAME_SELL_REASON =   'sreason'
    HERE_IT_GO =            15

    def __init__(self, cfg, colnames):
        super(CondSell, self).__init__()
        accums = cfg.sum.accums
        colnames.append(self.COLNAME_SELL_POINT)
        colnames.append(self.COLNAME_SELL_REASON)
        self.iscnt = colnames.index(self.COLNAME_SELL_POINT)
        self.isreason = colnames.index(self.COLNAME_SELL_REASON)
        self.isprice = colnames.index(cfg.price.sell.colname)
        self.ibvolume = colnames.index(CalBuy.COLNAME_BUY_VOLUME)
        self.ibaverage = colnames.index(CalBuy.COLNAME_BUY_AVERAGE)
        _curve_step = AlgoTable.get_curve_step_colname
        self.steps = [f'{_curve_step(x, accums)}Md' for x in range(len(accums))]
        self.isteps = [colnames.index(x) for x in self.steps]
        _minmax_percent = OpMinMax.COLNAME_PERCENT.format
        self.percents = [_minmax_percent(x) for x in cfg.minmax.accums]
        self.ipercents = [colnames.index(x) for x in self.percents]
        self.std_hhupup = int(cfg.buy.after.hhupup.begin/2)
        self.ihhupup = colnames.index(CondBuy.COLNAME_AFTER_HHUPUP)
        self.rrate = 1.0 + cfg.price.sell.return_rate/100.0
        self.method = cfg.sell.method

    def process(self, cfg, idx, fields):
        sellcnt = 0
        sreason = ''
        field = fields[idx]

        if field[self.ibvolume] > 0:
            # if self.method == 1:
            #     if self.is_any(self.isteps, ['HH','HH',None], field):
            #         # XXX: Added New Condition
            #         # if self.is_ge_any(self.ipercents, [150,130,110,100,None,None], field):
            #         #    if field[self.ihhupup] >= self.std_hhupup:
            #         wanted = field[self.ibaverage]*self.rrate
            #         if field[self.isprice] > wanted:
            #             sellcnt = self.HERE_IT_GO

            # if self.method == 2:
            #     if self.is_any(self.isteps, ['HH','HH',None], field):
            #         # XXX: Added New Condition
            #         if self.is_ge_any(self.ipercents, [150,125,105,95,None,None], field):
            #             if field[self.ihhupup] >= self.std_hhupup:
            #                 wanted = field[self.ibaverage]*self.rrate
            #                 if field[self.isprice] > wanted:
            #                     sellcnt = self.HERE_IT_GO

            if self.method == 3:
                if self.is_any(self.isteps, ['HH','HH',None], field) or \
                self.is_or('is_all', self.isteps, [['DN','UP',None], ['LW','UP',None]], field):
                    # XXX: Added New Condition
                    if self.is_ge_any(self.ipercents, [150,125,105,95,None,None], field):
                        if field[self.ihhupup] >= self.std_hhupup:
                            wanted = field[self.ibaverage]*self.rrate
                            if field[self.isprice] > wanted:
                                sellcnt = self.HERE_IT_GO

            if self.method == 4:
                if self.is_any(self.isteps, ['HH','HH',None], field) or \
                self.is_or('is_all', self.isteps, [['DN','UP',None], ['LW','UP',None]], field):
                    # XXX: Added New Condition
                    # if self.is_ge_any(self.ipercents, [150,130,110,95,None,None], field):
                    if field[self.ihhupup] >= self.std_hhupup:
                        wanted = field[self.ibaverage]*self.rrate
                        if field[self.isprice] > wanted:
                            sellcnt = self.HERE_IT_GO

        indexes = [self.iscnt, self.isreason]
        values = [sellcnt, sreason]
        self._fill_data(indexes, values, field)


class CalSell(AlgoProc):
    COLNAME_SELL_AMOUNT =   'samount'
    COLNAME_SELL_PROFIT =   'profit'
    WORK_DAYS_PER_YEAR =    245

    def __init__(self, cfg, colnames, calbuy):
        super(CalSell, self).__init__()
        self.cfg = cfg
        self.calbuy = calbuy
        colnames.append(self.COLNAME_SELL_AMOUNT)
        colnames.append(self.COLNAME_SELL_PROFIT)
        self.isamount = colnames.index(self.COLNAME_SELL_AMOUNT)
        self.iprofit = colnames.index(self.COLNAME_SELL_PROFIT)
        self.ibamount = colnames.index(CalBuy.COLNAME_BUY_AMOUNT)
        self.ivolume = colnames.index(CalBuy.COLNAME_BUY_VOLUME)
        self.iscnt = colnames.index(CondSell.COLNAME_SELL_POINT)
        self.isprice = colnames.index(cfg.price.sell.colname)
        self.investment_amount = 0
        self.earnings_amount = 0
        self.investment_days = 0
        self.earnings_count = 0
        self.earnings_last_count = 0
    
    def get_report(self):
        def to_float(x):
            return float('{:.2f}'.format(x))
        report = Dict()
        report.investment_amount = self.investment_amount
        report.earnings_amount = self.earnings_amount
        profit = 0
        if self.investment_amount > 0:
            profit = (self.earnings_amount/self.investment_amount*100)-100
        report.return_rate = to_float(profit)
        report.investment_days = self.investment_days
        report.earnings_count = self.earnings_count
        report.earnings_last_count = self.earnings_last_count
        return report

    def process(self, cfg, idx, fields):
        amount = None
        profit = None
        field = fields[idx]

        sprice = field[self.isprice]
        if field[self.iscnt] > 0 and sprice > 0:
            amount = field[self.ivolume] * sprice
            profit = '{:.2f}'.format((amount/field[self.ibamount]*100)-100)
            self.investment_amount += field[self.ibamount]
            self.earnings_amount += amount
            self.earnings_count += 1
            if idx >= (len(fields)-self.WORK_DAYS_PER_YEAR):
                self.earnings_last_count += 1
            self.calbuy.reset(field=field)

        if field[self.ivolume] > 0:
            self.investment_days += 1

        indexes = [self.isamount, self.iprofit]
        values = [amount, profit]
        self._fill_data(indexes, values, field)


class AlgoTable:
    NAME = 'JNLON'

    def __init__(self, qdata, cfg=None):
        self.qdata = Dict(json.loads(json.dumps(qdata)))
        self.operate = []
        qcolnames = self.qdata.colnames
        self.cfg = self.default_option() if cfg is None else cfg

        self.operate.append(OpPrice(self.cfg, qcolnames))
        self.operate.append(OpGradient(self.cfg, 'end', qcolnames))
        for sa in self.cfg.sum.accums:
            op = OpSumAvg(sa, qcolnames)
            self.operate.append(op)
            self.operate.append(OpGradient(self.cfg, op.name, qcolnames))
        for p in self.cfg.curve.step:
            self.operate.append(OpCurveStep(p.gradnames, p.stepname, qcolnames))
        for mm in self.cfg.minmax.accums:
            self.operate.append(OpMinMax(mm, qcolnames))

        self.generate()

    @classmethod
    def default_option(cls):
        cfg = Dict()
        cfg.algo.index = None
        cfg.algo.start.stamp = None
        cfg.gradient.accum = 5
        cfg.sum.accums = [3, 6, 12]                 # [2..5][4..10][8..20]
        cfg.minmax.accums = [1, 2, 3, 6, 9, 12]     # [1, 2, 4, 8, 12, 18]
        cfg.curve.step = cls.get_curve_step_params(cfg.sum.accums)
        cfg.price.ref_colname.low = 'low'
        cfg.price.ref_colname.high = 'high'
        cfg.price.buy.colname = 'bprice'
        cfg.price.buy.percent = 50
        cfg.price.sell.colname = 'sprice'
        cfg.price.sell.percent = 50
        cfg.price.sell.return_rate = 7              # [5..15]
        cfg.buy.after.hhupup.begin = 15             # [7..20]
        cfg.buy.after.hhupup.append = 4             # [2..8]
        cfg.buy.after.hhupup.hhup_lwhh.begin = 5    # [3..8]
        cfg.buy.after.hhupup.hhup_lwhh.append = 2   # [1..5]
        cfg.buy.after.hhupup.thresholds = 0         # [0..7]
        cfg.sell.method = 4
        return cfg

    @classmethod
    def get_curve_step_colname(cls, i, accums):
        if i == 0:
            return f'et{accums[i]}Sp'
        return f'{accums[i-1]}t{accums[i]}Sp'

    @classmethod
    def get_curve_step_params(cls, accums):
        params = []
        for i in range(len(accums)):
            if i == 0:
                p = StepParam(
                        ['endGt', f's{accums[i]}AvGt'], 
                        cls.get_curve_step_colname(i, accums))
                params.append(p)
                continue
            p = StepParam(
                        [f's{accums[i-1]}AvGt', f's{accums[i]}AvGt'],
                        cls.get_curve_step_colname(i, accums))
            params.append(p)
        return params

    def generate(self):
        for idx in range(len(self.qdata.fields)):
            for op in self.operate:
                op.generate(idx, self.qdata.fields)
    
    def process(self):
        pdata = Dict(json.loads(json.dumps(self.qdata)))
        operate = []
        condbuy = CondBuy(self.cfg, pdata.colnames)
        operate.append(condbuy)
        calbuy = CalBuy(self.cfg, pdata.colnames)
        operate.append(calbuy)
        operate.append(CondSell(self.cfg, pdata.colnames))
        calsell = CalSell(self.cfg, pdata.colnames, calbuy)
        operate.append(calsell)
        condbuy.init_extra_columns(self.cfg, pdata.colnames)

        for idx in range(len(pdata.fields)):
            for op in operate:
                op.process(self.cfg, idx, pdata.fields)

        pdata.cfg = self.cfg
        pdata.report = calsell.get_report()
        return pdata


class IterAlgo:
    CfgParam = namedtuple('CfgParam', 
                          'sell_method minmax_index '
                          'hhupup_thresholds hhupup_begin hhupup_append '
                          'hhup_lwhh_begin hhup_lwhh_append '
                          'sum_accum_index')
    SUM_ACCUMS = [
        [2, 3, 4], [2, 3, 5], [2, 3, 6],  # [2, 3, 8], [2, 3, 10],
        [2, 4, 6], [2, 4, 8],  # [2, 4, 10], [2, 4, 12],
        [2, 5, 10],
        [3, 5, 7], [3, 5, 9],  # [3, 5, 11],
        [3, 6, 9], [3, 6, 12],
        [4, 5, 6], [4, 5, 10],
        [4, 6, 8], 
        [4, 7, 10],
    ]
    MINMAX_ACCUMS = [[1, 2, 3, 6, 9, 12]]  # [1, 2, 4, 8, 12, 18], 
    COND_SELL_METHOD = [3, 4]

    def __init__(self):
        self.iterlist = []
        sell_method = range(len(self.COND_SELL_METHOD))
        self.iterlist.append(sell_method)
        minmax_index = range(len(self.MINMAX_ACCUMS))
        self.iterlist.append(minmax_index)
        hhupup_thresholds = range(0, 3)
        self.iterlist.append(hhupup_thresholds)
        hhupup_begin = range(14, 21)
        self.iterlist.append(hhupup_begin)
        hhupup_append = range(3, 8)
        self.iterlist.append(hhupup_append)
        hhup_lwhh_begin = range(3, 8)
        self.iterlist.append(hhup_lwhh_begin)
        hhup_lwhh_append = range(0, 5)
        self.iterlist.append(hhup_lwhh_append)
        sum_accum_index = range(len(self.SUM_ACCUMS))
        self.iterlist.append(sum_accum_index)

    def _param(self, i, p):
        cfg = AlgoTable.default_option()
        cfg.algo.index = i
        cfg.price.sell.return_rate = 7
        cfg.sum.accums = IterAlgo.SUM_ACCUMS[p.sum_accum_index]
        cfg.minmax.accums = IterAlgo.MINMAX_ACCUMS[p.minmax_index]
        cfg.curve.step = AlgoTable.get_curve_step_params(cfg.sum.accums)
        cfg.buy.after.hhupup.begin = p.hhupup_begin
        cfg.buy.after.hhupup.append = p.hhupup_append
        cfg.buy.after.hhupup.hhup_lwhh.begin = p.hhup_lwhh_begin
        cfg.buy.after.hhupup.hhup_lwhh.append = p.hhup_lwhh_append
        cfg.buy.after.hhupup.thresholds = p.hhupup_thresholds
        cfg.sell.method = IterAlgo.COND_SELL_METHOD[p.sell_method]
        return cfg

    def gen_params(self, data):
        for i, x in enumerate(itertools.product(*self.iterlist)):
            p = IterAlgo.CfgParam(*x)
            cfg = self._param(i, p)

            param = Dict()
            param.cfg = cfg
            param.data = data

            yield param

    def gen_index_params(self, data, idx):
        for i, x in enumerate(itertools.product(*self.iterlist)):
            if idx != i:
                continue
            p = IterAlgo.CfgParam(*x)
            cfg = self._param(i, p)

            param = Dict()
            param.cfg = cfg
            param.data = data

            if idx >= 0:
                return param

        if idx >= 0:
            raise IndexError(f'Out Of Range: {idx}')

    def calculate(self, p):
        algo = AlgoTable(p.data, cfg=p.cfg)
        return  algo.process()

    @classmethod
    def save_data(cls, fname, data):
        with codecs.open(fname, 'w', encoding='utf-8') as fd:
            m = cls.dump_brief(data) + '\n'
            fd.write(m)
            fd.write(json.dumps(data))

    @classmethod
    def compute(cls, code, **kwargs):
        def_colnames = ['stamp', 'start', 'low', 'high', 'end', 'volume']
        colnames = kwargs.get('colnames', def_colnames)
        months = kwargs.get('months', 72)
        folder = kwargs.get('folder', 'brief')

        if not os.path.exists(folder):
            os.mkdir(folder)
        
        sidb = StockItemDB.factory(code)
        qdata = StockQuery.raw_data_of_each_colnames(sidb, colnames, months=months)
        it = cls()
        it.run(qdata, work_folder=folder, code=code, months=months)

    @classmethod
    def compute_index(cls, code, index, **kwargs):
        def_colnames = ['stamp', 'start', 'low', 'high', 'end', 'volume']
        colnames = kwargs.get('colnames', def_colnames)
        months = kwargs.get('months', 72)
        fg_save = kwargs.get('save_file', False)
        folder = kwargs.get('folder', 'brief')
        cfg = kwargs.get('cfg', None)

        sidb = StockItemDB.factory(code)
        qdata = StockQuery.raw_data_of_each_colnames(sidb, colnames, months=months)
        it = IterAlgo()

        index = int(index)
        param = it.gen_index_params(qdata, index)
        if cfg:
            param.cfg = cfg

        data = it.calculate(param)
        if fg_save:
            if not os.path.exists(folder):
                os.mkdir(folder)
            fname = f'{folder}/index-{code}-{index:06d}.log'
            cls.save_data(fname, data)

        return data

    @classmethod
    def compute_index_chart(cls, code, index, **kwargs):
        def filter_out(cns, data):
            # cns: Colnames
            # icns: index Colnames
            icns = [data.colnames.index(x) for x in cns]
            fields = data.fields
            istamp = data.colnames.index('stamp')
            data.colnames = cns
            data.fields = []
            start_stamp = data.cfg.algo.start.stamp
            for field in fields:
                if field[istamp] < start_stamp:
                    continue
                _field = [x for i, x in enumerate(field) if i in icns]
                data.fields.append(_field)
            return data

        if 'colnames' in kwargs:
            colnames = kwargs.get('colnames')
            del kwargs['colnames']
        else:
            colnames = ['stamp', 'end', 'afhuu', 'buycnt', 'sellcnt']
        data = cls.compute_index(code, index, **kwargs)
        return filter_out(colnames, data)

    @classmethod
    def dump_brief(cls, data):
        c = data.cfg
        b = data.cfg.buy.after.hhupup
        s = data.cfg.sell
        r = data.report
        m  = f'{c.algo.index:06d}:' if type(c.algo.index) is int else '------:'
        m += f'{" ".join([str(x) for x in c.sum.accums])}:'
        m += f'{" ".join([str(x) for x in c.minmax.accums])}:'
        m += f'{b.begin} {b.append}:'
        m += f'{b.hhup_lwhh.begin} {b.hhup_lwhh.append}:'
        m += f'{b.thresholds}:'
        m += f'{s.method}:'
        m += f'{r.investment_amount} {r.return_rate} {r.investment_days} '
        m += f'{r.earnings_count} {r.earnings_last_count}'
        return m

    def run(self, qdata, **kwargs):
        work_folder = kwargs.get('work_folder', None)
        code = kwargs.get('code', 'XXXXXX')
        months = kwargs.get('months')
        
        sim = Dict()
        cpu = multiprocessing.cpu_count()
        pool = multiprocessing.Pool(processes=cpu)
        std_ecount = int((months/12)*(2/3))
        max_ecount = 0
        logfd = None
        md5 = hashlib.md5()
        
        if work_folder and os.path.exists(work_folder):
            logfile = f'{work_folder}/brief-{code}.txt'
            # if 'ENV_CASE_ALGO' in os.environ:
            #     env_algo = os.environ["ENV_CASE_ALGO"]
            #     logfile = f'{work_folder}/brief-{env_algo}.txt'
            logfd = codecs.open(logfile, 'w', encoding='utf-8')

        for data in pool.imap(self.calculate, self.gen_params(qdata)):
            if logfd:
                if data.report.earnings_count >= std_ecount:
                    m = self.dump_brief(data) + '\n'
                    md5.update(m.encode('utf-8'))
                    logfd.write(m)

            max_ecount = max(data.report.earnings_count, max_ecount)

        if logfd:
            m = f'MAX Earnings Count: {max_ecount} \n'
            md5.update(m.encode('utf-8'))
            logfd.write(m)
            logfd.write(f'{md5.hexdigest()}')
            logfd.close()

        return sim


if __name__ == '__main__':
    import sys

    def usage():
        '''
    Usage: finalgo <cmd> <code> [<index>]
        cmd:
            compute <code>
            compute <code> <index>
            chart <code> <index>
        '''
        print(usage.__doc__)
        exit(-1)

    def cmd_compute(code, index):
        if index >= 0:
            print('compute_index', code, index)
            IterAlgo.compute_index(code, index, save_file=True)
        else:
            print('compute', code)
            IterAlgo.compute(code)
    
    def cmd_chart(code, index):
        if index < 0:
            raise Exception('Invalid Index')
        print('chart', code, index)
        data = IterAlgo.compute_index_chart(code, index)
        print(data)

    def cmd_unknown(code, index):
        raise Exception('Unknown Command')


    if len(sys.argv) < 3:
        usage()
    
    cmd_pool = {
        'compute':  cmd_compute,
        'chart':    cmd_chart,
    }
    cmd = sys.argv[1]
    code = sys.argv[2]
    index = -1
    if len(sys.argv) == 4:
        index = int(sys.argv[3])

    func = cmd_pool.get(cmd, cmd_unknown)
    try:
        func(code, index)
    except Exception as e:
        print(f'Error: {e}')
        exit(-1)
    

