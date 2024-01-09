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
from argparse import _SubParsersAction

from app.command import Command
from app.lib import Remote
from app import util

class PutToDst(Command):
    '''
    This class is used for put something to destination, 
    include other local directories, mounted shared disks, remote servers, etc
    '''
    def __init__(self):
        self.remote = None

        super().__init__(
            "put to destination", 
            "put files from a specified local dir to the destination", 
            """
            This class is used for put something to destination,
            include other local directories, mounted shared disks, remote servers, etc
            """)

    def do_add_parser(self, parser_addr:_SubParsersAction):
        parser_addr.add_argument('-t', '--dst_type', dest="dst_type")
        parser_addr.add_argument('-dd', '--dst_dir', dest="dst_dir")
        parser_addr.add_argument('-ld', '--local_dir', dest="local_dir")
        parser_addr.add_argument('-sign', '--sign_file', dest="sign_file", action="store_true")
        parser_addr.add_argument('-d', '--delete_original', dest="delete_original", action="store_true")
        parser_addr.add_argument('-i', '--remote_dst_ip', dest="remote_dst_ip", default=None)
        parser_addr.add_argument('-u', '--remote_dst_user', dest="remote_dst_user", default=None)
        parser_addr.add_argument('-w', '--remote_dst_pwd', dest="remote_dst_pwd", default=None)
        parser_addr.add_argument('-k', '--remote_dst_sshkey', dest="remote_dst_sshkey", default=None)

        return parser_addr

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)
        local_dir = args.local_dir
        dst_dir = args.dst_dir

        #remote
        if int(args.dst_type) == 0:
            if args.remote_dst_ip is None or args.remote_dst_user is None or (args.remote_dst_pwd is None and args.remote_dst_sshkey is None):
                return ValueError("Missing remote related parameters!")

            if args.sign_file:
                util.add_sum_to_local_dir(local_dir=local_dir)

            self.remote = Remote(
                remote_ip=args.remote_dst_ip,
                remote_user=args.remote_dst_user,
                remote_pwd=args.remote_dst_pwd,
                remote_key=args.remote_dst_sshkey
                )
            self.remote.put_to_remote(
                local_dir=local_dir,
                dst_dir=dst_dir,
                is_delete_dst=args.delete_original)

        #Shared disk or local folder
        elif int(args.dst_type) == 1:
            if args.sign_file:
                util.add_sum_to_local_dir(local_dir=local_dir)
            if args.delete_original:
                if os.path.isdir(dst_dir):
                    shutil.rmtree(dst_dir)
            os.makedirs(os.path.dirname(dst_dir), exist_ok=True)
            shutil.copytree(local_dir, dst_dir)
        #error value
        else:
            return ValueError("The type value does not have a corresponding destination type!")
