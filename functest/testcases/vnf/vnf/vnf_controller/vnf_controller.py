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

import ssh_client 
import command_generator
import checker
import functest.utils.functest_logger as ft_logger


""" logging configuration """
logger = ft_logger.Logger("vnf_test.vnf_controller").getLogger()

REPO_PATH = os.environ['repos_dir'] + '/functest/'
if not os.path.exists(REPO_PATH):
    logger.error("Functest repository directory not found '%s'" % REPO_PATH)
    exit(-1)

with open(os.environ["CONFIG_FUNCTEST_YAML"]) as f:
    functest_yaml = yaml.safe_load(f)
f.close()

VNF_DATA_DIR = functest_yaml.get("general").get(
    "directories").get("dir_vnf_test_data") + "/"

class VNF_controller():

    def __init__(self):
        logger.debug("init vnf controller")
        self.command_gen = command_generator.Command_generator()

    def command_gen_from_template(self, command_file_dir, command_file_name, parameter):
        template = self.command_gen.load_template(command_file_dir, command_file_name)
        return self.command_gen.command_create(template, parameter)

    def commands_execute(self, ssh, commands):
        for command in commands:
            res = self.command_execute(ssh, command)        

    def command_execute(self, ssh, command):
        return ssh.send(command)
        #print command
        #return "test"


if __name__ == '__main__':
    vnf_ctrl = VNF_controller()

