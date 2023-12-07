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

NATIVE_SDK_DIR= "/opt/buildtools/nativesdk"
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
        if os.path.exists(oebuild_workspace):
            shutil.rmtree(oebuild_workspace)
        os.chdir(param.workspace)
        err_code, result = subprocess.getstatusoutput("oebuild init oebuild_workspace")
        if err_code != 0:
            print(result)
            raise ValueError(result)
        print(result)
        oebuild_src_dir = os.path.join(oebuild_workspace, 'src')
        yocto_in_src_path = os.path.join(oebuild_src_dir, "yocto-meta-openeuler")
        shutil.copytree(param.build_code, yocto_in_src_path)
        print("=========================== init finished ===========================")

        print("======================== oebuild generate =========================")
        os.chdir(oebuild_workspace)
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

        print("========================= download layer ==========================")
        # download layer with manifest.yaml
        build_dir = os.path.join(oebuild_workspace, 'build', param.directory)
        compile_path = os.path.join(build_dir, 'compile.yaml')
        layer_list = util.parse_yaml(compile_path)['repos']
        manifest_path = os.path.join(yocto_in_src_path, '.oebuild/manifest.yaml')
        if os.path.exists(manifest_path):
            manifest = util.parse_yaml(manifest_path)['manifest_list']
            for value in layer_list:
                if value in manifest:
                    layer_repo = manifest[value]
                    print(f"clone {value}")
                    if os.path.exists(os.path.join(oebuild_src_dir, value)):
                        shutil.rmtree(os.path.join(oebuild_src_dir, value))
                    util.clone_repo_with_version_depth(
                        src_dir = oebuild_src_dir,
                        repo_dir = value,
                        remote_url = layer_repo['remote_url'],
                        version = layer_repo['version'],
                        depth = 1)
                else:
                    print(f"\n\n[ERROR]:manifest.yaml don't have info to download repo {value}.")
                    raise ValueError(f"manifest.yaml don't have info to download repo {value}.")
        print("==================== download layer finished ======================")

        # add not_use_repos = true
        self._add_content_to_file(compile_path, "not_use_repos: true")

        # add rm_work in case avoid large cache causes the disk to fill up when building
        compile_conf = util.parse_yaml(compile_path)
        local_conf = compile_conf['local_conf']
        local_conf += '\nINHERIT += "rm_work"\n'
        local_conf += 'RM_WORK_EXCLUDE += "glog libflann"\n'
        local_conf += f"""DATETIME = "{param.datetime}" \n"""
        compile_conf['local_conf'] = local_conf
        util.write_yaml(compile_path, compile_conf)

        #establish a soft link to access the source code present in the container
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
                    raise self.BuildError("Build Error")
            print(f"============== bitbake {param.directory}->{image} successful =================")
        print("=========================oebuild finished==========================")

    def _add_content_to_file(self, file_path, context):
        with open(file_path, 'r', encoding='utf-8') as r_f:
            data = r_f.read()

        data = context + "\n" + data
        with open(file_path, 'w', encoding= 'utf-8') as w_f:
            w_f.write(data)
