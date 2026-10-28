#!/usr/bin/python

# This is the python script will capture all the Grid Wide features

import infoblox.one.util as ou
import infoblox.one.onedb as onedb
import infoblox.common.ilog as ilog
import common_utils as common
import infoblox.one.license_util as lu
import infoblox.one.one_include as oi

#Importing the 'license' module will result in change of some of the keys in the db. Be informed about the same.
#import infoblox.one.license as lic
import json
import os
import re
import sys

class grid_feature_usage():

    # network template counters
    def get_templates_count(self):
        templates = common.get_db_count(self.db, '?dns.network_template_dhcp_member') + common.get_db_count(self.db, '?dns.fixed_address_template') + common.get_db_count(self.db, '?dns.dhcp_range_template')
        return templates

    # IPV4 data
    def get_ipv4_data(self):
        self.data = common.fill_up_count_options(self.db, d=self.data, k='dhcp.ipv4.networks', \
                q='?dns.network', o={'is_ipv4':'true'}, dv=0)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='dhcp.ipv4.ranges', \
                q='?dns.dhcp_range', o={'is_ipv4':'true'}, dv=0)
        
        exclusion_range_count = 0
        exclusion_range_data = self.db.call('?dns.exclusion_range')
        for item in exclusion_range_data:
           is_ipv4 = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", item['start_address'])
           if is_ipv4:
               exclusion_range_count += 1
        self.data['dhcp.ipv4.exclusion_ranges'] = exclusion_range_count

        self.data = common.fill_up_count_options(self.db, d=self.data, k='dhcp.ipv4.fixed_addresses', \
                q='?dns.fixed_address', o={'is_ipv4':'true'}, dv=0)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='dhcp.ipv4.reservations', \
                q='?dns.fixed_address', o={'is_ipv4':'true', 'match_option':'2'}, dv=0)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='dhcp.ipv4.hosts', \
                q='?dns.host_address', o={'is_ipv4':'true'}, dv=0)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='dhcp.ipv4.roaming_hosts', \
                q='?dns.roaming_host', o={'address_type':'IPV4'}, dv=0)
        self.data = common.fill_up_count(self.db, d=self.data, k='dhcp.ipv4.superhost', \
                q='?dns.superhost', dv=0)

    # DHCP filters
    def get_dhcp_filters(self):
        filters = common.get_db_count(self.db, '?dns.dhcp_mac_filter') + common.get_db_count(self.db, '?dns.dhcp_option_filter') + common.get_db_count(self.db, '?dns.nac_filter') + common.get_db_count(self.db, '?dns.dhcp_option_82_filter') + common.get_db_count(self.db, '?dns.dhcp_fingerprint_filter')
        self.data['dhcp.filters'] = filters

    # IPV6 data
    def get_ipv6_data(self):
        self.data = common.fill_up_count_options(self.db, d=self.data, k='dhcp.ipv6.networks', \
                q='?dns.network', o={'is_ipv4':'false'}, dv=0)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='dhcp.ipv6.ranges', \
                q='?dns.dhcp_range', o={'is_ipv4':'false'}, dv=0)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='dhcp.ipv6.fixed_addresses', \
                q='?dns.fixed_address', o={'is_ipv4':'false'}, dv=0)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='dhcp.ipv6.shared_networks', \
                q='?dns.shared_network', o={'is_ipv4':'false'}, dv=0)

    # DHCP feature data
    def feature_dhcp_data(self):
        if self.cluster_dhcp_object is not None:
            self.data['dhcp.expert_mode'] = bool(self.cluster_dhcp_object['enable_expert_mode'])
            self.data['dhcp.pxe_lease_time_enabled'] = bool(self.cluster_dhcp_object['enable_pxe_lease_time'])
            self.data['dhcp.deny_bootp'] = bool(self.cluster_dhcp_object['deny_bootp'])
            self.data['dhcp.enable_roaming_hosts'] = bool(self.cluster_dhcp_object['enable_roaming_hosts'])
            self.data['dhcp.enable_ifmap'] = bool(self.cluster_dhcp_object['enable_ifmap'])
            self.data['dhcp.enable_cisco_ise_dhcpd_lease_publishing'] = bool(self.cluster_dhcp_object['enable_cisco_ise_dhcpd_lease_publishing'])
            self.data['dhcp.v6_enable_gss_tsig'] = bool(self.cluster_dhcp_object['v6_enable_gss_tsig'])
            self.data['dhcp.cluster_log_lease_events'] = bool(self.cluster_dhcp_object['log_lease_events'])
            self.data['dhcp.update_static_leases'] = bool(self.cluster_dhcp_object['update_static_leases'])
            self.data['dhcp.utf8_hostname_encoding'] = False
            v4 = self.cluster_dhcp_object['windows_code_page']
            v6 = self.cluster_dhcp_object['v6_windows_code_page']
            if v4 != 'None' or v6 != 'None':
                self.data['dhcp.utf8_hostname_encoding'] = True
            self.data['dhcp.fingerprinting'] = bool(self.cluster_dhcp_object['enable_fingerprint'])
            self.data = common.fill_up_bool_option(self.db, d=self.data, k='dhcp.dhcpv4_options.custom', \
                q='?dns.option', o={'is_ipv4':'true'}, dv=False)
            self.data['dhcp.ipv6.lease_affinity'] = int(self.cluster_dhcp_object['v6_recycle_leases'])
            self.data = common.fill_up_count(self.db, d=self.data, k='dhcp.ipv6.global_prefixes', \
                q='?dns.ipv6_global_prefix', dv=0)
            self.data = common.fill_up_bool_option(self.db, d=self.data, k='dhcp.ipv6_options.custom', \
                q='?dns.option', o={'is_ipv4':'false'}, dv=False)
            self.data['dhcp.enable_gss_tsig'] = bool(self.cluster_dhcp_object['enable_gss_tsig'])
            self.data['dhcp.dns_update_style'] = str(self.cluster_dhcp_object['dns_update_style'])
            self.data['dhcp.recycle_leases'] = bool(self.cluster_dhcp_object['recycle_leases'])
            self.data['dhcp.v6_leases_scavenging_enabled'] = bool(self.cluster_dhcp_object['v6_leases_scavenging_enabled'])
            self.data['dhcp.v6_leases_scavenging_grace_period'] = int(self.cluster_dhcp_object['v6_leases_scavenging_grace_period'])
            self.data['dhcp.update_dns_on_lease_renewal'] = bool(self.cluster_dhcp_object['update_dns_on_lease_renewal'])
            self.data['dhcp.v6_update_dns_on_lease_renewal'] = bool(self.cluster_dhcp_object['v6_update_dns_on_lease_renewal'])
            self.data['dns.tsig_ddns_authentication'] = False
            tsig = self.db.call('?dns.remote_ddns_forward_zone',{'tsig_option':'tsig'},limit=1)
            if tsig:
                self.data['dns.tsig_ddns_authentication'] = True
            
            self.data['dns.gss_tsig_ddns_authentication'] = False
            gss_tsig = self.db.call('?dns.remote_ddns_forward_zone',{'tsig_option':'gss-tsig'}, limit=1)
            if gss_tsig:
                self.data['dns.gss_tsig_ddns_authentication'] = True
            
        else:
            ilog.log('Error occurred while fetch cluster DHCP object')

    def feature_ipv4_ipv6_data(self):
        self.get_ipv4_data()
        self.get_dhcp_filters()
        self.get_ipv6_data()

    # Network data       
    def feature_network_data(self):
        self.data = common.fill_up_count(self.db, d=self.data, k='dhcp.network_views', \
                q='?dns.network_view', dv=0)
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='dhcp.captive_portal', \
            q='?one.member_captive_portal_properties', \
                o={'service_enabled': True}, limit=1, dv=False)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='dhcp.shared_networks', \
                q='?dns.shared_network', o={'is_ipv4':'true'}, dv=0)
        self.data['dhcp.templates'] = int(self.get_templates_count())
        self.data = common.fill_up_count(self.db, d=self.data, k='dhcp.dhcp_failover', \
	            q='?dns.dhcp_failover_association', dv=0)
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='dhcp.authenticated_dhcp', \
            q='?dns.member_dhcp_captive_portal', o={'enabled': True}, \
                limit=1, dv=False)
    
        cidr_31 = common.get_db_count(self.db, '?dns.network', {'cidr':'31'})
        cidr_32 = common.get_db_count(self.db, '?dns.network', {'cidr':'32'})
        cidr_128 = common.get_db_count(self.db, '?dns.network', {'cidr':'128'})
        self.data['dns.network.cidr_31_32_128'] = cidr_31 + cidr_32 + cidr_128

        self.data = common.fill_up_count_options(self.db, d=self.data, k='networks.override_boot_file', \
                q='?dns.network', o={'override_boot_file':'true'}, dv=0)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='networks.override_boot_server', \
                q='?dns.network', o={'override_boot_server':'true'}, dv=0)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='networks.override_next_server', \
                q='?dns.network', o={'override_next_server':'true'}, dv=0)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='networks.deny_bootp', \
                q='?dns.network', o={'deny_bootp':'true'}, dv=0)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='networks.pxe_lease_time_enabled', \
                q='?dns.network', o={'pxe_lease_time_enabled':'true'}, dv=0)

    # DNS record counters
    def feature_dns_records(self):
        self.data = common.fill_up_count(self.db, d=self.data, k='dhcp.lease', \
	            q='?dns.lease', dv=0)
        self.data = common.fill_up_count(self.db, d=self.data, k='dns.bind_a', \
	            q='?dns.bind_a', dv=0)
        self.data = common.fill_up_count(self.db, d=self.data, k='dns.bind_ptr', \
	            q='?dns.bind_ptr', dv=0)      
        self.data = common.fill_up_count(self.db, d=self.data, k='dns.bind_txt', \
	            q='?dns.bind_txt', dv=0)   
        self.data = common.fill_up_count(self.db, d=self.data, k='dns.bind_srv', \
	            q='?dns.bind_srv', dv=0)                       
        self.data = common.fill_up_count(self.db, d=self.data, k='dns.bind_cname', \
	            q='?dns.bind_cname', dv=0)   
        self.data = common.fill_up_count(self.db, d=self.data, k='dns.zone', \
	            q='?dns.zone', dv=0)      
        self.data = common.fill_up_count(self.db, d=self.data, k='dns.bind_soa', \
	            q='?dns.bind_soa', dv=0)
        self.data = common.fill_up_count(self.db, d=self.data, k='dns.bind_ns', \
	            q='?dns.bind_ns', dv=0)  
        self.data = common.fill_up_count(self.db, d=self.data, k='dns.bind_mx', \
	            q='?dns.bind_mx', dv=0) 
        self.data = common.fill_up_count(self.db, d=self.data, k='dns.bind_aaaa', \
	            q='?dns.bind_aaaa', dv=0)                                

    # Feature zone data
    def feature_zone_data(self):
        aws_r53 = False
        aws_obj = self.db.call('?dns.aws_rte53_zone_info',
                        limit=1, factory=onedb.todict)
        if aws_obj:
            aws_r53 = True
        self.data['dns.aws_r53'] = aws_r53

        self.data = common.fill_up_bool_option(self.db, d=self.data, k='dns.multi_master', \
            q='?dns.zone', o={'is_multimaster':'true'}, limit=1, dv=False)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='dns.forwarding_zones', \
			q='?dns.zone', o={'zone_type':'Forward'}, dv=0)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='dhcp_custom_options.ipv4_type', \
                q='?dns.option', o={'is_ipv4':'true'}, dv=0)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='dhcp_custom_options.ipv6_type', \
                q='?dns.option', o={'is_ipv4':'false'}, dv=0)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='zones.is_external_primary', \
                q='?dns.zone', o={'is_external_primary':'true'}, dv=0)
        self.data = common.fill_up_count(self.db, d=self.data, k='dns.secondary_authoritative_zones', \
                q='?dns.zone_cluster_secondary_server', dv=0)  
        self.data = common.fill_up_count_options(self.db, d=self.data, k='zones.view_zone_type', \
                q='?dns.zone', o={'zone_type':'View'}, dv=0)    
        self.data = common.fill_up_count_options(self.db, d=self.data, k='zones.sharedrecordgroup_zone_type', \
                q='?dns.zone', o={'zone_type':'SharedRecordGroup'}, dv=0)                      
        self.data = common.fill_up_count_options(self.db, d=self.data, k='zones.responsepolicy_zone_type', \
                q='?dns.zone', o={'zone_type':'ResponsePolicy'}, dv=0)        
        self.data = common.fill_up_count_options(self.db, d=self.data, k='zones.dummy_zone_type', \
                q='?dns.zone', o={'zone_type':'Dummy'}, dv=0)     
        self.data = common.fill_up_count_options(self.db, d=self.data, k='zones.nondnshost_zone_type', \
                q='?dns.zone', o={'zone_type':'NonDNSHost'}, dv=0)  
        self.data = common.fill_up_count_options(self.db, d=self.data, k='zones.idnsroot_zone_type', \
                q='?dns.zone', o={'zone_type':'IdnsRoot'}, dv=0) 
        self.data = common.fill_up_count_options(self.db, d=self.data, k='zones.authoritative_zone_type', \
                q='?dns.zone', o={'zone_type':'Authoritative'}, dv=0) 
        self.data = common.fill_up_count_options(self.db, d=self.data, k='zones.delegate_zone_type', \
                q='?dns.zone', o={'zone_type':'Delegated'}, dv=0)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='zones.stub_zones', \
                q='?dns.zone', o={'zone_type':'Stub'}, dv=0) 
        self.data = common.fill_up_count_options(self.db, d=self.data, k='zones.primary_none_type', \
                q='?dns.zone', o={'primary_type':'None'}, dv=0) 
        self.data = common.fill_up_count_options(self.db, d=self.data, k='zones.primary_grid_type', \
                q='?dns.zone', o={'primary_type':'Grid'}, dv=0) 
        self.data = common.fill_up_count_options(self.db, d=self.data, k='zones.is_multimaster', \
                q='?dns.zone', o={'is_multimaster':'true'}, dv=0)
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='dhcp.zone_network_association', \
            q='?dns.network_zone_association', o={'is_default':'true'}, dv=False)
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='zone.dnssec', \
            q='?dns.zone', o={'is_dnssec_signed':'true'}, limit=1, dv=False)

    # DNS feature data
    def feature_dns_data(self):
        if self.cluster_dns_object is not None:
            self.data['dns.dnssec'] = bool(self.cluster_dns_object['enable_dnssec'])
            self.data['dns.blackhole'] = bool(self.cluster_dns_object['enable_blackhole'])
            self.data['dns.dns64'] = bool(self.cluster_dns_object['enable_dns64'])
            q_log = bool(self.cluster_dns_object['log_queries'])
            r_log = bool(self.cluster_dns_object['log_responses'])
            self.data['dns.query_response_logging'] = q_log or r_log
            self.data['dns.allow_gss_tsig_zone_updates'] = bool(self.cluster_dns_object['allow_gss_tsig_zone_updates'])
            self.data['dns.blacklist_enabled'] = bool(self.cluster_dns_object['enable_blacklist'])
            self.data['dns.dns_health_check_enabled'] = bool(self.cluster_dns_object['dns_health_check_enabled'])
            if 'enable_anycast_restart' in self.cluster_dns_object:
                self.data['dns.anycast'] = bool(self.cluster_dns_object['enable_anycast_restart'])
            else:
                self.data['dns.anycast'] = False

            self.data['dns.nxdomain_redirection'] = bool(self.cluster_dns_object['enable_nxdomain_redirect'])
            self.data['dns.rrset_order'] = bool(self.cluster_dns_object['host_rrset_order'])
            self.data['dns.custom_root_name_servers'] = bool(self.cluster_dns_object['enable_custom_root_server'])
            self.data['dns.enable_recursion'] = bool(self.cluster_dns_object['recursion_enabled'])
            self.data['dns.hsm_signing'] = bool(self.cluster_dns_object['enable_hsm_signing'])
            self.data['dns.enable_gss_tsig'] = bool(self.cluster_dns_object['enable_gss_tsig'])
            self.data['dns.log_queries'] = bool(self.cluster_dns_object['log_queries'])
            if 'enable_dnstap_responses' in self.cluster_dns_object:
                self.data['dns.pdns'] = bool(self.cluster_dns_object['enable_dnstap_responses'])
            else:
                self.data['dns.pdns'] = False
            self.data['dns.smartcache_enabled'] = bool(self.cluster_dns_object['enable_smartcache'])
            self.data['dns.rpz_disable_nsdname_nsip'] = bool(self.cluster_dns_object['rpz_disable_nsdname_nsip'])
        else:
            ilog.log('Error occurred while fetch cluster DNS object')
               
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='dns.dns_scavenging', \
            q='?dns.reclamation_properties', o={'enable_reclamation':'true'}, dv=False)

        bulk_host = False
        bulk_host_obj = self.db.call('?dns.bulk_host',
                        limit=1, factory=onedb.todict)
        if bulk_host_obj:
            bulk_host = True
        self.data['dns.bulk_hosts'] = bulk_host

        self.data = common.fill_up_bool_option(self.db, d=self.data, k='dns.dns_over_http_s', \
            q='?dns.member_dns_properties', o={'doh_service':'true'}, limit=1, dv=False)
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='dns.parental_control', \
            q='?one.imc_subscriber_secure_properties', o={'use_parental_control_enabled':'true'}, dv=False)
        self.data = common.fill_up_count(self.db, d=self.data, k='dns.dns_views', \
	        q='?dns.view', dv=0)
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='dns.minimal_responses', \
            q='?dns.member_dns_properties', o={'minimal_response':'true'}, limit=1, dv=False)
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='dns.response_rate_limiting', \
            q='?dns.response_rate_limiting', o={'enable_rrl':'true'}, limit=1, dv=False)
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='dns.xfrs', \
            q='?one.ac_item', o={'function_type':'ZONE_TRANSFER','permission':'ALLOW'}, limit=1, dv=False)
        
        record_name_policy = False
        record_name_policy_obj = self.db.call('?dns.record_name_policy',
                        limit=1, factory=onedb.todict)
        if record_name_policy_obj:
            record_name_policy = True
        self.data['dns.hostname_policy'] = record_name_policy

        cluster_dns_forwarders = common.get_db_count(self.db, '?dns.cluster_forwarder')
        if cluster_dns_forwarders :
            self.data['dns.cluster_dns_forwarders'] = True
        else :
            self.data['dns.cluster_dns_forwarders'] = False

        ns = False
        ns_obj = self.db.call('?dns.ns_group',
                    limit=1, factory=onedb.todict)
        if ns_obj:
            ns = True
        self.data['dns.nameserver_groups'] = ns
        
        self.data['dns.dtc'] = False
        vnodes = self.db.call('?one.virtual_node')
        for vnode in vnodes:
            lbdns = self.db.call('dns.get_idns_lbdn_zone_links_assigned_to_member',
                {'member_oid': vnode['virtual_oid'], 'disabled': False}, factory=onedb.todict)
            if len(lbdns) > 0:
                self.data['dns.dtc'] = True
                break
        
        self.data['dns.idn_i18n_punycode'] = False
        zones = self.db.call('?dns.zone', factory=onedb.todict)
        for item in zones:
            try:
                item['display_domain'].encode('ascii')
            except UnicodeEncodeError:
                self.data['dns.idn_i18n_punycode'] = True
                break
            except Exception as e:
                ilog.log('Error occurred while checking IDN I18N Punycode : %s' % e)
                break
    # IPAM feature data
    def feature_ipam_data(self):
        self.data = common.fill_up_count(self.db, d=self.data, k='ipam.network_views', \
	        q='?dns.network_view', dv=0)
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='ipam.discovery', \
            q='?discovery.discovery_target', o={'enable_discovery':'true'}, limit=1, dv=False)

        vlan_link = False
        vlan_obj = self.db.call('?dns.vlan_link',
                  limit=1, factory=onedb.todict)
        if vlan_obj:
            vlan_link = True
        self.data['ipam.vlan_mgmt'] = vlan_link 

    # Microsoft feature data
    def feature_ms_data(self):
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='microsoft_management.dns', \
                q='?dns.ms_server_dns_properties', o={'managed': 'true'}, dv=False)
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='microsoft_management.dhcp', \
                q='?dns.ms_server_dhcp_properties', o={'managed': 'true'}, dv=False)
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='microsoft_management.ad_sites_and_services', \
                q='?dns.ms_ad_sites_properties', o={'managed': 'true'}, dv=False)
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='microsoft_management.user_id', \
                q='?dns.ms_ad_user_properties', o={'enable_ad_user_sync': 'true'}, dv=False)
    
    # NIOS data
    def feature_nios_data(self):
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='nios.network_insight', \
            q='?discovery.member_discovery_properties', o={'enable_service':'true'}, limit=1, dv=False)
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='nios.ntp', \
            q='?one.vnode_time', o={'ntp_service_enabled':'true'}, limit=1, dv=False)
        self.data = common.fill_up_count(self.db, d=self.data, k='nios.admins', q='?one.admin', dv=0)
        
        smart_folders = common.get_db_count(self.db, '?one.personal_smart_folder') + common.get_db_count(self.db, '?one.global_smart_folder')
        self.data['nios.smart_folders'] = smart_folders

        self.data['nios.authentication'] = False
        ldap = self.db.call('?one.admin_auth_method',{'auth_method_type':'LDAP'}, limit=1)
        radius = self.db.call('?one.admin_auth_method',{'auth_method_type':'RADIUS'}, limit=1)
        if ldap or radius:
            self.data['nios.authentication'] = True

        self.data['nios.authorization'] = False
        tacacs = self.db.call('?one.admin_auth_method',{'auth_method_type':'TACACS+'}, limit=1)
        if tacacs:
            self.data['nios.authorization'] = True

        tftp_flag = False
        tftp_obj = self.db.call('?one.member_tftp_properties',
                    {'tftp_enabled':'true'}, limit=1)
        if tftp_obj:
            tftp_flag = True
        ftp_flag = False
        ftp_obj = self.db.call('?one.member_tftp_properties',
                    {'ftp_enabled':'true'}, limit=1)
        if ftp_obj:
            ftp_flag = True      
        http_flag = False
        http_obj = self.db.call('?one.member_tftp_properties',
                    {'http_enabled':'true'}, limit=1)
        if http_obj:
            http_flag = True
        self.data['nios.file_distribution'] = tftp_flag | ftp_flag | http_flag

        self.data = common.fill_up_bool_option(self.db, d=self.data, k='nios.ospf', \
            q='?one.member_virtual_ip', o={'enable_ospf':'true'}, limit=1, dv=False)
        self.data = common.fill_up_bool_option(self.db, d=self.data, k='nios.bgp', \
            q='?one.member_virtual_ip', o={'enable_bgp':'true'}, limit=1, dv=False)       

    # GRID specific data
    def cluster_data(self):
        self.data = common.fill_up_count(self.db, d=self.data, k='virtual_node_count', q='?one.virtual_node', dv=0)
        self.data = common.fill_up_count(self.db, d=self.data, k='physical_node_count', q='?one.physical_node', dv=0)
            
        cluster_object = self.db.call('?one.cluster',
                     {'cluster' : self.cluster_id},
                     single = True)
        if cluster_object is not None:
            self.data['enable_extended_discovery'] = bool(cluster_object['extended_discovery_enabled'])
            self.data['enable_wins_forwarding'] = bool(cluster_object['enable_wins_forwarding'])

        self.data = common.fill_up_bool_option(self.db, d=self.data, k='data_collector.enable_registration', \
            q='?one.datacollector_cluster', o={'enable_registration':'true'}, limit=1, dv=False)
        
    # DTC specific data
    def feature_dtc_data(self):
        self.data['dtc.members_pct'] = 0
        license_count = 0
        dtc_members = lu.get_vnodes_by_license_type(self.db, oi.IB_LICENSE_TYPE_IDNS)
        license_count += len(dtc_members)
        # Check license on passive member
        vnodes = self.db.call('?one.virtual_node', factory=onedb.DBRecord)
        for vnode in vnodes:
            ret_dict = lu.check_member_for_license_type_expired(self.db,
                oi.IB_LICENSE_TYPE_IDNS, vnode.ref())
            if ret_dict.get('valid_on_passive'):
                if (not ret_dict.get('expired')) or (not ret_dict.get('is_temp_license')):
                    license_count += 1

        pnode_count = common.get_db_count(self.db, '?one.physical_node')
        if (pnode_count > 0) and (license_count > 0):
            self.data['dtc.members_pct'] = float(license_count)/float(pnode_count)*100
        self.data = common.fill_up_count_options(self.db, d=self.data, k='dtc.health_monitor_http', \
            q='?dns.idns_monitor_http', o={'secure':'false'}, dv=0)
        self.data = common.fill_up_count(self.db, d=self.data, k='dtc.health_monitor_snmp', q='?dns.idns_monitor_snmp', dv=0)
        self.data = common.fill_up_count(self.db, d=self.data, k='dtc.health_monitor_tcp', q='?dns.idns_monitor_tcp', dv=0)
        self.data = common.fill_up_count_options(self.db, d=self.data, k='dtc.health_monitor_https', \
            q='?dns.idns_monitor_http', o={'secure':'true'}, dv=0)
        self.data = common.fill_up_count(self.db, d=self.data, k='dtc.health_monitor_icmp', q='?dns.idns_monitor_icmp', dv=0)
        self.data = common.fill_up_count(self.db, d=self.data, k='dtc.health_monitor_pdp', q='?dns.idns_monitor_pdp', dv=0)
        self.data = common.fill_up_count(self.db, d=self.data, k='dtc.health_monitor_sip', q='?dns.idns_monitor_sip', dv=0)
        self.data = common.fill_up_count(self.db, d=self.data, k='dtc.consolidated_monitors', q='?dns.idns_consolidated_monitor_health', dv=0)

    # NI specific data
    def feature_ni_data(self):
        unmanaged_networks = 0
        unmanaged_ip_addresses = 0
        discovery = self.db.call('?discovery.statistics')
        for item in discovery:
            unmanaged_networks += int(item['networks_unmanaged'])
            unmanaged_ip_addresses += int(item['hosts_unmanaged'])
        self.data['ni.unmanaged_networks'] = unmanaged_networks
        self.data['ni.unmanaged_ip_addresses'] = unmanaged_ip_addresses

    def dump(self):
        try:
            #DHCP feature data
            self.feature_dhcp_data()
            #IPAM feature data
            self.feature_ipam_data()
            #ms feature data
            self.feature_ms_data()
            #cluster related counts
            self.cluster_data()
            #DTC data
            self.feature_dtc_data()
            #NI data
            self.feature_ni_data()
            #Total DB objects
            self.data['db.objects_count'] = ou.onedb_object_count_get()
            #IBALIAS active record count
            self.data = common.fill_up_count_options(self.db, d=self.data, k='dns.ib_records.ibalias_count', \
               q='?dns.alias_record', o={'disabled':'false'}, dv=0)
            return self.data
        except Exception as e:
            ilog.log('Error occurred while fetch feature data : %s' % e)
            return ({'error': str(e)})

    def dump_dns_data(self):
        try:
            #DNS feature data
            self.feature_dns_data()
            return self.data
        except Exception as e:
            ilog.log('Error occurred while fetch feature dns data : %s' % e)
            return ({'error': str(e)})

    def dump_network_data(self):
        try:
            #network data
            self.feature_network_data()
            return self.data
        except Exception as e:
            ilog.log('Error occurred while fetch feature network data : %s' % e)
            return ({'error': str(e)})

    def dump_nios_data(self):
        try:
            #nios feature data
            self.feature_nios_data()
            return self.data
        except Exception as e:
            ilog.log('Error occurred while fetch feature nios data : %s' % e)
            return ({'error': str(e)})

    def dump_dns_records(self):
        try:
            #DNS feature records
            self.feature_dns_records()
            return self.data
        except Exception as e:
            ilog.log('Error occurred while fetch feature dns records : %s' % e)
            return ({'error': str(e)})

    def dump_zone_data(self):
        try:
            #Zone data
            self.feature_zone_data()
            return self.data
        except Exception as e:
            ilog.log('Error occurred while fetch feature zone data : %s' % e)
            return ({'error': str(e)})
        
    def dump_ipv4_ipv6_data(self):
        try:
            #Ipv4/Ipv6 data
            self.feature_ipv4_ipv6_data()
            return self.data
        except Exception as e:
            ilog.log('Error occurred while fetch feature Ipv4/Ipv6 data : %s' % e)
            return ({'error': str(e)})

    def __init__(self, db):
        self.data = {}
        self.db = db
        self.cluster_id = ou.get_my_cluster_id()
        
        #Cluster DHCP object
        self.cluster_dhcp_object = self.db.call('?dns.cluster_dhcp_properties',
                     {'cluster' : self.cluster_id},
                     single = True)
        
        #Cluster DNS object
        self.cluster_dns_object = self.db.call('?dns.cluster_dns_properties',
                     {'cluster' : self.cluster_id},
                     single = True)
