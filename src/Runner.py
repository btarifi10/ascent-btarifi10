from src.core import *
from src.utils import *


class Runner(Exceptionable, Configurable):

    def __init__(self, config_file_path: str):

        # initialize Configurable super class
        Configurable.__init__(self, SetupMode.NEW, ConfigKeys.MAIN.value, config_file_path)

        # get config path info from config and set to class vars
        self.exceptions_config_path = self.path(ConfigKeys.MAIN.value, 'config_paths', 'exceptions')

        # initialize Exceptionable super class
        Exceptionable.__init__(self, SetupMode.NEW, self.exceptions_config_path)

    def run(self):
        print('CURRENT CONFIGS: {}'.format(self.configs))
        _ = SlideMap(self.configs[ConfigKeys.MAIN.value],
                     self.configs[ConfigKeys.EXCEPTIONS.value])

        # quick sanity check
        print('exceptions_config_path:\t{}'.format(self.exceptions_config_path))

        # TEST: retrieve data from config file
        # print(self.search('test_array', 0, 'test'))

        # TEST: throw error
        # self.throw(3)
