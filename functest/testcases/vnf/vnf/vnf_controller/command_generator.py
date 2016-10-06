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

    parameter = {"haveaddr1":"x.x.x.x"}

    commands = command_gen.command_create(template, parameter)
    for command in commands:
        print command


