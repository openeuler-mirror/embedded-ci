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
import shutil
import datetime
import re
import json

from app import util
from app.build import Utest, UtestParam

class Run(Utest):
    '''
    do basic test for ci
    '''
    def __init__(self) -> None:
        self.arch = None
        self.target_dir = None
        self.platform = None
        self.workspace = os.getcwd()
        self.mugen_url = None
        self.mugen_branch = None
        self.branch = None

    def do_utest(self, param: UtestParam):
        '''
        the exec will be called by gate
        '''
        self.arch = param.arch
        self.target_dir = param.target_dir
        self.platform = os.path.basename(self.target_dir)
        self.mugen_url = param.mugen_url
        self.mugen_branch = param.mugen_branch
        self.branch = "master"

        self.exec()

    def exec(self):
        '''
        the exec will be called by gate
        '''
        if not os.path.exists(os.path.join(self.workspace, "mugen")):
            self.clone_mugen()

        os.chdir(os.path.dirname(self.workspace))
        # get config
        test_faild_list = []
        test_faild_logs = []
        output_dir = os.path.join(self.target_dir, 'output')
        if not os.path.exists(output_dir):
            return
        fail_arr = self.run_basic_test(self.arch, self.target_dir, output_dir)
        if len(fail_arr) > 0 :
            fail_title = "WARN"
            build_faild = {
                        'arch': self.arch,
                        'directory': self.platform,
                        'generate': "; ".join(fail_arr),
                        'bitbake': "do basic test had fail testcasees"
            }
            test_faild_list.append(build_faild)
            print("%s : Do %s basic test from dir %s fail;\n fail info: %s\n"%(
                    fail_title, self.arch, self.platform, "\n\t".join(fail_arr)))
            run_info = f"{self.arch}_{self.platform}"
            test_faild_logs.extend(
                self.get_all_fail_test_info(
                    os.path.join(self.workspace, "mugen"),
                    run_info))

        print("======================= Summary =======================")
        if len(test_faild_list) == 0:
            print("[INFO] : Run all test success.")
        else:
            for one_fail in test_faild_list:
                print(f"""
                      [Error] : Do {one_fail['arch']} basic test from dir {one_fail['directory']} fail;
                      fail info: {one_fail['generate']}""")
            print("======================= Fail logs =======================")
            self.print_test_fail_log(test_faild_logs)
            print("=========================================================")
            raise ValueError("test failed")

    def print_test_fail_log(self, test_faild_logs):
        if len(test_faild_logs) == 0:
            return
        for one_info in test_faild_logs:
            print(f"For {one_info[0]}")
            if one_info[1] == "":
                print(f"\t{one_info[4]}")
                continue
            if one_info[2] == "":
                print(f"""\t
for combination - {one_info[1]}, {one_info[4]}
""")
                continue
            if one_info[3] == "":
                print(f"""\t
for combination - {one_info[1]} testsuite - {one_info[2]}, {one_info[4]}
""")
                continue
            if one_info[4] == "":
                print(f"""\t
for combination - {one_info[1]} testsuite - {one_info[2]} testcase - {one_info[3]}, {one_info[4]}
""")
                continue
            if not os.path.exists(one_info[4]):
                print(f"""\t
for combination - {one_info[1]} testsuite - {one_info[2]} testcase - {one_info[3]}, {one_info[4]} log file can't find
""")
                continue
            print(f"""\t
for combination - {one_info[1]} testsuite - {one_info[2]} testcase - {one_info[3]}, log is
""")
            with open(one_info[4], "r", encoding="utf-8") as rf:
                all_str = rf.readlines()
                all_str[0] = "\t\t" + all_str[0]
                print("\t\t".join(all_str))

    def clone_mugen(self):
        '''
        clone mugen for test builded image
        '''
        test_path = os.path.join(self.workspace, "mugen")
        if os.path.exists(test_path):
            shutil.rmtree(test_path)
        util.clone_repo_with_depth(
            src_dir=self.workspace,
            repo="mugen",
            remote_url=self.mugen_url,
            branch=self.mugen_branch,
            depth=1)
        with subprocess.Popen(f"""
cd {test_path} && sudo sh dep_install.sh -e && sudo yum install -y qemu-system-riscv elfutils-libelf-devel qemu-system-x86_64
""",
                              shell=True,
                              cwd=test_path,
                              encoding="utf-8") as r_p:
            r_p.communicate()

    def get_file_from_dir(self, filename, find_dir, match_type = "full"):
        return_path = []
        all_files = os.listdir(find_dir)
        for one_file in all_files:
            full_path = os.path.join(find_dir, one_file)
            if os.path.isfile(full_path):
                if match_type == "fuzzy":
                    if one_file.find(filename) >= 0:
                        return_path.append(full_path)
                elif match_type == "full":
                    if one_file == filename:
                        return_path.append(full_path)
                elif match_type == "re":
                    if re.search(filename, one_file):
                        return_path.append(full_path)
            elif os.path.isdir(full_path):
                return_path.extend(self.get_file_from_dir(filename, full_path, match_type))
        return return_path

    def get_testcase_log_path(self, mugen_path, suite_name, case_name):
        logs_path = os.path.join(mugen_path, "logs", suite_name, case_name)
        all_logs = os.listdir(logs_path)
        all_times = []
        for one in all_logs:
            one_time = datetime.datetime.strptime(os.path.splitext(one)[0], "%Y-%m-%d-%H:%M:%S")
            all_times.append((one_time, one))
        def get_sort_key(elem):
            return elem[0]
        all_times.sort(key = get_sort_key, reverse = True)

        return os.path.join(logs_path, all_times[0][1])

    def get_all_fail_test_info(self, mugen_path, run_info):
        ret_fail_info = []
        results_path = os.path.join(mugen_path, "combination_results")
        if not os.path.exists(results_path):
            ret_fail_info.append([run_info, "", "", "", "not run any combination"])
            return ret_fail_info

        all_result = os.listdir(results_path)

        for one_result in all_result:
            tmp_path = os.path.join(results_path, one_result)
            tmp_suite = os.listdir(tmp_path)
            if not tmp_suite or len(tmp_path) == 0:
                ret_fail_info.append([run_info, one_result, "", "", "not run any testcase"])
                continue
            for one_suite in tmp_suite:
                tmp_suite_path = os.path.join(tmp_path, one_suite)
                tmp_case = os.listdir(tmp_suite_path)
                if not tmp_case or len(tmp_case) == 0:
                    ret_fail_info.append(
                        [
                            run_info,
                            one_result,
                            one_suite,
                            "",
                            "not run any testcase"
                            ])
                    continue
                fail_case_path = os.path.join(tmp_suite_path, "failed")
                if not os.path.exists(fail_case_path):
                    continue
                tmp_fail_case = os.listdir(fail_case_path)
                if not tmp_fail_case or len(tmp_fail_case) == 0:
                    ret_fail_info.append(
                        [
                            run_info,
                            one_result,
                            one_suite,
                            "",
                            "fail testcase info get error"
                            ])
                for one in tmp_fail_case:
                    ret_fail_info.append(
                        [
                            run_info,
                            one_result,
                            one_suite,
                            one,
                            self.get_testcase_log_path(mugen_path, one_suite, one)
                            ])
        if len(ret_fail_info) == 0:
            ret_fail_info.append([run_info, "", "", "", "no resultes in mugen"])
        return ret_fail_info

    def run_basic_test(self, arch, platform, img_dir):
        fail_infos = []
        if (platform.find("-std") < 0 and platform.find("qemu") < 0):
            print(f"""
[WARN]: build {arch} for {platform} not support run automatic in qemu, skip run this image test
""")
            return fail_infos
        test_path = os.path.join(self.workspace, "mugen")
        conf_dir = util.get_conf_path()
        test_template_path = os.path.join(conf_dir, "basic_test.json")

        arch_map = {
            # arch type : qemu_arch qemu_image_name qemu_cpu qemu_machine
            "aarch64":["aarch64", "zImage", "cortex-a57", "virt-4.0"],
            "x86-64":["x86_64", "bzImage", "qemu64", "pc"],
            "riscv64":["riscv64", "Image", "rv64", "virt"],
            "arm32":["arm", "zImage", "cortex-a15", "virt-4.0"],
        }
        qemu_type = arch_map[arch][0]
        login_wait_str = "openEuler Embedded(openEuler Embedded Reference Distro)"
        zimage_path = self.get_file_from_dir(arch_map[arch][1], img_dir)
        print(zimage_path)
        if len(zimage_path) != 1:
            print(f"""
[WARN]: find more then one or zero zImage from {img_dir} skip run test build {arch} for {platform}
""")
            fail_infos.append("find zimage file fail")
        else:
            zimage_path = zimage_path[0]

        initrd_path = self.get_file_from_dir(r'rootfs\.cpio\.gz$', img_dir, "re")
        print(initrd_path)
        if len(initrd_path) != 1:
            print(f"""
[WARN]: find more then one or zero initrd from {img_dir} skip run test build {arch} for {platform}
""")
            fail_infos.append("find initrd file fail")
        else:
            initrd_path = initrd_path[0]

        sdk_path = self.get_file_from_dir(r'toolchain.*\.sh$', img_dir, "re")
        print(sdk_path)
        if len(sdk_path) != 1:
            print(f"""
[ERROR]: find more then one or zero sdk script from {img_dir} skip run test build {arch} for {platform}
""")
            fail_infos.append("find sdk file fail")
        else:
            sdk_path = sdk_path[0]

        if len(fail_infos) > 0:
            return fail_infos
        sdk_basic_path = os.path.dirname(sdk_path)
        sdk_install_path = os.path.join(sdk_basic_path, "sdk")
        with subprocess.Popen(f"sh {sdk_path}",
                                    shell=True,
                                    stdin=subprocess.PIPE,
                                    cwd=sdk_basic_path,
                                    encoding="utf-8") as s_p:
            s_p.stdin.write(sdk_install_path + "\n")
            s_p.stdin.write("y\n")
            s_p.communicate()
            if s_p.returncode != 0:
                fail_infos.append("install sdk fail")
        with open(test_template_path, "r", encoding="utf-8") as r_f:
            test_json = json.load(r_f)
        test_json["env"][0]["kernal_img_path"] = zimage_path
        test_json["env"][0]["initrd_path"] = initrd_path
        test_json["env"][0]["login_wait_str"] = login_wait_str
        test_json["env"][0]["qemu_type"] = qemu_type
        test_json["env"][0]["sdk_path"] = sdk_install_path
        test_json["env"][0]["cpu"] = arch_map[arch][2]
        test_json["env"][0]["machine"] = arch_map[arch][3]
        if arch == "x86-64":
            test_json["env"][0]["option_wait_time"] = 240
        test_json["export"]["DOWNLOAD_BRANCH"] = self.branch
        combination_file_name = f"{qemu_type}_basic_com_test.json"
        run_conf_path = os.path.join(test_path, "combination", combination_file_name)
        with open(run_conf_path, "w", encoding="utf-8") as w_f:
            json.dump(test_json, w_f, indent=4)
        print("=======================start combination run====================================")
        with subprocess.Popen(f"""
sudo sh combination.sh -r {os.path.splitext(combination_file_name)[0]}
""",
                              shell=True,
                              cwd=test_path,
                              encoding="utf-8") as r_p:
            r_p.communicate()
            if r_p.returncode != 0:
                fail_infos.append("run basic test fail")
        print("========================end combination run====================================")
        with subprocess.Popen(f'sudo rm -rf {sdk_install_path} || rm -rf {sdk_install_path}',
                              shell=True,
                              cwd=test_path,
                              encoding="utf-8") as r_p:
            r_p.communicate()
        return fail_infos
