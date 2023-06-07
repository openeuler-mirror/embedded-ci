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
import shutil
import subprocess

from app.build import Build,BuildRes,Arch,Board
from app import util
from app.lib import Result

NATIVE_SDK_DIR= "/opt/buildtools/nativesdk"
GCC_DIR = "/usr1/openeuler/gcc"

class Run(Build):
    '''
    Inherit the Build interface class to implement specific services
    '''
    def do_build(self, param):
        oebuild_workspace = os.path.join(param.workspace, "oebuild_workspace")
        # because oebuild_worksapce directory will be initialize by oebuild,
        # so if exists and delete it
        if os.path.exists(oebuild_workspace):
            shutil.rmtree(oebuild_workspace)

        # execute oebuild init and move repo to oebuild_workspace's src directory
        os.chdir(param.workspace)
        err_code, result = subprocess.getstatusoutput("oebuild init oebuild_workspace")
        if err_code != 0:
            raise ValueError(result)
        print(result)
        oebuild_src_dir = os.path.join(oebuild_workspace, 'src')
        shutil.move(
            src = param.repo_dir,
            dst = os.path.join(oebuild_src_dir, os.path.basename(param.repo_dir)))

        # param trigger conf
        gate_path = os.path.join(os.path.dirname(__file__), "build.yaml")
        gate_conf = util.parse_yaml(gate_path)

        arch_res = []
        for arch in gate_conf['build_check']:
            toolchain_dir = os.path.join(GCC_DIR, arch['toolchain'])
            board_res = []
            for board in arch['board']:
                os.chdir(oebuild_workspace)
                err_code, result = subprocess.getstatusoutput(f"oebuild generate\
                    -p {board['platform']}\
                    -n {NATIVE_SDK_DIR}\
                    -t {toolchain_dir}\
                    -b_in host\
                    -d {board['directory']}")
                if err_code != 0:
                    raise ValueError(result)
                print(result)

                # download layer with manifest
                yocto_dir = os.path.join(oebuild_src_dir, os.path.basename(param.repo_dir))
                compile_path = os.path.join(
                    oebuild_workspace,
                    'build',
                    board['directory'],
                    'compile.yaml')
                layer_list = util.parse_yaml(compile_path)['repos']
                manifest_path = os.path.join(yocto_dir, '.oebuild/manifest.yaml')
                if os.path.exists(manifest_path):
                    manifest = util.parse_yaml(manifest_path)['manifest_list']
                    for value in layer_list:
                        if value in manifest:
                            layer_repo = manifest[value]
                            print(f"clone {value}")
                            if os.path.exists(os.path.join(oebuild_src_dir, value)):
                                continue
                            util.clone_repo_with_version_depth(
                                src_dir = oebuild_src_dir,
                                repo_dir = value,
                                remote_url = layer_repo['remote_url'],
                                version = layer_repo['version'],
                                depth = 1)

                for image in board['image']:
                    # run `oebuild bitbake openeuler-image`
                    with subprocess.Popen(
                                f"oebuild bitbake {image['name']}",
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                cwd=os.path.join(oebuild_workspace, 'build', board['directory']),
                                encoding="utf-8") as s_p:
                        last_line = ""
                        for line in s_p.stderr:
                            line = line.strip('\n')
                            last_line = line
                            print(line)
                        for line in s_p.stdout:
                            line = line.strip('\n')
                            last_line = line
                            print(line)
                        s_p.wait()

                        if last_line.find("returning a non-zero exit code.") != -1:
                            build_res = Result().faild
                        else:
                            build_res = Result().success
                        board_res.append(Board(name=f"{image['name']}({board['name']})", result=build_res))
                # because tmp directory use large space so support a param to delete it
                # when build finished
                tmp_dir = os.path.join(oebuild_workspace, 'build', board['directory'], 'tmp')
                if os.path.exists(tmp_dir):
                    shutil.rmtree(tmp_dir)
            arch_res.append(Arch(name=arch['arch'],boards=board_res))

        return BuildRes(archs=arch_res)
