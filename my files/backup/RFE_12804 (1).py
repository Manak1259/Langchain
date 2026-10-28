#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Manak Sahu"
__email__  = "msahu2@infoblox.com"

########################################################################################
#  Grid Set up required:                                                               #
#  1. SA Grid Master                                                                   #
#  2. Licenses : DNS, DHCP, Grid, NIOS (IB-V1425), RPZ                                 #
########################################################################################

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
import ib_utils.common_utilities as common_util
import re
from ib_utils.file_content_validation import log_validation as logv
from ib_utils.start_stop_logs import log_action as log


#####################################################################################################
#STEPS TO REPRODUCE:                                                                               
#1. Create an authoritative zone 'test.com' and assign it to Grid Master.                          
#2.Execute "query_fqdn_on_member" function with mandatory field "fqdn" with member as GM               
#####################################################################################################


logging.basicConfig(format='%(asctime)s - %(name)s(%(process)d) - %(levelname)s - %(message)s',filename="EDE_RFE.log" ,level=logging.DEBUG,filemode='w')

def display_message(x=""):
    # Additional function used to log and print with a single line
    logging.info(x)
    print(x)

def Restart_services():

        display_message("\n========================================================\n")
        display_message("Restarting Services")
        display_message("\n========================================================\n")

        grid = ib_NIOS.wapi_request('GET', object_type="grid")
        ref = json.loads(grid)[0]['_ref']
        request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=requestrestartservicestatus")
        restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices")
        sleep(35)

        display_message("\n***************. Services Restarted successfully.***************\n")

def restart_services_IF_NEEDED():
    print("Service restart start")
    grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid_vip)
    ref = json.loads(grid)[0]['_ref']
    data= {"member_order" : "SIMULTANEOUSLY","restart_option":"RESTART_IF_NEEDED","service_option": "ALL"}
    request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices",fields=json.dumps(data),grid_vip=config.grid_vip)
    sleep(40)
    print("Service restart Done")


def check_able_to_login_appliances(ip_address=config.grid1_master_mgmt_vip):
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
        data={"name":""+config.grid1_master_dname_record+"."+config.grid1_master_zone+"","canonical": "test.com","view": "default"}
        response4 = ib_NIOS.wapi_request('POST', object_type="record:dname",fields=json.dumps(data))
        data={"name": ""+config.grid1_master_naptr_record+"."+config.grid1_master_zone+"","order": 10,"preference": 10,"view":"default","replacement": "arec.outbound_test.com","services": "http+E2U"}
        response5 = ib_NIOS.wapi_request('POST', object_type="record:naptr",fields=json.dumps(data))
        data={"name":""+config.grid1_master_ns_record+"."+config.grid1_master_zone+"","nameserver":config.grid1_master_vip,"addresses":[{"address":"4.3.2.1"}]}
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

class NIOS_12804(unittest.TestCase):
        #Starting DNS services
        @pytest.mark.run(order=1)
        def test_001_Start_DNS_Service(self):

                logging.info("Start DNS Service")
                get_ref = ib_NIOS.wapi_request('GET', object_type="member:dns")
                logging.info(get_ref)
                res = json.loads(get_ref)
                for i in res:
                        logging.info("Start DNS service")
                        data = {"enable_dns": True}
                        response = ib_NIOS.wapi_request('PUT', ref=i['_ref'], fields=json.dumps(data))
                        print(response)

                logging.info(response)
                read  = re.search(r'200',response)
                for read in  response:
                        assert True
                print("Test Case 1 Execution Completed")
        @pytest.mark.run(order=2)
        def test_002_Validate_DNS_service_Enabled(self):
                logging.info("Validate DNs Service is enabled")
                get_tacacsplus = ib_NIOS.wapi_request('GET', object_type="member:dns",params="?_return_fields=enable_dns")
                logging.info(get_tacacsplus)
                res = json.loads(get_tacacsplus)
                print(res)
                for i in res:
                        print(i)
                        logging.info("found")
                        assert i["enable_dns"] == True
                print("Test Case 2 Execution Completed")

        @pytest.mark.run(order=3)
        def test_003_Add_Authoritative_zone(self):
                logging.info("Create Auth Zone")
                grid_member=config.grid1_master_fqdn
                data = {"fqdn": config.grid1_master_zone,"grid_primary": [{"name":config.grid1_master_fqdn,"stealth":False}]}
                response = ib_NIOS.wapi_request('POST', object_type="zone_auth", fields=json.dumps(data))
                res=json.loads(response)
                logging.info(response)
                read  = re.search(r'201',response)
                for read in  response:
                        assert True
                print("Test Case 003 Execution Completed")
                restart_services_IF_NEEDED()

        @pytest.mark.run(order=4)
        def test_004_validate_auth_zone(self):
                print("\n============================================\n")
                print("Validating Authoratative zone")
                print("\n============================================\n")

                response = ib_NIOS.wapi_request('GET', object_type="zone_auth?fqdn="+config.grid1_master_zone+"", grid_vip=config.grid_vip)
                response=json.loads(response)

                for ref in response:
                       
                        if config.grid1_master_zone in ref['_ref']:
                                print(ref["_ref"])
                                print("SUCCESS: Authoratative Zone "+config.grid1_master_zone+" was created!")
                                assert True
                        else:
                                print("FAILURE: Authoratative Zone "+config.grid1_master_zone+" was NOT created!")

        @pytest.mark.run(order=5)
        def test_005_create_and_validate_a_record(self):

                data = {"name": "" + config.grid1_master_a_record + "." + config.grid1_master_zone + "", "ipv4addr": "3.3.3.3",
                        "view": "default"}
                response1 = ib_NIOS.wapi_request('POST', object_type="record:a", fields=json.dumps(data))
                display_message(response1)
                grid = ib_NIOS.wapi_request('GET', object_type="record:a")
                display_message(grid)
                ref = json.loads(grid)[0]['name']
                display_message(ref)
                record_zone_name = config.grid1_master_a_record + "." + config.grid1_master_zone
                # import pdb
                # pdb.set_trace()
                if record_zone_name == ref:
                       

                        display_message("Success: " + config.grid1_master_a_record + " record is created successfully")

                else:
                        display_message("Failure: " + config.grid1_master_a_record + " record is not created successfully")
        @pytest.mark.run(order=6)
        def test_006_enable_rpz_responses_queries_from_DNS_properties_logging(self):
                
                logging.info("Fetching the reference of grid dns properties")
                ref_grid_dns = ib_NIOS.wapi_request('GET',object_type="grid:dns")
                logging.info(ref_grid_dns)
                ref_gd=json.loads(ref_grid_dns)[0]['_ref']
                logging.info("Enabling recursive queries and logging for rpz")
                data={"allow_recursive_query": True,"logging_categories": {"log_rpz": True,"log_queries": True,"log_responses": True}}
                ref_changed_properties = ib_NIOS.wapi_request('PUT',ref=ref_gd,fields=json.dumps(data),grid_vip=config.grid_vip)
                logging.info(ref_changed_properties)
                restart_services_IF_NEEDED()
                if bool(re.match("\"grid:dns*.",str(ref_changed_properties))):
                       
                        logging.info("Properties changed successfully")
                else:
                        raise Exception("Unable to enable the recursive queries and logging for rpz")

        @pytest.mark.run(order=7)
        def test_007_Perform_Dig_Query_and_Verify_EDNS_Data_from_response_and_validatesyslog(self):

                log("start","/var/log/syslog",config.grid_vip)
                sleep(5)
                global log_validation
                try:

                        logging.info("Perform Dig Query and Verify EDNS Data from response and validatesyslog")
                        child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@' + config.client_ip)
                        child.logfile = sys.stdout
                        child.expect("password:")
                        child.sendline(config.password)
                        sleep(5)
                        child.expect("#")
                        record_data = "" + config.grid1_master_a_record + "." + config.grid1_master_zone + ""
                        child.sendline(
                                "dig @" + config.grid1_master_vip + " " + record_data + " ")
                        child.expect("#")
                        output1 = child.before
                        display_message(output1)
                        child.close()
                except Exception as e:
                        child.close()
                        display_message(e)
                        sleep(20)
                        display_message("Failure")

                if "EDNS" and config.grid1_master_a_record + "." + config.grid1_master_zone in output1:
                        display_message(output1)
                        display_message("SUCCESS: ENDS data from response verified sucessfully")
                else:
                       display_message("FAILURE: ENDS data from response not verified sucessfully")
                sleep(20)
                log("stop","/var/log/syslog",config.grid_vip)
                LookFor = config.grid1_master_a_record + "." + config.grid1_master_zone
                log_validation = logv(LookFor,"/var/log/syslog",config.grid_vip)
                print(log_validation)
        
        @pytest.mark.run(order=8)
        def test_008_Perform_Dig_Query_and_Verify_recursivequery_from_denied_ipaddress_dueto_query_cache_ACL(self):
                get_ref = ib_NIOS.wapi_request('GET', object_type="grid:dns?_return_fields=allow_query", grid_vip=config.grid_vip)
                logging.info(get_ref)
                res = json.loads(get_ref)
                ref1 = json.loads(get_ref)[0]['_ref']
                log("start","/var/log/syslog",config.grid_vip)
                data = {"allow_query":[{"_struct":"addressac","address":config.grid_vip,"permission":"DENY"}]}
                response = ib_NIOS.wapi_request('PUT',ref=ref1,fields=json.dumps(data), grid_vip=config.grid_vip)
                restart_services_IF_NEEDED()
                get_ref = ib_NIOS.wapi_request('GET', object_type="grid:dns?_return_fields=allow_query", grid_vip=config.grid_vip)
                res = json.loads(get_ref)
                actual_res=res[0]["allow_query"]
                
                if (actual_res[0]["permission"]=="DENY") and actual_res[0]["address"]==config.grid_vip:
                       display_message("Success: data of set of ACE's is created successfully")
                else:
                       display_message("Failure: data of set of ACE's is not created successfully")
                
                sleep(5)
                global log_validation

                logging.info("Enabling Debug Logs to Capture Transaction Logs")
                child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@'+config.grid_vip)
                child.logfile=sys.stdout
                child.expect('#')
                child.sendline("dig @" + config.grid_vip + " " + config.client_ip + " ")
                output1=child.before
                print(type(output1))
               
                sleep(20)
                log("stop","/var/log/syslog",config.grid_vip)
                LookFor = "EDE-ERROR-CODE=18" 
                log_validation = logv(LookFor,"/var/log/syslog",config.grid_vip)
                LookFor = "Denied due to query-cache ACL"
                log_validation = logv(LookFor,"/var/log/syslog",config.grid_vip)
                print(log_validation)
                display_message("change the allow query data to default")
                data = {"allow_query":[]}
                response = ib_NIOS.wapi_request('PUT',ref=ref1,fields=json.dumps(data), grid_vip=config.grid_vip)
                restart_services_IF_NEEDED()


        @pytest.mark.run(order=9)
        def test_009_Perform_Dig_Query_and_Verify_recursivequery_from_denied_ipaddress_dueto_query_ACL(self):
               
               get_ref = ib_NIOS.wapi_request('GET', object_type="grid:dns", grid_vip=config.grid_vip)
               log("start","/var/log/syslog",config.grid_vip)
               logging.info(get_ref)
               res = json.loads(get_ref)
               ref1 = json.loads(get_ref)[0]['_ref']
               print(ref1)
               data = {"allow_recursive_query":True}
               response = ib_NIOS.wapi_request('PUT',ref=ref1,fields=json.dumps(data), grid_vip=config.grid_vip)
               logging.info(response)
               sleep(5)
               restart_services_IF_NEEDED()
               get_ref = ib_NIOS.wapi_request('GET', object_type="grid:dns?_return_fields=allow_recursive_query", grid_vip=config.grid_vip)
               res = json.loads(get_ref)
               rc_status=res[0]['allow_recursive_query']
               if rc_status:
                       display_message("Success: allow recursion is enabled successfully")
               else:
                      display_message("Failure: allow recursion is not enabled successfully")
               
               logging.info(res)
               data = {"recursive_query_list":[{"_struct":"addressac","address":"10.197.56.151","permission":"DENY"}]}
               response = ib_NIOS.wapi_request('PUT',ref=ref1,fields=json.dumps(data), grid_vip=config.grid_vip)
               restart_services_IF_NEEDED()
               get_ref = ib_NIOS.wapi_request('GET', object_type="grid:dns?_return_fields=recursive_query_list", grid_vip=config.grid_vip)
               res = json.loads(get_ref)
               permission_status=res[0]['recursive_query_list'][0]['permission']
               address_updated=res[0]['recursive_query_list'][0]['address']
               if (permission_status=="DENY") and address_updated==config.grid_vip:
                        display_message("Success: data of set of ACE's is created successfully in allow recursion queries ")
               else:
                        display_message("Failure: data of set of ACE's is not created successfully in allow recursion queries")
               sleep(5)
               global log_validation
               logging.info("Enabling Debug Logs to Capture Transaction Logs")
               child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@'+config.grid_vip)
               child.logfile=sys.stdout
               child.expect('#')
               child.sendline("dig @" + config.grid_vip + " " + config.client_ip + " ")
               output1=child.before
               print(type(output1))
               sleep(20)
               log("stop","/var/log/syslog",config.grid_vip)
               LookFor = "EDE-ERROR-CODE=18" 
               log_validation = logv(LookFor,"/var/log/syslog",config.grid_vip)
               LookFor = "Denied due to query ACL"
               log_validation = logv(LookFor,"/var/log/syslog",config.grid_vip)
               print(log_validation)
               display_message("change the recursive query list data to default")
               data = {"recursive_query_list":[]}
               response = ib_NIOS.wapi_request('PUT',ref=ref1,fields=json.dumps(data), grid_vip=config.grid_vip)
               restart_services_IF_NEEDED()


        @pytest.mark.run(order=11)
        def test_011_Create_Local_RPZ_Domain_queryrecordfor_RPZblockrule_validate_infocode(self):
                # logging.info("Create Auth Zone")
                # grid_member=config.grid1_master_fqdn
                # data = {"fqdn": "zone_for_rpz.com","grid_primary": [{"name":config.grid1_master_fqdn,"stealth":False}]}
                # response = ib_NIOS.wapi_request('POST', object_type="zone_auth", fields=json.dumps(data))
                # res=json.loads(response)
                # logging.info(response)
                # read  = re.search(r'201',response)
                # for read in  response:
                #         assert True
                # print("Test Case 003 Execution Completed")
                # restart_services_IF_NEEDED()
                
                # print("\n============================================\n")
                # print("Validating Authoratative zone")
                # print("\n============================================\n")

                # response = ib_NIOS.wapi_request('GET', object_type="zone_auth?fqdn=zone_for_rpz.com", grid_vip=config.grid_vip)
                # response=json.loads(response)

                # for ref in response:
                        
                #         if config.grid1_master_zone in ref['_ref']:
                #                 print(ref["_ref"])
                #                 print("SUCCESS: Authoratative Zone zone_for_rpz.com was created!")
                #                 assert True
                #         else:
                #                 print("FAILURE: Authoratative Zone zone_for_rpz.com was NOT created!")
                # data = {"name": "a.zone_for_rpz.com", "ipv4addr": "10.0.0.5",
                #         "view": "default"}
                # response1 = ib_NIOS.wapi_request('POST', object_type="record:a", fields=json.dumps(data))
                # display_message(response1)
                # grid = ib_NIOS.wapi_request('GET', object_type="record:a")
                # display_message(grid)
                # ref = json.loads(grid)[0]['name']
                # display_message(ref)
                # record_zone_name = "a.zone_for_rpz.com"
                # # import pdb
                # # pdb.set_trace()
                # if record_zone_name == ref:
                        

                #         display_message("Success: a.zone_for_rpz.com record is created successfully")

                # else:
                #         display_message("Failure:a.zone_for_rpz.com record is not created successfully")

                # data1 = {"fqdn":"rpz_zone.com","grid_primary": [{"name": config.grid1_master_fqdn,"stealth": False}]}
                # response = ib_NIOS.wapi_request('POST', object_type="zone_rp", fields=json.dumps(data1))
                # restart_services_IF_NEEDED()

                # substitute_obj = {"canonical": "google.com", "rp_zone": "rpz.com", "name": "g.com.rpz.com"}
                # substitute_rule=ib_NIOS.wapi_request('POST', object_type="record:rpz:cname", fields=json.dumps(substitute_obj))

               

                # display_message("Creating Local RPZ domain zone.com")
                # log("start","/var/log/syslog",config.grid_vip)
                # data = {"fqdn": "zone12.com","grid_primary": [{"name": "infoblox.localdomain","stealth": False}]}
                # response = ib_NIOS.wapi_request('POST',object_type='zone_rp',fields=json.dumps(data))
                # display_message(response)

                # if bool(re.match("zone12.com",str(response))):
                #         display_message("Local RPZ domain zone.com creation successful")
                        
                # else:
                #         display_message("Local RPZ domain zone.com creation failed")
                #         assert False

                # restart_services_IF_NEEDED()
               
                # display_message("create Substitute Domain name rule")
                # sub_a_rec_obj = {"name":"asm.zone12.com","rp_zone":"zone12.com","ipv4addr":"10.197.56.151"}
                # sub_a_rec_rule=ib_NIOS.wapi_request('POST', object_type="record:rpz:a", fields=json.dumps(sub_a_rec_obj),grid_vip=config.grid_vip)

                # display_message("query A record data")  
                # global log_validation
                # logging.info("Enabling Debug Logs to Capture Transaction Logs")
                # child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@'+config.grid_vip)
                # child.logfile=sys.stdout
                # child.expect('#')
                # child.sendline("dig @" + config.grid_vip + " " + config.grid1_master_a_record + "." + config.grid1_master_zone + " ")
                # output1=child.before
                # print(type(output1))
                # # import pdb
                # # pdb.set_trace()
                # sleep(20)
                # log("stop","/var/log/syslog",config.grid_vip)
                # LookFor = "EDE-ERROR-CODE=4" 
                # log_validation = logv(LookFor,"/var/log/syslog",config.grid_vip)
                # LookFor = "Answer rewritten due to policy"
                # log_validation = logv(LookFor,"/var/log/syslog",config.grid_vip)
                # print(log_validation)
        
        @pytest.mark.run(order=10)
        def test_010_Create_Local_RPZ_Domain_queryrecord_RPZ_Substitute_Domainname_validate_infocode(self):
                
                display_message("Creating Local RPZ domain zone.com")
                log("start","/var/log/syslog",config.grid_vip)
                data = {"fqdn": "zone12.com","grid_primary": [{"name": "infoblox.localdomain","stealth": False}]}
                response = ib_NIOS.wapi_request('POST',object_type='zone_rp',fields=json.dumps(data))
                display_message(response)
                if bool(re.match("\"zone_rp*.",str(response))):
                        display_message("Local RPZ domain zone.com creation successful")
                        
                else:
                        display_message("Local RPZ domain zone.com creation failed")
                        assert False

                restart_services_IF_NEEDED()
                display_message("create Substitute block name rule")
                no_data_obj = {"canonical": "*", "rp_zone": "rpz.com", "name": "blockdn.com.rpz.com"}
                no_data_rule=ib_NIOS.wapi_request('POST', object_type="record:rpz:cname", fields=json.dumps(no_data_obj))

                display_message("query A record data")  
                global log_validation
                logging.info("Enabling Debug Logs to Capture Transaction Logs")
                child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@'+config.grid_vip)
                child.logfile=sys.stdout
                child.expect('#')
                child.sendline("dig @" + config.grid_vip + " " + config.grid1_master_a_record + "." + config.grid1_master_zone + " ")
                output1=child.before
                print(type(output1))
                sleep(20)
                log("stop","/var/log/syslog",config.grid_vip)
                LookFor = "EDE-ERROR-CODE=15" 
                log_validation = logv(LookFor,"/var/log/syslog",config.grid_vip)
                LookFor = "Query/answer blocked due to policy"
                log_validation = logv(LookFor,"/var/log/syslog",config.grid_vip)
                print(log_validation)

        @pytest.mark.run(order=12)
        def test_012_create_FMZ_NamedACL_Administration_clientip_deny_validate_DNS_query_Infocode(self):
                display_message("Create an Forward mapping zone")
                log("start","/var/log/syslog",config.grid_vip)
                data = {"fqdn": "test1.com",
                "forward_to": [{"name": "test1","address":"10.1.1.1"}]}
                # "grid_secondaries": [{"name": config.grid_member1_fqdn}]}
                response = ib_NIOS.wapi_request('POST', object_type="zone_forward?_return_fields=fqdn", fields=json.dumps(data),grid_vip=config.grid_vip)
                print(response)
                import pdb
                pdb.set_trace()

        #        print(type(response))
                if type(response) == tuple:
                        if response[0] == 400 or response[0] == 401:
                                print("Failure: Create an Forward mapping zone")
                                assert False
                        else:
                                display_message("Success: Create an Forward mapping zone")
                assert True
                display_message("Adding IPv4 Named ACL with Deny Permission")
                data = {"name": "test","access_list": [{"_struct": "addressac","address": "10.1.1.1","permission": "DENY"}]}
                response = ib_NIOS.wapi_request('POST', object_type="namedacl",fields=json.dumps(data),grid_vip=config.grid_vip)
                print(response)
                child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@'+config.grid_vip)
                child.logfile=sys.stdout
                child.expect('#')
                child.sendline("set allow_query_domain add default test.com namedacl")
                child.expect("#")
                record_data = "" + config.grid1_master_a_record + "." + config.grid1_master_zone + ""
                child.sendline(
                        "dig @" + config.grid1_master_vip + " " + record_data + " ")
                child.expect("#")
                output1 = child.before
                sleep(20)
                log("stop","/var/log/syslog",config.grid_vip)
                LookFor = "EDE-ERROR-CODE=18" 
                log_validation = logv(LookFor,"/var/log/syslog",config.grid_vip)
                LookFor = "Denied due to query-domain ACL"
                log_validation = logv(LookFor,"/var/log/syslog",config.grid_vip)
                print(log_validation)

        @pytest.mark.run(order=13)
        def test_013_SignZone_addDNSkey_grid2_Validate_infocode(self):
                
                logging.info("Create Auth Zone")
                log("start","/var/log/syslog",config.grid2_master_vip)
                grid_member=config.grid1_master_fqdn
                data = {"fqdn": "dns_signed_nzone.com","grid_primary": [{"name":config.grid1_master_fqdn,"stealth":False}]}
                response = ib_NIOS.wapi_request('POST', object_type="zone_auth", fields=json.dumps(data))
                res=json.loads(response)
                logging.info(response)
                read  = re.search(r'201',response)
                for read in  response:
                        assert True
                restart_services_IF_NEEDED()
                data = {"name": "" + config.grid1_master_a_record + ".dns_signed_nzone.com", "ipv4addr": "3.3.3.3",
                        "view": "default"}
                response1 = ib_NIOS.wapi_request('POST', object_type="record:a", fields=json.dumps(data))
                display_message(response1)
                grid = ib_NIOS.wapi_request('GET', object_type="record:a")
                display_message(grid)
                ref = json.loads(grid)[0]['name']
                display_message(ref)
                record_zone_name = config.grid1_master_a_record + ".dns_signed_nzone.com"
                # import pdb
                # pdb.set_trace()
                if record_zone_name in grid:
                       

                        display_message("Success: " + config.grid1_master_a_record + " record is created successfully")

                else:
                        display_message("Failure: " + config.grid1_master_a_record + " record is not created successfully")
                logging.info("Sign Auth zone with default algorithm")
                data = {"fqdn":"dns_signed_nzone.com"}
                endpoint=common_util.get_object_reference(object_type="zone_auth",data=data)
                ref=endpoint
                print ("###########",ref)
                data={"buffer":"KSK","operation":"SIGN"}
                response = ib_NIOS.wapi_request('POST', object_type=ref,fields=json.dumps(data),params="?_function=dnssec_operation")
                print (response)
                for read in response:
                        assert True
                logging.info("The selected zone is signed successfully")
                restart_services_IF_NEEDED()
                child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@'+config.grid_vip)
                child.logfile=sys.stdout
                child.expect('#')
                child.sendline("dig @"+config.grid_vip+" dns_signed_nzone.com +dnssec  dnskey")
                child.expect("#")
                output1 = child.before
                pattern = r"257 3 8 (.*?)\s+dns_signed_nzone\.com"

                # Search for the pattern in the data
                match = re.search(pattern, output1, re.DOTALL)
                token = match.group(1).strip()
                if match:
                # Print the captured data
                        print("Fetched data:", match.group(1).strip())
                else:
                        print("No match found.")

               
                grid = ib_NIOS.wapi_request('GET', object_type="grid:dns",grid_vip=config.grid2_master_vip)
                ref = json.loads(grid)[0]['_ref']
                
                data = {"allow_recursive_query": True, "forwarders":[config.grid1_master_vip], "forward_only": True, "dnssec_trusted_keys": [{"dnssec_must_be_secure": False, "algorithm": "14", "fqdn": "dns_signed_nzone.com","key": token, "secure_entry_point": True}],  "logging_categories": {"log_responses": True}}
     
                response = ib_NIOS.wapi_request('PUT',ref=ref,fields=json.dumps(data),grid_vip=config.grid2_master_vip)
                
                print(response)
                sleep(10)
                
                print("Service restart start")
                grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid2_master_vip)
                ref = json.loads(grid)[0]['_ref']
                data= {"member_order" : "SIMULTANEOUSLY","restart_option":"RESTART_IF_NEEDED","service_option": "ALL"}
                request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices",fields=json.dumps(data),grid_vip=config.grid2_master_vip)
                sleep(40)
                print("Service restart Done")
                child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@'+config.grid_vip)
                child.logfile=sys.stdout
                child.expect('#')
                record_data = "" + config.grid1_master_a_record + ".dns_signed_nzone.com"
                child.sendline(
                        "dig @" + config.grid2_master_vip + " " + record_data + " ")
                child.expect("#")
                output1 = child.before
                

                if ("EDE: 6" and "DNSSEC validation failed; trust chain is broken") in output1:
                       display_message("Success: Eror code EDE: 6 is validated successfully in "+output1)
                else:
                       display_message("Failure: Eror code EDE: 6 is not validated successfully in "+output1)
                       assert False
                       
                sleep(20)
                log("stop","/var/log/syslog",config.grid2_master_vip)
                LookFor = "EDE-ERROR-CODE=6" 
                log_validation = logv(LookFor,"/var/log/syslog",config.grid2_master_vip)
                LookFor = "DNSSEC validation failed; trust chain is broken"
                log_validation = logv(LookFor,"/var/log/syslog",config.grid2_master_vip)
                print(log_validation)


        @pytest.mark.run(order=14)
        def test_014_Perform_Dig_Query_and_Verify_recursivequery_from_denied_ipaddress_dueto_query_ACL_in_grid2(self):
               
               
               grid = ib_NIOS.wapi_request('GET', object_type="grid:dns",grid_vip=config.grid_vip)
               ref = json.loads(grid)[0]['_ref']
               data = {"allow_recursive_query": True, "forwarders":[config.grid2_master_vip], "forward_only": True}
               response = ib_NIOS.wapi_request('PUT',ref=ref,fields=json.dumps(data),grid_vip=config.grid_vip)
               print(response)
               restart_services_IF_NEEDED()
               logging.info("Create Auth Zone")
        #        grid_member=config.grid1_master_fqdn
               data = {"fqdn": "grid2_zone.com","grid_primary": [{"name":config.grid2_master_fqdn,"stealth":False}]}
               response = ib_NIOS.wapi_request('POST', object_type="zone_auth", fields=json.dumps(data),grid_vip=config.grid2_master_vip)
               res=json.loads(response)
               logging.info(response)
               read  = re.search(r'201',response)
               for read in  response:
                       assert True
               restart_services_IF_NEEDED() 
               data = {"name": "grid2record.grid2_zone.com", "ipv4addr": "2.2.2.2",
                        "view": "default"}
               response1 = ib_NIOS.wapi_request('POST', object_type="record:a", fields=json.dumps(data), grid_vip=config.grid2_master_vip)
               display_message(response1)
               grid = ib_NIOS.wapi_request('GET', object_type="record:a", grid_vip=config.grid2_master_vip)
               print(grid)
               print("manak",type(grid))
               ref = json.loads(grid)
               display_message(ref[1])
               record_zone_name = "grid2record.grid2_zone.com"
             
               if record_zone_name == ref[1]['name']:
                       

                       display_message("Success: " + config.grid1_master_a_record + " record is created successfully")

               else:
                       display_message("Failure: " + config.grid1_master_a_record + " record is not created successfully")

               get_ref = ib_NIOS.wapi_request('GET', object_type="grid:dns", grid_vip=config.grid2_master_vip)
               log("start","/var/log/syslog",config.grid_vip)
               logging.info(get_ref)
               res = json.loads(get_ref)
               ref1 = json.loads(get_ref)[0]['_ref']
               print(ref1)
               data = {"allow_recursive_query":True}
               response = ib_NIOS.wapi_request('PUT',ref=ref1,fields=json.dumps(data), grid_vip=config.grid2_master_vip)
               logging.info(response)
               sleep(5)
               print("Service restart start")
               grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid2_master_vip)
               ref = json.loads(grid)[0]['_ref']
               data= {"member_order" : "SIMULTANEOUSLY","restart_option":"RESTART_IF_NEEDED","service_option": "ALL"}
               request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices",fields=json.dumps(data),grid_vip=config.grid2_master_vip)
               sleep(40)
               print("Service restart Done")
               get_ref = ib_NIOS.wapi_request('GET', object_type="grid:dns?_return_fields=allow_recursive_query", grid_vip=config.grid2_master_vip)
               res = json.loads(get_ref)
               rc_status=res[0]['allow_recursive_query']
               if rc_status:
                       display_message("Success: allow recursion is enabled successfully")
               else:
                      display_message("Failure: allow recursion is not enabled successfully")
               
               logging.info(res)
               
               data = {"allow_query":[{"_struct":"addressac","address":"2.2.2.2","permission":"DENY"}]}
               response = ib_NIOS.wapi_request('PUT',ref=ref1, fields=json.dumps(data), grid_vip=config.grid2_master_vip)
               print("Service restart start")
               grid =  ib_NIOS.wapi_request('GET', object_type="grid", grid_vip=config.grid2_master_vip)
               ref = json.loads(grid)[0]['_ref']
               data= {"member_order" : "SIMULTANEOUSLY","restart_option":"RESTART_IF_NEEDED","service_option": "ALL"}
               request_restart = ib_NIOS.wapi_request('POST', object_type = ref + "?_function=restartservices",fields=json.dumps(data),grid_vip=config.grid2_master_vip)
               sleep(40)
               print("Service restart Done")
               get_ref = ib_NIOS.wapi_request('GET', object_type="grid:dns?_return_fields=allow_query", grid_vip=config.grid2_master_vip)
               res = json.loads(get_ref)
               actual_res=res[0]["allow_query"]
                
               if (actual_res[0]["permission"]=="DENY") and actual_res[0]["address"]==config.grid2_master_vip:
                      display_message("Success: data of set of ACE's is created successfully")
               else:
                      display_message("Failure: data of set of ACE's is not created successfully")
                
               sleep(5)
               global log_validation

               logging.info("Enabling Debug Logs to Capture Transaction Logs")
               child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@'+config.grid2_master_vip)
               child.logfile=sys.stdout
               child.expect('#')
               child.sendline("dig @"+config.grid_vip+" grid2record.grid2_zone.com")
               output1=child.before
               print(type(output1))
               sleep(20)
               log("stop","/var/log/syslog",config.grid_vip)
               LookFor = "EDE-ERROR-CODE=22" 
               log_validation = logv(LookFor,"/var/log/syslog",config.grid_vip)
               LookFor = "Resolver error: all nameservers are marked bad"
               log_validation = logv(LookFor,"/var/log/syslog",config.grid_vip)
               print(log_validation)
       



       