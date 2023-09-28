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
from dataclasses import dataclass
from typing import Optional

@dataclass
class CommendParam:
    '''
    commend param item
    '''
    # param name
    name:  Optional[str]
    # action like build or test
    action: Optional[str]
    # action result like success or failed
    result: Optional[str]
    # action workspace
    workspace: Optional[str]
    # action log link
    log_path: Optional[str]

def translate_commend_param(obj)->CommendParam:
    '''
    translate json to CommendParam object
    '''
    commend_param = CommendParam(
        name=obj['name'] if "name" in obj else "",
        action=obj['action'] if "action" in obj else "",
        result=obj['result'] if "result" in obj else "",
        workspace=obj['workspace'] if "workspace" in obj else "",
        log_path=obj['log_path'] if "log_path" in obj else "",
    )
    return commend_param
