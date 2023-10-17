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
import json
from app.build import Check
from app.lib import Gitee

class Run(Check):
    '''
    determine whether the submitted content is document or non document in every commit,
    and both cannot coexist in a commit
    '''
    def do_check(self, param):
        gitee = Gitee(owner=param.owner, repo=param.repo)
        #get commits in a pr
        commit_hash_list = json.loads(gitee.get_pr_commits(param.pr_num))
        if len(commit_hash_list) == 0:
            print("In a pull request, no files have been deleted, added, or modified. \
                    Please commit something.")
            raise ValueError("no commit files")

        check_success = True
        for commit in commit_hash_list:
            #get all filename in a commit
            commit_info = json.loads(gitee.get_a_commit_info(commit["sha"]))
            filename_list = [commit_files["filename"] for commit_files in commit_info["files"]]
            if len(filename_list) == 0:
                print("In a pull request, no files have been deleted, added, or modified. \
                    Please commit something.")
                raise ValueError("no commit files")
            if not self.check_scope(commit["sha"], filename_list):
                check_success = False

        if not check_success:
            raise self.CheckError("Can't include both doc and non-doc content in a commit.")
        print("The result of commit scope check is successful!")

    def check_scope(self, commit_id, filename_list)->bool:
        '''
        Can't have both doc file and non doc file in a commit
        '''
        doc_list = [filename for filename in filename_list if filename.startswith('docs/')]
        non_doc_list = [filename for filename in filename_list if not filename.startswith('docs/')]
        if len(doc_list) > 0 and len(non_doc_list) > 0:
            print(f"In commit id: {commit_id}")
            print("Can't include both doc and non-doc content in a commit.")
            print("==============================================================")
            print("doc paths:")
            for doc_path in doc_list:
                print("     ", doc_path)
            print("non doc paths:")
            for non_doc_path in non_doc_list:
                print("     ", non_doc_path)
            print("==============================================================\n\n")
            return False
        return True
