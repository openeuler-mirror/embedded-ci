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
import shutil

from app.command import Command
from app import util


class CloneRepo(Command):
    '''
    This class is used to download the corresponding code.
    It can be downloaded by version, pr_num, or specified
    download depth, etc.
    '''
    def __init__(self):

        super().__init__(
            "CloneRepo ", 
            "download repo code", 
            """This class is used to download the corresponding code.
    It can be downloaded by version, pr_num, or specified
    download depth, etc.""")

    def do_add_parser(self,parser_addr: argparse._SubParsersAction):
        parser = parser_addr.add_parser(name=self.name)
        parser.add_argument('-r', '--remote_url', dest="remote_url", default=None)
        parser.add_argument('-w', '--workspace', dest="workspace", default=None)
        parser.add_argument('-p', '--repo', dest="repo")
        parser.add_argument('-pr', '--pr_num', dest="pr_num", default=None)
        parser.add_argument('-v', '--version', dest="version", default=None)
        parser.add_argument('-dp', '--depth', dest="depth", default=1)

        return parser

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)
        if args.workspace is not None:
            if not os.path.exists(args.workspace):
                os.makedirs(args.workspace)
            os.chdir(args.workspace)

        if os.path.exists(args.repo):
            shutil.rmtree(args.repo)

        if args.pr_num is not None:
            util.clone_repo_with_pr(
                src_dir="./",
                repo=args.repo,
                remote_url=args.remote_url,
                pr_num=args.pr_num,
                depth=int(args.depth))
        else:
            util.clone_repo_with_version_depth(
                src_dir="./",
                repo_dir=args.repo,
                remote_url=args.remote_url,
                version=args.version,
                depth=int(args.depth))
             