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

from app.build import Build

class Run(Build):
    """
    do openeuler doc build
    """
    def do_build(self, param):
        '''
        doc build
        '''
        doc_dir = os.path.join(param.build_code, "docs")
        if not os.path.exists(doc_dir):
            raise ValueError(f"The path of doc to build is not exist: {doc_dir}")
        os.chdir(doc_dir)
        doc_build_result = subprocess.run(['make', 'html','SPHINXOPTS="-W"'],
                                          capture_output=True,
                                          text=True,
                                          check=False)
        if doc_build_result.returncode == 0:
            print(doc_build_result.stdout)
        else:
            print('============文档构建失败，错误信息：============')
            print(doc_build_result.stderr)
            print("============================================")
            raise self.BuildError("Doc Build ERROR")
