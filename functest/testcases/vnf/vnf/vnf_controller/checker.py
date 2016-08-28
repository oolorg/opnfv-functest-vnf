##!/usr/bin/python
## coding: utf8
#######################################################################
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
#######################################################################
import json
import re
from jinja2 import Environment, FileSystemLoader
import functest.utils.functest_logger as ft_logger

""" logging configuration """
logger = ft_logger.Logger("vnf_test.cecker").getLogger()

class Checker:
    def __init__(self):
        logger.debug("init cecker")

    def load_check_rule(self, rule_file_dir, rule_file_name, parameter):
        env = Environment(loader=FileSystemLoader(rule_file_dir, encoding='utf8'))
        check_rule_template = env.get_template(rule_file_name)
        check_rule =  check_rule_template.render(parameter)
        check_rule_data = json.loads(check_rule)
        #check_rule = rule_file_dir + "/" + rule_file_name
        #file = open(check_rule, 'r')
        ##print file.read()
        #check_rule_data = json.load(file)
        #file.close()
        #return check_rule_data["rules"]
        return check_rule_data


    def regexp_information(self, response, rules):
        status = False
        for rule in rules:
            match = re.search(rule["regexp"] , response)
            if match == None:
                logger.error("Nothing Match Data")
                logger.error("rule     : " + rule["regexp"])
                logger.error("response : " + response)
                return False

            if not match.group(1) == rule["result"] :
                logger.info("check NG")
                status = False
            else:
                logger.info("check OK")
                status = True

        return status


if __name__ == '__main__':
    checker = Checker()

    data = "Total number of neighbors 1"

    check_rules = checker.load_check_rule("/home/opnfv/functest/data/vnf/opnfv-vnf-data/command_template/VyOS/bgp/check_rule", "summary")
    checker.regexp_information(data, check_rules)




