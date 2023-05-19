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

from abc import abstractmethod, ABC
from dataclasses import dataclass

from app.lib import Result

@dataclass
class Board:
    '''
    This class hosts simple properties of the veneer and
    is mainly used to record build results
    '''
    # mark board name
    name: str
    # mark board build result
    result: Result

@dataclass
class Arch:
    '''
    This class carries simple properties of arch and
    is mainly used to record build results
    '''
    # mark arch name
    name: str
    # mark boards result
    boards: list[Board]

@dataclass
class BuildRes:
    '''
    The class is returned as a standard for building interfaces
    '''
    # mark arch reault list
    archs: list[Arch]

@dataclass
class BuildParam:
    '''
    This class defines some basic parameter properties
    as a standard for building interface parameters
    '''
    repo_dir: str
    workspace: str
    share_dir: str
    branch: str
    pr_num: int

class Build(ABC):
    '''
    The build class is a defined interface class that defines
    the called build function, the subject gate will call the
    interface to get the build result, and the business needs
    to inherit the interface class and implement the build interface
    '''

    @abstractmethod
    def do_build(self, param: BuildParam) -> BuildRes:
        '''
        This interface needs to be implemented by specific services
        '''

    def build(self, param: BuildParam) -> BuildRes:
        '''
        This function is called by the body framework
        '''
        return self.do_build(param)
