##!/usr/bin/python
## coding: utf8
#######################################################################
#
# Copyright (c) 2016 Okinawa Open Laboratory
# opnfv-ool-member@okinawaopenlabs.org
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
########################################################################
import os
import yaml
import time
 
import command_generator
import functest.utils.functest_logger as ft_logger
import functest.testcases.vnf.vRouter.vnf_controller.ssh_client as ssh_client
from functest.testcases.vnf.vRouter.vnf_controller.checker import Checker
from functest.testcases.vnf.vRouter.utilvnf import utilvnf

""" logging configuration """
logger = ft_logger.Logger("vRouter.vnf_controller").getLogger()

REPO_PATH = os.environ['repos_dir'] + '/functest/'
if not os.path.exists(REPO_PATH):
    logger.error("Functest repository directory not found '%s'" % REPO_PATH)
    exit(-1)

with open(os.environ["CONFIG_FUNCTEST_YAML"]) as f:
    functest_yaml = yaml.safe_load(f)
f.close()

VNF_DATA_DIR = functest_yaml.get("general").get(
    "directories").get("dir_vRouter_data") + "/"

REBOOT_WAIT = functest_yaml.get("vRouter").get("general").get("reboot_wait")

class VNF_controller():

    def __init__(self, util_info):
        logger.debug("init vnf controller")
        self.WAIT = 1
        self.COMMAND_WAIT = 1
        self.TIMEOUT = 15
        self.RETRYCOUNT = 20
        self.AFTER_REBOOT_RETRYCOUNT = 40
        self.command_gen = command_generator.Command_generator()
        self.credentials = util_info["credentials"]

        self.util = utilvnf(logger)
        self.util.set_credentials(self.credentials["username"],
                                  self.credentials["password"],
                                  self.credentials["auth_url"],
                                  self.credentials["tenant_name"],
                                  self.credentials["region_name"])


    def command_gen_from_template(self, command_file_dir, command_file_name, parameter):
        template = self.command_gen.load_template(command_file_dir, command_file_name)
        return self.command_gen.command_create(template, parameter)


    def config_vnf(self, origin_vnf, neighbor_vnf, test_cmd_file_path, parameter_file_path, prompt_file_path):
        parameter_file = open(parameter_file_path, 'r')
        parameter = yaml.safe_load(parameter_file)
        parameter_file.close() 

        parameter["ipv4_origin"] = origin_vnf["data_plane_network_ip"]

        prompt_file = open(prompt_file_path, 'r')
        prompt = yaml.safe_load(prompt_file)
        prompt_file.close()
        config_mode_prompt = prompt["config_mode"]

        ssh = ssh_client.SSH_Client(origin_vnf["floating_ip"], origin_vnf["user"], origin_vnf["pass"])

        if not ssh.connect(self.TIMEOUT, self.RETRYCOUNT):
            logger.debug("try to vm reboot.")
            self.util.reboot_v(origin_vnf["vnf_name"])
            time.sleep(REBOOT_WAIT)
            if not ssh.connect(self.TIMEOUT, self.AFTER_REBOOT_RETRYCOUNT):
                return False

        parameter["ipv4_neighbor"] = neighbor_vnf["data_plane_network_ip"]
        parameter["neighbor_ip"] = neighbor_vnf["data_plane_network_ip"]

        (test_cmd_dir, test_cmd_file) = os.path.split(test_cmd_file_path)
        commands = self.command_gen_from_template(test_cmd_dir,
                                                           test_cmd_file,
                                                           parameter)
        if not self.command_list_execute(ssh, commands, config_mode_prompt):
            ssh.close()
            return False

        ssh.close()

        return True


    def result_check(self, target_vnf, reference_vnf, check_rule_file_path_list, parameter_file_path, prompt_file_path):
        parameter_file = open(parameter_file_path, 'r')
        parameter = yaml.safe_load(parameter_file)
        parameter_file.close()

        parameter["ipv4_origin"] = target_vnf["data_plane_network_ip"]

        prompt_file = open(prompt_file_path, 'r')
        prompt = yaml.safe_load(prompt_file)
        prompt_file.close()
        terminal_mode_prompt = prompt["terminal_mode"]

        ssh = ssh_client.SSH_Client(target_vnf["floating_ip"], target_vnf["user"], target_vnf["pass"])

        if not ssh.connect(self.TIMEOUT, self.RETRYCOUNT):
            return False

        checker = Checker()

        parameter["ipv4_neighbor"] = reference_vnf["data_plane_network_ip"]
        parameter["neighbor_ip"] = reference_vnf["data_plane_network_ip"]

        status = True
        res_data_list = []
        for check_rule_file_path in check_rule_file_path_list:
            (check_rule_dir, check_rule_file) = os.path.split(check_rule_file_path)
            check_rules = checker.load_check_rule(check_rule_dir, check_rule_file, parameter)
            res = self.command_execute(ssh, check_rules["command"], terminal_mode_prompt)
            res_data_list.append(res)
            if res == None:
                status = False
                break
            checker.regexp_information(res, check_rules)
            time.sleep(self.COMMAND_WAIT)

        ssh.close()

        self.output_chcke_result_detail_data(res_data_list) 

        return status

    def output_chcke_result_detail_data(self, res_data_list):
        for res_data in res_data_list:
             logger.debug(res_data)

    def command_list_execute(self, ssh, commands, prompt):
        for command in commands:
            logger.debug("Command : " + command)
            res = self.command_execute(ssh, command, prompt)
            time.sleep(self.WAIT)
            logger.debug("Response : " + res)
            if not ssh.error_check(res):
                logger.debug("Command : " + command)
                res = self.command_execute(ssh, command, prompt)
                logger.debug("Response : " + res)
                if not ssh.error_check(res):
                    return False

        return True

    def command_execute(self, ssh, command, prompt):
        res = ssh.send(command, prompt)
        if res == None:
            logger.info("retry send command : " + command)
            res = ssh.send(command, prompt)

        return res

