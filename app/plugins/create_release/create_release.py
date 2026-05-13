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
try:
    from ruamel.yaml import YAML
except ImportError:
    from app.util import install_package
    install_package('ruamel.yaml')
    from ruamel.yaml import YAML

from app.command import Command

API_BASE = "https://api.gitcode.com/api/v5/repos"


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
        parser_addr.add_argument('-gt', '--git_token', dest="git_token")
        parser_addr.add_argument('-y', '--yaml_path', dest="yaml_path")
        parser_addr.add_argument('-f', '--file', dest="file_path")
        return parser_addr

    def do_run(self, args, unknow):
        args = self.parser.parse_args(unknow)

        if args.yaml_path:
            if not os.path.exists(args.yaml_path):
                raise FileNotFoundError(f"the {args.yaml_path} not exists")

        if args.file_path:
            if not os.path.exists(args.file_path):
                raise FileNotFoundError(f"the {args.file_path} not exists")

        json_data = read_yaml(pathlib.Path(args.yaml_path))

        release_info = get_release_by_tag(args.git_token, json_data)
        if release_info:
            update_release(args.git_token, json_data)
            logging.info('Successfully update release')
        else:
            response_info = create_release(args.git_token, json_data)
            if response_info.status_code not in (200, 201):
                print(response_info.text)
                logging.error('create release failed')
                sys.exit(1)
            logging.info('Successfully created release')

        upload_file(args.file_path, json_data['tag_name'], json_data['owner'],
                    json_data['repo'], args.git_token)
        logging.info('file upload successful')


def read_yaml(yaml_dir: pathlib.Path):
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
    create_url = f'{API_BASE}/{json_data["owner"]}/{json_data["repo"]}/releases'
    params = {"access_token": access_token}
    headers = {"Content-Type": "application/json"}
    res = requests.post(create_url, headers=headers, json=json_data, params=params)
    return res


def update_release(access_token, json_data):
    tag = json_data.get("tag_name", "")
    if not tag:
        logging.error(f'update release failed: tag is empty')
        sys.exit(1)
    owner = json_data["owner"]
    repo = json_data["repo"]
    update_url = f'{API_BASE}/{owner}/{repo}/releases/{tag}'
    params = {"access_token": access_token}
    body = {
        "name": json_data.get("name", ""),
        "body": json_data.get("body", ""),
        "release_status": "latest",
    }
    requests.patch(update_url, params=params, json=body)
    logging.info(f'Updated release {tag} for overwrite')

def get_release_by_tag(access_token, json_data):
    repo = json_data["repo"]
    tag = json_data["tag_name"]
    if not tag:
        logging.error(f'get release by tag failed: tag is empty')
        sys.exit(1)
    owner = json_data["owner"]
    url = f'{API_BASE}/{owner}/{repo}/releases/{tag}'
    params = {"access_token": access_token}
    res = requests.get(url, params=params)
    if res.status_code != 200:
        logging.error(f'get release by tag failed: {res.text}')
        return None
    return res.json()

def get_upload_url(access_token, owner, repo, tag, file_name):
    url = f'{API_BASE}/{owner}/{repo}/releases/{tag}/upload_url'
    params = {"access_token": access_token, "file_name": file_name}
    res = requests.get(url, params=params)
    if res.status_code != 200:
        logging.error(f'get upload url failed: {res.text}')
        sys.exit(1)
    return res.json()


def upload_file(file_dir, tag, owner, repo, access_token):
    files = os.listdir(file_dir)
    for file in files:
        upload_info = get_upload_url(access_token, owner, repo, tag, file)
        upload_url = upload_info.get("url", "")
        upload_header = upload_info.get("headers")
        with open(pathlib.Path(file_dir, file), 'rb') as f:
            logging.info(f'uploading {file}')
            response = requests.put(upload_url, headers=upload_header, data=f, verify=False, timeout=600)
            if response.status_code not in (200, 201):
                logging.error(f'upload file {file} failed: {response.text}')
                sys.exit(1)
            logging.info(f'uploaded {file}')
