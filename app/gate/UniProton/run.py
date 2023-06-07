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

from app.build import Build,BuildRes,Arch,Board
from app import util
from app.lib import Result

class Run(Build):
    '''
    Inherit the Build interface class to implement specific services
    '''
    def do_build(self,param):
        libbound_repo = "libboundscheck"
        libbound_repo_remote = "https://gitee.com/openeuler/libboundscheck.git"
        libbounds_dir = os.path.join(param.workspace, libbound_repo)
        # download libboundscheck
        if not os.path.exists(libbounds_dir):
            util.clone_repo_with_depth(
                src_dir=param.workspace,
                repo=libbound_repo,
                remote_url=libbound_repo_remote,
                branch="master",
                depth=1)
        gate_path = os.path.join(os.path.dirname(__file__), "build.yaml")
        gate_conf = util.parse_yaml(gate_path)
        os.chdir(param.workspace)
        # copy libboundcheck rely to
        subprocess.getstatusoutput(f"cp {libbounds_dir}/include/* {param.repo_dir}/platform/libboundscheck/include")
        subprocess.getstatusoutput(f"cp {libbounds_dir}/include/* {param.repo_dir}/include")
        subprocess.getstatusoutput(f"cp {libbounds_dir}/src/* {param.repo_dir}/platform/libboundscheck/src")
        arch_res = []
        for arch in gate_conf['build_check']:
            board_res = []
            for board in arch['board']:
                # run `oebuild bitbake openeuler-image`
                with subprocess.Popen(
                    f"python3 build.py {board['name']}",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=param.repo_dir,
                    encoding="utf-8") as s_p:

                    last_line = ""
                    for line in s_p.stdout:
                        line = line.strip('\n')
                        last_line = line
                        print(line)
                    for line in s_p.stderr:
                        line = line.strip('\n')
                        last_line = line
                        print(line)
                    s_p.wait()

                    if last_line.find("all lib succeed! ####################") != -1:
                        build_res = Result().success
                    else:
                        build_res = Result().faild
                    board_res.append(Board(name=f"{board['name']}", result=build_res))
            arch_res.append(Arch(name=arch["arch"], boards=board_res))
        return BuildRes(archs=arch_res)
