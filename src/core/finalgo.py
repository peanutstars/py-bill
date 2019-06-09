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
        colnames.append(cfg.buy.colname)
        colnames.append(cfg.sell.colname)
        self.ilow = colnames.index(cfg.ref_colname.low)
        self.ihigh = colnames.index(cfg.ref_colname.high)
        self.ibuypn = colnames.index(cfg.buy.colname)
        self.isellpn = colnames.index(cfg.sell.colname)
        self.bpercent = cfg.buy.percent
        self.spercent = cfg.sell.percent

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
        buyp = None
        sellp = None
        lowprice = fields[idx][self.ilow]
        highprice = fields[idx][self.ihigh]
        if lowprice is not None and highprice is not None:
            buyp = lowprice + int((highprice-lowprice)*self.bpercent/100)
            buyp = self.to_unit_price(buyp, roundup=True)
            sellp = lowprice + int((highprice-lowprice)*self.spercent/100)
            sellp = self.to_unit_price(sellp, roundup=False)
        self._fill_data([self.ibuypn, self.isellpn], [buyp, sellp], fields[idx])


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
        self.accum = cfg.accum
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


# class CondBuy(AlgoProc):
#     COLNAME = 'buycnt'

#     def __init__(self, cfg, colnames):
#         accums = cfg.sum.accums
#         colnames.append(self.COLNAME)
#         self.ibuy = colnames.index(self.COLNAME)
#         self.step_colnames = [
#             f'{AlgoTable.get_curve_step_colname(x, accums)}Md' for x in range(len(accums))
#         ]
#         self.isteps = [colnames.index(x) for x in self.step_colnames]
#         self.percent_colnames = {
#             x: OpMinMax.COLNAME_PERCENT.format(x) for x in cfg.minmax.accums
#         }
    
#     def process(self, cfg, idx, fields):
#         buy_cnt = 0
#         # If All is Not NULL
#         if all([fields[idx][x] is not None for x in self.isteps]):
#             f_steps = [fields[idx][x] for x in self.isteps]
#             while True:
#                 fgexit = False
#                 for c in cfg.condition.buy.negative:
#                     c = Dict(c)
#                     if c.steps:
#                         length = len(c.steps.val)
#                         if c.steps.op == 'OR' and any([f_steps[x]==c.steps.val[x] for x in range(length)]):
#                             fgexit = True
#                             break
#                         if c.steps.op == 'AND' and all([f_steps[x]==c.steps.val[x] for x in range(length)]):
#                             fgexit = True
#                             break
#                 if fgexit:
#                     break
#                 buy_cnt += 1
#                 break
#             for c in cfg.condition.buy.positive:
#                 c = Dict(c)
#                 if c.steps:
#                     length = len(c.steps.val)
#                     if c.steps.op == 'OR' and any([f_steps[x]==c.steps.val[x] for x in range(length)]):
#                         buy_cnt += 1
#                     if c.steps.op == 'AND' and all([f_steps[x]==c.steps.val[x] for x in range(length)]):
#                         buy_cnt += 1
#         if len(fields[idx]) == self.ibuy:
#             fields[idx].append(buy_cnt)
#             return
#         fields[idx][self.ibuy] = buy_cnt

class CondBuy(AlgoProc):
    COLNAME_BUYCNT = 'buycnt'
    COLNAME_BUYREASON = 'breason'

    def __init__(self, cfg, colnames):
        accums = cfg.sum.accums
        colnames.append(self.COLNAME_BUYCNT)
        colnames.append(self.COLNAME_BUYREASON)
        self.ibuycnt = colnames.index(self.COLNAME_BUYCNT)
        self.ibuyreason = colnames.index(self.COLNAME_BUYREASON)
        _curve_step = AlgoTable.get_curve_step_colname
        self.steps = [f'{_curve_step(x, accums)}Md' for x in range(len(accums))]
        self.isteps = [colnames.index(x) for x in self.steps]
        _minmax_percent = OpMinMax.COLNAME_PERCENT.format
        self.percents = [_minmax_percent(x) for x in cfg.minmax.accums]
        self.ipercents = [colnames.index(x) for x in self.percents]
        self.after_hhupup = 0
    
    def _check_array(self, idxs, values, field):
        if len(idxs) != len(values):
            raise Algo.Error('Not Enough each Count of Parameter.')
        return [field[x] for x in idxs]

    def is_matched_all(self, idxs, values, field, **kwargs):
        fvalues = self._check_array(idxs, values, field)
        return all([x==y for x, y in zip(fvalues, values) if y is not None])

    def is_matched_any(self, idxs, values, field, **kwargs):
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

    def is_skipped(self, field):
        if self.is_matched_any(self.isteps, [None]*len(self.isteps), 
                               field, none_skip=False):
            return True
        if self.is_matched_any(self.ipercents, [None]*len(self.ipercents), 
                               field, none_skip=False):
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

            if self.is_matched_all(self.isteps, ['HH','UP','UP'], field):
                if self.after_hhupup <= 0:
                    self.after_hhupup = 15 
                else:
                    self.after_hhupup += 4
            elif self.is_matched_all(self.isteps, ['HH','UP',None], field) or \
                 self.is_matched_all(self.isteps, ['LW','HH',None], field):
                if self.after_hhupup <= 0:
                    self.after_hhupup = 2
                else:
                    self.after_hhupup += 2
            else:
                self.after_hhupup -= 1

            if self.is_matched_all(self.isteps, ['UP','UP','UP'], field) or \
               self.is_matched_any(self.isteps, ['HH','HH','HH'], field):
                break

            if self.is_matched_any(self.isteps, ['DN','DN','DN'], field):
                if self.is_matched_all(self.isteps, ['LW','DN','DN'], field):
                    buycnt += 1
            elif self.is_matched_all(self.isteps, ['HH','UP',None], field):
                pass
            else:
                buycnt += 1

            if self.is_ge_any(self.ipercents, [90,80,None,60,60,None], field):
                buycnt = 0
                break
            elif self.is_le_all(self.ipercents, [0,0,0,0,0,0], field) or \
                 self.is_le_all(self.ipercents, [10,10,10,10,10,25], field):
                buycnt += 1
            
            if buycnt > 0 and self.after_hhupup >0:
                buycnt = 0

            break  # End of While

        if not fg_skip:
            buyreason += f'{self.after_hhupup}:'+','.join([str(field[x]) for x in self.isteps])
            buyreason += ':'+','.join([str(field[x]) for x in self.ipercents])

        self._fill_data([self.ibuycnt, self.ibuyreason], [buycnt, buyreason], field)


class AlgoTable(AlgoModel):

    def __init__(self, qdata, cfg=None):
        self.qdata = Dict(json.loads(json.dumps(qdata)))
        self.operate = []
        qcolnames = self.qdata.colnames
        self.cfg = self.default_option() if cfg is None else cfg

        self.operate.append(OpPrice(self.cfg.price, qcolnames))
        self.operate.append(OpGradient(self.cfg.gradient, 'end', qcolnames))
        for sa in self.cfg.sum.accums:
            op = OpSumAvg(sa, qcolnames)
            self.operate.append(op)
            self.operate.append(OpGradient(self.cfg.gradient, op.name, qcolnames))
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
        cfg.price.buy.colname = 'buyp'
        cfg.price.buy.percent = 20
        cfg.price.sell.colname = 'sellp'
        cfg.price.sell.percent = 80
        cfg.condition.buy.negative = [
            {'steps': Dict({'op':'OR', 'val':['DN', 'DN', 'DN']})},
        ]
        cfg.condition.buy.positive = [
            {'steps': Dict({'op':'AND', 'val':['LW', 'DN', 'DN']})},
        ]
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
        operate = [CondBuy(self.cfg, pdata.colnames)]

        for idx in range(len(pdata.fields)):
            for op in operate:
                op.process(self.cfg, idx, pdata.fields)

        return pdata


