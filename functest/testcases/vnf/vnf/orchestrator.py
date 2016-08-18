#!/usr/bin/python
# coding: utf8
#######################################################################
#
#   Copyright (c) 2015 Orange
#   valentin.boucher@orange.com
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
########################################################################
import subprocess32 as subprocess
import os
import shutil
import yaml
from git import Repo


class orchestrator:

    def __init__(self, testcase_dir, inputs={}, logger=None):
        self.testcase_dir = testcase_dir
        self.blueprint_dir = testcase_dir + 'cloudify-blueprint/'
        self.input_file = 'inputs.yaml'
        self.blueprint = False
        self.config = inputs
        self.logger = logger
        self.config['region'] = 'RegionOne'

    def set_credentials(self, username, password, tenant_name, auth_url):
        self.config['keystone_username'] = username
        self.config['keystone_password'] = password
        self.config['keystone_url'] = auth_url
        self.config['keystone_tenant_name'] = tenant_name

    def set_flavor_id(self, flavor_id):
        self.config['target_vnf_flavor_id'] = flavor_id
        self.config['reference_vnf_flavor_id'] = flavor_id

    def set_image_id(self, image_id):
        self.config['target_vnf_image_id'] = image_id
        self.config['reference_vnf_image_id'] = image_id

    def set_external_network_name(self, external_network_name):
        self.config['external_network_name'] = external_network_name

    def set_logger(self, logger):
        self.logger = logger

    def download_blueprint(self, blueprint_url,
                                 blueprint_branch):
        if self.blueprint:
            if self.logger:
                self.logger.info(
                    "blueprint is already downloaded !")
        else:
            if self.logger:
                self.logger.info(
                    "Downloading the blueprint")
            download_result = download_blueprints(
                blueprint_url,
                blueprint_branch,
                self.blueprint_dir)

            if not download_result:
                if self.logger:
                    self.logger.error("Failed to download blueprint")
                exit(-1)

    def deploy(self):
        if self.blueprint:
            if self.logger:
                self.logger.info("Writing the inputs file")
            with open(self.blueprint_dir + "inputs.yaml", "w") as f:
                f.write(yaml.dump(self.config, default_style='"'))
            f.close()

            if self.logger:
                self.logger.info("Launching the vnf deployment")
            script = "set -e; "
            script += ("source " + self.testcase_dir +
                       "venv_cloudify/bin/activate; ")
            script += "cd " + self.testcase_dir + "; "
            script += "cfy init -r; "
            script += "cd cloudify-blueprint; "
            script += "(cfy local init --install-plugins -p openstack-blueprint.yaml -i inputs.yaml && cfy local execute -w install --task-retries=9 --task-retry-interval=10 && cfy local outputs)"
#            script += ("cfy local create-requirements -o requirements.txt " +
#                       "-p openstack-manager-blueprint.yaml; ")
#            script += "pip install -r requirements.txt; "
#            script += ("cfy bootstrap --install-plugins " +
#                       "-p openstack-manager-blueprint.yaml -i inputs.yaml; ")
            cmd = "/bin/bash -c '" + script + "'"
            error = execute_command(cmd, self.logger)
            if error:
                return error

            if self.logger:
                self.logger.info("vnf is UP !")

    def undeploy(self):
        if self.logger:
            self.logger.info("Launching vnf undeployment")

        script = "source " + self.testcase_dir + "venv_cloudify/bin/activate; "
        script += "cd " + self.testcase_dir + "; "
        script += "cd cloudify-blueprint; "
        script += "(cfy local execute -w uninstall --task-retries=9 --task-retry-interval=10)"
#        script += "cfy teardown -f --ignore-deployments; "
        cmd = "/bin/bash -c '" + script + "'"
        execute_command(cmd, self.logger)

        if self.logger:
            self.logger.info(
                "vnf has been successfully removed!")

def execute_command(cmd, logger, timeout=1800):
    """
    Execute Linux command
    """
    if logger:
        logger.debug('Executing command : {}'.format(cmd))
    timeout_exception = False
    output_file = "output.txt"
    f = open(output_file, 'w+')
    try:
        p = subprocess.call(cmd, shell=True, stdout=f,
                            stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.TimeoutExpired:
        timeout_exception = True
        if logger:
            logger.error("TIMEOUT when executing command %s" % cmd)
        pass

    f.close()
    f = open(output_file, 'r')
    result = f.read()
    if result != "" and logger:
        logger.debug(result)
    if p == 0:
        return False
    else:
        if logger and not timeout_exception:
            logger.error("Error when executing command %s" % cmd)
        f = open(output_file, 'r')
        lines = f.readlines()
        result = lines[len(lines) - 3]
        result += lines[len(lines) - 2]
        result += lines[len(lines) - 1]
        return result


def download_blueprints(blueprint_url, branch, dest_path):
    if os.path.exists(dest_path):
        shutil.rmtree(dest_path)
    try:
        Repo.clone_from(blueprint_url, dest_path, branch=branch)
        return True
    except:
        return False
