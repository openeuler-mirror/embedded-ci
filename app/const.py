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

GATE_CONF = "gate.yaml"
CRON_CONF = "cron.yaml"
CI_CONF = "ci.yaml"
CRON_WORKSPACE = "cron"
GATE_WORKSPACE = "gate"
CI_WORKSPACE = "ci"
GCC_DIR = "/usr1/openeuler/gcc"
NATIVE_SDK_DIR = "/opt/buildtools/nativesdk/"

PROCESS_LABEL = "ci_processing"
SUCCESS_LABEL = "ci_successful"
FAILED_LABEL = "ci_failed"

RELEASE_SUCCESS = "release_successful"
RELEASE_FAILED = "release_failed"
