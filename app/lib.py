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

import requests
import jenkins
from paramiko import SSHClient, AutoAddPolicy, RSAKey, SSHException

from app import util

class Gitee:
    '''
    reencapsulate some of Gitee's interface to pull requests
    '''

    def __init__(self, owner, repo, token=None):
        self._owner = owner
        self._repo = repo
        self._token = token
        self._api_url_pre = "https://gitee.com/api/v5/repos"
        self.request_ok_list = [
            requests.codes['ok'],
            requests.codes['created'],
            requests.codes['no_content']]
        self.request_timeout = 10

    @property
    def owner(self):
        '''
        return param owner
        '''
        return self._owner

    @property
    def repo(self):
        '''
        return param repo
        '''
        return self._repo

    @property
    def token(self):
        '''
        return param token
        '''
        return self._token

    def get_pr_commits(self, pr_num):
        '''
        get pull request commits list
        '''
        url = rf"{self._api_url_pre}/{self._owner}/{self._repo}/pulls/{pr_num}/commits"
        resp = requests.get(url=url, timeout=self.request_timeout)
        if resp.status_code not in self.request_ok_list:
            return None

        return resp.content

    def get_commits_files(self, pr_num):
        """
        get pull request commits with files
        """
        url = rf"{self._api_url_pre}/{self._owner}/{self._repo}/pulls/{pr_num}/files"
        resp = requests.get(url=url, timeout=self.request_timeout)
        if resp.status_code not in self.request_ok_list:
            return None

        return resp.content

    def get_a_commit_info(self, commit_id):
        """
        get a commit info from repository
        """
        url = rf"{self._api_url_pre}/{self._owner}/{self._repo}/commits/{commit_id}"
        resp = requests.get(url=url, timeout=self.request_timeout)
        if resp.status_code not in self.request_ok_list:
            return None

        return resp.content

    def comment_pr(self, pr_num, comment):
        '''
        add comment to pull request
        '''
        url = rf"{self._api_url_pre}/{self._owner}/{self._repo}/pulls/{pr_num}/comments"
        data = {"access_token": self._token, "body": comment}

        resp = requests.post(url=url, data=data, timeout=self.request_timeout)

        if resp.status_code not in self.request_ok_list:
            print(f"status_code: {resp.status_code}, content: {resp.content.decode()}")
            return False
        return True

    def add_tags_of_pr(self, pr_num, *tags):
        '''
        add tags to pull request
        '''
        url = rf"{self._api_url_pre}/{self._owner}/{self._repo}/pulls/{pr_num}/labels?access_token={self._token}"

        resp = requests.post(url=url, json=list(tags), timeout=self.request_timeout)
        if resp.status_code not in self.request_ok_list:
            print(f"status_code: {resp.status_code}, content: {resp.content.decode()}")
            return False
        return True

    def delete_tags_of_pr(self, pr_num, *tags):
        '''
        delete tags to pull request
        '''
        name = ','.join(list(tags))
        url = rf"{self._api_url_pre}/{self._owner}/{self._repo}/pulls/{pr_num}/labels/{name}?access_token={self._token}"

        resp = requests.delete(url=url, timeout=self.request_timeout)
        if resp.status_code not in self.request_ok_list:
            print(f"status_code: {resp.status_code}, content: {resp.content.decode()}")
            return False
        return True

    def add_issue_to_repo(self, title, body):
        '''
        add issue to repo
        '''
        url = rf"{self._api_url_pre}/{self._owner}/issues"
        data = {"access_token": self._token, "repo": self._repo,"title":title, "body": body}

        resp = requests.post(url=url, data=data, timeout=self.request_timeout)

        if resp.status_code not in self.request_ok_list:
            print(f"status_code: {resp.status_code}, content: {resp.content.decode()}")
            return False
        return True

class Jenkins:
    '''
    a simple Jenkins class with built-in interfaces with high demand frequency
    '''
    def __init__(self, jenkins_user, jenkins_token):
        comm_conf = util.get_common_conf()
        jenkins_conf = comm_conf['jenkins']
        base_url = jenkins_conf['base_url']
        self._jenkins = jenkins.Jenkins(url = base_url,
                                        username=jenkins_user,
                                        password=jenkins_token,
                                        timeout=30)

    def stop_build_by_build_num(self, job_name, build_num):
        '''
        stop jenkins job by build number
        '''
        if not isinstance(build_num, int):
            build_num = int(build_num)
        self._jenkins.stop_build(name=job_name, number=build_num)

    def get_build_info(self,job_name, build_num):
        '''
        get build info and return
        '''
        if not isinstance(build_num, int):
            build_num = int(build_num)
        return self._jenkins.get_build_info(name=job_name, number=build_num)

class Remote:
    '''
    A simple Remote class that mainly implements the function of file upload
    '''
    def __init__(self, remote_ip, remote_user, remote_pwd, remote_key):
        self.remote_ip = remote_ip
        self.remote_user = remote_user
        self.remote_pwd = remote_pwd
        self.remote_key = remote_key

    def _get_ssh_client(self):
        ssh_cli = SSHClient()
        ssh_cli.set_missing_host_key_policy(AutoAddPolicy)
        try:
            if self.remote_key is None:
                ssh_cli.connect(
                    hostname = self.remote_ip,
                    username = self.remote_user,
                    password = self.remote_pwd)
            else:
                pri_key = RSAKey.from_private_key_file(self.remote_key)
                ssh_cli.connect(
                    hostname = self.remote_ip,
                    username = self.remote_user,
                    pkey=pri_key)

            sftp_cli = ssh_cli.open_sftp()
            return ssh_cli, sftp_cli
        except SSHException:
            print("ssh init faild")
        return None, None

    def _get_files_from_dir(self, local_dir):
        all_files = []
        files = os.listdir(local_dir)
        for file_name in files:
            file_path = os.path.join(local_dir, file_name)
            if os.path.isdir(file_path):
                all_files.extend(self._get_files_from_dir(local_dir = file_path))
            else:
                all_files.append(file_path)
        return all_files


    def put_to_remote(self, local_dir, dst_dir, is_delete_dst=False):
        '''
        put local directory to destination
        '''
        ssh_cli, sftp_cli = self._get_ssh_client()
        if is_delete_dst:
            ssh_cli.exec_command(f"rm -rf {dst_dir}")
            ssh_cli.exec_command(f"mkdir -p {dst_dir}")
        os.chdir(local_dir)
        all_files = self._get_files_from_dir(local_dir=local_dir)
        print(all_files)
        for file_path in all_files:
            remote_dir = os.path.dirname(file_path)
            remote_dir = os.path.relpath(remote_dir, local_dir)
            dst_remote_dir = os.path.join(dst_dir, remote_dir)
            ssh_cli.exec_command(f"mkdir -p {dst_remote_dir}")
            remote_file = os.path.join(dst_remote_dir, os.path.basename(file_path))
            try:
                sftp_cli.put(file_path, remote_file)
                print(f"dst_file: {remote_file} successful")
            except FileNotFoundError:
                print(f"local_file: {file_path} not exists")
        sftp_cli.close()
        ssh_cli.close()

class Result:
    '''
    A result formatting class that performs formatting operations on result parameters
    '''
    def __init__(self):
        self._success = 0
        self._faild = 1

    @property
    def success(self):
        '''
        return success
        '''
        return self._success

    @property
    def faild(self):
        '''
        return faild
        '''
        return self._faild

    @staticmethod
    def get_hint(hint):
        '''
        return result index
        '''
        return ['SUCCESS', 'FAILD'][hint]

    @staticmethod
    def get_emoji(hint):
        '''
        return emoji from index
        '''
        return [" :white_check_mark: ", ":x:"][hint]
