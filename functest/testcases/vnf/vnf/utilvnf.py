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
import os
from novaclient import client as novaclient
import requests


class utilvnf:

    def __init__(self, logger=None):
        self.logger = logger
        self.username = ""
        self.password = ""
        self.auth_url = ""
        self.tenant_name = ""
        self.region_name = ""

    def set_credentials(self, username, password, auth_url, tenant_name, region_name):
        self.username = username
        self.password = password
        self.auth_url = auth_url
        self.tenant_name = tenant_name
        self.region_name = region_name


    def get_nova_credentials(self):
        d = {}
        d['version'] = '2'
        d['username'] = self.username
        d['api_key'] = self.password
        d['auth_url'] = self.auth_url
        d['project_id'] = self.tenant_name
        d['region_name'] = self.region_name
        return d

    def get_address(self, server_name, network_name ):
        creds = self.get_nova_credentials()
        nova_client = novaclient.Client(**creds)
        servers_list = nova_client.servers.list()

        for s in servers_list:
            if s.name == server_name:
                break

        address = s.addresses[network_name][0]["addr"]

        return address

    def get_blueprint_outputs(self, cfy_manager_ip, deployment_name, first_key, second_key ):
        url ="http://"+ cfy_manager_ip + "/deployments/" + deployment_name + "/outputs"

        response = requests.get(url)

        resp_data=response.json()
        data = resp_data["outputs"][first_key][second_key]
        return data
