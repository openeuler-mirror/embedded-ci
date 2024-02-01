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

import subprocess

from app.build import Build,BuildParam

class Run(Build):
    """
    do openeuler image build
    """
    def do_build(self, param:BuildParam):
        self._install_wheel()
        res = subprocess.run(
            "python3 setup.py bdist_wheel",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            encoding="utf-8",
            text=True,
            cwd=param.build_code)
        if res.returncode != 0:
            print(res.stderr)
            raise ValueError("pypi package task failed")
        print(res.stdout)

    def _install_wheel(self):
        show_res = subprocess.run(
            "pip show wheel",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            check=False)
        if show_res.returncode != 0:
            print("wheel is not installed")
            install_res = subprocess.run(
                "pip install wheel -i https://pypi.tuna.tsinghua.edu.cn/simple",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                check=False)
            if install_res.returncode != 0:
                raise ValueError("install wheel faild")
            print("wheel install successful!!!")
