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

from app.command import Command
from app.lib import Remote
from app import util

class PutRemote(Command):
    '''
    This class is used for preliminary preparations for PR, such as stopping
    previous access control projects and tagging PR.
    '''
    def __init__(self):
        self.remote = None

        super().__init__(
            "pre", 
            "do some previous works for pr", 
            """
            This class is used for preliminary preparations for PR, such as stopping
            previous access control projects and tagging PR.
            """)

    def do_add_parser(self,parser_addr: argparse._SubParsersAction):
        parser = parser_addr.add_parser(name=self.name)
        parser.add_argument('-e', '--remote_dst_dir', dest="remote_dst_dir")
        parser.add_argument('-i', '--remote_dst_ip', dest="remote_dst_ip")
        parser.add_argument('-u', '--remote_dst_user', dest="remote_dst_user")
        parser.add_argument('-w', '--remote_dst_pwd', dest="remote_dst_pwd")
        parser.add_argument('-k', '--remote_dst_sshkey', dest="remote_dst_sshkey")
        parser.add_argument('-ld', '--local_dir', dest="local_dir")
        parser.add_argument('-sign', '--sign_file', dest="sign_file", action="store_true")

        return parser

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)

        if args.sign_file:
            util.add_sum_to_local_dir(local_dir=args.local_dir)

        self.remote = Remote(
            remote_ip=args.remote_dst_ip,
            remote_user=args.remote_dst_user,
            remote_pwd=args.remote_dst_pwd,
            remote_key=args.remote_dst_sshkey
            )

        self.remote.put_to_remote(
            local_dir=args.local_dir,
            dst_dir=args.remote_dst_dir,
            is_delete_dst=True)
