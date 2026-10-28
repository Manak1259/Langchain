#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Manak Sahu"
__email__  = "msahu2@infoblox.com"

#############################################################################
# Grid Set up required:                                                     #
#  1. Grid Master (SA,HA)  - 9.0.4 build                                    #
#  2. Licenses : DNS, DHCP, Grid, NIOS                                      #
#                                                                           #
#############################################################################

#### REQUIRED LIBRARIES ####
import os
import pexpect
import paramiko
import config
import pytest
import unittest
import logging
import json
from time import sleep
import ib_utils.ib_NIOS as ib_NIOS
import sys
import ib_utils.ib_NIOS as ib_NIOS
import ib_utils.common_utilities as common_util
import re


#####################################################################################################
#STEPS TO REPRODUCE:                                                                               
#1. Create an authoritative zone 'test.com' and assign it to Grid Master.                          
#2.Execute "query_fqdn_on_member" function with mandatory field "fqdn" with member as GM               
#####################################################################################################


logging.basicConfig(format='%(asctime)s - %(name)s(%(process)d) - %(levelname)s - %(message)s',filename="niosspt_12961.log" ,level=logging.DEBUG,filemode='w')

def display_message(x=""):
    # Additional function used to log and print with a single line
    logging.info(x)
    print(x)

def Restart_services( ):

        display_message("\n========================================================\n")
        display_message("Restarting Services")
        display_message("\n========================================================\n")

        grid = ib_NIOS.wapi_request('GET', object_type="grid")
        ref = json.loads(grid)[0]['_ref']
        request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus")
        restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices")
        sleep(35)

        display_message("\n***************. Services Restarted successfully.***************\n")


def ospf_ipv6_configuration():
    print("\n============================================\n")
    print("create OSFP IVP4 & IPV6 for member ")
    print("\n============================================\n")

    get_ref = ib_NIOS.wapi_request('GET', object_type='member?_return_fields=additional_ip_list')
    print(get_ref)
    for ref in json.loads(get_ref):

        data={"ospf_list": [
            {
                "area_id": "0.0.0.12",
                "area_type": "STANDARD",
                "authentication_type": "NONE",
                "auto_calc_cost_enabled": True,
                "cost": 1,
                "dead_interval": 40,
                "enable_bfd": False,
                "hello_interval": 10,
                "interface": "LAN_HA",
                "is_ipv4": True,
                "key_id": 1,
                "retransmit_interval": 5,
                "transmit_delay": 1
            },
            {
                "area_id": "0.0.0.12",
                "area_type": "STANDARD",
                "authentication_type": "NONE",
                "auto_calc_cost_enabled": True,
                "cost": 1,
                "dead_interval": 40,
                "enable_bfd": False,
                "hello_interval": 10,
                "interface": "LAN_HA",
                "is_ipv4": False,
                "key_id": 1,
                "retransmit_interval": 5,
                "transmit_delay": 1
            }
        ]}

        response = ib_NIOS.wapi_request('PUT', ref=ref['_ref'], fields=json.dumps(data),grid_vip=config.grid_vip)

        print(response)
        if type(response) == tuple:
            if response[0]==400 or response[0]==401:
                print("Failure: Configure OSPF ipv6 for advertising")
                assert False
        else:
            print("Success: Configure OSPF ipv6 for advertising")
            assert True

def convert_ipv6_to_uppercase(ipv6_address):
    # Split the address into its components
    components = ipv6_address.split(':')
    
    # Convert each component to uppercase
    uppercase_components = [component.upper() for component in components]
    
    # Join the components back together with colons
    uppercase_ipv6 = ':'.join(uppercase_components)
    
    return uppercase_ipv6
	
def anycast_ipv6_configuration():

    print("\n============================================\n")
    print("Configuring IVP4 & IPV6 Anycast IP for member")
    print("\n============================================\n")

    get_ref = ib_NIOS.wapi_request('GET', object_type='member?_return_fields=additional_ip_list')
    print(get_ref)
    for ref in json.loads(get_ref):
        data={"config_addr_type": "BOTH",
        "additional_ip_list": [
            {
                "anycast": True,
                "enable_bgp": False,
                "enable_ospf": True,
                "interface": "LOOPBACK",
                "ipv4_network_setting": {
                    "address": "1.3.3.3",
                    "dscp": 0,
                    "primary": False,
                    "subnet_mask": "255.255.255.255",
                    "use_dscp": False
                }
            },
            {
                "anycast": True,
                "enable_bgp": False,
                "enable_ospf": True,
                "interface": "LOOPBACK",
                "ipv6_network_setting": {
                    "cidr_prefix": 128,
                    "dscp": 0,
                    "enabled": True,
                    "primary": False,
                    "use_dscp": False,
                    "virtual_ip": "3333::3331"
                }
            }
        ]}

        response = ib_NIOS.wapi_request('PUT', ref=ref['_ref'], fields=json.dumps(data))
        print(response)

        if type(response) == tuple:
            if response[0]==400 or response[0]==401:
                print("Failure: Anycast configuration")
                assert False
        else:
            print("Success: Anycast configuration")
            sleep(90)
            check_able_to_login_appliances(config.grid_vip)

    sleep(30)
    check_able_to_login_appliances(config.grid_vip)
    sleep(30)
    print("\n============================================\n")
    print("Configure IVP4 & IPV6 anycast IP for DNS")
    print("\n============================================\n")

    get_ref = ib_NIOS.wapi_request('GET', object_type='member:dns?_return_fields=additional_ip_list_struct')

    print(get_ref)
    for ref in json.loads(get_ref):
        print(ref['_ref'])
        data={"use_lan_ipv6_port":True,
        "additional_ip_list_struct": [
            {
                "ip_address": "1.3.3.3"
            },
            {
                "ip_address": "3333::3331"
            }
        ]}
        response = ib_NIOS.wapi_request('PUT', ref=ref['_ref'], fields=json.dumps(data))
        print(response)

        if type(response) == tuple:
            if response[0]==400 or response[0]==401:
                print("Failure: Configure IPV6 anycast IP for member DNS")
                assert False
        else:
            print("Success: Configure IPV6 anycast IP for member DNS")
            assert True

def check_able_to_login_appliances(ip_address=config.grid_vip):
    # remove()
    # for i in range(5):
    try:
        child = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@'+ip_address)
        child.logfile=sys.stdout
        child.expect('password:')
        child.sendline('infoblox')
        child.expect('Infoblox >')

        child.sendline('show version')

        child.expect('>')

        if 'Version :' in child.before:
            child.close()
            print("\n************Appliances is Working************\n ")
            sleep(60)
            assert True
        else:

            raise(Exception)

    except Exception as e:
        child.close()
        print(e)
        sleep(20)
        print("Failure")

        assert False

def Promoting_Member_as_Master(ip_address):
                try:
                        child = pexpect.spawn('ssh -o StrictHostKeyChecking=no admin@'+ip_address)
                        child.logfile=sys.stdout
                        child.expect('password:')
                        child.sendline('infoblox')
                        child.expect('Infoblox >')
                        child.sendline('set promote_master')
                        child.expect(':')
                        child.sendline('y')
                        child.expect(':')
                        child.sendline('10')
                        child.expect(':')
                        child.sendline('y')
                        child.expect(':')
                        child.sendline('y')
                        sleep(300)
                        child.expect('closed.')
                except Exception as error_message:
                        print(error_message)
                        assert False
                      

def Create_validate_auth_zone():
      
        display_message("\n========================================================\n")
        display_message("Creating an Authoratative zone")
        display_message("\n========================================================\n")

        data = {"fqdn": config.grid1_master_zone,"grid_primary": [{"name": config.grid1_master_fqdn}, {"name": config.grid1_member1_fqdn}, {"name": config.grid1_member2_fqdn} ]}
        response = ib_NIOS.wapi_request('POST', object_type="zone_auth", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        display_message(response)
        print("zone created :", response)
        if response[0]==400 or response[0]==401 or response[0]==404 or response[0]==500:
                display_message("FAILURE: Create authoratative zone.")
                assert False
        else:
                display_message()
                display_message("\n--------------------------------------------------------\n")
                display_message("Validating Authoratative zone ")
                display_message("\n--------------------------------------------------------\n")

        response = ib_NIOS.wapi_request('GET', object_type="zone_auth?fqdn="+config.grid1_master_zone+"", grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)[0]
        display_message(response)

        if config.grid1_master_zone in response['_ref']:
                display_message(response["_ref"])
                display_message("SUCCESS: Authoratative Zone "+config.grid1_master_zone+" was created!")

                assert True
        else:
                display_message("FAILURE: Authoratative Zone "+config.grid1_master_zone+"  was NOT created!")
                assert False
                
        Restart_services()
        sleep(90)
        
def Add_loopback_ip_member1():

        display_message("\n========================================================\n")
        display_message("Adding loopback IP address to member")
        display_message("\n========================================================\n")
        get_ref = ib_NIOS.wapi_request('GET', object_type='member')
        logging.info(get_ref)
        res = json.loads(get_ref)
        print("response is", res)
        ref1 = json.loads(get_ref)[1]['_ref']
        print("reference is" , ref1)
        print(get_ref)
        print(get_ref[-1])
        print(get_ref[-2])
        # print(type(get_ref))
        for ref in json.loads(get_ref):
            data={"additional_ip_list": [
                {
                    "anycast": False,
                    "enable_bgp": False,
                    "enable_ospf": False,
                    "interface": "LOOPBACK",
                    "ipv4_network_setting": {
                        "address": "1.1.1.1",
                        "dscp": 0,
                        "primary": False,
                        "subnet_mask": "255.255.255.255",
                        "use_dscp": False
                    }
                }
            ]}
            # print(get_ref[-1])
            # print(get_ref[-2])
            # print(type(get_ref))
            response = ib_NIOS.wapi_request('PUT', ref=ref1, fields=json.dumps(data))
            print(response)
            if type(response) == tuple:
                if response[0]==400 or response[0]==401:
                    print("Failure: configure loopback IP address")
                    assert False
            else:
                print("Success: configure loopback IP address")
                sleep(90)

def master_member_DNS_Interface_Update():

        display_message("\n========================================================\n")
        display_message("Updating master and member DNS interface")
        display_message("\n========================================================\n")
        get_ref = ib_NIOS.wapi_request('GET', object_type='member:dns?_return_fields=use_lan2_port')
        logging.info(get_ref)
        # res = json.loads(get_ref)
        # print("response is", res)
        ref1 = json.loads(get_ref)[0]['_ref']
        ref2 = json.loads(get_ref)[1]['_ref']
        print(ref2)
        data1={"use_lan2_port": True, "use_lan_port": True, "use_mgmt_port": True, "use_mgmt_ipv6_port": True, "use_lan_ipv6_port": True}
        data2={ "use_lan_port": True, "use_mgmt_port": True, "use_mgmt_ipv6_port": True, "use_lan_ipv6_port": True}
        response1 = ib_NIOS.wapi_request('PUT', ref=ref1, fields=json.dumps(data1))
        response2 = ib_NIOS.wapi_request('PUT', ref=ref2, fields=json.dumps(data2))

        # response = ib_NIOS.wapi_request('PUT', ref=ref2, fields=json.dumps(data))
        # print("first response is ",response1)
        print("first response is ",response1)
        if type(response1) == tuple:
            if response1[0]==400 or response1[0]==401:
                print("Failure: DNS interfaces not Updated Successfully in Grid master")
                assert False
        else:
            print("Success: DNS interfaces Updated Successfully in Grid master")

        if type(response2) == tuple:
            if response2[0]==400 or response2[0]==401:
                print("Failure: DNS interfaces not Updated Successfully in Grid member")
                assert False
        else:
            print("Success: DNS interfaces Updated Successfully in Grid member")
        #     sleep(90)
        Restart_services()

def dns_member_all_record_creation():

        display_message("\n========================================================\n")
        display_message("Creating all type or records to Authoratative zone")
        display_message("\n========================================================\n")
        data={"name":""+config.grid1_master_a_record+"."+config.grid1_master_zone+"","ipv4addr":"3.3.3.3","view": "default"}
        response1 = ib_NIOS.wapi_request('POST', object_type="record:a",fields=json.dumps(data))

        data={"name":""+config.grid1_master_aaaa_record+"."+config.grid1_master_zone+"","ipv6addr": "23::","view": "default"}
        response2 = ib_NIOS.wapi_request('POST', object_type="record:aaaa",fields=json.dumps(data))
        data={"name":""+config.grid1_master_cname_record+"."+config.grid1_master_zone+"","canonical": "test.com","view": "default"}
        response3 = ib_NIOS.wapi_request('POST', object_type="record:cname",fields=json.dumps(data))
        data={"name":""+config.grid1_master_dname_record+"."+config.grid1_master_zone+"","target": "test","view": "default"}
        response4 = ib_NIOS.wapi_request('POST', object_type="record:dname",fields=json.dumps(data))
        data={"name": ""+config.grid1_master_naptr_record+"."+config.grid1_master_zone+"","order": 10,"preference": 10,"view":"default","replacement": "arec.outbound_test.com","services": "http+E2U"}
        response5 = ib_NIOS.wapi_request('POST', object_type="record:naptr",fields=json.dumps(data))
        data={"name":config.grid1_master_zone,"nameserver":config.grid1_master_vip,"addresses":[{"address":"4.3.2.1"}]}
        response6 = ib_NIOS.wapi_request('POST', object_type="record:ns",fields=json.dumps(data))
        data = {"ptrdname": "www.infoblox.com","name": ""+config.grid1_master_ptr_record+"."+config.grid1_master_zone+"","view": "default"}
        response7 = ib_NIOS.wapi_request('POST', object_type="record:ptr",fields=json.dumps(data))

        data = {"name": ""+config.grid1_master_srv_record+"."+config.grid1_master_zone+"","port": 22,"priority": 0,"target": "test.com","view": "default","weight": 0}
        response8 = ib_NIOS.wapi_request('POST', object_type="record:srv",fields=json.dumps(data))

        data = {"name": ""+config.grid1_master_txt_record+"."+config.grid1_master_zone+"","text": "testing","view": "default"}
        response9 = ib_NIOS.wapi_request('POST',object_type="record:txt",fields=json.dumps(data))
        response = [response1,response2,response3,response4,response5,response6,response7,response8,response9]
        i=0
        for i in range(len(response)):
                actual_response=json.loads(response[i])
                if type(actual_response) == tuple:
                        if actual_response[0]==400 or actual_response[0]==401:
                                display_message("Failure: "+actual_response+" record not created successfully")
                                assert False
                        else:
                                display_message("Success: "+actual_response+" record created successfully")
                        assert True

def Make_normal_member_as_GMC_member_and_validate_the_GMC_member():
            
        print("\n============================\n")
        print("Make normal member as GMC member")
        print("================================")
        get_ref = ib_NIOS.wapi_request('GET', object_type="member", grid_vip=config.grid_vip)
        ref = json.loads(get_ref)[1]['_ref']
        print(ref)
        data = {"master_candidate": True}
        output = ib_NIOS.wapi_request('PUT',ref=ref,fields=json.dumps(data),grid_vip=config.grid_vip)
        print(output)
        get_ref = ib_NIOS.wapi_request('GET', object_type="member", grid_vip=config.grid_vip)
        ref = json.loads(get_ref)[1]['_ref']
        print(ref)	
        gmc_output = ib_NIOS.wapi_request('GET',ref=ref,params="?_return_fields=master_candidate")
        print(gmc_output)
        if '"master_candidate": true' in gmc_output:
            assert True
        else:
            assert False
        sleep(600)


def Adding_forwarder_grid_DNS():

        display_message("\n========================================================\n")
        display_message("Adding forwarder ip to grid")
        display_message("\n========================================================\n")
        print("Add DNS forwarder : 10.30.16.160")
        grid_dns_ref = ib_NIOS.wapi_request('GET', object_type='grid:dns')
        data = {"forwarders":["10.30.16.160"]}
        response = ib_NIOS.wapi_request('PUT', ref=json.loads(grid_dns_ref)[0]['_ref'], fields=json.dumps(data))

        if type(response) == tuple:
            if response[0]==400 or response[0]==401:
                print("Failure: Adding DNS Forwarder")
                assert False
        # Restart_services()

        data = {"forward_only":True}
        response = ib_NIOS.wapi_request('PUT', ref=json.loads(grid_dns_ref)[0]['_ref'], fields=json.dumps(data))
        Restart_services()
def Start_DNS_Service():
            logging.info("Start DNS Service")
            get_ref = ib_NIOS.wapi_request('GET', object_type="member:dns")
            logging.info(get_ref)
            res = json.loads(get_ref)
            for i in res:
                    logging.info("Modify a enable_dns")
                    data = {"enable_dns": True}
                    response = ib_NIOS.wapi_request('PUT', ref=i['_ref'], fields=json.dumps(data))
                    print(response)

            logging.info(response)
            read  = re.search(r'200',response)
            for read in  response:
                    assert True
            print("DNS Service Started")
    
class NIOS_10242(unittest.TestCase):
    @pytest.mark.run(order=1)
    def test_001_validate_fqdn_field(self):
        Start_DNS_Service()
        Create_validate_auth_zone()
        logging.info("Validate fqdn field")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and config.loopback_ip in response['source_address']:
                display_message(response["result_text"])
                display_message(response['source_address'])
                display_message("SUCCESS: fqdn field is executed with expected "+config.loopback_ip+" source address")
                assert True
        else:
                display_message("FAILURE: fqdn field is not executed with expected "+config.loopback_ip+" source address")
                assert False

    @pytest.mark.run(order=2)
    def test_002_validate_fqdn_field_with_member_as_GM(self):
        master_member_DNS_Interface_Update()
        logging.info("Validating fqdn field with  grid ip")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone,"member": config.grid1_master_fqdn}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and config.loopback_ip in response['source_address']:
                display_message(response["result_text"])
                display_message(response['source_address'])
                display_message("SUCCESS: fqdn with member as GM is executed with expected "+config.loopback_ip+" source address")
                assert True
        else:
                display_message("FAILURE: fqdn with member as GM is Not executed without expected "+config.loopback_ip+" source address")
                assert False
    @pytest.mark.run(order=3)
    def test_003_validate_fqdn_member_as_GM_Nameserver_as_masterlanip(self):
        logging.info("Validating fqdn field with name server and lanip")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone,"member": config.grid1_master_fqdn, "name_server": config.grid1_master_vip}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and config.loopback_ip in response['source_address']:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn with member as GM is executed with expected "+config.loopback_ip+" source address and name server as master lanip")
                assert True
        else:
                display_message("FAILURE: fqdn with member as GM is Not executed with expected "+config.loopback_ip+" source address and name server as master lanip")
                assert False

    @pytest.mark.run(order=4)
    def test_004_validate_fqdn_member_as_GM_Nameserver_as_master_mgmtip(self):
        logging.info("Validating fqdn field with name server and mgmt ip")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone,"member": config.grid1_master_fqdn, "name_server": config.grid1_master_mgmt_vip}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and "any" in response['source_address']:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn with member as GM is executed with expected  source address and name server as master mgmtip")
                assert True
        else:
                display_message("FAILURE: fqdn with member as GM is Not executed with expected  source address and name server as master mgmtip")
                assert False

    @pytest.mark.run(order=5)
    def test_005_validate_fqdn_member_as_GM_Nameserver_as_memberlanip(self):
        logging.info("Validating fqdn field with name server and member lanip")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone,"member": config.grid1_master_fqdn, "name_server": config.grid1_member1_vip}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and "any" in response['source_address']:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn with member as GM is executed with expected source address and name server as member lanip")
                assert True
        else:
                display_message("FAILURE: fqdn with member as GM is Not executed with expected source address and name server as master lanip")
                assert False
				

    @pytest.mark.run(order=6)
    def test_006_validate_fqdn_member_as_GM_Nameserver_as_memberlanip_with_recordA(self):
        dns_member_all_record_creation()
        logging.info("Validating fqdn field with name server and lanip with record A")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : ""+config.grid1_master_a_record+"."+config.grid1_master_zone+"","member": config.grid1_master_fqdn, "name_server": config.grid1_member1_vip,"record_type":"A"}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and "any" in response['source_address']:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn with member as member1 is executed with expected name server as member LAN ip and Record Type A")
                assert True
        else:
                display_message("FAILURE: fqdn with member as member1 is Not executed with expected name server as member LAN ip and Record Type A")
                assert False
				
				
    @pytest.mark.run(order=7)
    def test_007_validate_fqdn_recursivequery_false(self):
        logging.info("Validating fqdn field with recursive query false")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : ""+config.grid1_master_a_record+"."+config.grid1_master_zone+"","member": config.grid1_master_fqdn, "name_server": config.grid1_member1_vip,"recursive_query": False}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" and "norecurse" in response["result_text"] and "any" in response['source_address']:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn member with host name is executed with recursive query as false")
                assert True
        else:
                display_message("FAILURE: fqdn member with host name is Not executed with recursive query as false")
                assert False
    @pytest.mark.run(order=8)
    def test_008_validate_fqdn_new_rfe_object_sourceip_as_masterlanip(self):
        logging.info("Validating fqdn field with new rfe object and master lanip")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone,"source_ip": config.grid1_master_vip}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and config.grid1_master_vip in response['source_address']:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn field is executed with "+config.grid1_master_vip+"  source address as master LAN IP")
                assert True
        else:
                display_message("FAILURE: fqdn field is Not executed with "+config.grid1_master_vip+" source address as master LAN IP")
                assert False
        
    @pytest.mark.run(order=9)
    def test_009_validate_fqdn_source_mastermgmtip(self):
        logging.info("Validating fqdn field with master master mgmt ip")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone,"source_ip": config.grid1_master_mgmt_vip}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and config.grid1_master_mgmt_vip in response['source_address']:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn field is executed with source address as "+config.grid1_master_mgmt_vip+" MGMT IP")
                assert True
        else:
                display_message("FAILURE: fqdn field is Not executed with source address as "+config.grid1_master_mgmt_vip+" MGMT IP")
                assert False

    @pytest.mark.run(order=10)
    def test_010_validate_fqdn_source_masterlan2_ip(self):
        logging.info("Validating fqdn field with master master lan2 ip")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        print(ref)
        data = {"fqdn" : config.grid1_master_zone,"source_ip": config.grid1_master_lan2}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        # print(response)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and config.grid1_master_lan2 in response['source_address']:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn field is executed with source address as master "+config.grid1_master_lan2+" LAN2 IP")
                assert True
        else:
                display_message("FAILURE: fqdn field is Not executed with source address as master "+config.grid1_master_lan2+" LAN2 IP")
                assert False


    @pytest.mark.run(order=11)
    def test_011_validate_digquery_gridmaster_Lanip_Lan2ip_Mgmtip(self):
        logging.info("Perform dig query with master lan, lan2 and mgmt ip address")
        child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@'+config.grid1_master_mgmt_vip)
        child.logfile=sys.stdout
        child.expect('#')
        record_data =""+config.grid1_master_a_record+"."+config.grid1_master_zone+""
        child.sendline("dig @"+config.grid1_master_vip+" "+record_data+" -b "+config.grid1_master_mgmt_vip+"")
        child.expect("#")
        output1=child.before
        display_message(output1)
        child.expect('#')
        child.sendline("dig @"+config.grid1_master_lan2+" "+record_data+" -b "+config.grid1_master_mgmt_vip+"")
        child.expect('#')
        output2 = child.before
        child.expect('#')
        child.sendline("dig @"+config.grid1_master_mgmt_vip+" "+record_data+" -b "+config.grid1_master_mgmt_vip+"")
        child.expect('#')
        output3 = child.before
        child.close()

        if config.grid1_dig_expected_ip in output1:
                display_message(output1)
                display_message("SUCCESS: fqdn field is executed with dig query for grid master cli LAN IP "+config.grid1_master_vip+"")
                assert True
        else:
                display_message("FAILURE: fqdn field is Not executed with dig query for grid master cli LAN IP "+config.grid1_master_vip+"")
                assert False

        if config.grid1_dig_expected_ip in output2:
                display_message(output2)
                display_message("SUCCESS: fqdn field is executed with dig query for grid master cli LAN2 IP "+config.grid1_master_lan2+"")
                assert True
        else:
                display_message("FAILURE: fqdn field is Not executed with dig query for grid master cli LAN2 IP "+config.grid1_master_lan2+"")
                assert False

        if config.grid1_dig_expected_ip in output3:
                display_message(output3)
                display_message("SUCCESS: fqdn field is executed with dig query for grid master cli MGMT IP "+config.grid1_master_mgmt_vip+" ")
                assert True
        else:
                display_message("FAILURE: fqdn field is Not executed with dig query for grid master cli MGMT IP "+config.grid1_master_mgmt_vip+" ")
                assert False
        
    @pytest.mark.run(order=12)
    def test_012_validate_fqdn_sourceip_member_lanip(self):
        logging.info("Validating fqdn field with member lan ip")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone,"source_ip": config.grid1_member1_vip,"member": config.grid1_member1_fqdn}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and config.grid1_member1_vip in response['source_address']:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn is executed with souce address as member's LAN IP "+config.grid1_member1_vip+" and member as Hostname of member")
                assert True
        else:
                display_message("FAILURE: fqdn is Not executed with souce address as member's LAN IP "+config.grid1_member1_vip+" and member as Hostname of member")
                assert False
    @pytest.mark.run(order=13)
    def test_013_validate_fqdn_sourceip_mgmtipmember(self):
        logging.info("Validating fqdn field with member mgmt ip")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone,"source_ip": config.grid1_member1_mgmt_ip,"member": config.grid1_member1_fqdn}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and config.grid1_member1_mgmt_ip in response['source_address']:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn is executed with souce address as member's MGMT IP and member as Hostname of member")
                assert True
        else:
                display_message("FAILURE: fqdn is Not executed with souce address as member's MGMT IP and member as Hostname of member")
                assert False
        
    @pytest.mark.run(order=14)
    def test_014_validate_fqdn_sourceip_lan2ipmember(self):
        logging.info("Validating fqdn field with member lan2 ip")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone,"source_ip": config.grid1_member1_lan2,"member": config.grid1_member1_fqdn}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and config.grid1_member1_lan2 in response['source_address']:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn is executed with souce address as member's LAN2 IP and member as Hostname of member")
                assert True
        else:
                display_message("FAILURE: fqdn is Not executed with souce address as member's LAN2 IP and member as Hostname of member")
                assert False
    @pytest.mark.run(order=15)
    def test_015_validate_fqdn_sourceip_vip_HA_HAlanipnameserver(self):
        logging.info("Validating fqdn field with HA member lan ip")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone,"member": config.grid1_member2_fqdn,"name_server":config.grid1_member2_vip,"source_ip": config.grid1_member2_vip}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and config.grid1_member2_vip in response['source_address']:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn is executed with souce address as member's VIP of HA member and member as Hostname of member and nameserver as HA LAN VIP")
                assert True
        else:
                display_message("FAILURE: fqdn is Not executed with souce address as member's VIP of HA member and member as Hostname of member and nameserver as HA LAN VIP")
                assert False

    @pytest.mark.run(order=16)
    def test_016_validate_fqdn_sourceip_activememberipha_halanipnameserver(self):
        logging.info("Validating fqdn field with HA active member lan ip")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone,"member": config.grid1_member2_fqdn,"name_server":config.grid1_member2_vip,"source_ip": config.grid1_member2_ha_activeip}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and config.grid1_member2_ha_activeip in response['source_address']:        
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn is executed with souce address as member's ActiveIP of HA member and member as Hostname of member and nameserver as HA LAN VIP")
                assert True
        else:
                display_message("FAILURE: fqdn is Not executed with souce address as member's ActiveIP of HA member and member as Hostname of member and nameserver as HA LAN VIP")
                assert False

    @pytest.mark.run(order=17)
    def test_017_validate_fqdn_sourceip_passive_member_ip_ha_lan_ip_nameserver(self):
        logging.info("Validating fqdn field with HA passive member lan ip")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone,"member": config.grid1_member2_fqdn,"name_server":config.grid1_member2_vip,"source_ip": config.grid1_member2_ha_passiveip}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response = response[1]
        print("output is :",response)
        print(type(response))
        
        
        if "Source IP address has not been configured on the specified grid member" in response:
                display_message("SUCCESS: fqdn is executed with souce address as member's PassiveIP of HA member and member as Hostname of member and nameserver as HA LAN VIP")
                assert True
        else:
                display_message("FAILURE: fqdn is Not executed with souce address as member's PassiveIP of HA member and member as Hostname of member and nameserver as HA LAN VIP")
                assert False

    @pytest.mark.run(order=18)
    def test_018_validate_fqdn_sourceip_mgmt_ha_memberip_halanip_nameserver_recordtype_a(self):
        logging.info("Validating fqdn field with HA member lan ip with record a")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone,"member": config.grid1_member1_fqdn,"name_server":config.grid1_member1_vip,"source_ip": config.grid1_master_mgmt_vip, "record_type": "A"}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        display_message(response)
        print(type(response[1]))
        if "Source IP address has not been configured on the specified grid member" in response[1]:
                display_message("SUCCESS: fqdn is executed with souce address as MGMT ip of master and member as HA member and name server as member's LAN IP ,with A record type")
                assert True
        else:
                display_message("FAILURE: fqdn is Not  executed with souce address as MGMT ip of master and member as HA member and name server as member's LAN IP ,with A record type")
                assert False

    @pytest.mark.run(order=19)
    def test_019_validate_fqdn_sourceip_anyrecord(self):
        logging.info("Validating fqdn field with ANY record")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : ""+config.grid1_master_aaaa_record+"."+config.grid1_master_zone+"","member": config.grid1_member1_fqdn,"name_server":config.grid1_member1_vip,"source_ip": config.grid1_member1_mgmt_ip, "record_type": "ANY"}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        if "NOERROR" in response["result"] and config.grid1_member1_mgmt_ip in response['source_address']:
                display_message("SUCCESS: fqdn field is executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with AANY record type")
                assert True
        else:
                display_message("FAILURE: fqdn field is Not executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with AANY record type")
                assert False

    @pytest.mark.run(order=20)
    def test_020_validate_fqdn_sourceip_AAAArecord(self):
        logging.info("Validating fqdn field with AAAA record")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" :  ""+config.grid1_master_aaaa_record+"."+config.grid1_master_zone+"","member": config.grid1_member1_fqdn,"name_server":config.grid1_member1_vip,"source_ip": config.grid1_member1_mgmt_ip, "record_type": "AAAA"}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        if "NOERROR" in response["result"] and config.grid1_member1_mgmt_ip in response['source_address']:
                display_message("SUCCESS: fqdn field is executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with AAAA record type")
                assert True
        else:
                display_message("FAILURE: fqdn field is Not executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with AAAA record type")
                assert False

    @pytest.mark.run(order=21)
    def test_021_validate_fqdn_sourceip_CNAMErecord(self):
        logging.info("Validating fqdn field with CNAME record")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" :  ""+config.grid1_master_cname_record+"."+config.grid1_master_zone+"","member": config.grid1_member1_fqdn,"name_server":config.grid1_member1_vip,"source_ip": config.grid1_member1_mgmt_ip, "record_type": "CNAME"}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "NOERROR" in response["result"] and config.grid1_member1_mgmt_ip in response['source_address']:
                display_message("SUCCESS: fqdn field is executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with CNAME record type")
                assert True
        else:
                display_message("FAILURE: fqdn field is Not executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with CNAME record type")
                assert False

    @pytest.mark.run(order=22)
    def test_022_validate_fqdn_sourceip_DNAMErecord(self):
        logging.info("Validating fqdn field with DNAME record")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" :  ""+config.grid1_master_dname_record+"."+config.grid1_master_zone+"","member": config.grid1_member1_fqdn,"name_server":config.grid1_member1_vip,"source_ip": config.grid1_member1_mgmt_ip, "record_type": "DNAME"}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "NOERROR" in response["result"] and config.grid1_member1_mgmt_ip in response['source_address']:
                display_message("SUCCESS: fqdn field is executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with DNAME record type")
                assert True
        else:
                display_message("FAILURE: fqdn field is Not executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with DNAME record type")
                assert False


    @pytest.mark.run(order=23)
    def test_023_validate_fqdn_sourceip_NAPTRrecord(self):
        logging.info("Validating fqdn field with NAPTR record")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" :  ""+config.grid1_master_naptr_record+"."+config.grid1_master_zone+"","member": config.grid1_member1_fqdn,"name_server":config.grid1_member1_vip,"source_ip": config.grid1_member1_mgmt_ip, "record_type": "NAPTR"}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "NOERROR" in response["result"] and config.grid1_member1_mgmt_ip in response['source_address']:
                display_message("SUCCESS: fqdn field is executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with NAPTR record type")
                assert True
        else:
                display_message("FAILURE: fqdn field is Not executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with NAPTR record type")
                assert False

    @pytest.mark.run(order=24)
    def test_024_validate_fqdn_sourceip_NSRrecord(self):
        logging.info("Validating fqdn field with NSR record")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" :  ""+config.grid1_master_ns_record+"."+config.grid1_master_zone+"","member": config.grid1_member1_fqdn,"name_server":config.grid1_member1_vip,"source_ip": config.grid1_member1_mgmt_ip, "record_type": "NS"}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "NOERROR" in response["result"] and config.grid1_member1_mgmt_ip in response['source_address']:
                display_message("SUCCESS: fqdn field is executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with NSR record type")
                assert True
        else:
                display_message("FAILURE: fqdn field is Not executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with NSR record type")
                assert False

    @pytest.mark.run(order=25)
    def test_025_validate_fqdn_sourceip_PTRrecord(self):
        logging.info("Validating fqdn field with PTR record")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" :  ""+config.grid1_master_ptr_record+"."+config.grid1_master_zone+"","member": config.grid1_member1_fqdn,"name_server":config.grid1_member1_vip,"source_ip": config.grid1_member1_mgmt_ip, "record_type": "PTR"}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "NOERROR" in response["result"] and config.grid1_member1_mgmt_ip in response['source_address']:
                display_message("SUCCESS: fqdn field is executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with PTR record type")
                assert True
        else:
                display_message("FAILURE: fqdn field is Not executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with PTR record type")
                assert False

    @pytest.mark.run(order=26)
    def test_026_validate_fqdn_sourceip_SRVrecord(self):
        logging.info("Validating fqdn field with SRV record")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" :  ""+config.grid1_master_srv_record+"."+config.grid1_master_zone+"","member": config.grid1_member1_fqdn,"name_server":config.grid1_member1_vip,"source_ip": config.grid1_member1_mgmt_ip, "record_type": "SRV"}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "NOERROR" in response["result"] and config.grid1_member1_mgmt_ip in response['source_address']:
                display_message("SUCCESS: fqdn field is executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with SVR record type")
                assert True
        else:
                display_message("FAILURE: fqdn field is Not executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with SVR record type")
                assert False

    @pytest.mark.run(order=27)
    def test_027_validate_fqdn_sourceip_TXTrecord(self):
        logging.info("Validating fqdn field with TXT record")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" :  ""+config.grid1_master_txt_record+"."+config.grid1_master_zone+"","member": config.grid1_member1_fqdn,"name_server":config.grid1_member1_vip,"source_ip": config.grid1_member1_mgmt_ip, "record_type": "TXT"}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "NOERROR" in response["result"] and config.grid1_member1_mgmt_ip in response['source_address']:
                display_message("SUCCESS: fqdn field is executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with TXT record type")
                assert True
        else:
                display_message("FAILURE: fqdn field is Not executed with souce address as MGMT ip of master and member as SA member and name server as member's LAN IP ,with TXT record type")
                assert False

    @pytest.mark.run(order=28)
    def test_028_validate_fqdn_sourceip_AXFR_Record(self):
        logging.info("Validating fqdn field with AXFR record")
        child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@'+config.grid1_master_mgmt_vip)
        child.logfile=sys.stdout
        child.expect('#')
        
        # child.sendline('dig @10.35.191.6 10.35.191.6zone.com IN AXFR')
        child.sendline("dig @"+config.grid1_member1_vip+" "+config.grid1_master_zone+" -b "+config.grid1_master_mgmt_vip+"")
        child.expect("#")
        #output1 = child.read()
        output1=child.before
        child.close()
        if "1.1.1.1" and config.grid1_member1_vip in output1:
                display_message(output1)
                display_message("SUCCESS: fqdn field is executed with AXFR record")
                assert True
        else:
                display_message("FAILURE: fqdn field is Not executed with AXFR record")
                assert False

    @pytest.mark.run(order=29)
    def test_029_validate_fqdn_sourceip_memberip_hostname_recursivequery_true(self):
        logging.info("Validating fqdn field with recursive query as true")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : ""+config.grid1_master_a_record+"."+config.grid1_master_zone+"","member": config.grid1_member1_fqdn,"name_server":config.grid1_member1_vip,"recursive_query": True, "source_ip": config.grid1_member1_mgmt_ip}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and config.grid1_member1_mgmt_ip in response['source_address']:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn is executed with source ip as member IP and member as hostname and recursive query as True")
                assert True
        else:
                display_message("FAILURE: fqdn is Not executed with source ip as member IP and member as hostname and recursive query as True")
                assert False

    @pytest.mark.run(order=30)
    def test_030_validate_fqdn_sourceip_memberip_hostname_recursivequery_false(self):
        logging.info("Validating fqdn field with recursive query as false")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : ""+config.grid1_master_a_record+"."+config.grid1_master_zone+"","member": config.grid1_member1_fqdn,"name_server":config.grid1_member1_vip,"recursive_query": False, "source_ip": config.grid1_member1_mgmt_ip}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and config.grid1_member1_mgmt_ip in response['source_address']:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn is executed with source ip as member IP and member as hostname and recursive query as False")
                assert True
        else:
                display_message("FAILURE: fqdn is Not executed with source ip as member IP and member as hostname and recursive query as False")
                assert False

    @pytest.mark.run(order=31)
    def test_031_validate_fqdn_sourceip_with_mgmt_IPV6_member(self):
        Adding_forwarder_grid_DNS()
        logging.info("Validating fqdn field with member's mgmt ipv6 address")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        print(ref)
        data = {"fqdn" : "google.com","source_ip": config.grid1_member1_mgmt_ipv6,"member": config.grid1_member1_fqdn,"name_server": config.grid1_member1_mgmt_ipv6}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
	expected_ipv6 = response['result_text']
        if "NOERROR" in response["result"] and config.grid1_member1_mgmt_ipv6 in expected_ipv6:
                display_message(response["result"])
                display_message("SUCCESS: fqdn with member as GM executed with expected source address")
                assert True
        else:
                display_message("FAILURE: fqdn with member as GM executed without expected source address")
                assert False

    @pytest.mark.run(order=32)
    def test_032_validate_fqdn_sourceip_with_mgmt_IPV6_master(self):
        logging.info("Validating fqdn field with master mgmt ipv6 address")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone,"source_ip": config.grid1_master_mgmt_ipv6,"member": config.grid1_master_fqdn,"name_server": config.grid1_master_mgmt_ipv6}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
	expected_ipv6 = response['result_text']
        if "status: NOERROR" in response["result_text"] and config.grid1_master_mgmt_ipv6 in expected_ipv6:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn with member as GM executed with expected "+config.grid1_master_mgmt_ipv6+" source address")
                assert True
        else:
                display_message("FAILURE: fqdn with member as GM executed without expected "+config.grid1_master_mgmt_ipv6+" source address")
                assert False

    

    @pytest.mark.run(order=33)
    def test_033_validate_fqdn_sourceip_with_LAN_IPV6_member(self):
        logging.info("Validating fqdn field with master LAN ipv6 address")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone,"source_ip": config.grid1_member1_ipv6,"member": config.grid1_member1_fqdn,"name_server": config.grid1_member1_ipv6}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
	expected_ipv6 = response['result_text']
        if "status: NOERROR" in response["result_text"] and config.grid1_member1_ipv6 in expected_ipv6:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn with member as GM executed with expected "+config.grid1_member1_ipv6+" source address")
                assert True
        else:
                display_message("FAILURE: fqdn with member as GM executed without expected "+config.grid1_member1_ipv6+" source address")
                assert False

    @pytest.mark.run(order=34)
    def test_034_validate_fqdn_sourceip_with_Invalid_ipaddress(self):
        logging.info("Validating fqdn field with invalid ip address")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        print(ref)
        print(config.grid1_master_mgmt_vip)
        data = {"fqdn" : ""+config.grid1_master_a_record+"."+config.grid1_master_zone+"","member": config.grid1_member1_fqdn, "source_ip": "10.36.191"}
        response = ib_NIOS.wapi_request('POST', object_type=grid, params="?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        print(response[1])
       
        if '400 Bad Request' in response[1]:
                display_message(response[1])
                display_message("SUCCESS: fqdn with member as GM executed with expected invalid source address")
                assert True
        else:
                display_message("FAILURE: fqdn with member as GM executed without expected invalid source address")
                assert False

    @pytest.mark.run(order=35)
    def test_035_validate_fqdn_Loopback_address_member1(self):
        Add_loopback_ip_member1()
        logging.info("Validating fqdn field with loopback address")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : config.grid1_master_zone,"member": config.grid1_member1_fqdn,"source_ip": config.loopback_ip_member1}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "status: NOERROR" in response["result_text"] and config.loopback_ip_member1 in response['source_address']:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn is executed with loopback ip address")
                assert True
        else:
                display_message("FAILURE: fqdn is Not  executed with loopback ip address")
                assert False

   
    @pytest.mark.run(order=36)
    def test_036_validate_fqdn_Anycast_ipv4_ipv6(self):
        check_able_to_login_appliances(config.grid_vip)
        ospf_ipv6_configuration()
        anycast_ipv6_configuration()
        sleep(120)
        Restart_services()
        logging.info("Validating fqdn field with anycast configurations")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : ""+config.grid1_master_a_record+"."+config.grid1_master_zone+"","member": config.grid1_member1_fqdn,"source_ip":config.grid1_member1_anycast_ipv4,"name_server": config.grid1_member1_vip,"record_type":"A"}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)
        if "NOERROR" in response["result"] and config.grid1_member1_anycast_ipv4 in response['source_address']:
                display_message(response["result"])
                display_message("SUCCESS: fqdn is executed with anycast ipv4 address with A record type")
                assert True
        else:
                display_message("FAILURE: fqdn is Not  executed with anycast ipv4 address with A record type")
                assert False
        data = {"fqdn" : ""+config.grid1_master_a_record+"."+config.grid1_master_zone+"","member": config.grid1_member1_fqdn,"source_ip":config.grid1_member1_anycast_ipv6,"name_server": config.grid1_member1_vip,"record_type":"A"}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        response=json.loads(response)
        display_message(response)

        if "NOERROR" in response["result"] and config.grid1_member1_anycast_ipv6 in response['source_address']:
                display_message(response["result"])
                display_message("SUCCESS: fqdn is executed with anycast ipv6 address with A record type")
                assert True
        else:
                display_message("FAILURE: fqdn is Not  executed with anycast ipv6 address with A record type")
                assert False

    

    @pytest.mark.run(order=37)
    def test_037_validate_fqdn_disabled_sourceip(self):
        logging.info("Validating fqdn field with disabled source ip")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_master_mgmt_vip)
        ref = json.loads(grid)[0]['_ref']
        data = {"fqdn" : ""+config.grid1_master_a_record+"."+config.grid1_master_zone+"","member": config.grid1_member1_fqdn, "source_ip": config.grid1_master_mgmt_vip}
        response = ib_NIOS.wapi_request('POST', object_type=ref + "?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_master_mgmt_vip)
        display_message(response)
        
        if "Source IP address has not been configured on the specified grid member" in response[1]:
                display_message("SUCCESS: fqdn is executed with disabled source ip")
                assert True
        else:
                display_message("FAILURE: fqdn is Not  executed with disabled source ip")
                assert False

    @pytest.mark.run(order=38)
    def test_038_validate_fqdn_sourceip_mgmt_GMC(self):
        Make_normal_member_as_GMC_member_and_validate_the_GMC_member()
        Promoting_Member_as_Master(config.grid1_member1_vip)
        logging.info("Validating fqdn field with GMC member")
        grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid1_member1_mgmt_ip)
        # print(grid)
        print(type(grid))
        ref = json.loads(grid)
        print(type(ref))
        ref = ref[0]["_ref"]
        data = {"fqdn" : config.grid1_master_zone,"source_ip": config.grid1_member1_mgmt_ip}
        response = ib_NIOS.wapi_request('POST', object_type=ref+"?_function=query_fqdn_on_member", fields=json.dumps(data), grid_vip=config.grid1_member1_mgmt_ip)
        response=json.loads(response)
        print(type(response))
        display_message(response)
        if "NOERROR" in response["result"] and config.grid1_member1_mgmt_ip in response['source_address']:
                display_message(response["result_text"])
                display_message("SUCCESS: fqdn is executed with source ip of GMC mgmt")
                assert True
        else:
                display_message("FAILURE: fqdn is Not  executed with source ip of GMC mgmt")
                assert False
        Promoting_Member_as_Master(config.grid1_master_vip)
### cleanup function
'''
    @pytest.mark.run(order=39)
    def test_39_cleanup_objects(self):
        print("\n============================================\n")
        print("CLEANUP: Reverting back to original setup...")
        print("\n============================================\n")

        get_ref = ib_NIOS.wapi_request('GET',object_type="zone_auth")
        for ref in json.loads(get_ref):
            if config.grid1_master_zone in ref["_ref"]:
                ib_NIOS.wapi_request('DELETE',object_type=ref['_ref'])

        print("\n***************. Cleanup test case completed .***************\n")


# Restart services
    @pytest.mark.run(order=40)
    def test_40_Restart_services(self):

        display_message("\n========================================================\n")
        display_message("Restarting Services")
        display_message("\n========================================================\n")

        grid = ib_NIOS.wapi_request('GET', object_type="grid")
        ref = json.loads(grid)[0]['_ref']
        request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus")
        restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices")
        sleep(35)
'''
        
