#!/usr/bin/python
# coding: utf8
#######################################################################
#
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
########################################################################

import argparse
import datetime
import json
import os
import pprint
import requests
import subprocess
import time
import yaml

import keystoneclient.v2_0.client as ksclient
import glanceclient.client as glclient
import novaclient.client as nvclient
from neutronclient.v2_0 import client as ntclient

import functest.utils.functest_logger as ft_logger
import functest.utils.functest_utils as functest_utils
import functest.utils.openstack_utils as os_utils

from orchestrator import orchestrator
from topology import topology

pp = pprint.PrettyPrinter(indent=4)


parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", help="Debug mode", action="store_true")
parser.add_argument("-r", "--report",
                    help="Create json result file",
                    action="store_true")
parser.add_argument("-n", "--noclean",
                    help="Don't clean the created resources for this test.",
                    action="store_true")
args = parser.parse_args()

""" logging configuration """
logger = ft_logger.Logger("vnf_test").getLogger()

REPO_PATH = os.environ['repos_dir'] + '/functest/'
if not os.path.exists(REPO_PATH):
    logger.error("Functest repository directory not found '%s'" % REPO_PATH)
    exit(-1)

with open(os.environ["CONFIG_FUNCTEST_YAML"]) as f:
    functest_yaml = yaml.safe_load(f)
f.close()

# Cloudify parameters
VNF_DIR = (REPO_PATH +
            functest_yaml.get("general").get("directories").get("dir_vnf_test"))
VNF_DATA_DIR = functest_yaml.get("general").get(
    "directories").get("dir_vnf_test_data") + "/"
VNF_TEST_DIR = functest_yaml.get("general").get(
    "directories").get("dir_repo_vnf_test") + "/"
DB_URL = functest_yaml.get("results").get("test_db_url")

TENANT_NAME = functest_yaml.get("vnf_test").get("general").get("tenant_name")
TENANT_DESCRIPTION = functest_yaml.get("vnf_test").get(
    "general").get("tenant_description")
IMAGES = functest_yaml.get("vnf_test").get("general").get("images")

CFY_MANAGER_BLUEPRINT = functest_yaml.get(
    "vnf_test").get("cloudify").get("blueprint")
CFY_MANAGER_REQUIERMENTS = functest_yaml.get(
    "vnf_test").get("cloudify").get("requierments")
CFY_INPUTS = functest_yaml.get("vnf_test").get("cloudify").get("inputs")


TPLGY_BLUEPRINT = functest_yaml.get("vnf_test").get("vnf_topology").get("blueprint")
TPLGY_DEPLOYMENT_NAME = functest_yaml.get("vnf_test").get(
    "vnf_topology").get("deployment-name")
TPLGY_INPUTS = functest_yaml.get("vnf_test").get("vnf_topology").get("inputs")
TPLGY_REQUIERMENTS = functest_yaml.get("vnf_test").get(
    "vnf_topology").get("requierments")

TPLGY_TGT_FLAVOR_ID =  functest_yaml.get("vnf_test").get("vnf_topology").get(
    "inputs").get("target_vnf_flavor_id")
TPLGY_TGT_IMAGE_ID =  functest_yaml.get("vnf_test").get("vnf_topology").get(
    "inputs").get("target_vnf_image_id")

TPLGY_REF_FLAVOR_ID =  functest_yaml.get("vnf_test").get("vnf_topology").get(
    "inputs").get("reference_vnf_flavor_id")
TPLGY_REF_IMAGE_ID =  functest_yaml.get("vnf_test").get("vnf_topology").get(
    "inputs").get("reference_vnf_image_id")

TPLGY_IMAGE_NAME = functest_yaml.get("vnf_test").get("vnf_topology").get(
    "requierments").get("os_image")

TPLGY_DEPLOY_NAME = functest_yaml.get("vnf_test").get("vnf_topology").get(
    "blueprint").get("deployment_name")


CFY_DEPLOYMENT_DURATION = 0
TPLGY_DEPLOYMENT_DURATION = 0



TESTCASE_START_TIME = time.time()
RESULTS = {'orchestrator': {'duration': 0, 'result': ''},
           'vnf_test': {'duration': 0, 'result': ''},
           'sig_test': {'duration': 0, 'result': ''}}


def download_and_add_image_on_glance(glance, image_name, image_url):
    dest_path = VNF_DATA_DIR + "tmp/"
    if not os.path.exists(dest_path):
        os.makedirs(dest_path)
    file_name = image_url.rsplit('/')[-1]
    if not functest_utils.download_url(image_url, dest_path):
        logger.error("Failed to download image %s" % file_name)
        return False

    image = os_utils.create_glance_image(
        glance, image_name, dest_path + file_name)
    if not image:
        logger.error("Failed to upload image on glance")
        return False

    return image


def step_failure(step_name, error_msg):
    logger.error(error_msg)
    set_result(step_name, 0, error_msg)
    status = "FAIL"
    # in case of failure starting and stoping time are not correct
    stop_time = time.time()
    if step_name == "sig_test":
        status = "PASS"
    functest_utils.push_results_to_db("functest",
                                      "vnf_test",
                                      None,
                                      TESTCASE_START_TIME,
                                      stop_time,
                                      status,
                                      RESULTS)
    exit(-1)


def set_result(step_name, duration=0, result=""):
    RESULTS[step_name] = {'duration': duration, 'result': result}


def main():

    # ###############?GENERAL INITIALISATION ################

    if not os.path.exists(VNF_DATA_DIR):
        os.makedirs(VNF_DATA_DIR)

    ks_creds = os_utils.get_credentials("keystone")
    #logger.info("keystone:"+ks_creds)
    nv_creds = os_utils.get_credentials("nova")
    #logger.info("nova:"+nv_creds)
    nt_creds = os_utils.get_credentials("neutron")
    #logger.info("neutron:"+nt_creds)

    logger.info("Prepare OpenStack plateform (create tenant and user)")
    keystone = ksclient.Client(**ks_creds)

    user_id = os_utils.get_user_id(keystone, ks_creds['username'])
    if user_id == '':
        step_failure("init", "Error : Failed to get id of " +
                     ks_creds['username'])

    tenant_id = os_utils.create_tenant(
        keystone, TENANT_NAME, TENANT_DESCRIPTION)
    if tenant_id == '':
        step_failure("init", "Error : Failed to create " +
                     TENANT_NAME + " tenant")

    roles_name = ["admin", "Admin"]
    role_id = ''
    for role_name in roles_name:
        if role_id == '':
            role_id = os_utils.get_role_id(keystone, role_name)

    if role_id == '':
        logger.error("Error : Failed to get id for %s role" % role_name)

    if not os_utils.add_role_user(keystone, user_id, role_id, tenant_id):
        logger.error("Error : Failed to add %s on tenant" %
                     ks_creds['username'])

    user_id = os_utils.create_user(
        keystone, TENANT_NAME, TENANT_NAME, None, tenant_id)
    if user_id == '':
        logger.error("Error : Failed to create %s user" % TENANT_NAME)

    logger.info("Update OpenStack creds informations")
    ks_creds.update({
        "username": TENANT_NAME,
        "password": TENANT_NAME,
        "tenant_name": TENANT_NAME,
    })

    nt_creds.update({
        "tenant_name": TENANT_NAME,
    })

    nv_creds.update({
        "project_id": TENANT_NAME,
    })

    logger.info("Upload some OS images if it doesn't exist")
    glance_endpoint = keystone.service_catalog.url_for(
        service_type='image', endpoint_type='publicURL')
    glance = glclient.Client(1, glance_endpoint, token=keystone.auth_token)

    for img in IMAGES.keys():
        image_name = IMAGES[img]['image_name']
        image_url = IMAGES[img]['image_url']

        image_id = os_utils.get_image_id(glance, image_name)

        if image_id == '':
            logger.info("""%s image doesn't exist on glance repository. Try
            downloading this image and upload on glance !""" % image_name)
            image_id = download_and_add_image_on_glance(
                glance, image_name, image_url)

        if image_id == '':
            step_failure(
                "init",
                "Error : Failed to find or upload required OS "
                "image for this deployment")

    nova = nvclient.Client("2", **nv_creds)

    logger.info("Update security group quota for this tenant")
    neutron = ntclient.Client(**nt_creds)
    if not os_utils.update_sg_quota(neutron, tenant_id, 50, 100):
        step_failure(
            "init",
            "Failed to update security group quota for tenant " + TENANT_NAME)

    logger.info("Update cinder quota for this tenant")
    from cinderclient import client as cinderclient

    creds_cinder = os_utils.get_credentials("cinder")
    cinder_client = cinderclient.Client('1', creds_cinder['username'],
                                        creds_cinder['api_key'],
                                        creds_cinder['project_id'],
                                        creds_cinder['auth_url'],
                                        service_type="volume")
    if not os_utils.update_cinder_quota(cinder_client, tenant_id, 20, 10, 150):
        step_failure(
            "init", "Failed to update cinder quota for tenant " + TENANT_NAME)

    # ###############ﾂ| CLOUDIFY INITIALISATION ################


    cfy = orchestrator(VNF_DATA_DIR, CFY_INPUTS, logger)

    cfy.set_credentials(username=ks_creds['username'], password=ks_creds[
                        'password'], tenant_name=ks_creds['tenant_name'],
                        auth_url=ks_creds['auth_url'])

    logger.info("Collect flavor id for cloudify manager server")
    nova = nvclient.Client("2", **nv_creds)

    flavor_name = "m1.large"
    flavor_id = os_utils.get_flavor_id(nova, flavor_name)
    for requirement in CFY_MANAGER_REQUIERMENTS:
        if requirement == 'ram_min':
            flavor_id = os_utils.get_flavor_id_by_ram_range(
                nova, CFY_MANAGER_REQUIERMENTS['ram_min'], 10000)

    if flavor_id == '':
        logger.error(
            "Failed to find %s flavor. "
            "Try with ram range default requirement !" % flavor_name)
        flavor_id = os_utils.get_flavor_id_by_ram_range(nova, 4000, 8196)

    if flavor_id == '':
        step_failure("orchestrator",
                     "Failed to find required flavor for this deployment")

    cfy.set_flavor_id(flavor_id)

    image_name = "centos_7"
    image_id = os_utils.get_image_id(glance, image_name)
    for requirement in CFY_MANAGER_REQUIERMENTS:
        if requirement == 'os_image':
            image_id = os_utils.get_image_id(
                glance, CFY_MANAGER_REQUIERMENTS['os_image'])

    if image_id == '':
        step_failure(
            "orchestrator",
            "Error : Failed to find required OS image for cloudify manager")

    cfy.set_image_id(image_id)

    ext_net = os_utils.get_external_net(neutron)
    if not ext_net:
        step_failure("orchestrator", "Failed to get external network")

    cfy.set_external_network_name(ext_net)

    ns = functest_utils.get_resolvconf_ns()
    if ns:
        cfy.set_nameservers(ns)


    logger.info("Prepare virtualenv for cloudify-cli")
    cmd = "chmod +x " + VNF_DIR + "create_venv.sh"
    functest_utils.execute_command(cmd, logger)
    time.sleep(3)
    cmd = VNF_DIR + "create_venv.sh " + VNF_DATA_DIR
    functest_utils.execute_command(cmd, logger)

    cfy.download_manager_blueprint(
        CFY_MANAGER_BLUEPRINT['url'], CFY_MANAGER_BLUEPRINT['branch'])

    # ###############ﾂ| CLOUDIFY DEPLOYMENT ################
    start_time_ts = time.time()
    end_time_ts = start_time_ts
    logger.info("Cloudify deployment Start Time:'%s'" % (
        datetime.datetime.fromtimestamp(start_time_ts).strftime(
            '%Y-%m-%d %H:%M:%S')))

    error = cfy.deploy_manager()
    if error:
        step_failure("orchestrator", error)

    end_time_ts = time.time()
    duration = round(end_time_ts - start_time_ts, 1)
    logger.info("Cloudify deployment duration:'%s'" % duration)
    set_result("orchestrator", duration, "")


    # ############### VNF TOPOLOGY INITIALISATION  ################
    tplgy = topology(TPLGY_INPUTS, cfy, logger)

    logger.info("Collect flavor id for all topology vm")
    nova = nvclient.Client("2", **nv_creds)


    target_vnf_flavor_id = TPLGY_TGT_FLAVOR_ID
    target_vnf_image_id  = TPLGY_TGT_IMAGE_ID
    reference_vnf_flavor_id = TPLGY_REF_FLAVOR_ID
    reference_vnf_image_id  = TPLGY_REF_IMAGE_ID


    if target_vnf_flavor_id == '':
        for requirement in TPLGY_REQUIERMENTS:
            if requirement == 'ram_min':
                target_vnf_flavor_id = os_utils.get_flavor_id_by_ram_range(
                    nova, TPLGY_REQUIERMENTS['ram_min'], 8196)
        logger.info("target_vnf_flavor_id id search set")

    tplgy.set_reference_vnf_flavor_id(target_vnf_flavor_id)

    if reference_vnf_flavor_id == '':
        for requirement in TPLGY_REQUIERMENTS:
            if requirement == 'ram_min':
                reference_vnf_flavor_id = os_utils.get_flavor_id_by_ram_range(
                    nova, TPLGY_REQUIERMENTS['ram_min'], 8196)
        logger.info("reference_vnf_flavor_id id search set")

    tplgy.set_target_vnf_flavor_id(reference_vnf_flavor_id)

    if reference_vnf_image_id == '' or  target_vnf_image_id == '' :
        image_name = TPLGY_IMAGE_NAME
        image_id = os_utils.get_image_id(glance, image_name)
        for requirement in TPLGY_REQUIERMENTS:
            if requirement == 'os_image':
                image_id = os_utils.get_image_id(
                    glance, TPLGY_REQUIERMENTS['os_image'])

    if image_id == '':
        step_failure(
            "vnt_test",
            "Error : Failed to find required OS image for cloudify manager")

    if reference_vnf_image_id == '':
        tplgy.set_reference_vnf_image_id(image_id)

    if target_vnf_image_id == '':
        tplgy.set_target_vnf_image_id(image_id)

    tplgy.set_region("RegionOne")

    ext_net = os_utils.get_external_net(neutron)
    if not ext_net:
        step_failure("vnt_test", "Failed to get external network")

    tplgy.set_external_network_name(ext_net)

    tplgy.set_credentials(username=ks_creds['username'], password=ks_creds[
                        'password'], tenant_name=ks_creds['tenant_name'],
                        auth_url=ks_creds['auth_url'])


    # ###############? VNF TOPOLOGY DEPLOYMENT ################

    start_time_ts = time.time()
    end_time_ts = start_time_ts
    logger.info("vnt_test VNF deployment Start Time:'%s'" % (
        datetime.datetime.fromtimestamp(start_time_ts).strftime(
            '%Y-%m-%d %H:%M:%S')))

    # deploy
    error = tplgy.deploy_vnf(TPLGY_BLUEPRINT, TPLGY_DEPLOY_NAME)
    if error:
        step_failure("vnt_test", error)

    end_time_ts = time.time()
    duration = round(end_time_ts - start_time_ts, 1)
    logger.info("vnt_test VNF deployment duration:'%s'" % duration)
    set_result("vnt_test", duration, "")


    # ###########?CLOUDIFY UNDEPLOYMENT #############

    cfy.undeploy_manager()

    # ############## GENERAL CLEANUP ################
    if args.noclean:
        exit(0)

    ks_creds = os_utils.get_credentials("keystone")

    keystone = ksclient.Client(**ks_creds)

    logger.info("Removing %s tenant .." % CFY_INPUTS['keystone_tenant_name'])
    tenant_id = os_utils.get_tenant_id(
        keystone, CFY_INPUTS['keystone_tenant_name'])
    if tenant_id == '':
        logger.error("Error : Failed to get id of %s tenant" %
                     CFY_INPUTS['keystone_tenant_name'])
    else:
        if not os_utils.delete_tenant(keystone, tenant_id):
            logger.error("Error : Failed to remove %s tenant" %
                         CFY_INPUTS['keystone_tenant_name'])

    logger.info("Removing %s user .." % CFY_INPUTS['keystone_username'])
    user_id = os_utils.get_user_id(
        keystone, CFY_INPUTS['keystone_username'])
    if user_id == '':
        logger.error("Error : Failed to get id of %s user" %
                     CFY_INPUTS['keystone_username'])
    else:
        if not os_utils.delete_user(keystone, user_id):
            logger.error("Error : Failed to remove %s user" %
                         CFY_INPUTS['keystone_username'])


if __name__ == '__main__':
    main()


