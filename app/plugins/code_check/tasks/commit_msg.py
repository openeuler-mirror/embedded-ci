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
import os
import subprocess
import json

from app import util
from app.build import Check
from app.lib import Gitee

class Run(Check):
    '''
    check commit msg and return result
    '''
    def do_check(self, param):
        gitee = Gitee(owner=param.owner, repo=param.repo)
        commit_hash_list = json.loads(gitee.get_pr_commits(param.pr_num))

        #select config to use
        if param.check_code is not None and os.path.exists(param.check_code) and os.path.exists(os.path.join(param.check_code, ".gitlint")):
            os.chdir(param.check_code)
            config_path = os.path.join(param.check_code, ".gitlint")
        else:
            config_path = os.path.join(util.get_conf_path(), '.gitlint')

        res = []
        for commit in commit_hash_list:
            # get commit and add to dist for follow using
            commit_hash = commit["sha"]
            command = f"gitlint --commit {commit_hash} -C {config_path}"
            check_res = subprocess.getoutput(cmd=command)
            if check_res != "":
                res.append({'commit': commit_hash, 'result': check_res})

        if len(res) > 0:
            print("===================Commit Msg Errors========================")
            for check_res in res:
                print("commit:" + check_res['commit'])
                print("check result: \n", check_res['result'])
                link = "https://openeuler.gitee.io/yocto-meta-openeuler/master/develop_help/commit.html"
                print(f"refer to commit msg convention with link:\n\n\n    {link}")
                print("============================================================")
            raise self.CheckError("Commit msg did't comply with the convention")
        print("commit msg check successful!")
