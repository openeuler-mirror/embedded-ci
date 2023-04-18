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
import logging
import argparse
import shutil
import time
from io import StringIO

import yaml

from app import util
from app.command import Command
from app import const
from app.lib import Gitee

log = logging.getLogger()

class Cron(Command):
    '''
    Cron is to generate sstate-cache timing
    '''
    def __init__(self):
        self.gitee = None
        self.branch = None
        super().__init__(
        "cron", 
        "this is a CI timed task", 
        "this task is for generating sstate-cache and used in gate and ci")

    def do_add_parser(self,parser_addr: argparse._SubParsersAction):
        parser = parser_addr.add_parser(name=self.name)
        parser.add_argument('-s', '--share_dir', dest = "share_dir")
        parser.add_argument('-b', '--branch', dest = "branch", default="master")
        parser.add_argument('-m',
                            '--tmp_dir',
                            dest = "tmp_dir",
                            default = "/home/jenkins/agent/openeuler_tmp")
        parser.add_argument('-dm', '--delete_tmp', dest = "is_delete_tmp", action = "store_true")
        parser.add_argument('-o', '--owner', dest = "owner")
        parser.add_argument('-p', '--repo', dest = "repo")
        parser.add_argument('-gt', '--gitee_token', dest = "gitee_token")
        parser.add_argument('-sf', '--send_faild', dest = "is_send_faild", action = "store_true")

        return parser

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)
        cron_workspace = os.path.join(args.share_dir, const.CRON_WORKSPACE)
        if not os.path.exists(cron_workspace):
            os.makedirs(cron_workspace)
        workspace = os.path.join(cron_workspace, f"openeuler_{args.branch}")

        self.branch = args.branch

        if not os.path.exists(args.tmp_dir):
            os.makedirs(args.tmp_dir)

        if args.is_send_faild:
            self.gitee = Gitee(owner=args.owner, repo=args.repo, token=args.gitee_token)

        self.exec(workspace = workspace,
                  branch = args.branch,
                  cron_tmp_dir = args.tmp_dir,
                  is_delete_tmp = args.is_delete_tmp,
                  is_send_faild = args.is_send_faild)

    def exec(self, workspace, branch, cron_tmp_dir, is_delete_tmp, is_send_faild):
        '''
        the exec will be called by gate
        '''
        # first run oebuild init
        if not util.check_oebuild_directory(workspace):
            os.chdir(os.path.dirname(workspace))
            cmd = f"oebuild init -b {branch} {workspace}"
            err_code, result = subprocess.getstatusoutput(cmd=cmd)
            if err_code != 0:
                raise ValueError(result)
            print(result)

        # list workspace
        if os.path.exists(os.path.join(workspace, 'build')):
            print(os.listdir(os.path.join(workspace, 'build')))

        # second run oebuild update
        os.chdir(workspace)
        cmd = "oebuild update -e meta"
        err_code, result = subprocess.getstatusoutput(cmd=cmd)
        if err_code != 0:
            raise ValueError(result)
        print(result)

        # rm manifest is for building without manifest file
        yocto_dir = os.path.join(workspace, "src/yocto-meta-openeuler")
        self.rm_manifest_file(yocto_dir=yocto_dir)

        # get cron config
        conf_dir = util.get_conf_path()
        cron_conf = util.parse_yaml(os.path.join(conf_dir, const.CRON_CONF))

        err_list = []
        build_faild_list = []
        # third run oebuild generate
        for arch in cron_conf['build_list']:
            # set gcc toolchain directory
            toolchain_dir = os.path.join(const.GCC_DIR, arch['toolchain'])
            for board in arch['board']:
                # delete build cache
                print(f"delete {board['directory']} cache")
                self._delete_build_cache(
                    build_dir=os.path.join(workspace, 'build',board['directory']),
                    board_conf=board)

                features = None
                if "feature" in board and board['feature'] is not None and len(board['feature']) > 0:
                    features = ""
                    for feature in board['feature']:
                        features = features + f" -f {feature['name']}"
                tmp_dir = os.path.join(cron_tmp_dir, board['directory'], 'tmp')
                generate_cmd = f"oebuild generate\
                            -p {board['platform']}\
                            -n {const.NATIVE_SDK_DIR}\
                            -t {toolchain_dir}\
                            -m {tmp_dir}\
                            -b_in host\
                            -d {board['directory']}"
                if features is not None:
                    generate_cmd += features
                print(f"build command is: {generate_cmd}")
                # run `oebuild generate` for compile.yaml
                err_code, result = subprocess.getstatusoutput(generate_cmd)
                if err_code != 0:
                    raise ValueError(result)
                print(result)

                # run `oebuild bitbake openeuler-image`
                print(f"========================={board['directory']}==========================")
                for bitbake in board['bitbake']:
                    with subprocess.Popen(f"oebuild bitbake {bitbake['target']}",
                                    shell=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    cwd=os.path.join(workspace, 'build', board['directory']),
                                    encoding="utf-8") as s_p:
                        last_line = ""
                        for line in s_p.stdout:
                            line = line.strip('\n')
                            last_line = line
                            print(line)
                        s_p.wait()
                        print("====================================================")
                        if last_line.find("returning a non-zero exit code.") != -1:
                            err_msg = rf"build {board['directory']}->{bitbake['target']} faild"
                            err_list.append(err_msg)
                            print(err_msg)
                            build_faild = {
                                'arch': arch['arch'],
                                'directory': board['directory'],
                                'generate': generate_cmd,
                                'bitbake': bitbake['target']
                            }
                            build_faild_list.append(build_faild)
                        else:
                            print(f"bitbake {board['directory']}->{bitbake['target']} successful")
                # because tmp directory use large space so support a param to delete it
                # when build finished
                if is_delete_tmp:
                    shutil.rmtree(tmp_dir)

        if len(err_list) > 0:
            for err_msg in err_list:
                err_msg:str = err_msg
                print(err_msg)
            raise ValueError("build project bas error")

        # send build faild msg to issue
        if is_send_faild:
            self.send_issue_with_build_faild(build_faild_list)

    def _delete_build_cache(self, build_dir, board_conf):
        if not os.path.exists(build_dir):
            return

        if "delete_cache" not in board_conf:
            return

        delete_cache:str = board_conf['delete_cache']
        delete_cache = delete_cache.strip()
        if delete_cache == "":
            return

        delete_split = delete_cache.split('|')
        for delete_name in delete_split:
            delete_dir = os.path.join(build_dir, delete_name)
            if os.path.exists(delete_dir):
                shutil.rmtree(delete_dir)
                print(f"delete {delete_dir} successful")

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

    @staticmethod
    def rm_manifest_file(yocto_dir):
        '''
        rm manifest file from yocto-meta-openeuler/.oebuild/manifest.yaml
        '''
        manifest_path = os.path.join(yocto_dir, ".oebuild/manifest.yaml")
        if not os.path.exists(manifest_path):
            return
        os.remove(manifest_path)
