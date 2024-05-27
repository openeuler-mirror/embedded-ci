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

from app.build import Build
from app import util


NATIVE_SDK_DIR = "/opt/buildtools/nativesdk"
GCC_DIR = "/usr1/openeuler/gcc"
PRE_SOURCE_DIR = "/usr1/src"


class Run(Build):
    """
    do openeuler image build
    """
    def do_build(self, param):
        '''
        image build
        '''
        oebuild_workspace = os.path.join(param.workspace, "oebuild_workspace")
        print("=========================== oebuild init ============================")
        check_init = False
        if os.path.exists(oebuild_workspace):
            # check if oebuild_workspace if oebuild workspace
            list_dir = os.listdir(oebuild_workspace)
            if ".oebuild" not in list_dir or "src" not in list_dir:
                shutil.rmtree(oebuild_workspace)
                check_init = True
        else:
            check_init = True
        if check_init:
            os.chdir(param.workspace)
            err_code, result = subprocess.getstatusoutput("oebuild init oebuild_workspace")
            if err_code != 0:
                print(result)
                raise ValueError(result)
            print(result)
        oebuild_src_dir = os.path.join(oebuild_workspace, 'src')
        yocto_in_src_path = os.path.join(oebuild_src_dir, "yocto-meta-openeuler")
        err_code, result = subprocess.getstatusoutput(
            f"ln -sf {param.build_code} {yocto_in_src_path}")
        if err_code != 0:
            print(result)
            raise ValueError(result)
        print("=========================== init finished ===========================")

        print("======================== oebuild generate =========================")
        os.chdir(oebuild_workspace)
        # if exists build dir,delete it
        build_dir = os.path.join(oebuild_workspace, 'build', param.directory)
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        generate_cmd = f"oebuild generate\
            -p {param.platform}\
            -n {NATIVE_SDK_DIR}\
            -t {os.path.join(GCC_DIR, param.toolchain)}\
            -b_in host\
            -d {param.directory}"
        if param.features is not None:
            for feature in [i.strip() for i in str(param.features).split(';')]:
                generate_cmd = generate_cmd + f" -f {feature}"
        if param.sstate_cache_in is not None:
            if os.path.isdir(param.sstate_cache_in):
                generate_cmd = generate_cmd + f" -s {param.sstate_cache_in}"
            else:
                print("[WARN]:Parameter sstate_cache_in was not successfully applied ")
        if param.sstate_cache_out is not None:
            if os.path.isdir(param.sstate_cache_out):
                generate_cmd = generate_cmd + f" -s_dir {param.sstate_cache_out}"
            else:
                print("[WARN]:Parameter sstate_cache_out was not successfully applied ")

        err_code, result = subprocess.getstatusoutput(generate_cmd)
        if err_code != 0:
            print(result)
            raise ValueError(result)

        print("======================== generate finished ========================")

        # add rm_work in case avoid large cache causes the disk to fill up when building
        compile_path = os.path.join(build_dir, 'compile.yaml')
        compile_conf = util.parse_yaml(compile_path)
        local_conf = compile_conf['local_conf']
        local_conf += '\nINHERIT += "rm_work"\n'
        local_conf += 'RM_WORK_EXCLUDE += "glog libflann"\n'
        local_conf += f"""DATETIME = "{param.datetime}" \n"""
        compile_conf['local_conf'] = local_conf
        util.write_yaml(compile_path, compile_conf)

        # establish a soft link to access the source code present in the container
        if os.path.isdir(PRE_SOURCE_DIR):
            for pkg_name in os.listdir(PRE_SOURCE_DIR):
                pkg_path = os.path.join(PRE_SOURCE_DIR, pkg_name)
                if os.path.isdir(pkg_path):
                    link_path = os.path.join(oebuild_src_dir, pkg_name)
                    try:
                        os.symlink(pkg_path, link_path)
                    except FileExistsError:
                        print(f"{pkg_name} already exists in Path:{oebuild_src_dir}")
                        continue

        print("======================== oebuild bitbake ==========================")
        image_list = [i.strip() for i in str(param.images).split(';')]
        # run `oebuild bitbake openeuler-image`
        for image in image_list:
            print(f"==================== bitbake {param.directory}->{image} ======================")
            with subprocess.Popen(
                        f"oebuild bitbake {image} -k",
                        shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        cwd=build_dir,
                        encoding="utf-8") as s_p:
                if s_p.returncode is not None and s_p.returncode != 0:
                    err_msg = ''
                    if s_p.stderr is not None:
                        for line in s_p.stderr:
                            err_msg.join(line)
                        raise ValueError(err_msg)
                res = None
                while res is None:
                    res = s_p.poll()
                    if s_p.stdout is not None:
                        for line in s_p.stdout:
                            print(line.strip('\n'))
                    if s_p.stderr is not None:
                        for line in s_p.stderr:
                            print(line.strip('\n'))
                s_p.wait()
                if res != 0:
                    raise self.BuildError("Build Error")
            print(f"============== bitbake {param.directory}->{image} successful =================")
        print("=========================oebuild finished==========================")

    def _add_content_to_file(self, file_path, context):
        with open(file_path, 'r', encoding='utf-8') as r_f:
            data = r_f.read()

        data = context + "\n" + data
        with open(file_path, 'w', encoding='utf-8') as w_f:
            w_f.write(data)
