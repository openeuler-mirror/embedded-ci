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

from app.plugins.comment.interface import translate_commend_param
from app.command import Command
from app.plugins.comment.cgate import CGate
from app import util

class Comment(Command):
    '''
    This command is to format result that come from gate or ci
    '''

    def __init__(self):

        super().__init__(
            "comment", 
            "format gate or ci result", 
            "This command is to format result that come from gate or ci")

    def do_add_parser(self,parser_addr: argparse._SubParsersAction):
        parser = parser_addr.add_parser(name=self.name)
        parser.add_argument('-m', '--method', dest="method")
        parser.add_argument('-o', '--owner', dest="owner")
        parser.add_argument('-p', '--repo', dest="repo")
        parser.add_argument('-dt', '--duration_time', dest="duration_time", default=None)
        parser.add_argument('-gt', '--gitee_token', dest="gitee_token")
        parser.add_argument('-pr', '--pr_num', dest="pr_num")
        parser.add_argument('-chk', '--checks', dest='checks', action='append')

        return parser

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)
        check_list = []
        for check in args.checks:
            check = util.base64_decode(check)
            check_list.append(translate_commend_param(json.loads(check)))
        print(check_list)

        duration_str = None
        if args.duration_time is not None:
            duration_str = self.format_time(int(args.duration_time))

        if args.method == "gate":
            cls = CGate()
            cls.run(check_list=check_list,
                    pr_num=args.pr_num,
                    repo=args.repo,
                    owner=args.owner,
                    gitee_token=args.gitee_token,
                    duration = duration_str)

    def format_time(self, duration_time)->str:
        '''
        duration_time must be in millisecond
        '''
        duration_s = duration_time / 1000
        # Extraction time, minute, second
        hours, remainder = divmod(duration_s, 3600)
        minutes, seconds = divmod(remainder, 60)

        # format duration string
        duration_parts = []
        if hours > 0:
            duration_parts.append(f"{int(hours)}小时")
        if minutes > 0:
            duration_parts.append(f"{int(minutes)}分")
        if seconds > 0:
            duration_parts.append(f"{int(seconds)}秒")

        return ''.join(duration_parts)
