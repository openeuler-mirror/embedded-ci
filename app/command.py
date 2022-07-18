'''
Copyright (c) 2023 openEuler Embedded
oebuild is licensed under Mulan PSL v2.
You can use this software according to the terms and conditions of the Mulan PSL v2.
You may obtain a copy of Mulan PSL v2 at:
         http://license.coscl.org.cn/MulanPSL2
THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
See the Mulan PSL v2 for more details.
'''

from abc import abstractmethod, ABC
import argparse
from typing import List

class Command(ABC):
    '''
    The command business class has a built-in command interface
    that is called, and new commands need to inherit this class
    '''
    def __init__(self, name, help_msg, description):
        self.name = name
        self.help_msg = help_msg
        self.description = description
        self.parser = None

    @abstractmethod
    def do_add_parser(self, parser_addr):
        '''
        the interface will be invoke by run
        '''

    @abstractmethod
    def do_run(self, args: argparse.Namespace, unknow: List[str]):
        '''
        the interface will be invoke by add_parser
        '''

    def run(self, args: argparse.Namespace, unknow: List[str]):
        '''
        run command with args
        '''
        self.do_run(args=args, unknow=unknow)

    def add_parser(self, parser_addr):
        '''
        add sub parser
        '''
        parser = self.do_add_parser(parser_addr=parser_addr)
        if parser is None:
            raise ValueError('add parser faild')

        self.parser = parser
        return self.parser
