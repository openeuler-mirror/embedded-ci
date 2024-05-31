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
from typing import Optional

from app.lib import Result
from app.lib import Gitee

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
    boards: list

@dataclass
class BuildRes:
    '''
    The class is returned as a standard for building interfaces
    '''
    # mark arch reault list
    archs: list

@dataclass
class BuildParam:
    '''
    This class defines some basic parameter properties
    as a standard for building interface parameters
    '''
    workspace: str = None
    build_code: str = None
    arch: str = None
    toolchain: str = None
    platform: str = None
    images: str = None
    features: str = None
    directory: str = None
    datetime: str = None
    sstate_cache_in: str = None
    sstate_cache_out: str = None
    oebuild_extra: str = None

    #when gate.py remove ,four para can be delete
    repo_dir: str = None
    share_dir: str = None
    branch: str = None
    pr_num: int = None

@dataclass
class UtestParam:
    '''
    This class defines some basic parameter properties
    as a standard for building interface parameters
    '''
    arch:Optional[str] = None
    target_dir:Optional[str] = None
    mugen_url:Optional[str] = None
    mugen_branch:Optional[str] = None

@dataclass
class CheckParam:
    '''
    This class defines some basic parameter properties
    as a standard for checking interface parameters
    '''
    check_code: str = None
    owner: str = None
    repo: str = None
    pr_num: int = None
    gitee: Gitee = None

    # for code check
    diff_files:str = None


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

    class BuildError(Exception):
        """
        Build Error
        """
        def __init__(self, message):
            super().__init__(message)

class Utest(ABC):
    '''
    The build class is a defined interface class that defines
    the called build function, the subject gate will call the
    interface to get the build result, and the business needs
    to inherit the interface class and implement the build interface
    '''

    @abstractmethod
    def do_utest(self, param: UtestParam):
        '''
        This interface needs to be implemented by specific services
        '''

    def utest(self, param: UtestParam):
        '''
        This function is called by the body framework
        '''
        return self.do_utest(param)

    class UtestError(Exception):
        """
        Test Error
        """
        def __init__(self, message):
            super().__init__(message)


class Check(ABC):
    '''
    The check class is a defined interface class that defines
    the called check function, the subject gate will call the
    interface to get the check result, and the business needs
    to inherit the interface class and implement the check interface
    '''

    @abstractmethod
    def do_check(self, param: CheckParam):
        '''
        This interface needs to be implemented by specific services
        '''

    def check(self, param: CheckParam):
        '''
        This function is called by the body framework
        '''
        return self.do_check(param)

    class CheckError(Exception):
        """
        Check Error
        """
        def __init__(self, message):
            super().__init__(message)
