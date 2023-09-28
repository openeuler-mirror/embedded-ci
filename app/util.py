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
import shutil
import importlib.util
import subprocess
import random
import base64

import yaml
import git

from json2table import convert

def check_oebuild_directory(o_dir: str):
    '''
    Detects whether the directory has been initialized by OEBUILD
    '''
    if not os.path.exists(o_dir):
        return False
    oebuild_dir = os.path.join(o_dir, '.oebuild')
    if os.path.exists(oebuild_dir):
        return True
    shutil.rmtree(o_dir)
    return False

def parse_yaml(yaml_dir):
    '''
    parser yaml file and return json object
    '''
    with open(yaml_dir, 'r', encoding='utf-8') as r_f:
        data = yaml.load(r_f.read(), yaml.Loader)
        return data

def write_yaml(yaml_dir, data):
    '''
    write data to yaml file
    '''
    with open(yaml_dir, 'w', encoding='utf-8') as w_f:
        yaml.dump(data, w_f)

def get_common_conf():
    '''
    parser comm.yaml file and return json object
    '''
    yaml_dir = os.path.join(get_conf_path(), "comm.yaml")
    with open(yaml_dir, 'r', encoding='utf-8') as r_f:
        data = yaml.load(r_f.read(), yaml.Loader)
        return data

def get_top_path():
    '''
    return the top path
    '''
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def get_conf_path():
    '''
    return the conf path
    '''
    return os.path.join(get_top_path(), 'conf')

def get_app_path():
    '''
    return the plugins path
    '''
    return os.path.join(get_top_path(), 'app')

def clone_repo_with_pr(src_dir, repo, remote_url, pr_num, depth):
    '''
    clone remote repo to local with pull request num
    '''
    depth = depth + 1
    repo_dir = os.path.join(src_dir, repo)
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)
    os.mkdir(repo_dir)
    os.chdir(repo_dir)
    subprocess.getoutput('git init')
    subprocess.getoutput(f'git remote add origin {remote_url}')
    subprocess.getoutput(f'git fetch origin pull/{pr_num}/MERGE:pr_{pr_num} --depth={depth}')
    subprocess.getoutput(f'git checkout pr_{pr_num}')

def clone_repo_with_depth(src_dir, repo, remote_url, branch, depth):
    '''
    clone remote repo to local with depth
    '''
    os.chdir(src_dir)
    git.Repo.clone_from(url=remote_url, to_path=repo, branch = branch, depth = depth)

def clone_repo_with_version_depth(src_dir, repo_dir, remote_url, version, depth):
    '''
    clone remote repo to local with depth
    '''
    os.chdir(src_dir)
    repo = git.Repo.init(repo_dir)
    remote = git.Remote.add(repo = repo, name = "origin", url = remote_url)
    remote.fetch(version, depth = depth)
    repo.git.checkout(version)

def get_spec_ext(file, mod_name):
    '''
    get instance from mod name
    '''
    file = os.path.join(get_app_path(), file)
    mod = commands_module_from_file(file=file, mod_name=mod_name)
    cls = getattr(mod, mod_name)
    return cls()

def commands_module_from_file(file, mod_name):
    '''
    Python magic for importing a module containing oebuild extension
    commands. To avoid polluting the sys.modules key space, we put
    these modules in an (otherwise unpopulated) oebuild.commands.ext
    package.
    '''

    # spec = importlib.find_loader(name = mod_name, path = file)
    spec = importlib.util.spec_from_file_location(mod_name, file)
    # mod = importlib.import_module(file, mod_name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    return mod

def json_to_html(json_data, direc="LEFT_TO_RIGHT"):
    '''
    translate json object to html data
    '''
    table_attributes = {"style" : "align: center"}
    html = convert(json_data, build_direction=direc, table_attributes=table_attributes)
    return html

def generate_random_str(randomlength=16):
    '''
    generate a random string by length
    '''
    random_str = ''
    base_str = 'ABCDEFGHIGKLMNOPQRSTUVWXYZabcdefghigklmnopqrstuvwxyz0123456789'
    length = len(base_str) - 1
    for _ in range(randomlength):
        random_str += base_str[random.randint(0, length)]
    return random_str

def install_package(package_name, remote_url = None):
    '''
    install python package dynamic
    '''
    try:
        if remote_url is None:
            subprocess.check_call(["pip3", "install", package_name])
        else:
            subprocess.check_call(["pip3", "install", package_name, "-i", remote_url])
    except subprocess.CalledProcessError:
        print(f"install {package_name} failed, please do it manual")

def base64_encode(text):
    """
    encode text with base64
    """
    return base64.b64encode(text.encode()).decode()

def base64_decode(text):
    """
    decode text with base64
    """
    return base64.b64decode(text.encode()).decode()
