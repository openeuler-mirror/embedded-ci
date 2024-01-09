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
from argparse import _SubParsersAction
import os
import json

from jenkins import JenkinsException

from app.command import Command
from app.lib import Jenkins, Gitee
from app.const import PROCESS_LABEL, SUCCESS_LABEL, FAILED_LABEL

class Pre(Command):
    '''
    This class is used for preliminary preparations for PR, such as stopping previous access control projects and tagging PR.
    '''
    def __init__(self):
        self.jenkins = None
        self.gitee = None
        self.owner = None
        self.repo = None
        self.pr_num = None
        self.share_dir = None

        super().__init__(
            "pre", 
            "do some previous works for pr", 
            "This class is used for preliminary preparations for PR, such as stopping previous access control projects and tagging PR.")

    def do_add_parser(self, parser_addr:_SubParsersAction):
        parser_addr.add_argument('-o', '--owner', dest="owner")
        parser_addr.add_argument('-p', '--repo', dest="repo")
        parser_addr.add_argument('-pr', '--pr_num', dest="pr_num")
        parser_addr.add_argument('-s', '--share_dir', dest = "share_dir")
        parser_addr.add_argument('-juser', '--jenkins_user', dest="jenkins_user")
        parser_addr.add_argument('-jpwd', '--jenkins_pwd', dest="jenkins_pwd")
        parser_addr.add_argument('-gt', '--gitee_token', dest="gitee_token")

        return parser_addr

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)
        self.owner = args.owner
        self.repo = args.repo
        self.pr_num = args.pr_num
        self.share_dir = args.share_dir
        self.jenkins = Jenkins(jenkins_user=args.jenkins_user, jenkins_token=args.jenkins_pwd)
        self.gitee = Gitee(owner=args.owner, repo=args.repo, token=args.gitee_token)

        jenkins_info = self.get_jenkins_job_info()
        if jenkins_info is not None:
            # if pre job exists and building, stop it
            self.delete_pre_jenkins(job_name=jenkins_info['job_name'], build_num=jenkins_info['build_num'])
        self.set_jenkins_job_info()
        self._set_process_label()

    def init_gate_dir(self, ):
        '''
        initinal gate dir, if not exists and make it
        '''
        gate_dir = os.path.join(self.share_dir, self.repo, self.owner, "gate")
        if not os.path.exists(gate_dir):
            os.makedirs(gate_dir, exist_ok=True)
        return gate_dir

    def get_jenkins_job_info(self, mode = "file"):
        '''
        get jenkins job info from some platform like db or file, default file
        '''
        if mode == "file":
            info = self._get_jenkins_job_from_file()
        if mode == "db":
            info = self._get_jenkins_job_from_db()
        return info

    def _get_jenkins_job_from_file(self, ):
        gate_dir = self.init_gate_dir()
        pr_file = os.path.join(gate_dir, f"pr_{self.pr_num}")
        if os.path.exists(pr_file):
            with open(pr_file, 'r', encoding="utf-8") as f:
                obj = json.loads(f.read())
                return obj
        else:
            return None

    # @abstractmethod
    def _get_jenkins_job_from_db(self, ):
        '''
        todo implement function that get info from mysql
        '''
        return "gg"

    def set_jenkins_job_info(self, mode = "file"):
        '''
        set jenkins job info in some platform like db or file, default file
        '''
        job_name = os.environ['JOB_NAME']
        build_num = os.environ['BUILD_NUMBER']
        if mode == "file":
            self._set_jenkins_job_in_file(job_name=job_name, build_num=build_num)
        if mode == "db":
            self._set_jenkins_job_in_db(job_name=job_name, build_num=build_num)

    def _set_jenkins_job_in_file(self, job_name, build_num):
        gate_dir = self.init_gate_dir()
        pr_file = os.path.join(gate_dir, f"pr_{self.pr_num}")
        if not os.path.exists(pr_file):
            os.mknod(pr_file)
        obj = {"job_name": job_name, "build_num": build_num}
        with open(pr_file, 'w', encoding="utf-8") as f:
            f.write(json.dumps(obj=obj, indent=2, ensure_ascii=False))

    # @abstractmethod
    def _set_jenkins_job_in_db(self, job_name, build_num):
        '''
        todo implement function that set info in mysql
        '''
        print(f"this is implement, param is job_name: {job_name}, build_num: {build_num}")

    def delete_pre_jenkins(self, job_name, build_num):
        '''
        delete jenkins job when exists
        '''
        try:
            pre_build_info = self.jenkins.get_build_info(job_name=job_name, build_num=build_num)
            if 'building' in pre_build_info and pre_build_info['building']:
                comment = "you retrigger the gatekeeper, the previous access task will stop and then restart the new access mission"
                self.gitee.comment_pr(pr_num=self.pr_num, comment=comment)
                self.jenkins.stop_build_by_build_num(
                    job_name=job_name,
                    build_num=build_num)
        except JenkinsException:
            # if jenkins action faild do nothing
            pass

    def _set_process_label(self, ):
        self.gitee.delete_tags_of_pr(self.pr_num, SUCCESS_LABEL, FAILED_LABEL)
        self.gitee.add_tags_of_pr(self.pr_num, PROCESS_LABEL)
