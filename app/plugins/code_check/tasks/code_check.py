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

import sys
import subprocess

from app.build import Check

class Run(Check):
    '''
    check commit msg and return result
    '''
    def do_check(self, param):
        # param need list variables:
        # pr_branch, head_branch, repo_dir
        check_res = True
        for file_path in param.diff_files.split(" "):
            if file_path.endswith(".py"):
                print("check python")
                check_res = check_res & self._check_python(file_path=file_path)
        if not check_res:
            sys.exit(1)

    def _check_python(self, file_path:str):
        show_res = subprocess.run("pip show flake8", shell=True, check=False)
        if show_res.returncode != 0:
            install_res = subprocess.run(
                "pip install flake8 -i https://pypi.tuna.tsinghua.edu.cn/simple",
                shell=True,
                check=False)
            if install_res.returncode != 0:
                raise self.CheckError("install flake8 faild")
        res = subprocess.run(
            f"flake8 {file_path} --max-line-length 100",
            stdout=subprocess.PIPE,
            shell=True,
            check=False,
            encoding="utf-8")
        if res.returncode != 0:
            print("=============================================")
            print(res.stdout)
            print("=============================================")
            return False
        return True
