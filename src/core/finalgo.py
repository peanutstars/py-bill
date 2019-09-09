#!/usr/bin/env python3

import codecs
import datetime
import hashlib
import itertools
import json
import multiprocessing
import os

from collections import namedtuple

from pysp.serror import SDebug

from core.model import Dict
from core.connect import Http
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

    def is_le_any(self, idxs, values, field):
        fvalues = self._check_array(idxs, values, field)
        return any([x<=y for x, y in zip(fvalues, values) if y is not None])

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
    def to_unit_price(cls, price, roundup, updown=0):
        uprice = price
        for k, v in cls.TRADE_UNIT.items():
            if price < k:
                mod = price % v
                # print('@', k, v)
                if (mod) == 0:
                    if updown:
                        uprice += (v*updown)
                    break
                uprice = (price-mod+v) if roundup else (price-mod)
                if updown:
                    uprice += (v*updown)
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
        self.ilow = colnames.index('low')
        self.ihigh = colnames.index('high')
        self.imin = colnames.index(self.minname)
        self.imax = colnames.index(self.maxname)
        self.ipct = colnames.index(self.pctname)
        self.accum = accum*5*4
        self.array = Dict()
        self.array.low = []
        self.array.high = []
    
    def generate(self, idx, fields):
        minvalue = None
        maxvalue = None
        percent = None
        data = fields[idx][self.iend]
        lowdata = fields[idx][self.ilow]
        highdata = fields[idx][self.ihigh]
        if len(self.array.low) == self.accum:
            minvalue = min(self.array.low)
            maxvalue = max(self.array.high)
            # print('@', self.pctname, minvalue, maxvalue, data)
            if minvalue == maxvalue:
                percent = 0  # if data < minvalue else 100
            else:
                percent = int((data-minvalue)/(maxvalue-minvalue)*100)
            self.array.low.pop(0)
            self.array.high.pop(0)
        self.array.low.append(lowdata)
        self.array.high.append(highdata)
        self._fill_data([self.imin, self.imax, self.ipct], 
                        [minvalue, maxvalue, percent], fields[idx])


class CondBuy(AlgoProc):
    COLNAME_BUYCNT =        'buycnt'
    COLNAME_BUYREASON =     'breason'
    COLNAME_AFTER_HHUPUP =  'afhuu'
    COLNAME_DAYRATES =      'dayrates'
    BUY_NORMAL =            11
    BUY_DROPPING =          22
    AVG_DROP_RATE =         0.925

    def __init__(self, cfg, colnames):
        super(CondBuy, self).__init__()
        accums = cfg.sum.accums
        colnames.append(self.COLNAME_AFTER_HHUPUP)
        colnames.append(self.COLNAME_BUYCNT)
        colnames.append(self.COLNAME_BUYREASON)
        colnames.append(self.COLNAME_DAYRATES)
        self.iend = colnames.index('end')
        self.istamp = colnames.index('stamp')
        self.ihhupup = colnames.index(self.COLNAME_AFTER_HHUPUP)
        self.ibcnt = colnames.index(self.COLNAME_BUYCNT)
        self.ibreason = colnames.index(self.COLNAME_BUYREASON)
        self.idayrate = colnames.index(self.COLNAME_DAYRATES)
        _curve_step = AlgoTable.get_curve_step_colname
        self.steps = [f'{_curve_step(x, accums)}Md' for x in range(len(accums))]
        self.isteps = [colnames.index(x) for x in self.steps]
        _minmax_percent = OpMinMax.COLNAME_PERCENT.format
        self.percents = [_minmax_percent(x) for x in cfg.minmax.accums]
        self.ipercents = [colnames.index(x) for x in self.percents]
        self.after_hhupup = 0
        self.start = False
        drop_rate = cfg.buy.dropping_rate
        self.drop_rate_1day = drop_rate * -1
        self.drop_rate_2day = drop_rate * -1.77

    def init_extra_columns(self, cfg, colnames):
        self.ibprice = colnames.index(cfg.price.buy.colname)
        self.ibaverage = colnames.index(CalBuy.COLNAME_BUY_AVERAGE)

    def is_skipped(self, field):
        if self.is_any(self.isteps, [None]*len(self.isteps), field, none_skip=False):
            return True
        if self.is_any(self.ipercents, [None]*len(self.ipercents), field, none_skip=False):
            return True
        return False

    def get_rate(self, a, b):
        if a == 0:
            return 1000 * (1 if (b-a) > 0 else -1)
        return (b-a)*100/a

    def process(self, cfg, idx, fields):
        buycnt = 0
        buyreason = ''
        dayrates = ''

        field = fields[idx]
        fg_skip = self.is_skipped(field)
        
        while True:
            if fg_skip:
                break

            rate_1day = self.get_rate(fields[idx-1][self.iend], fields[idx][self.iend])
            rate_2day = self.get_rate(fields[idx-2][self.iend], fields[idx][self.iend])
            dayrates = f'{rate_1day:.1f}:{rate_2day:.1f}'

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
            
            if (rate_1day < self.drop_rate_1day or rate_2day < self.drop_rate_2day) and\
            self.is_le_any(self.ipercents, [None,None,None,50,55,60], field):
            # self.is_ge_any(self.ipercents, [None,None,None,30,25,20], field) and\
                # Dropping Highly
                buyreason += 'BD#'
                buycnt = self.BUY_DROPPING
                # Adjust buy price, because the price is dropping
                field[self.ibprice] = OpPrice.to_unit_price(field[self.iend], True, updown=2)
                break

            if self.is_or(['is_all','is_any'], self.isteps, 
                          [['UP','UP','UP'], ['HH','HH','HH']], field):
                break

            if self.is_or('is_any', self.isteps, [['DN','DN','DN']], field):
                if self.is_or('is_all', self.isteps, [['LW','DN','DN']], field):
                    buyreason += 'B0#'
                    buycnt = self.BUY_NORMAL
                elif self.is_or('is_all', self.isteps, [['UP','LW','DN']], field):
                    buyreason += 'B1#'
                    buycnt = self.BUY_NORMAL
            # elif self.is_or('is_all', self.isteps, [['HH','UP',None]], field):
            #     # High point
            #     pass

            if self.is_ge_any(self.ipercents, [90,80,None,60,60,None], field):
                # Too High
                buyreason += 'TH#'
                buycnt = 0
                break
            elif self.is_le_any(self.ipercents, [-10,-5,0,0,4,8], field):
                # Too Low
                buyreason += 'TL#'
                buycnt = 0
                break 

            if buycnt > 0:
                if self.start is False or self.after_hhupup > cfg.buy.after.hhupup.thresholds:
                    # Threshold
                    buyreason += 'TS#'
                    buycnt = 0

            # Additional purchase
            prevfield = fields[idx-1]
            baverage = prevfield[self.ibaverage]
            if baverage and int(baverage*self.AVG_DROP_RATE) > field[self.ibprice]:
                buyreason += 'Av#'
                buycnt = self.BUY_NORMAL

            break  # End of While

        if not fg_skip:
            buyreason += ''.join([str(field[x]) for x in self.isteps])
            buyreason += '#'+':'.join([str(field[x]) for x in self.ipercents])
            
        indexes = [self.ihhupup, self.ibcnt, self.ibreason, self.idayrate]
        values = [self.after_hhupup, buycnt, buyreason, dayrates]
        self._fill_data(indexes, values, field)


class CalBuy(AlgoProc):
    COLNAME_BUY_VOLUME =        'bvolume'
    COLNAME_BUY_AMOUNT =        'bamount'
    COLNAME_BUY_AVERAGE =       'bavg'
    COLNAME_BUY_DROP_VOLUME =   'bdvolume'
    COLNAME_BUY_DROP_AMOUNT =   'bdamount'
    COLNAME_BUY_DROP_AVERAGE =  'bdavg'

    def __init__(self, cfg, colnames):
        super(CalBuy, self).__init__()
        colnames.append(self.COLNAME_BUY_VOLUME)
        colnames.append(self.COLNAME_BUY_AMOUNT)
        colnames.append(self.COLNAME_BUY_AVERAGE)
        colnames.append(self.COLNAME_BUY_DROP_VOLUME)
        colnames.append(self.COLNAME_BUY_DROP_AMOUNT)
        colnames.append(self.COLNAME_BUY_DROP_AVERAGE)
        self.ibcnt = colnames.index(CondBuy.COLNAME_BUYCNT)
        self.ibprice = colnames.index(cfg.price.buy.colname)
        self.ivolume = colnames.index(self.COLNAME_BUY_VOLUME)
        self.iamount = colnames.index(self.COLNAME_BUY_AMOUNT)
        self.iaverage = colnames.index(self.COLNAME_BUY_AVERAGE)
        self.idvolume = colnames.index(self.COLNAME_BUY_DROP_VOLUME)
        self.idamount = colnames.index(self.COLNAME_BUY_DROP_AMOUNT)
        self.idaverage = colnames.index(self.COLNAME_BUY_DROP_AVERAGE)
        self.volume = 0
        self.amount = 0
        self.average = 0
        self.dvolume = 0
        self.damount = 0
        self.daverage = 0
        self.reset()
        self.reset_bdrop()

    def reset(self, **kwargs):
        self.volume = 0
        self.amount = 0
        self.average = 0
        field = kwargs.get('field', None)
        if field:
            indexes = [self.ivolume, self.iamount, self.iaverage]
            values = [self.volume, self.amount, self.average]
            self._fill_data(indexes, values, field)

    def reset_bdrop(self, **kwargs):
        field = kwargs.get('field', None)
        sprice = kwargs.get('sprice', 0)
        if self.volume != self.dvolume:
            self.volume -= self.dvolume
            self.amount -= ((self.dvolume*sprice) if sprice else self.damount)
            self.average = int(self.amount / self.volume)
            if field:
                indexes = [self.ivolume, self.iamount, self.iaverage]
                values = [self.volume, self.amount, self.average]
                self._fill_data(indexes, values, field)
        self.dvolume = 0
        self.damount = 0
        self.daverage = 0
        if field:
            indexes = [self.idvolume, self.idamount, self.idaverage]
            values = [self.dvolume, self.damount, self.daverage]
            self._fill_data(indexes, values, field)


    def process(self, cfg, idx, fields):
        field = fields[idx]
        indexes = [self.ivolume, self.iamount, self.iaverage, 
                   self.idvolume, self.idamount, self.idaverage]

        buy_count = field[self.ibcnt]
        bprice = field[self.ibprice]
        if bprice > 0:
            if buy_count == CondBuy.BUY_NORMAL:
                self.volume += 1
                self.amount += (1 * field[self.ibprice])
                self.average = int(self.amount / self.volume)
            elif buy_count == CondBuy.BUY_DROPPING:
                self.volume += 2
                self.amount += (2 * field[self.ibprice])
                self.average = int(self.amount / self.volume)
                self.dvolume += 2
                self.damount += (2 * field[self.ibprice])
                self.daverage = int(self.damount / self.dvolume)                

        values = [self.volume, self.amount, self.average,
                  self.dvolume, self.damount, self.daverage]
        self._fill_data(indexes, values, field)


class CondSell(AlgoProc):
    COLNAME_SELL_POINT =    'sellcnt'
    COLNAME_SELL_REASON =   'sreason'
    SELL_NORMAL =           11
    SELL_DROPPING =         22
    DROP_RETURN_RATE =      0.00643

    def __init__(self, cfg, colnames):
        super(CondSell, self).__init__()
        accums = cfg.sum.accums
        colnames.append(self.COLNAME_SELL_POINT)
        colnames.append(self.COLNAME_SELL_REASON)
        self.iscnt = colnames.index(self.COLNAME_SELL_POINT)
        self.isreason = colnames.index(self.COLNAME_SELL_REASON)
        self.isprice = colnames.index(cfg.price.sell.colname)
        self.ihigh = colnames.index('high')
        self.ibcnt = colnames.index(CondBuy.COLNAME_BUYCNT)
        self.ibvolume = colnames.index(CalBuy.COLNAME_BUY_VOLUME)
        self.ibaverage = colnames.index(CalBuy.COLNAME_BUY_AVERAGE)
        self.ibdvolume = colnames.index(CalBuy.COLNAME_BUY_DROP_VOLUME)
        self.ibdaverage = colnames.index(CalBuy.COLNAME_BUY_DROP_AVERAGE)
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
        self.drop_return_rate = 1.0 + self.DROP_RETURN_RATE*cfg.buy.dropping_rate

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
            #             sellcnt = self.SELL_NORMAL

            # if self.method == 2:
            #     if self.is_any(self.isteps, ['HH','HH',None], field):
            #         # XXX: Added New Condition
            #         if self.is_ge_any(self.ipercents, [150,125,105,95,None,None], field):
            #             if field[self.ihhupup] >= self.std_hhupup:
            #                 wanted = field[self.ibaverage]*self.rrate
            #                 if field[self.isprice] > wanted:
            #                     sellcnt = self.SELL_NORMAL

            if self.method == 3:
                if self.is_any(self.isteps, ['HH','HH',None], field) or \
                self.is_or('is_all', self.isteps, [['DN','UP',None], ['LW','UP',None]], field):
                    # XXX: Added New Condition
                    if self.is_ge_any(self.ipercents, [150,125,105,95,None,None], field):
                        if field[self.ihhupup] >= self.std_hhupup:
                            wanted = field[self.ibaverage]*self.rrate
                            if field[self.isprice] > wanted:
                                sellcnt = self.SELL_NORMAL
                                sreason += 'SN#'

            if self.method == 4:
                if self.is_any(self.isteps, ['HH','HH',None], field) or \
                self.is_or('is_all', self.isteps, [['DN','UP',None],['LW','UP',None],
                                                   ['UP','LW',None],['UP','UP',None]], field):
                    if field[self.ihhupup] >= self.std_hhupup:
                        # TODO: Add that Profit is Up Side Rapidly
                        wanted = field[self.ibaverage]*self.rrate
                        if field[self.isprice] > wanted:
                            sellcnt = self.SELL_NORMAL
                            sreason += 'SN#'

            # check to sell for a stock which it bought when the big drop.
            if field[self.ibcnt] != CondBuy.BUY_DROPPING and field[self.ibdvolume] > 0:
                wanted = field[self.ibdaverage]*self.drop_return_rate
                curprice = OpPrice.to_unit_price(field[self.ihigh], True, updown=-2)
                if curprice > wanted:
                    field[self.isprice] = curprice
                    # check to sell everythings
                    wanted = field[self.ibaverage]*self.rrate
                    if field[self.isprice] > wanted:
                        sellcnt += (self.SELL_NORMAL if sellcnt == 0 else 0)
                        sreason += 'SN#'
                    sellcnt += self.SELL_DROPPING
                    sreason += 'SD#'

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
        self.ibdamount = colnames.index(CalBuy.COLNAME_BUY_DROP_AMOUNT)
        self.ivolume = colnames.index(CalBuy.COLNAME_BUY_VOLUME)
        self.idvolume = colnames.index(CalBuy.COLNAME_BUY_DROP_VOLUME)
        self.iscnt = colnames.index(CondSell.COLNAME_SELL_POINT)
        self.isprice = colnames.index(cfg.price.sell.colname)
        self.investment_amount = 0
        self.earnings_amount = 0
        self.investment_days = 0
        self.earnings_count = 0
        self.last_earnings_count = 0
    
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
        report.last_earnings_count = self.last_earnings_count
        return report

    def process(self, cfg, idx, fields):
        amount = None
        profit = None
        field = fields[idx]
        fg_earning = False

        sprice = field[self.isprice]
        scnt = field[self.iscnt]

        if sprice > 0:
            if scnt == (CondSell.SELL_DROPPING+CondSell.SELL_NORMAL):
                amount = field[self.ivolume] * sprice
                profit = '{:.2f}'.format((amount/field[self.ibamount]*100)-100)
                self.investment_amount += field[self.ibamount]
                self.earnings_amount += amount
                self.calbuy.reset_bdrop(field=field, sprice=sprice)
                self.calbuy.reset(field=field)
                fg_earning = True
            elif scnt == CondSell.SELL_DROPPING:
                fg_same = field[self.idvolume] == field[self.ivolume]
                self.investment_amount += field[self.ibdamount]
                self.earnings_amount += field[self.idvolume] * sprice
                self.calbuy.reset_bdrop(field=field, sprice=sprice)
                amount = field[self.ivolume] * sprice
                profit = '{:.2f}'.format((amount/field[self.ibamount]*100)-100)
                # self.investment_amount += field[self.ibamount]
                # self.earnings_amount += amount
                if fg_same:
                    self.calbuy.reset(field=field)
                    fg_earning = True
            elif scnt == CondSell.SELL_NORMAL:
                amount = field[self.ivolume] * sprice
                profit = '{:.2f}'.format((amount/field[self.ibamount]*100)-100)
                self.investment_amount += field[self.ibamount]
                self.earnings_amount += amount
                self.calbuy.reset_bdrop(field=field, sprice=sprice)
                self.calbuy.reset(field=field)
                fg_earning = True

        if profit is None and field[self.ivolume]:
            _amount = field[self.ivolume] * sprice
            profit = '{:.2f}'.format((_amount/field[self.ibamount]*100)-100)

        if fg_earning:
            self.earnings_count += 1
            if idx >= (len(fields)-self.WORK_DAYS_PER_YEAR):
                self.last_earnings_count += 1
        
        # if field[self.iscnt] > 0 and sprice > 0:
        #     amount = field[self.ivolume] * sprice
        #     profit = '{:.2f}'.format((amount/field[self.ibamount]*100)-100)
        #     self.investment_amount += field[self.ibamount]
        #     self.earnings_amount += amount
        #     self.earnings_count += 1
        #     if idx >= (len(fields)-self.WORK_DAYS_PER_YEAR):
        #         self.last_earnings_count += 1
        #     self.calbuy.reset(field=field)
        # elif field[self.ivolume]:
        #     _amount = field[self.ivolume] * sprice
        #     profit = '{:.2f}'.format((_amount/field[self.ibamount]*100)-100)

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
        cfg.buy.dropping_rate = 7                   # [7, 3]
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
    class Error(Exception):
        pass

    CfgParam = namedtuple('CfgParam', 
                          'sell_method minmax_index '
                          'dropping_rate '
                          'hhupup_thresholds hhupup_begin hhupup_append '
                          'hhup_lwhh_begin hhup_lwhh_append '
                          'sum_accum_index')
    SUM_ACCUMS = [
        [2, 3, 4], [2, 3, 5], [2, 3, 6],  # [2, 3, 8], [2, 3, 10],
        [2, 4, 6], [2, 4, 8],  # [2, 4, 10], [2, 4, 12],
        [2, 5, 10],
        [3, 5, 7], [3, 5, 9],  # [3, 5, 11],
        [3, 6, 9], [3, 6, 12],
        [4, 6, 8], 
        [4, 7, 10],
    ]
    MINMAX_ACCUMS = [[1, 2, 3, 6, 9, 12]]  # [1, 2, 4, 8, 12, 18], 
    COND_SELL_METHOD = [4]

    def __init__(self):
        self.iterlist = []
        sell_method = range(len(self.COND_SELL_METHOD))
        self.iterlist.append(sell_method)
        minmax_index = range(len(self.MINMAX_ACCUMS))
        self.iterlist.append(minmax_index)
        dropping_rate = [7, 3]
        self.iterlist.append(dropping_rate)
        hhupup_thresholds = range(0, 3)
        self.iterlist.append(hhupup_thresholds)
        hhupup_begin = range(14, 22, 2)
        self.iterlist.append(hhupup_begin)
        hhupup_append = range(3, 8)
        self.iterlist.append(hhupup_append)
        hhup_lwhh_begin = range(3, 8, 2)
        self.iterlist.append(hhup_lwhh_begin)
        hhup_lwhh_append = range(0, 5, 2)
        self.iterlist.append(hhup_lwhh_append)
        sum_accum_index = range(len(self.SUM_ACCUMS))
        self.iterlist.append(sum_accum_index)

    def _param(self, i, p):
        cfg = AlgoTable.default_option()
        cfg.algo.index = i
        # cfg.price.sell.return_rate = 7
        cfg.sum.accums = IterAlgo.SUM_ACCUMS[p.sum_accum_index]
        cfg.minmax.accums = IterAlgo.MINMAX_ACCUMS[p.minmax_index]
        cfg.curve.step = AlgoTable.get_curve_step_params(cfg.sum.accums)
        cfg.buy.dropping_rate = p.dropping_rate
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
            # param.data = data
            param.data = json.loads(json.dumps(data))

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
        folder = kwargs.get('folder', 'algo')

        if not os.path.exists(folder):
            os.mkdir(folder)
        
        sidb = StockItemDB.factory(code)
        qdata = StockQuery.raw_data_of_each_colnames(sidb, colnames, months=months)
        it = cls()
        it.run(qdata, work_folder=folder, code=code, months=months)

    @classmethod
    def current_stock(cls, code, qdata):
        def renew_last_field(field, cs):
            field[istamp] = cs.date
            field[istart] = int(cs.openingPrice)
            field[ilow] =   int(cs.lowPrice)
            field[ihigh] =  int(cs.highPrice)
            field[iend] =   int(cs.tradePrice)
            field[ivolume] = int(cs.accTradeVolume)

        now = datetime.datetime.now()
        if now.hour in range(0, 9):
            # Not opening the stock market.
            return

        url = 'https://stock.kakao.com/api/securities/KOREA-A'+code+'.json'
        options = {
            'json':     True,
            'duration': 90,
        }
        cstock = Http.proxy('GET', url, **options)
        if cstock:
            cstock = Dict(cstock['recentSecurity'])
            # print(json.dumps(cstock, indent=1))
            cdate = datetime.datetime.now().strftime("%Y-%m-%d")
            if cstock.date != cdate:
                # Maybe Holiday or Not opened yet.
                return
            istamp = qdata.colnames.index('stamp')
            istart = qdata.colnames.index('start')
            ilow = qdata.colnames.index('low')
            ihigh = qdata.colnames.index('high')
            iend = qdata.colnames.index('end')
            ivolume = qdata.colnames.index('volume')

            if cdate == qdata.fields[-1][istamp]:
                pass
            else:
                field = [None]*len(qdata.colnames)
                qdata.fields.append(field)
            renew_last_field(qdata.fields[-1], cstock)

    @classmethod
    def compute_index(cls, code, index, **kwargs):
        def_colnames = ['stamp', 'start', 'low', 'high', 'end', 'volume']
        colnames = kwargs.get('colnames', def_colnames)
        months = kwargs.get('months', 72)
        return_rate = kwargs.get('return_rate', 7.0)
        fg_save = kwargs.get('save_file', False)
        folder = kwargs.get('folder', 'algo')
        cfg = kwargs.get('cfg', None)

        sidb = StockItemDB.factory(code)
        qdata = StockQuery.raw_data_of_each_colnames(sidb, colnames, months=months)
        # print(qdata.fields[-1])
        cls.current_stock(code, qdata)
        # print(qdata.fields[-1])
        it = IterAlgo()

        index = int(index)
        param = it.gen_index_params(qdata, index)
        if cfg:
            param.cfg = cfg
        param.cfg.price.sell.return_rate = return_rate

        data = it.calculate(param)
        if fg_save:
            if not os.path.exists(folder):
                os.mkdir(folder)
            fname = f'{folder}/index-{code}-{index:06d}.log'
            cls.save_data(fname, data)

        return data

    @classmethod
    def compute_index_chart(cls, code, index, **kwargs):
        def chart_today(data):
            lastfield = data.fields[-1]
            istamp = data.colnames.index('stamp')
            ibreason = data.colnames.index(CondBuy.COLNAME_BUYREASON)
            ibvolume = data.colnames.index(CalBuy.COLNAME_BUY_VOLUME)
            ibavg = data.colnames.index(CalBuy.COLNAME_BUY_AVERAGE)
            ibuycnt = data.colnames.index(CondBuy.COLNAME_BUYCNT)
            isellcnt = data.colnames.index(CondSell.COLNAME_SELL_POINT)
            isprofit = data.colnames.index(CalSell.COLNAME_SELL_PROFIT)
            icprice = data.colnames.index('end')
            ibprice = data.colnames.index(data.cfg.price.buy.colname)
            isprice = data.colnames.index(data.cfg.price.sell.colname)
            isreason = data.colnames.index(CondSell.COLNAME_SELL_REASON)

            brief = Dict()
            brief.date = lastfield[istamp]
            brief.breason = lastfield[ibreason]
            brief.bvolume = lastfield[ibvolume]
            brief.bavg = lastfield[ibavg]
            brief.bpoint = 1 if lastfield[ibuycnt] else 0
            brief.spoint = 1 if lastfield[isellcnt] else 0
            brief.sprofit = lastfield[isprofit]
            brief.cprice = lastfield[icprice]
            brief.bprice = lastfield[ibprice]
            brief.sprice = lastfield[isprice]
            brief.sreason = lastfield[isreason]
            brief.last.colnames = data.colnames
            brief.last.field = data.fields[-1]
            data.chart.today = brief

        def filter_out(cns, data):
            # cns: Colnames
            # icns: index Colnames
            chart_today(data)
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
        b = data.cfg.buy
        h = data.cfg.buy.after.hhupup
        s = data.cfg.sell
        r = data.report
        m  = f'{c.algo.index:06d}:' if type(c.algo.index) is int else '------:'
        m += f'{" ".join([str(x) for x in c.sum.accums])}:'
        m += f'{" ".join([str(x) for x in c.minmax.accums])}:'
        m += f'{b.dropping_rate}:'
        m += f'{h.begin} {h.append} '
        m += f'{h.hhup_lwhh.begin} {h.hhup_lwhh.append} '
        m += f'{h.thresholds}:'
        m += f'{s.method}:'
        m += f'{r.investment_amount} {r.return_rate} {r.investment_days} '
        m += f'{r.earnings_count} {r.last_earnings_count}'
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
        max_last_ecount = 0
        logfd = None
        md5 = hashlib.md5()
        
        if work_folder and os.path.exists(work_folder):
            logfile = f'{work_folder}/{code}.brief'
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
            max_last_ecount = max(data.report.last_earnings_count, max_last_ecount)

        if logfd:
            m  = f'MAX Earnings Count: {max_ecount}\n'
            m += f'MAX Last Earnings Count: {max_last_ecount}\n'
            m += f'Build Date: {datetime.datetime.now().strftime("%Y-%m-%d")}\n'
            md5.update(m.encode('utf-8'))
            logfd.write(m)
            logfd.write(f'MD5SUM: {md5.hexdigest()}')
            logfd.close()

        return sim
    
    @classmethod
    def load_brief(cls, code, **kwargs):
        def col_to_list(arr):
            return arr[:-1] + arr[-1].split()

        folder = kwargs.get('folder', '/var/pybill/stock/algo')

        data = Dict()
        data.colnames = ['index', 'sum', 'minmax', 'droprate', 'hhupup', 'sell', 
                         'iamount', 'return', 'idays', 'ecount', 'lecount']
        data.fields = []
        data.md5sum = False
        md5 = hashlib.md5()
        # _code = int(code)
        path = f'{folder}/{int(code):06d}.brief'
        if not os.path.exists(path):
            cls.Error(f'Not Exists: {path}')

        with codecs.open(path, 'r', encoding='utf-8') as fd:
            for line in fd:
                arr = line.split(':')
                arrc = len(arr)
                if arrc == 7:
                    data.fields.append(col_to_list(arr))
                else:
                    if arr[0].find('MAX Earnings Count') >= 0:
                        data.max_ecount = int(arr[1])
                    elif arr[0].find('MAX Last Earnings Count') >= 0:
                        data.max_lecount = int(arr[1])
                    elif arr[0].find('Build Date') >= 0:
                        data.build_date = arr[1].strip()
                    elif arr[0].find('MD5SUM') >= 0:
                        md5sum = arr[1].strip()
                        if md5sum == md5.hexdigest():
                            data.md5sum = True
                    else:
                        raise cls.Error(f'Unknown Format: "{line}"')
                md5.update(line.encode('utf-8'))

        return data


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
    

