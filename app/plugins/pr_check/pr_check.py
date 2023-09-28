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
from app.lib import Gitee

class PrCheck(Command):
    '''
    This class is used to screen the changes in the current code, and determine which inspection tasks need to be executed.
    '''
    def __init__(self):
        self.gitee = None

        super().__init__(
            "pr_check", 
            "get task range for this pr", 
            "This class is used to screen the changes in the current code, and determine which inspection tasks need to be executed.")

    def do_add_parser(self,parser_addr: argparse._SubParsersAction):
        parser = parser_addr.add_parser(name=self.name)
        parser.add_argument('-o', '--owner', dest="owner")
        parser.add_argument('-p', '--repo', dest="repo")
        parser.add_argument('-gt', '--gitee_token', dest="gitee_token")
        parser.add_argument('-pr', '--pr_num', dest="pr_num")

        return parser

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)
        self.gitee = Gitee(owner=args.owner, repo= args.repo, token=args.gitee_token)
        commits_files_data = self.gitee.get_commits_files(args.pr_num)
        commit_files_list = json.loads(commits_files_data)
        path_list = self._get_file_path_list(commit_files_list=commit_files_list)
        result = []
        if self.has_docs(path_list=path_list):
            result.append("docs")
        if self.has_code(path_list=path_list):
            result.append("code")
        print(' '.join(result))

    def _get_file_path_list(self, commit_files_list:list):
        path_list = []
        for commit_files in commit_files_list:
            #get the path of files that have been updated, added, or deleted
            change_path = commit_files['filename'].split('\n')
            path_list.extend(change_path)
        return path_list

    def has_docs(self, path_list :list):
        '''
        determine whether to ask for document build
        '''
        for file_path in path_list:
            if file_path.startswith("docs/"):
                return True
        return False

    def has_code(self, path_list: list):
        '''
        datermine whether to ask for code build
        '''
        for file_path in path_list:
            if not file_path.startswith("docs/"):
                return True
        return False
