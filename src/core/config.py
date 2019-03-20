
import os

from pysp.sbasic import SSingleton
from pysp.sconf import SConfig


class BillConfig(SConfig, metaclass=SSingleton):
    def __init__(self):
        folder = os.path.dirname(os.path.abspath(__file__))
        self.config_folder = f'{folder}/../config/'
        configyml = f'{self.config_folder}/config.yml'
        super(BillConfig, self).__init__(yml_file=configyml)
        self.init_variables()

    def init_variables(self):
        stock_yml = f'{self.config_folder}/db/stock.yml'
        self.set_value('_config.db.stock_yml', stock_yml)
        stock_folder = self.get_value('folder.stock', './')
        self.set_value('_config.db.stock_folder', stock_folder)
