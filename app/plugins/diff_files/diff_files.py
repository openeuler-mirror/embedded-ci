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

from argparse import _SubParsersAction
import os
import subprocess

from app.command import Command

class DiffFiles(Command):
    '''
    code check, including commit msg check, commit scope check, etc
    '''
    def __init__(self):
        super().__init__(
            "DiffFiles ", 
            "Code check pull request business", 
            "Code check pull request business, including commit msg check, commit scope check, etc")

    def do_add_parser(self, parser_addr:_SubParsersAction):
        parser_addr.add_argument('-r', '--repo_dir', dest="repo_dir", default=None)
        parser_addr.add_argument('--remote_name', dest="remote_name")
        parser_addr.add_argument('--pre_branch', dest="pre_branch")
        parser_addr.add_argument('--diff_branch', dest="diff_branch")
        return parser_addr

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)
        # check if exists repo_dir
        if not os.path.exists(args.repo_dir):
            raise FileNotFoundError(f"the {args.repo_dir} not exists")
        # check repo_dir if is git repo
        result = subprocess.run(
            f'git -C {args.repo_dir} rev-parse --is-inside-work-tree',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True)
        if result.returncode != 0:
            raise ValueError(f"{args.repo_dir} is not repo dir")
        # fetch the diff branch
        result = subprocess.run(
            f"git fetch {args.remote_name} {args.diff_branch} --depth=1",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            cwd=args.repo_dir,
            encoding="utf-8",
            text=True)
        if result.returncode != 0:
            raise ValueError(result.stderr)
        # make diff between pre_branch and diff_branch
        result = subprocess.run(
            f"git diff {args.pre_branch} {args.remote_name}/{args.diff_branch} --name-only",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            check=True,
            cwd=args.repo_dir,
            encoding="utf-8",
            text=True)
        if result.returncode != 0:
            raise ValueError(result.stderr)
        output = result.stdout.strip("\n")
        file_splits = output.split("\n")
        for index,_ in enumerate(file_splits):
            file_splits[index] = os.path.join(args.repo_dir, file_splits[index])
        print(" ".join(file_splits))
