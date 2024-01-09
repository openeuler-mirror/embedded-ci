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
from argparse import _SubParsersAction
import time
import getpass
import hashlib

from app.command import Command
from app.lib import Gitee,Remote

class OTest(Command):
    '''
    xxx
    '''

    def __init__(self):

        super().__init__(
            "otest", 
            "this is help", 
            "this is description")

    def do_add_parser(self, parser_addr:_SubParsersAction):
        parser_addr.add_argument('-o', '--owner', dest="owner")
        parser_addr.add_argument('-p', '--repo', dest="repo")
        parser_addr.add_argument('-gt', '--gitee_token', dest="gitee_token")
        parser_addr.add_argument('-b', '--branch', dest="branch", default="master")
        parser_addr.add_argument('-l', '--local_dir', dest="local_dir")
        parser_addr.add_argument('-e', '--remote_dst_dir', dest="remote_dst_dir")
        parser_addr.add_argument('-i', '--remote_dst_ip', dest="remote_dst_ip")
        parser_addr.add_argument('-u', '--remote_dst_user', dest="remote_dst_user")
        parser_addr.add_argument('-w', '--remote_dst_pwd', dest="remote_dst_pwd")
        parser_addr.add_argument('-k', '--remote_dst_sshkey', dest="remote_dst_sshkey")
        parser_addr.add_argument('-pr', '--pr_num', dest="pr_num")
        parser_addr.add_argument('-f', '--function', dest="function")

        return parser_addr

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)

        if args.function == "send_comment":
            self.send_comment(args=args)
        if args.function == "send_tag":
            self.send_tag(args=args)
        if args.function == "print_env":
            self.print_env()
        if args.function == "remote_put_file":
            self.remote_put_file(args=args)
        if args.function == "add_sum_to_local":
            self.add_sum_to_local(args=args)
        if args.function == "add_issue_to_repo":
            self.add_issue_to_repo(args=args)


    def send_comment(self,args):
        '''
        xxxx
        '''
        gitee = Gitee(owner=args.owner, repo=args.repo, token=args.gitee_token)
        comment = "this is just a test comment"
        gitee.comment_pr(pr_num=args.pr_num, comment=comment)

    def send_tag(self, args):
        '''
        xxx
        '''
        gitee = Gitee(owner=args.owner, repo=args.repo, token=args.gitee_token)
        gitee.delete_tags_of_pr(args.pr_num, "ci_processing")

    def print_env(self):
        '''
        xxx
        '''
        print(f"environment: {os.environ}")

    def remote_put_file(self,args):
        '''
        xxx
        '''
        remote = Remote(
            remote_ip=args.remote_dst_ip,
            remote_user=args.remote_dst_user,
            remote_pwd=args.remote_dst_pwd,
            remote_key=args.remote_dst_sshkey
            )
        remote.put_to_remote(local_dir = args.local_dir, dst_dir=args.remote_dst_dir)

    def add_issue_to_repo(self, args):
        '''
        xxx
        '''
        gitee = Gitee(owner=args.owner, repo=args.repo, token=args.gitee_token)
        time_str = time.strftime("%Y-%m-%d %X", time.localtime())
        title = f"[openEuler-23.03]构建失败  {time_str}"
        body = '''
        aarch64:
            aarch64-qemu:
                bitbake openeuler-image faild
                bitbake openeuler-image -c do_populate_sdk faild
        arm32:
            arm-qemu:
                bitbake openeuler-image faild
                bitbake openeuler-image -c do_populate_sdk faild
        '''
        gitee.add_issue_to_repo(title=title, body=body)

    def add_sum_to_local(self,args):
        '''
        xxx
        '''
        print(getpass.getuser())
        self._add_sum_to_local_dir(local_dir= args.local_dir)

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
