##!/usr/bin/python
## coding: utf8
#######################################################################
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
########################################################################
import os
import yaml
import time

import functest.testcases.vnf.vnf.vnf_controller.vnf_controller as ft_vnf_controller
import functest.utils.functest_logger as ft_logger

from functest.testcases.vnf.vnf.utilvnf import utilvnf

""" logging configuration """
logger = ft_logger.Logger("vnf_test.test_exec").getLogger()

with open(os.environ["CONFIG_FUNCTEST_YAML"]) as f:
    functest_yaml = yaml.safe_load(f)
f.close()

VNF_DATA_DIR = functest_yaml.get("general").get(
    "directories").get("dir_vnf_test_data") + "/"

class Test_exec():

    def __init__(self, util_info):
        logger.debug("init test exec")
        self.credentials = util_info["credentials"]
        self.vnf_ctrl = ft_vnf_controller.VNF_controller(util_info)
        self.REBOOT_WAIT = 30
        self.WAIT = 30

        test_cmd_map_file = open(VNF_DATA_DIR + "opnfv-vnf-data/command_template/test_cmd_map.yaml", 'r')
        self.test_cmd_map_yaml = yaml.safe_load(test_cmd_map_file)
        test_cmd_map_file.close()

        self.util = utilvnf(logger)
        self.util.set_credentials(self.credentials["username"],
                                  self.credentials["password"],
                                  self.credentials["auth_url"],
                                  self.credentials["tenant_name"],
                                  self.credentials["region_name"])


    def config_target_vnf(self, target_vnf, reference_vnf, test_kind):
        logger.debug("Configuration to target vnf")
        test_info = self.test_cmd_map_yaml[target_vnf["vnf_image"]][test_kind]
        test_cmd_file_path = test_info["pre_command"]
        target_parameter_file_path = test_info["parameter_target"]

        return self.vnf_ctrl.config_vnf(target_vnf,
                                        reference_vnf,
                                        test_cmd_file_path,
                                        target_parameter_file_path)


    def config_reference_vnf(self, reference_vnf, target_vnf, test_kind):
        logger.debug("Configuration to reference vnf")
        test_info = self.test_cmd_map_yaml[reference_vnf["vnf_image"]][test_kind]
        test_cmd_file_path = test_info["pre_command"]
        reference_parameter_file_path = test_info["parameter_reference"]

        return self.vnf_ctrl.config_vnf(reference_vnf,
                                        target_vnf,
                                        test_cmd_file_path,
                                        reference_parameter_file_path)


    def result_check(self, target_vnf, reference_vnf, test_kind, test_list):
        test_info = self.test_cmd_map_yaml[target_vnf["vnf_image"]][test_kind]
        target_parameter_file_path = test_info["parameter_target"]
        check_rule_file_path_list = []

        for test in test_list:
            check_rule_file_path_list.append(test_info[test])

        return self.vnf_ctrl.result_check(target_vnf,
                                          reference_vnf,
                                          check_rule_file_path_list,
                                          target_parameter_file_path)


    def run(self, target_vnf, reference_vnf_list, test_kind, test_list):
        for reference_vnf in reference_vnf_list:
            logger.debug("Start config command.")

            if not self.config_target_vnf(target_vnf, reference_vnf, test_kind):
                return False

            if not self.config_reference_vnf(reference_vnf, target_vnf, test_kind):
                return False

            logger.debug("Finish config command.")

            logger.debug("Start check method.")
            #time.sleep(self.WAIT)

            if not self.result_check(target_vnf, reference_vnf, test_kind, test_list):
                return False

            logger.debug("Finish check method.")

            # Clear the test configuration.
            self.util.reboot_v(target_vnf["vnf_name"])
            self.util.reboot_v(reference_vnf["vnf_name"])


        return True

