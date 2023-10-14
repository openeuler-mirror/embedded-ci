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
import os

from app import util
from app.command import Command
from app.build import Utest, UtestParam


NATIVE_SDK_DIR= "/opt/buildtools/nativesdk"
GCC_DIR = "/usr1/openeuler/gcc"

class TestPlatform(Command):
    '''
    Handle pull request business and build image which is specified by the passed in parameters
    '''
    def __init__(self):
        self.workspace = os.environ['HOME']

        super().__init__(
            "testPlatform", 
            "Test Platform", 
            "Test Platform is used to test images")

    def do_add_parser(self,parser_addr: argparse._SubParsersAction):
        parser = parser_addr.add_parser(name=self.name)
        parser.add_argument('-a', '--arch', dest="arch", default="basic_test.json")
        parser.add_argument('-target', '--target', dest="target")
        parser.add_argument('-td', '--target_directory', dest = "target_directory")
        parser.add_argument('-tm', '--mugen_url', dest = "mugen_url", default=None)
        parser.add_argument('-tb', '--mugen_branch', dest = "mugen_branch", default="master")

        return parser

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)
        #check build_code
        if not os.path.isdir(args.target_directory):
            raise ValueError(f"Code for build not exist in path: {args.target_directory} ! ")

        #invoke process class
        task_path = util.get_top_path() + f"/app/plugins/test_platform/tasks/{args.target}.py"
        cls:Utest = util.get_spec_ext(task_path, "Run")
        return cls.utest(param=UtestParam(
            arch=args.arch,
            target_dir=args.target_directory,
            mugen_url=args.mugen_url,
            mugen_branch=args.mugen_branch))
