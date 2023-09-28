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
        commit_file_list = json.loads(gitee.get_commits_files(param.pr_num))

        if len(commit_file_list) == 0:
            print("In a pull request, no files have been deleted, added, or modified. \
                  Please commit something.")
            raise ValueError("no commit files")

        #Create dictionary mapping from commit id to files
        hash_to_file = {}
        for commit_file in commit_file_list:
            commit_hash = commit_file['sha']
            new_path = commit_file['patch']['new_path']
            old_path = commit_file['patch']['old_path']
            if commit_hash in hash_to_file:
                hash_to_file[commit_hash].add(new_path)
                hash_to_file[commit_hash].add(old_path)
            else:
                hash_to_file[commit_hash] = {new_path, old_path}

        #Analyze the content of each commit:document or non document
        for commit_hash, files in hash_to_file.items():
            doc_list = [file_path for file_path in files if file_path.startswith('docs/')]
            non_doc_list = [file_path for file_path in files if not file_path.startswith('docs/')]
            if len(doc_list) > 0 and len(non_doc_list) > 0:
                print(f"In commit id: {commit_hash}")
                print("Can't include both doc and non-doc content in a commit.")
                print("==============================================================")
                print("doc paths:")
                for doc_path in doc_list:
                    print("     ", doc_path)
                print("non doc paths:")
                for non_doc_path in non_doc_list:
                    print("     ", non_doc_path)
                print("==============================================================")
                raise self.CheckError("Can't include both doc and non-doc content in a commit.")
        print("The result of commit scope check is successful!")
