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
import logging
import pathlib
import re
import subprocess
import sys
from argparse import _SubParsersAction
import os

import requests
from ruamel.yaml import YAML

from app.command import Command


class CreateRelease(Command):
    """
     Create a distribution and upload corresponding files
    """

    def __init__(self):
        super().__init__(
            "CreateRelease",
            "Create a distribution",
            " Create a distribution and upload corresponding files")

    def do_add_parser(self, parser_addr: _SubParsersAction):
        parser_addr.add_argument('-gt', '--gitee_token', dest="gitee_token")
        parser_addr.add_argument('-y', '--yaml_path', dest="yaml_path")
        parser_addr.add_argument('-f', '--file', dest="file_path")
        parser_addr.add_argument('-o', '--overwrite', dest="overwrite")
        return parser_addr

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)

        # check if exists yaml_path
        if args.yaml_path:
            if not os.path.exists(args.yaml_path):
                raise FileNotFoundError(f"the {args.yaml_path} not exists")

        if args.file_path:
            if not os.path.exists(args.file_path):
                raise FileNotFoundError(f"the {args.file_path} not exists")

        json_data = read_yaml(pathlib.Path(args.yaml_path))
        response_info = create_release(args.gitee_token, json_data)
        if response_info.status_code != 201:
            print(response_info.text)
            logging.error('create release failed')
            sys.exit(1)
        logging.info('Successfully created release')

        upload_file(args.file_path, json.loads(response_info.content)['id'], json_data['owner'],
                    json_data['repo'], args.gitee_token)
        logging.info('file upload successful')


def read_yaml(yaml_dir: pathlib.Path):
    """
    read yaml file and parse it to object
    """
    if not os.path.exists(yaml_dir.absolute()):
        raise ValueError(f"yaml_dir can not find in :{yaml_dir.absolute()}")

    try:
        with open(yaml_dir.absolute(), 'r', encoding='utf-8') as r_f:
            yaml = YAML()
            data = yaml.load(r_f.read())
            return data
    except Exception as e_p:
        raise e_p


def create_release(access_token, json_data):
    """

    Args:
        access_token:gitee token
        json_data:post data path

    Returns:

    """
    headers = {
        'Authorization': 'token ' + access_token,
        'Content-Type': 'application/json'
    }
    create_url = f'https://gitee.com/api/v5/repos/{json_data["owner"]}/{json_data["repo"]}/releases'
    res = requests.post(create_url, headers=headers, json=json_data)
    return res


def upload_file(file_dir, release_id, owner, repo, access_token):
    headers = {
        'Authorization': 'token ' + access_token
    }
    files = os.listdir(file_dir)
    chunk_size = 1024 * 1024 * 50  # 例如，每个分片1KB
    post_url = f'https://gitee.com/api/v5/repos/{owner}/{repo}/releases/{release_id}/attach_files'
    merge_sh = "#! /bin/bash\n\n"
    for file in files:
        if os.path.getsize(pathlib.Path(file_dir, file)) > chunk_size:
            cat_sh = 'cat '
            rm_sh = 'rm '
            file_path = pathlib.Path(file_dir, file)
            file_num = 1
            for chunk in split_binary_file(file_path, chunk_size):
                file_name = f'{file_dir}/{file_num}_{file}'
                cat_sh += f'{file_num}_{file} '
                rm_sh += f'{file_num}_{file} '
                # 处理每个分片
                with open(file_name, 'wb') as post_file:
                    post_file.write(chunk)

                with open(file_name, 'rb') as post_file:
                    response = requests.post(post_url, headers=headers, files={"file": post_file})
                subprocess.check_output(f'rm {file_name}', shell=True)
                if response.status_code != 201:
                    logging.error('upload file failed')
                    sys.exit(1)
                file_num += 1
            cat_sh += f'> {file}'
            merge_sh += cat_sh + '\n\n' + rm_sh + '\n\n'
        else:
            with open(pathlib.Path(file_dir, file), 'rb') as post_file:
                response = requests.post(post_url, headers=headers, files={"file": post_file})
                if response.status_code != 201:
                    logging.error('upload file failed')
                    sys.exit(1)
        if file.endswith('.sh'):
            merge_sh += f'chmod +x {file} \n\n'

    with open('merge_data.sh', 'w') as merge_file:
        merge_file.write(merge_sh)
    with open('merge_data.sh', 'r') as merge_file:
        response = requests.post(post_url, headers=headers, files={"file": merge_file})
        if response.status_code != 201:
            logging.error('upload file failed')
            sys.exit(1)


def split_binary_file(file_path, chunk_size):
    with open(file_path, 'rb') as f:
        while True:
            # 读取从当前位置到chunk_size字节长的块
            chunk = f.read(chunk_size)
            # 如果读取到的块大小小于chunk_size，说明已到达文件末尾
            if len(chunk) < chunk_size:
                yield chunk
                break

            yield chunk
