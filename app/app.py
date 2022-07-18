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

from dataclasses import dataclass
from app import util

@dataclass
class _Plugin:
    # command name
    name: str
    # class name
    class_name: str
    # path
    path: str

class App:
    '''
    Execute the ingress instance
    '''

    def __init__(self):
        self.plugins = self._get_plugins()
        self.spec_exts = {}
        self.parser = None
        self.subparser_gen = None

    def _get_ext_spec(self):
        for plugin in self.plugins:
            plugin:_Plugin = plugin
            self.spec_exts[plugin.name] = util.get_spec_ext(plugin.path, plugin.class_name)

    def _get_plugins(self):
        plugins_data = util.parse_yaml(os.path.join(util.get_conf_path(), 'plugins.yaml'))
        # print(plugins_data)
        plugins = []
        for plugin in plugins_data['plugins']:
            plugins.append(_Plugin(
                plugin['name'],
                plugin['class'],
                plugin['path']))
        return plugins

    def _setup_parsers(self):
        parser = argparse.ArgumentParser()
        subparser_gen = parser.add_subparsers(metavar='<command>', dest="command")
        for plugin in self.plugins:
            subparser_gen.add_parser(plugin.name)
        self.parser = parser
        self.subparser_gen = subparser_gen

    def run_command(self, argv):
        '''
        Responsible for the invocation of commands
        '''
        args, unknow = self.parser.parse_known_args(args=argv)
        if args.command is None or \
            args.command not in self.spec_exts or \
            args.command == 'help':
            self.help()
            return
        cmd = self.spec_exts[args.command]

        subargs = cmd.add_parser(self.subparser_gen)

        cmd.run(subargs, unknow)

    def help(self):
        '''
        print help message
        '''
        print("this is help msg")

    def run(self, argv):
        '''
        Program running portal
        '''
        self._get_ext_spec()
        self._setup_parsers()
        self.run_command(argv)
