##!/usr/bin/python
## coding: utf8
#######################################################################
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
#######################################################################
from jinja2 import Environment, FileSystemLoader
import functest.utils.functest_logger as ft_logger

""" logging configuration """
logger = ft_logger.Logger("vnf_test.command_gen").getLogger()

class Command_generator:
    def __init__(self):
        logger.debug("init command generator")

    def load_template(self, template_dir, template):
        env = Environment(loader=FileSystemLoader(template_dir, encoding='utf8'))
        return env.get_template(template)

    def command_create(self, template, parameter):
        commands = template.render(parameter)
        return commands.split('\n')


if __name__ == '__main__':
    command_gen = Command_generator()
    template = command_gen.load_template(
            "/home/opnfv/functest/data/vnf/opnfv-vnf-data/command_template/VyOS/bgp/",
            "bgp")

    parameter = {"have_addr":"10.0.1.0/24",
                 "have_addr2":"10.0.2.0/24",
                 "have_addr3":"10.0.3.0/24",
                 "have_addr4":"10.0.4.0/24",
                 "have_addr5":"10.0.5.0/24",
                 "have_addr6":"10.0.6.0/24",
                 "have_addr7":"10.0.7.0/24",
                 "have_addr8":"10.0.8.0/24",
                 "have_addr9":"10.0.9.0/24",
                 "have_addr10":"10.0.10.0/24",
                 "origin_as":"65001",
                 "peer_as":"65002",
                 "ipv4_origin":"192.168.220.4",
                 "ipv4_neighbor":"192.168.220.3"}
   
    commands = command_gen.command_create(template, parameter)
    for command in commands:
        print command


