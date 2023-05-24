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
import os
import subprocess
import shutil
import hashlib
from io import StringIO
import time

import yaml

from app import util
from app.command import Command
from app.lib import Remote, Gitee
from app import const

GITEE_YOCTO = "yocto-meta-openeuler"
GITEE_SPACE = "openeuler"
NATIVE_SDK_DIR= "/opt/buildtools/nativesdk"
GCC_DIR = "/usr1/openeuler/gcc"

class CI(Command):
    '''
    Regularly build the corresponding release image according
    to the relevant configuration file, CI construction will 
    rely on sstate-cache, and sstate-cache is stored in the 
    scheduled cron directory, so you need to pass in the shared 
    directory parameter when passing parameters, so the cron 
    directory will be found
    '''
    def __init__(self):
        self.workspace = os.path.join(os.environ['HOME'], 'oebuild_workspace')
        self.branch = None
        self.remote = None
        self.gitee = None

        super().__init__(
            "ci", 
            "for daily build",
            """
Periodically build the corresponding release image according to the relevant configuration file
""")

    def do_add_parser(self,parser_addr: argparse._SubParsersAction):
        parser = parser_addr.add_parser(name=self.name)
        parser.add_argument('-b', '--branch', dest="branch", default="master")
        parser.add_argument('-e', '--remote_dst_dir', dest="remote_dst_dir")
        parser.add_argument('-i', '--remote_dst_ip', dest="remote_dst_ip")
        parser.add_argument('-u', '--remote_dst_user', dest="remote_dst_user")
        parser.add_argument('-w', '--remote_dst_pwd', dest="remote_dst_pwd")
        parser.add_argument('-k', '--remote_dst_sshkey', dest="remote_dst_sshkey")
        parser.add_argument('-o', '--owner', dest="owner")
        parser.add_argument('-p', '--repo', dest="repo")
        parser.add_argument('-gt', '--gitee_token', dest="gitee_token")
        parser.add_argument('-sf', '--send_faild', dest = "is_send_faild", action = "store_true")
        parser.add_argument('-dm', '--delete_tmp', dest = "is_delete_tmp", action = "store_true")

        return parser

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)

        self.branch = args.branch
        # remote is to put local file to remote dir
        self.remote = Remote(
            remote_ip=args.remote_dst_ip,
            remote_user=args.remote_dst_user,
            remote_pwd=args.remote_dst_pwd,
            remote_key=args.remote_dst_sshkey
            )

        if args.is_send_faild:
            self.gitee = Gitee(owner=args.owner, repo=args.repo, token=args.gitee_token)

        self.exec(
            dst_dir=args.remote_dst_dir,
            is_delete_tmp=args.is_delete_tmp,
            is_send_faild=args.is_send_faild)

    def exec(self, dst_dir, is_delete_tmp, is_send_faild):
        '''
        the exec will be called by gate
        '''
        # first run oebuild init
        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)

        os.chdir(os.path.dirname(self.workspace))
        cmd = f"oebuild init -b {self.branch} {os.path.basename(self.workspace)}"
        err_code, result = subprocess.getstatusoutput(cmd=cmd)
        if err_code != 0:
            raise ValueError(result)
        print(result)

        # second copy basic layer to workspace and run oebuild update
        workspace_src_dir = os.path.join(self.workspace, "src")
        os.chdir(workspace_src_dir)
        print(f"clone {GITEE_YOCTO}")
        util.clone_repo_with_depth(
            src_dir=workspace_src_dir,
            repo=GITEE_YOCTO,
            remote_url=f"https://gitee.com/{GITEE_SPACE}/{GITEE_YOCTO}.git",
            depth=1)

        # get cron config
        conf_dir = util.get_conf_path()
        ci_conf = util.parse_yaml(os.path.join(conf_dir, const.CI_CONF))

        build_faild_list = []
        # third run oebuild generate
        for arch in ci_conf['build_list']:
            # set gcc toolchain directory
            toolchain_dir = os.path.join(GCC_DIR, arch['toolchain'])
            for board in arch['board']:
                features = None
                if "feature" in board and board['feature'] is not None and len(board['feature']) > 0:
                    features = ""
                    for feature in board['feature']:
                        features = features + f" -f {feature['name']}"
                # run `oebuild generate` for compile.yaml
                generate_cmd = f"oebuild generate\
                            -p {board['platform']}\
                            -n {NATIVE_SDK_DIR}\
                            -t {toolchain_dir}\
                            -b_in host\
                            -dt \
                            -d {board['directory']}"
                if features is not None:
                    generate_cmd += features
                err_code, result = subprocess.getstatusoutput(generate_cmd)
                if err_code != 0:
                    raise ValueError(result)
                print(result)

                # download layer with manifest
                yocto_dir = os.path.join(workspace_src_dir, GITEE_YOCTO)
                compile_path = os.path.join(
                    self.workspace,
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
                            if os.path.exists(os.path.join(workspace_src_dir, value)):
                                continue
                            util.clone_repo_with_version_depth(
                                src_dir = workspace_src_dir,
                                repo_dir = value,
                                remote_url = layer_repo['remote_url'],
                                version = layer_repo['version'],
                                depth = 1)

                # add not_use_repos = true
                key_value = 'not_use_repos: true'
                self._add_content_to_file(file_path=compile_path, key_value=key_value)

                # run `oebuild bitbake openeuler-image`
                print(f"========================={board['directory']}==========================")
                for bitbake in board['bitbake']:
                    with subprocess.Popen(f"oebuild bitbake {bitbake['target']}",
                                    shell=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    cwd=os.path.join(self.workspace, 'build', board['directory']),
                                    encoding="utf-8") as s_p:
                        last_line = ""
                        for line in s_p.stdout:
                            line = line.strip('\n')
                            last_line = line
                            print(line)
                        s_p.wait()
                        if last_line.find("returning a non-zero exit code.") != -1:
                            print(f"build {board['directory']}->{bitbake['target']} faild")
                            build_faild = {
                                'arch': arch['arch'],
                                'directory': board['directory'],
                                'generate': generate_cmd,
                                'bitbake': bitbake['target']
                            }
                            build_faild_list.append(build_faild)
                            continue
                        # upload output
                        print(f"build {board['directory']}->{bitbake['target']} successful")

                # because tmp directory use large space so support a param to delete it
                # when build finished
                tmp_dir = os.path.join(self.workspace, 'build', board['directory'], 'tmp')
                if is_delete_tmp and os.path.exists(tmp_dir):
                    shutil.rmtree(tmp_dir)

                output_dir = os.path.join(self.workspace, 'build', board['directory'], 'output')
                if not os.path.exists(output_dir):
                    continue
                os.chdir(output_dir)
                # add sha256sum to every output file
                self._add_sum_to_local_dir(local_dir=output_dir)

                # put local_file to remote_dir
                put_dst_dir = os.path.join(dst_dir, arch['arch'], board['directory'])
                print("put local build files to remote path")
                dir_list = os.listdir(output_dir)
                for timestamp_dir in dir_list:
                    local_dir = os.path.join(output_dir, timestamp_dir)
                    self.remote.put_to_remote(
                        local_dir=local_dir,
                        dst_dir=put_dst_dir,
                        is_delete_dst=True)

        # send build faild msg to issue
        if is_send_faild:
            self.send_issue_with_build_faild(build_faild_list)

        # generate manifest.yaml and upload to remote server
        self._generate_upload_manifest(dst_dir=dst_dir)

        print("========================================================")
        if len(build_faild_list) <= 0:
            print("all build successful")
        else:
            print("the list faild:")
            for build_faild in build_faild_list:
                print(f"arch:{build_faild['arch']},    board:{build_faild['directory']},    bitbake: {build_faild['bitbake']}")

            raise ValueError("build project bas error")
        print("========================================================")

    def _generate_upload_manifest(self, dst_dir):
        print("=================generate manifest========================")
        source_list_dir = "source_list"
        manifest_dir = os.path.join(source_list_dir, "manifest.yaml")
        with subprocess.Popen(f"oebuild manifest -c -m_dir {manifest_dir}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self.workspace,
            encoding="utf-8") as s_p:
            for line in s_p.stdout:
                line = line.strip('\n')
                print(line)
        print("=================generate manifest========================")

        local_dir = os.path.join(self.workspace, source_list_dir)
        self._add_sum_to_local_dir(local_dir = local_dir)
        put_dst_dir = os.path.join(dst_dir, source_list_dir)
        self.remote.put_to_remote(
            local_dir=local_dir,
            dst_dir=put_dst_dir,
            is_delete_dst=True)

    def _add_sum_to_local_dir(self, local_dir):
        file_list = os.listdir(local_dir)
        for file_name in file_list:
            file_path = os.path.join(local_dir, file_name)
            if os.path.isdir(file_path):
                self._add_sum_to_local_dir(file_path)
            else:
                sha256 = hashlib.sha256(''.encode('utf-8'))
                with open(file_path, 'rb') as r_f:
                    while data := r_f.read(1024):
                        sha256.update(data)
                    with open(f'{file_path}.sha256sum', 'w', encoding="utf-8") as w_f:
                        w_f.write(f"{str(sha256.hexdigest())} {file_name}")

    def send_issue_with_build_faild(self, build_faild_list):
        '''
        send build faild message to issue
        '''
        def format_build_list(build_faild_list):
            msg_data = {}
            for build_faild in build_faild_list:
                if build_faild['arch'] in msg_data:
                    msg_arch = msg_data[build_faild['arch']]
                else:
                    msg_arch = {}

                if build_faild['directory'] in msg_arch:
                    msg_arch_directory = msg_arch[build_faild['directory']]
                else:
                    msg_arch_directory = {}

                if "generate" not in msg_arch_directory:
                    msg_arch_directory['generate'] = build_faild['generate']

                if "target" in msg_arch_directory:
                    msg_arch_directory_target = msg_arch_directory['target']
                else:
                    msg_arch_directory_target = []

                msg_arch_directory_target.append(f"bitbake {build_faild['bitbake']}")

                msg_arch_directory['target'] = msg_arch_directory_target
                msg_arch[build_faild['directory']] = msg_arch_directory

                msg_data[build_faild['arch']] = msg_arch
            return msg_data

        if len(build_faild_list) <= 0:
            return
        msg_data = format_build_list(build_faild_list)
        with StringIO() as sio:
            yaml.dump(msg_data, stream=sio)
            issue_msg = sio.getvalue()
            build_url = os.path.join(os.environ['BUILD_URL'], 'console')
            issue_msg = issue_msg + "\n\n"
            issue_msg = issue_msg + f"please click <a href={build_url}>here</a> for detail"
            time_str = time.strftime("%Y-%m-%d %X", time.localtime())
            title = f"[{self.branch}]构建失败  {time_str}"
            self.gitee.add_issue_to_repo(title=title, body=issue_msg)

    def _add_content_to_file(self, file_path, key_value):
        with open(file_path, 'r', encoding='utf-8') as r_f:
            content = r_f.read()

        content = key_value + "\n" + content
        with open(file_path, 'w', encoding= 'utf-8') as w_f:
            w_f.write(content)
