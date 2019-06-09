import json

from collections import namedtuple

from pysp.serror import SDebug


class Dict(dict):
    def __getattr__(self, name):
        try:
            attr = self[name]
        except KeyError:
            self[name] = Dict()
            attr = self[name]
        return attr
    def __setattr__(self, k, v):
        self[k] = v


class Algo:
    class Error(Exception):
        pass

    def _fill_data(self, idxs, values, field):
        if len(field) == idxs[0]:
            [field.append(x) for x in values]
            return
        for i, ix in enumerate(idxs):
            field[ix] = values[i]


class AlgoModel(object):
    # Gredient Parameter
    StepParam = namedtuple('StepParam', 'gradnames stepname')


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
            if self.is_all(self.isteps, ['DN','DN','DN'], field):
                self.start = True

            if self.is_or('is_all', self.isteps, [['HH','UP','UP']], field):
                if self.after_hhupup <= 0:
                    self.after_hhupup = 15 
                else:
                    self.after_hhupup += 4
            elif self.is_or('is_all', self.isteps,
                            [['HH','UP',None], ['LW','HH',None]], field):
                if self.after_hhupup <= 0:
                    self.after_hhupup = 5
                else:
                    self.after_hhupup += 2
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

            if buycnt > 0 and (self.start is False or self.after_hhupup > 0):
                buycnt = 0

            # Additional purchase
            prevfield = fields[idx-1]
            baverage = prevfield[self.ibaverage]
            if baverage and baverage > field[self.ibprice]:
                buycnt = self.HERE_IT_GO

            break  # End of While

        if not fg_skip:
            buyreason += ','.join([str(field[x]) for x in self.isteps])
            buyreason += ':'+','.join([str(field[x]) for x in self.ipercents])
            
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
        if buy_count > 0:
            self.volume += 1
            self.amount += (1 * field[self.ibprice])
            self.average = int(self.amount / self.volume)

        values = [self.volume, self.amount, self.average]
        self._fill_data(indexes, values, field)


class CondSell(AlgoProc):
    COLNAME_SELL_POINT =    'sellcnt'
    COLNAME_SELL_REASON =   'sreason'

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

    def process(self, cfg, idx, fields):
        def to_rate(rate):
            return 1.0 + rate/100.0

        sellcnt = 0
        sreason = ''
        field = fields[idx]

        if field[self.ibvolume] > 0:
            if self.is_any(self.isteps, ['HH','HH',None], field):
                wanted = field[self.ibaverage]*to_rate(cfg.price.sell.return_rate)
                if field[self.isprice] > wanted:
                    sellcnt = 20

        indexes = [self.iscnt, self.isreason]
        values = [sellcnt, sreason]
        self._fill_data(indexes, values, field)


class CalSell(AlgoProc):
    COLNAME_SELL_AMOUNT =   'samount'
    COLNAME_SELL_PROFIT =   'profit'

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
    
    def get_report(self):
        def to_float(x):
            return float('{:.2f}'.format(x))
        report = Dict()
        report.investment_amount = self.investment_amount
        report.earnings_amount = self.earnings_amount
        profit = (self.earnings_amount/self.investment_amount*100)-100
        report.return_rate = to_float(profit)
        report.expected_return_rate = to_float(self.cfg.price.sell.return_rate)
        return report

    def process(self, cfg, idx, fields):
        amount = None
        profit = None
        field = fields[idx]

        if field[self.iscnt] > 0:
            amount = field[self.ivolume] * field[self.isprice]
            profit = '{:.2f}'.format((amount/field[self.ibamount]*100)-100)
            self.investment_amount += field[self.ibamount]
            self.earnings_amount += amount
            self.calbuy.reset(field=field)

        indexes = [self.isamount, self.iprofit]
        values = [amount, profit]
        self._fill_data(indexes, values, field)


class AlgoTable(AlgoModel):

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
        cfg.gradient.accum = 5
        # cfg.sum.accums = [4, 8, 12]
        cfg.sum.accums = [3, 6, 12]
        cfg.minmax.accums = [1, 2, 4, 8, 12, 18]
        cfg.curve.step = cls.get_curve_step_params(cfg.sum.accums)
        cfg.price.ref_colname.low = 'low'
        cfg.price.ref_colname.high = 'high'
        cfg.price.buy.colname = 'bprice'
        cfg.price.buy.percent = 20
        cfg.price.sell.colname = 'sprice'
        cfg.price.sell.percent = 80
        cfg.price.sell.return_rate = 7
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
                p = AlgoModel.StepParam(
                        ['endGt', f's{accums[i]}AvGt'], 
                        cls.get_curve_step_colname(i, accums))
                params.append(p)
                continue
            p = AlgoModel.StepParam(
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

        pdata.report = calsell.get_report()
        return pdata


