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

import functest.testcases.vnf.vnf.vnf_controller.ssh_client as ft_ssh_client
import functest.testcases.vnf.vnf.vnf_controller.vnf_controller as ft_vnf_controller
import functest.testcases.vnf.vnf.vnf_controller.checker as ft_checker
import functest.utils.functest_logger as ft_logger

""" logging configuration """
logger = ft_logger.Logger("vnf_test.test_exec").getLogger()

with open(os.environ["CONFIG_FUNCTEST_YAML"]) as f:
    functest_yaml = yaml.safe_load(f)
f.close()

VNF_DATA_DIR = functest_yaml.get("general").get(
    "directories").get("dir_vnf_test_data") + "/"

class Test_exec():

    def __init__(self):
        logger.debug("init test exec")
        self.vnf_ctrl = ft_vnf_controller.VNF_controller()

        test_cmd_map_file = open(VNF_DATA_DIR + "opnfv-vnf-data/command_template/test_cmd_map.yaml", 'r')
        self.test_cmd_map_yaml = yaml.safe_load(test_cmd_map_file)
        test_cmd_map_file.close()


    def run(self, vnf_list, target, test_kind, test_list):
        ssh_target = None
        target_vnf = None

        for vnf in vnf_list:
            test_info = self.test_cmd_map_yaml[vnf["vnf_image"]][test_kind]

            ssh = ft_ssh_client.SSH_Client(vnf["m_plane_ip"], vnf["user"], vnf["pass"])

            if vnf["vnf_name"] == target:
                ssh_target = ssh
                target_vnf = vnf
                parameter_file_path = test_info["parameter_target"] 
            else:
                parameter_file_path = test_info["parameter_reference"]

            parameter_file = open(parameter_file_path, 'r')
            parameter = yaml.safe_load(parameter_file)
            parameter_file.close()

            for v in vnf_list:
                if v["vnf_name"] == vnf["vnf_name"]:
                    origin_ip = v["d_plane_ip"]
                else:
                    neighbor_ip = v["d_plane_ip"]

            parameter["ipv4_origin"] = origin_ip
            parameter["ipv4_neighbor"] = neighbor_ip


            #ssh.connect()
            (test_cmd_dir, test_cmd_file) = os.path.split(test_info["pre_command"])
            commands = self.vnf_ctrl.command_gen_from_template(test_cmd_dir,
                                                               test_cmd_file,
                                                               parameter)
            #self.vnf_ctrl.commands_execute(ssh, commands)
            #ssh.close()


        if ssh_target != None:
            ssh_target.connect()
            #print "ssh_target.connect()"
        else:
            return None

        checker = ft_checker.Checker()
        for test in test_list:
            (check_rule_dir, check_fule_file) = os.path.split(test_info[test])
            check_rules = checker.load_check_rule(check_rule_dir, check_fule_file)
            #print check_rules
            res = self.vnf_ctrl.command_execute(ssh_target, check_rules["command"])
            checker.regexp_information(res, check_rules["rules"])

        if ssh_target != None:
            ssh_target.close()
            #print "ssh_target.close()"
        else:
            return None



if __name__ == '__main__':
    test_exec = Test_exec()

    vnf_list = [{"vnf_name":"vnf1", "vnf_image":"vyos-1.1.7.img", "user":"vyos", "pass":"vyos", "m_plane_ip":"192.168.105.136", "d_plane_ip":"192.168.220.4"},
                {"vnf_name":"vnf2", "vnf_image":"vyos-1.1.7.img", "user":"vyos", "pass":"vyos", "m_plane_ip":"192.168.105.135", "d_plane_ip":"192.168.220.3"}]
    target_vnf = "vnf1"
    test_kind = "BGP"
    test_list = ["summary", "neighbor", "advertised-routes", "received-routes", "routes"]
    #test_list = ["neighbor"]

    test_exec.run(vnf_list, target_vnf, test_kind, test_list)



