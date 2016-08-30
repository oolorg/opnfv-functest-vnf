##!/usr/bin/python
## coding: utf8
#######################################################################
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
########################################################################

import paramiko
import time
import logging

import functest.utils.functest_logger as ft_logger

""" logging configuration """
logger = ft_logger.Logger("vnf_test.ssh_client").getLogger()
logger.setLevel(logging.INFO)

class SSH_Client():

    def __init__(self, ip, user, password, timeout=5):
        self.ip = ip
        self.user = user
        self.password = password
        self.timeout = timeout
        self.WAIT = 1
        self.BUFFER = 10240
        self.connected = False

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())


    def connect(self, retrycount=10):
        while retrycount > 0:
            try:
                logger.info("SSH connect to %s." % self.ip)
                self.ssh.connect(self.ip,
                                 username=self.user,
                                 password=self.password,
                                 timeout=10,
                                 look_for_keys=False,
                                 allow_agent=False)

                logger.info("SSH connection established to %s." % self.ip)

                self.shell = self.ssh.invoke_shell()

                time.sleep(self.WAIT)
                #self.shell.recv(self.BUFFER)
                break
            except:
                logger.info("Waiting for %s..." % self.ip)
                time.sleep(5)
                retrycount -= 1

        if retrycount == 0:
            logger.error("Cannot establish connection to IP '%s'. Aborting" % self.ip)
            self.connected = False
            return self.connected

        self.connected = True
        return self.connected


    def send(self, cmd, res_flag=False):
        if self.connected == True:
            logger.debug("Commandset : '%s'", cmd)
            time.sleep(1)
            self.shell.send(cmd + '\n')
            if cmd == "commit":
                time.sleep(10)  
            else:
                time.sleep(self.WAIT)
            if res_flag:
                return self.shell.recv(self.BUFFER)
            else:
                return ""
        else:
            logger.error("Cannot connected to IP '%s'." % self.ip)
            return None

    def close(self):
        self.shell.close() 
        self.ssh.close()
        logger.debug("SSH connection closed to %s." % self.ip)


if __name__ == '__main__':
    ssh_local = SSH_Client('192.168.105.136', 'vyos', 'vyos')
    ssh_local.connect()

    response = ssh_local.send("set terminal length 0")
    print response

    response = ssh_local.send("show interfaces")
    print response

    ssh_local.close()

