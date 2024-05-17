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

from app.plugins.comment.interface import CommendParam
from app.lib import Gitee, Result
from app.const import PROCESS_LABEL, SUCCESS_LABEL, FAILED_LABEL
from app import util

class CGate:
    '''
    for gate task
    '''
    def __init__(self) -> None:
        '''
        comment gate
        '''

    def run(self,
            check_list: list,
            pr_num: int,
            repo: str,
            owner: str,
            gitee_token: str,
            duration: str):
        '''
        gate run body
        '''
        if gitee_token != "":
            gitee = Gitee(owner=owner,repo=repo,token=gitee_token)
        else:
            gitee = None

        final_res = True
        for check in check_list:
            if check.result != "success":
                final_res = False
                break
        if final_res:
            self._set_success_label(pr_num=pr_num, gitee=gitee)
        else:
            self._set_failed_label(pr_num=pr_num, gitee=gitee)
        self.send_check_table(check_list=check_list,
                              pr_num=pr_num,
                              gitee=gitee,
                              final_res=final_res,
                              duration=duration)

    def send_check_table(self, check_list:list, pr_num, gitee:Gitee, final_res:bool, duration:str):
        '''
        xxx
        '''
        table_caption = "openEuler Embedded 门禁检查-"
        # caption
        if final_res:
            caption=table_caption+Result().get_emoji(Result().success)+"PASS"
        else:
            caption=table_caption+Result().get_emoji(Result().faild)+"FAILD"
        #add duration
        if duration is not None:
            caption = caption + "<br>" + "本次构建耗时  " + "<u>" + duration + "</u>"

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
        gitee.comment_pr(pr_num=pr_num, comment=html)

    def _set_success_label(self, pr_num, gitee: Gitee):
        gitee.delete_tags_of_pr(pr_num, PROCESS_LABEL, FAILED_LABEL)
        gitee.add_tags_of_pr(pr_num, SUCCESS_LABEL)

    def _set_failed_label(self, pr_num, gitee: Gitee):
        gitee.delete_tags_of_pr(pr_num, PROCESS_LABEL, SUCCESS_LABEL)
        gitee.add_tags_of_pr(pr_num, FAILED_LABEL)
