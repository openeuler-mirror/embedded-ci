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
from app.command import Command
from app.lib import Gitee
from app import util
from app.build import Check, CheckParam


class CodeCheck(Command):
    '''
    code check, including commit msg check, commit scope check, etc
    '''
    def __init__(self):
        self.workspace = os.environ['HOME']
        self.gitee = None
        self.pr_num = None
        self.repo = None

        super().__init__(
            "codeCheck ", 
            "Code check pull request business", 
            "Code check pull request business, including commit msg check, commit scope check, etc")

    def do_add_parser(self,parser_addr: argparse._SubParsersAction):
        parser = parser_addr.add_parser(name=self.name)
        parser.add_argument('-c', '--check_code', dest="check_code", default=None)
        parser.add_argument('-target', '--target', dest="target")
        parser.add_argument('-o', '--owner', dest="owner", default='openeuler')
        parser.add_argument('-p', '--repo', dest="repo", default="")
        parser.add_argument('-pr', '--pr_num', dest="pr_num", default=None)

        return parser

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)
        self.pr_num = args.pr_num
        self.repo = args.repo
        self.gitee = Gitee(owner=args.owner, repo=args.repo)

        #check build_code
        if args.check_code is not None and not os.path.isdir(args.check_code):
            raise ValueError(f"Code for build not exist in path: {args.check_code} ! ")

        #invoke process class
        task_path = util.get_top_path() + f"/app/plugins/code_check/tasks/{args.target}.py"
        cls:Check = util.get_spec_ext(task_path, "Run")
        cls.check(param=CheckParam(
            check_code=args.check_code,
            owner=args.owner,
            repo=args.repo,
            pr_num=args.pr_num))
