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
import subprocess
from threading import Timer
import time

from app.build import Build,BuildRes,Arch,Board
from app import util
from app.lib import Result

QEMU_WAIT_TIME = 30 * 60

def kill_qemu(sp):
    sp.terminate()
    sp.kill()

class Run(Build):
    '''
    Inherit the Build interface class to implement specific services
    '''
    def do_build(self, param):
        libbound_repo = "libboundscheck"
        libbound_repo_remote = "https://gitee.com/openeuler/libboundscheck.git"
        libbounds_dir = os.path.join(param.workspace, libbound_repo)
        do_test = True
        # download libboundscheck
        if not os.path.exists(libbounds_dir):
            util.clone_repo_with_depth(
                src_dir=param.workspace,
                repo=libbound_repo,
                remote_url=libbound_repo_remote,
                branch="master",
                depth=1)
        gate_path = os.path.join(os.path.dirname(__file__), "build.yaml")
        gate_conf = util.parse_yaml(gate_path)
        os.chdir(param.workspace)
        # copy libboundcheck rely to
        subprocess.getstatusoutput(f"cp {libbounds_dir}/include/* {param.repo_dir}/platform/libboundscheck/include")
        subprocess.getstatusoutput(f"cp {libbounds_dir}/include/* {param.repo_dir}/include")
        subprocess.getstatusoutput(f"cp {libbounds_dir}/src/* {param.repo_dir}/platform/libboundscheck/src")
        arch_res = []
        for arch in gate_conf['build_check']:
            board_res = []
            for board in arch['board']:
                # run `oebuild bitbake openeuler-image`
                build_cmd = f"python3 build.py {board['name']}"
                print(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run build cmd: {build_cmd}')
                output, ret = self.run_build_cmd(build_cmd, param.repo_dir)
                print(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: output: ')
                print(output)
                build_res = Result().success
                if output.find("all lib succeed! ####################") < 0 or ret != 0:
                    print(f'[ERROR][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run build cmd: {build_cmd} fail')
                    build_res = Result().faild
                    do_test = False
                elif output.find("all lib failed! ####################") >= 0 and board['name'] == all:
                    print(f'[ERROR][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run build cmd: {build_cmd} fail')
                    build_res = Result().faild
                    do_test = False
                board_res.append(Board(name=f"{board['name']}", result=build_res))
            arch_res.append(Arch(name=arch["arch"], boards=board_res))
        for arch in gate_conf['demo_check']:
            board_res = []
            for board in arch['board']:
                run_script = []
                build_run_path = os.path.join(param.repo_dir, "demos", board["name"], "build")
                if("app" in board.keys()):
                    for one_app in board["app"]:
                        run_script.append(f'sh -x -e build_app.sh {one_app["app_name"]}')
                else:
                    run_script.append(f'sh -x -e build_app.sh')
                
                for one_script in run_script:
                    run_res = Result().success
                    board_name = board["name"] if one_script.replace('sh -x -e build_app.sh', '') == "" else f"{board['name']} - {one_script.replace('sh -x -e build_app.sh', '')}"
                    print(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run demo cmd: {one_script} in {build_run_path}')
                    output, ret = self.run_build_cmd(one_script, build_run_path)
                    print(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run demo cmd: {one_script} in {build_run_path} finish')
                    if ret != 0:
                        print(f'[ERROR][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run demo cmd: {one_script} fail, output: ')
                        print(output)
                        run_res = Result().faild
                    board_res.append(Board(name=f"{board_name}", result=run_res))
            arch_res.append(Arch(name=f'demo build {arch["arch"]}', boards=board_res))

        if do_test:
            arch_res.extend(self.run_test(param))
        return BuildRes(archs=arch_res)

    def run_build_cmd(self, run_script, run_dir):
        print(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: begin run cmd: {run_script}')
        output = ""
        ret = 1
        with subprocess.Popen(
            run_script,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=run_dir,
            encoding="utf-8") as s_p:
            output, _ = s_p.communicate()
            ret = s_p.returncode
        print(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: end run cmd: {run_script}')
        return output, ret

    def run_test_build_cmd(self, run_test_path, build_cmd_prefix, testcase):
        build_cmd = f'sudo rm -rf {run_test_path}/*.bin {run_test_path}/*.elf && {build_cmd_prefix} {testcase}'
        print(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run build cmd: {build_cmd}')
        with subprocess.Popen(
                            build_cmd,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            cwd=run_test_path,
                            encoding="utf-8") as t_p:
                    output_out, _ = t_p.communicate()
                    if t_p.returncode != 0:
                        print(f'[ERROR][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run build cmd {build_cmd} fail, log: \n{output_out}\n')
                    else:
                        print(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run {build_cmd} success')
                    return t_p.returncode

    def run_m4_test(self, run_test_path, m4_info):
        step_reslt = []
        for testsuite in m4_info['suite']:
            testcase = testsuite["case"]
            build_ret = self.run_test_build_cmd(run_test_path, "sh build_app.sh sim", testcase)
            if build_ret != 0:
                step_reslt.append(Board(name=f'build {testsuite["case"]} test', result=Result().faild))
            else:
                step_reslt.append(Board(name=f'build {testsuite["case"]} test', result=Result().success))
            print(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}]: ===== begin run m4 test =====')
            all_files = os.listdir(run_test_path)
            run_fail = False
            for one_file in all_files:
                show_log = False
                run_info = []
                if os.path.splitext(one_file)[1] != ".bin":
                    continue
                if one_file.find("UniPorton_test_posix_exit_") >= 0:
                    print(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: skip run test: {one_file}')
                    continue
                qemu_cmd = f"qemu-system-arm -M mps2-an386 -cpu cortex-m4 --semihosting -kernel {os.path.join(run_test_path, one_file)}"
                print(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run test cmd: {qemu_cmd}')
                with subprocess.Popen(
                    qemu_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=run_test_path,
                    encoding="utf-8") as r_p:
                    # 判断是否正在运行
                    if r_p.poll() is not None:
                        output_out, _ = r_p.communicate()
                        run_fail = True
                        print(f'[ERROR][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run test cmd: {one_file} fail, log: \n{output_out}\n')
                        r_p.terminate()
                        r_p.kill()
                        continue
                    # 配置定时器，防止用例错误导致qemu一直不退出
                    r_p_stop_timer = Timer(QEMU_WAIT_TIME, kill_qemu, [r_p])
                    r_p_stop_timer.start()
                    check_line = r_p.stdout.readline()
                    while r_p.poll() is None:
                        run_info.append(check_line)
                        # 测试结束输出 Run total testcase x, failed y
                        if (check_line.find("Run total testcase") >= 0 and
                            check_line.find(", failed") >= 0) :
                            r_p_stop_timer.cancel()
                            r_p.terminate()
                            r_p.kill()
                            break
                        check_line = r_p.stdout.readline()
                    print(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run test cmd: {qemu_cmd} finish')
                    if (check_line.find("Run total testcase") >= 0 and
                            check_line.find(", failed") >= 0) :
                        if (check_line.strip()[-1] != "0" or 
                            check_line.strip()[-2] != " "):
                            run_fail = True
                            show_log = True
                            print(f'[ERROR][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run {one_file} fail, log:')
                    else:
                        run_fail = True
                        show_log = True
                        print(f'[ERROR][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run {one_file} timeout, log:')
                if show_log:
                    for one_log in run_info:
                        if one_log.strip() != "":
                            print("\t", one_log)
                if run_fail:
                    step_reslt.append(Board(name=f'run {testsuite["case"]} test', result=Result().faild))
                else:
                    step_reslt.append(Board(name=f'run {testsuite["case"]} test', result=Result().success))
        return step_reslt

    def run_test(self, param):
        run_test_path = os.path.join(param.repo_dir, "testsuites", "build")
        step_reslt = []
        test_conf_path = os.path.join(os.path.dirname(__file__), "test.yaml")
        test_conf = util.parse_yaml(test_conf_path)
        test_res = []
        for test_type in test_conf['test_check']:
            if test_type["type"] == "m4-qemu":
                step_reslt = self.run_m4_test(run_test_path, test_type)
            else:
                print(f'[ERROR][{time.strftime("%Y-%m-%d %H:%M:%S")}]: gate yaml had no run type!')
            test_res.append(Arch(name=f'{test_type["type"]}', boards=step_reslt))
        return test_res
