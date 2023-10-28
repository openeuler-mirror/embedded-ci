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

import argparse
import json

from app.command import Command
from app import util

class Serial(Command):
    '''
    this class is to encode param to base64 code, the result can be use
    as a string param, when we use some object param, it will be invalid
    in command, so we make object to string to solve it
    '''
    def __init__(self):
        super().__init__(
            "serial", 
            "translate param to base64 code", 
            """this class is to encode param to base64 code, the result can be use
    as a string param, when we use some object param, it will be invalid
    in command, so we make object to string to solve it""")

    def do_add_parser(self,parser_addr: argparse._SubParsersAction):
        parser = parser_addr.add_parser(name=self.name)
        parser.add_argument('-c', '--param', dest="params", action='append',
            help='''
            this param is some key and value that will be translate to base64 code, the format like -c key=value
            ''')

        return parser

    def do_run(self, args, unknow):
        if unknow[0] == "string":
            del unknow[0]
            print(util.base64_encode(" ".join(unknow)))
            return
        args = self.parser.parse_args(unknow)

        obj = {}
        for param in args.params:
            param_list = param.split('=')
            if len(param_list) < 2:
                continue
            obj[param_list[0]] = param_list[1]
        print(util.base64_encode(json.dumps(obj)))
