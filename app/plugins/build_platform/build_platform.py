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

from app import util
from app.command import Command
from app.build import Build,BuildParam


NATIVE_SDK_DIR= "/opt/buildtools/nativesdk"
GCC_DIR = "/usr1/openeuler/gcc"

class BuildPlatform(Command):
    '''
    Handle pull request business and build image which is specified by the passed in parameters
    '''
    def __init__(self):
        self.workspace = os.environ['HOME']

        super().__init__(
            "buildPlatform", 
            "Build Platform", 
            "Build Platform is used to build images, docs, sdks and hosttools")

    def do_add_parser(self,parser_addr: argparse._SubParsersAction):
        parser = parser_addr.add_parser(name=self.name)
        parser.add_argument('-c', '--build_code', dest="build_code")
        parser.add_argument('-target', '--target', dest="target")
        parser.add_argument('-a', '--arch', dest="arch", default="arch")
        parser.add_argument('-t', '--toolchain', dest="toolchain", default=None)
        parser.add_argument('-p', '--platform', dest="platform", default=None)
        parser.add_argument('-i', '--images', dest="images", default=None)
        parser.add_argument('-ic', '--img_cmds', dest="img_cmds", action="append", default=None)
        parser.add_argument('-f', '--features', dest="features", default=None)
        parser.add_argument('-dt', '--datetime', dest="datetime", default=None)
        parser.add_argument('-d', '--directory', dest="directory", default="build")
        parser.add_argument('-s_in', '--sstate_cache_in', dest="sstate_cache_in", default=None)
        parser.add_argument('-s_out', '--sstate_cache_out', dest="sstate_cache_out", default=None)

        return parser

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)
        #check build_code
        if not os.path.isdir(args.build_code):
            raise ValueError(f"Code for build not exist in path: {args.build_code} ! ")

        # 处理目标编码
        img_list = []
        if args.img_cmds is not None:
            for img_cmd in args.img_cmds:
                img_list.append(util.base64_decode(img_cmd))
        elif args.images is not None:
            img_list.append(args.images)

        #invoke process class
        task_path = util.get_top_path() + f"/app/plugins/build_platform/tasks/{args.target}.py"
        cls:Build = util.get_spec_ext(task_path, "Run")
        return cls.build(param=BuildParam(
            workspace=self.workspace,
            build_code=args.build_code,
            arch=args.arch,
            toolchain=args.toolchain,
            platform=args.platform,
            images=";".join(img_list),
            features=args.features,
            directory=args.directory,
            datetime=args.datetime,
            sstate_cache_in=args.sstate_cache_in,
            sstate_cache_out=args.sstate_cache_out))
