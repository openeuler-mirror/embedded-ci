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
import subprocess
import shutil
import json
import git
from git.exc import GitCommandError

from app import util
from app.command import Command
from app.lib import Gitee

class ReleaseDoc(Command):
    '''
    trigger doc deployment when PR is merged and is related to doc
    '''
    def __init__(self):
        self.gitee = None
        self.workspace = "/home/jenkins/agent"
        self.pr_num = None
        self.repo = None
        self.remote_url = None
        self.target = None
        self.gitee_token = None
        self.owner = None

        super().__init__(
            "releasedoc", 
            "Deploy documents", 
            "Build multiple versions of documents and deploy them to gitee pages")

    def do_add_parser(self, parser_addr:_SubParsersAction):
        parser_addr.add_argument('-o', '--owner', dest="owner")
        parser_addr.add_argument('-p', '--repo', dest="repo")
        parser_addr.add_argument('-gt', '--gitee_token', dest="gitee_token")
        parser_addr.add_argument('-pr', '--pr_num', dest="pr_num")
        parser_addr.add_argument('-t', '--target', dest="target")
        parser_addr.add_argument('-is_test', '--is_test', dest = "is_test", action = "store_true")

        return parser_addr

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)
        self.pr_num = args.pr_num
        self.target = args.target
        self.repo = args.repo
        self.gitee_token = args.gitee_token
        self.owner = args.owner

        self.gitee = Gitee(owner=self.owner, repo=self.repo, token=self.gitee_token)
        self.remote_url = f"https://{self.owner}:{self.gitee_token}@gitee.com/{self.target}/{self.repo}.git"
        self.exec(pr_num=self.pr_num, is_test=args.is_test)

    def exec(self, pr_num, is_test:bool):
        '''
        the exec will be called by releasedoc
        '''
        #determine if it is a document related PR
        commits_files_data = self.gitee.get_commits_files(pr_num)
        commit_files_list = json.loads(commits_files_data)
        if not self.is_docs_build(commit_files_list=commit_files_list):
            return

        repo_dir = os.path.join(self.workspace, self.repo)
        #pull remote code into the container, with branches limited on the branch_white_list
        print('============pull code to local for sphinx-multiversion operation===========')
        if not self.pull_code_to_local(repo_dir=repo_dir, remote_url=self.remote_url):
            self.comment_to_pr(is_test=is_test, is_success=False)
            return
        print('============================pull code finished=============================\n\n')

        #do doc multiversion build
        print('==========================sphinx-multiversion msg==========================')
        if not self.doc_multi_build(repo_dir=repo_dir):
            self.comment_to_pr(is_test=is_test, is_success=False)
            return
        print('========================sphinx-multiversion finshed========================\n\n')

        #push html to gitee_pages branch
        print('==========================push doc to gitee pages==========================')
        if not self.push_to_gitee_pages(repo_dir=repo_dir):
            self.comment_to_pr(is_test=is_test, is_success=False)
            print("===============================push failed=================================")
        else:
            comment = 'The regenerated document has been successfully pushed to gitee_pages'
            self.comment_to_pr(is_test=is_test, is_success=True, msg=comment)
            print('=============================push successful===============================')

    def is_docs_build(self, commit_files_list :list):
        '''
        determine whether to ask for document build
        '''
        for file_obj in commit_files_list:
            if not file_obj['filename'].startswith("docs"):
                return False
        return True

    def pull_code_to_local(self, repo_dir, remote_url):
        '''
        pull remote code into the container, with branches limited to those on the branch_white_list
        '''
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)
        git.Repo.clone_from(url=remote_url,to_path=repo_dir)
        git_repo = git.Repo(repo_dir)
        yaml_data = os.path.join(os.path.dirname(__file__), "release_doc.yaml")
        branch_white_list = util.parse_yaml(yaml_data)['branch_white_list']
        print('The branches pulled down include:')
        for remote_branch in git_repo.remote().refs:
            branch_name = remote_branch.name.split('/')[-1]
            if branch_name in branch_white_list:
                try:
                    branch_local = git_repo.create_head(branch_name, commit=remote_branch.commit)
                    branch_local.set_tracking_branch(remote_branch)
                    branch_local.checkout()
                    print('      ' + branch_name)
                except GitCommandError as git_pull_error:
                    print("pull code failed:\n" + git_pull_error.stderr)
                    return False
        git_repo.git.checkout('master')
        return True

    def doc_multi_build(self, repo_dir):
        '''
        do doc multiversion build
        '''
        os.chdir(repo_dir+'/docs')
        multibuild_res = subprocess.run(['sphinx-multiversion', 'source','build/html'],
                                        capture_output=True, text=True, check=False)
        if multibuild_res.returncode == 0:
            print(multibuild_res.stdout)
            return True
        print('doc build failed, errmsg:\n' + multibuild_res.stderr)
        return False

    def push_to_gitee_pages(self, repo_dir):
        '''
        push html to gitee pages
        '''
        #re or create a new index page
        with open(repo_dir+'/docs/build/html/index.html', 'w', encoding='utf-8') as index_f:
            index_f.write(f'''
<!DOCTYPE html>
<html class="writer-html5" lang="zh-CN">
    <head>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="0.1;url=https://{self.target}.gitee.io/{self.repo}/master/index.html">
    </head>
</html>
        ''')
        #clone and replace gitee_pages branch doc code
        repo_dir_for_gitee = os.path.join(self.workspace, 'docs_upload_work')
        if os.path.exists(repo_dir_for_gitee):
            shutil.rmtree(repo_dir_for_gitee)
        git.Repo.clone_from(url=self.remote_url, to_path=repo_dir_for_gitee, branch='gitee_pages')
        pages_repo = git.Repo(repo_dir_for_gitee)
        shutil.rmtree(repo_dir_for_gitee+'/docs/build/html')
        shutil.copytree(repo_dir+'/docs/build/html', repo_dir_for_gitee+'/docs/build/html')

        #push new html doc to gitee_pages branch
        try:
            pages_repo.git.add(repo_dir_for_gitee+'/docs/build/html')
            pages_repo.git.commit('-m', 'update docs!')
            pages_repo.git.push('origin', 'gitee_pages')
        except GitCommandError as push_error:
            print('push falied:\n' + push_error.stderr)
            return False
        return True

    def comment_to_pr(self, is_test: bool, is_success=False, msg=''):
        '''
        send comment to pr
        '''
        if msg != '':
            self.gitee.comment_pr(pr_num=self.pr_num, comment=msg)
            return
        if not is_success:
            build_url = ''
            if not is_test:
                build_url = os.path.join(os.environ['BUILD_URL'], 'console')
            comment = 'doc release job failed!.\n'
            comment = comment + f"Please click <a href='{build_url}'>here</a> for details"
            self.gitee.comment_pr(pr_num=self.pr_num, comment=comment)
