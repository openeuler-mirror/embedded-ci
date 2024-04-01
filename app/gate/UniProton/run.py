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
import re
import os
import subprocess
from threading import Timer
import time

from app.build import Build,BuildRes,Arch,Board
from app import util
from app.lib import Result

QEMU_WAIT_TIME = 60 * 30

def kill_qemu(sp):
    sp.terminate()
    sp.kill()

def find_first_number(string):
    match = re.search(r'\d+', string)
    if match:
        return int(match.group())
    else:
        return None

#基类对象定义
#run_name -> 定义的命名
#run_path -> 在哪个目录下运行cmd
#qemu_cmd -> 运行的qemu_cmd是什么
class outputParser:
    def __init__(self, run_name, run_path, qemu_cmd):
        self.run_path = run_path
        self.qemu_cmd = qemu_cmd
        self.run_name = run_name
        # log_run    -> 运行过程的日志记录
        # run_failed -> 是否运行成功或者失败
        #               None   -> 没有运行过
        #               True   -> 运行失败, 失败原因在self.result 里面 [当run_failed == True 的时候, result存放字符串, 对应失败原因]
        #               False  -> 运行成功, self.result 根据不同的类型进行确定[如 rhealstone 是运行获得的cycle数目, testcase的无意义 根据对应子类实现确定]
        # result     -> 失败则记录原因,成功则根据子类判断具体意义
        # stop_timer -> 存放qemu命令对应的定时器
        # running_process -> 存放对应qemu命令的进程句柄 
        self.log_run = []
        self.run_failed = None
        self.running_process = None
        self.stop_timer = None
        self.result = None
    
    def clean_state(self):
        # 清除内部状态
        # 运行过一次后,如果想要重复运行必须先调用clean_state
        # 在run_process之前调用无意义,并不会做任何事情, 不会出现未定义的情况
        if self.stop_timer is not None:
            if self.stop_timer.is_alive():
                self.stop_timer.cancel()       
            self.stop_timer = None
        if self.running_process is not None:
            kill_qemu(self.running_process)
            self.running_process = None
        self.run_failed = None
        self.result = None
        self.log_run = []
    def get_run_result(self):
        if self.run_failed is None:
            return (True,"not run yet")
        return (self.run_failed,self.result)
    def get_run_log(self):
        return self.log_run
    def run_process(self):
        # 运行命令并记录
        # 多次重复调用返回Fasle 
        # 调用顺序应该为 run_process -> clean -> run_process -> clean 
        if self.run_failed is not None:
            return False
        with subprocess.Popen(
            self.qemu_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self.run_path,
            encoding="utf-8") as r_p:
            # 判断是否正在运行
            if r_p.poll() is not None:
                output_out, _ = r_p.communicate()
                self.run_failed = True
                self.result = "[RUN_FAIL_REASON]: can't find target run file"
                self.log_run.append(f'[ERROR][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run {self.run_name} fail, log: \n{output_out}\n')
                kill_qemu(r_p)
                return True
            try:
                self.stop_timer = Timer(QEMU_WAIT_TIME, kill_qemu, [r_p])
                self.stop_timer.start()
                self.running_process = r_p
                self._private_check_output() # 私有,子类实现
            except NotImplementedError:
                self.run_failed = True
                self.result = "[RUN_FAIL_REASON]: can't use father to run"
            except Exception:
                self.run_failed = True
                self.result = "[RUN_FAIL_REASON]: a exception that i don't know"
            return True #表示执行 run成功 run faile 对应原因在 result, run success 对应结果也在result 
    #子类实现
    #需要遵守:
    #       检查 self.running_process的输出
    #       满足预期要求:
    #             self.run_failed = False
    #             self.result = .. [此处为用户自定义的数据,如rhealstone系列的qemu应该为延迟周期数,也可不用]
    #       未满足预期要求:
    #             self.run_failed = True
    #             self.result = ...[字符串类型,对应错误的原因]
    def _private_check_output(self):
        raise NotImplementedError("Subclasses must implement check_output method.")

class rheal_outParser(outputParser):
    def _private_check_output(self):
        self.log_run.append(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run {self.run_name} start')
        check_line = self.running_process.stdout.readline()
        while self.running_process.poll() is None:
            self.log_run.append(check_line)
            # 测试结束输出 Rhealstone
            if (check_line.find("Rhealstone:") >= 0 ):
                self.stop_timer.cancel()
                kill_qemu(self.running_process)
                break
            check_line = self.running_process.stdout.readline()
        self.log_run.append(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run {self.run_name} finish')
        if (check_line.find("Rhealstone:") >= 0):
            self.run_failed = False
            self.result = find_first_number(str(check_line))
            if self.result is None:
                self.run_failed = True
                self.result = "[RUN_FAIL_REASON]: rhealstone success but can't find a right number cycle"
                return
            self.log_run.append(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run {self.run_name} result : {check_line} ')
            return
        else:
            self.run_failed = True
            self.result = "[RUN_FAIL_REASON]: rhealstone run over time"
            return
        return

class testcase_outParser(outputParser):
    def _private_check_output(self):
        self.log_run.append(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run {self.run_name} start')
        check_line = self.running_process.stdout.readline()
        while self.running_process.poll() is None:
            self.log_run.append(check_line)
            # 测试结束输出 Run total testcase
            if (check_line.find("Run total testcase") >= 0 and
                check_line.find(", failed") >= 0):
                self.stop_timer.cancel()
                kill_qemu(self.running_process)
                break
            check_line = self.running_process.stdout.readline()
        self.log_run.append(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run {self.run_name} finish')
        if (check_line.find("Run total testcase") >= 0 and
            check_line.find(", failed") >= 0) :
            if (check_line.strip()[-1] != "0" or 
                check_line.strip()[-2] != " "):
                self.run_failed = True
                self.result = f'[RUN_FAIL_REASON]: {check_line}'
            else:
                self.run_failed = False
                self.result = "nothing else"
            return
        else:
            self.run_failed = True
            self.result = "[RUN_FAIL_REASON]: rhealstone run over time"
            return
        return


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
                run_info = []
                if os.path.splitext(one_file)[1] != ".bin":
                    continue
                if one_file.find("UniPorton_test_posix_exit_") >= 0:
                    print(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: skip run test: {one_file}')
                    continue
                qemu_cmd = f"qemu-system-arm -M mps2-an386 -cpu cortex-m4 --semihosting -kernel {os.path.join(run_test_path, one_file)}"
                print(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run test cmd: {qemu_cmd}')
                t_parser = testcase_outParser(one_file, run_test_path, qemu_cmd)
                t_parser.run_process()
                run_failed, result = t_parser.get_run_result()
                run_info.extend(t_parser.get_run_log())
                if run_failed == True:
                    run_fail = True
                    run_info.append(result)
                for one_log in run_info:
                    if one_log.strip() != "":
                        print("\t", one_log)
                if run_fail:
                    step_reslt.append(Board(name=f'run {testsuite["case"]} test', result=Result().faild))
                else:
                    step_reslt.append(Board(name=f'run {testsuite["case"]} test', result=Result().success))
        return step_reslt
    def run_rhealstone(self, run_test_path, rheal_elf_name, output_name):
        res = []
        print(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}]: ===== begin run rv64 test =====')
        run_info = []
        run_fail = False
        now_time = 999
        base_time = 0
        qemu_cmd = f"/opt/qemu/bin/qemu-system-riscv64 -bios none -M virt -m 512M  -nographic -smp 1 -kernel {os.path.join(run_test_path, rheal_elf_name)}"
        print(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run test cmd: {qemu_cmd}')
        r_parser = rheal_outParser(rheal_elf_name, run_test_path, qemu_cmd)
        r_parser.run_process()
        run_failed, result = r_parser.get_run_result()
        run_info.extend(r_parser.get_run_log())
        if run_failed == True:
            run_fail = True
            run_info.append(result)
        else:
            now_time = result
            run_info.append(f'{output_name} get first number -> now_time : {now_time}')
        qemu_cmd = f"/opt/qemu/bin/qemu-system-riscv64 -bios none -M virt -m 512M  -nographic -smp 1 -kernel {run_test_path}/baserheal/{rheal_elf_name}"
        print(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run test cmd: {qemu_cmd}')
        r_parser = rheal_outParser(f'baserheal/{rheal_elf_name}', run_test_path, qemu_cmd)
        r_parser.run_process()
        run_failed, result = r_parser.get_run_result()
        run_info.extend(r_parser.get_run_log())
        if run_failed == True:
            run_fail = True
            run_info.append(result)
        else:
            base_time = result
            run_info.append(f'baserheal/{output_name} get first number -> now_time : {base_time}')
        for one_log in run_info:
            if one_log.strip() != "":
                print("\t", one_log)
        if run_fail:
            res.append(Board(name=f'{output_name} - 999 cyc', result=Result().faild))
        else:
            if now_time > base_time:
                over_time = now_time - base_time
                res.append(Board(name=f'{output_name} +{over_time} cyc', result=Result().success))
            else :
                over_time = base_time - now_time
                res.append(Board(name=f'{output_name} -{over_time} cyc', result=Result().success))
        return res

    def run_rv64_test(self, run_test_path, rv64_info):
        step_reslt = []
        for testsuite in rv64_info['suite']:
            testcase = testsuite["case"]
            build_ret = self.run_test_build_cmd(run_test_path, "sh build_app_riscv64.sh", testcase)
            if build_ret != 0:
                step_reslt.append(Board(name=f'build {testsuite["case"]} test', result=Result().faild))
            else:
                step_reslt.append(Board(name=f'build {testsuite["case"]} test', result=Result().success))
            if str(testcase) == "rhealstone":
                step_reslt.extend(self.run_rhealstone(run_test_path, "semaphore-shuffle_rv.elf", "sema-shufl"))
                step_reslt.extend(self.run_rhealstone(run_test_path, "task-switch_rv.elf",       "task-swith"))
                step_reslt.extend(self.run_rhealstone(run_test_path, "task-preempt_rv.elf",      "task-prmpt"))
                step_reslt.extend(self.run_rhealstone(run_test_path, "message-latency_rv.elf",   "mesg-latny"))
                step_reslt.extend(self.run_rhealstone(run_test_path, "deadlock-break_rv.elf",    "dead-break"))
                continue
            print(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}]: ===== begin run rv64 test =====')
            all_files = os.listdir(run_test_path)
            run_fail = False
            for one_file in all_files:
                run_info = []
                if not one_file.endswith("_rv.elf"):
                    continue
                qemu_cmd = f"/opt/qemu/bin/qemu-system-riscv64 -bios none -M virt -m 512M  -nographic -smp 1 -kernel {os.path.join(run_test_path, one_file)}"
                print(f'[INFO][{time.strftime("%Y-%m-%d %H:%M:%S")}]: run test cmd: {qemu_cmd}')
                t_parser = testcase_outParser(one_file, run_test_path, qemu_cmd)
                t_parser.run_process()
                run_failed, result = t_parser.get_run_result()
                run_info.extend(t_parser.get_run_log())
                if run_failed == True:
                    run_fail = True
                    run_info.append(result)
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
            elif test_type["type"] == "rv64-qemu":
                step_reslt = self.run_rv64_test(run_test_path, test_type)
            else:
                print(f'[ERROR][{time.strftime("%Y-%m-%d %H:%M:%S")}]: gate yaml had no run type!')
            test_res.append(Arch(name=f'{test_type["type"]}', boards=step_reslt))
        return test_res

