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
        diff_files = param.diff_files.split(" ")
        self._install_plugins(diff_files=diff_files)
        check_res = True
        for file_path in param.diff_files.split(" "):
            if file_path.endswith(".py"):
                check_res = check_res & self._check_python(file_path=file_path)
        if not check_res:
            sys.exit(1)
        print("code check successful!!!")

    def _install_plugins(self, diff_files:list):
        install_plugin = {}
        for file_path in diff_files:
            if file_path.endswith(".py"):
                install_plugin['_install_flake8'] = True
                install_plugin['_install_pylint'] = True
        for plugin in install_plugin:
            getattr(self, plugin)()

    def _install_flake8(self):
        show_res = subprocess.run(
            "pip show flake8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            check=False)
        if show_res.returncode != 0:
            print("flake8 is not installed")
            install_res = subprocess.run(
                "pip install flake8 -i https://pypi.tuna.tsinghua.edu.cn/simple",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                check=False)
            if install_res.returncode != 0:
                raise self.CheckError("install flake8 faild")
            print("flake8 install successful!!!")

    def _install_pylint(self):
        show_res = subprocess.run(
            "pip show pylint",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            check=False)
        if show_res.returncode != 0:
            print("pylint is not installed")
            install_res = subprocess.run(
                "pip install pylint -i https://pypi.tuna.tsinghua.edu.cn/simple",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                check=False)
            if install_res.returncode != 0:
                raise self.CheckError("install pylint faild")
            print("pylint install successful!!!")

    def _check_python(self, file_path:str):
        print(f"===============->>>{file_path}")
        check_result = True
        # use flake8 to check code
        res = subprocess.run(
            f"flake8 {file_path} --max-line-length 100",
            stdout=subprocess.PIPE,
            shell=True,
            check=False,
            encoding="utf-8")
        if res.returncode != 0:
            print("flake8 check result:")
            print(res.stdout)
            check_result = False
        # use pylint to check code
        res = subprocess.run(
            f"pylint {file_path}",
            stdout=subprocess.PIPE,
            shell=True,
            check=False,
            encoding="utf-8")
        if res.returncode != 0:
            print("pylint check result:")
            print(res.stdout)
            check_result = False
        if check_result:
            print("this file check passed successfully.")
        print("====================================================================\n")
        return check_result
