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
import time

from app.lib import Gitee, Result
from app.plugins.comment.interface import CommendParam
from app import util

class CCI:
    '''
    for gate task
    '''
    def __init__(self) -> None:
        '''
        comment gate
        '''

    def run(self, 
            check_list: list,
            repo: str,
            owner: str,
            gitee_token: str,
            branch: str):
        '''
        asfdads
        '''
        if len(check_list) <= 0:
            pass
        if gitee_token != "":
            gitee = Gitee(owner=owner,repo=repo,token=gitee_token)
        else:
            gitee = None
        self.send_faild_issue(check_list=check_list, gitee=gitee, branch=branch)

    def send_faild_issue(self, check_list: list[CommendParam], gitee: Gitee, branch: str):
        '''
        xxx
        '''
        table_caption = "openEuler Embedded CI-"
        # caption
        caption=table_caption+Result().get_emoji(Result().faild)+"FAILD"
        # header data
        table = []
        for check in check_list:
            # body data
            if check.result == "success":
                check_result = Result().get_emoji(Result().success)+"SUCCESS"
            else:
                check_result = Result().get_emoji(Result().faild)+"FAILD"
            log_link = f"<a href='{os.path.join(os.environ['BUILD_URL'], check.log_path)}'>#{os.environ['BUILD_NUMBER']}</a>"
            table.append({"检查项":check.name,"操作":check.action,"结果":check_result,"链接":log_link})
        html = util.json_to_html(json_data={caption: table}, direc="TOP_TO_BOTTOM")
        time_str = time.strftime("%Y-%m-%d %X", time.localtime())
        title = f"[{branch}]构建失败  {time_str}"
        gitee.add_issue_to_repo(title=title, body=html)
        