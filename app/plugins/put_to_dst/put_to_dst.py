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
import subprocess

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
        # dst_type is for put the dst to where
        parser_addr.add_argument('-t', '--dst_type', dest="dst_type")
        parser_addr.add_argument('-dd', '--dst_dir', dest="dst_dir")
        parser_addr.add_argument('-ld', '--local_dir', dest="local_dir")
        parser_addr.add_argument('-sign', '--sign_file', dest="sign_file", action="store_true")
        parser_addr.add_argument('-d', '--delete_original', dest="delete_original", action="store_true")
        parser_addr.add_argument('-i', '--remote_dst_ip', dest="remote_dst_ip", default=None)
        parser_addr.add_argument('-u', '--remote_dst_user', dest="remote_dst_user", default=None)
        parser_addr.add_argument('-w', '--remote_dst_pwd', dest="remote_dst_pwd", default=None)
        parser_addr.add_argument('-k', '--remote_dst_sshkey', dest="remote_dst_sshkey", default=None)
        parser_addr.add_argument('-ptoken', '--pypi_token', dest="pypi_token", default=None)
        parser_addr.add_argument('-pserver', '--pypi_server_name', dest="pypi_server_name", default=None)
        return parser_addr

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)
        local_dir = args.local_dir
        dst_dir = args.dst_dir

        #remote
        if int(args.dst_type) == 0:
            self._put_dst_to_remote(
                remote_dst_ip = args.remote_dst_ip,
                remote_dst_user = args.remote_dst_user,
                remote_dst_pwd = args.remote_dst_pwd,
                remote_dst_sshkey = args.remote_dst_sshkey,
                sign_file = args.sign_file,
                local_dir = local_dir,
                dst_dir = dst_dir,
                delete_original = args.delete_original)

        #Shared disk or local folder
        elif int(args.dst_type) == 1:
            self._put_dst_to_local(
                sign_file=args.sign_file,
                local_dir=local_dir,
                dst_dir=dst_dir,
                delete_original=args.delete_original)

        # pypi
        elif int(args.dst_type) == 2:
            self._put_dst_to_pypi(local_dir=local_dir, token=args.pypi_token, server_name=args.pypi_server_name)
        #error value
        else:
            return ValueError("The type value does not have a corresponding destination type!")

    def _put_dst_to_remote(self,
                           remote_dst_ip,
                           remote_dst_user,
                           remote_dst_pwd,
                           remote_dst_sshkey,
                           sign_file,
                           local_dir,
                           dst_dir,
                           delete_original):
        if remote_dst_ip is None or remote_dst_user is None or (remote_dst_pwd is None and remote_dst_sshkey is None):
            return ValueError("Missing remote related parameters!")

        if sign_file:
            util.add_sum_to_local_dir(local_dir=local_dir)

        self.remote = Remote(
            remote_ip=remote_dst_ip,
            remote_user=remote_dst_user,
            remote_pwd=remote_dst_pwd,
            remote_key=remote_dst_sshkey
            )
        self.remote.put_to_remote(
            local_dir=local_dir,
            dst_dir=dst_dir,
            is_delete_dst=delete_original)


    def _put_dst_to_local(self,
                            sign_file,
                            local_dir,
                            dst_dir,
                            delete_original):
        if sign_file:
            util.add_sum_to_local_dir(local_dir=local_dir)
        if delete_original:
            if os.path.isdir(dst_dir):
                shutil.rmtree(dst_dir)
        os.makedirs(os.path.dirname(dst_dir), exist_ok=True)
        shutil.copytree(local_dir, dst_dir)

    def _put_dst_to_pypi(self,
                         local_dir,
                         token,
                         server_name = "pypi"):
        # install twine
        show_res = subprocess.run(
            "pip show twine",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            check=False)
        if show_res.returncode != 0:
            print("twine is not installed")
            install_res = subprocess.run(
                "pip install twine -i https://pypi.tuna.tsinghua.edu.cn/simple",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                check=False)
            if install_res.returncode != 0:
                raise ValueError("install flake8 faild")
            print("twine install successful!!!")
        # check if exists .pypirc
        if server_name == 'pypi':
            pypirc = f"""
[distutils]
  index-servers =
    pypi

[pypi]
  username = __token__
  password = {token}
"""
        elif server_name == 'testpypi':
            pypirc = f"""
[distutils]
  index-servers =
    testpypi

[testpypi]
  repository = https://test.pypi.org/legacy/
  username = __token__
  password = {token}
"""
        else:
            raise ValueError("param error")
        with open(os.path.join(os.environ['HOME'], ".pypirc"), mode="w", encoding="utf-8") as f:
            f.write(pypirc)
        if not os.path.isfile(local_dir):
            raise ValueError(f"{local_dir} is not exists")
        show_res = subprocess.run(
            f"twine upload -r {server_name} {local_dir}",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            check=True,
            encoding="utf-8",
            text=True)
        if show_res.returncode != 0:
            raise ValueError(show_res.stderr)
        print(show_res.stdout)
