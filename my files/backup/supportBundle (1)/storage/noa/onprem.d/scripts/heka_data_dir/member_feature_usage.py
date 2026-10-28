#!/usr/bin/python

# This is the python script will capture all the Member Wide features

import infoblox.one.util as ou
import infoblox.one.onedb as onedb
import infoblox.common.ilog as ilog
import common_utils as common
#Importing the 'license' module will result in change of some of the keys in the db. Be informed about the same.
#import infoblox.one.license as lic
import json
import os
import re

class member_feature_usage():
    
    # DHCP specific data
    def feature_dhcp_data(self):
        if self.member_dhcp_object is not None:
            self.data['dhcp.service_enabled'] = False
            service_enabled = bool(self.member_dhcp_object['enable_service'])
            lan2_service_enabled = bool(self.member_dhcp_object['enable_lan2_service'])
            if service_enabled or lan2_service_enabled:
                self.data['dhcp.service_enabled'] = True

            self.data['dhcpv6.service_enabled'] = False
            v6_service_enabled = bool(self.member_dhcp_object['enable_dhcpv6_service'])
            lan2_v6_service_enabled = bool(self.member_dhcp_object['enable_v6_lan2_service'])
            if v6_service_enabled or lan2_v6_service_enabled:
                self.data['dhcpv6.service_enabled'] = True

            if bool(self.member_dhcp_object['use_enable_fingerprint']):
                self.data['dhcp.fingerprinting'] = bool(self.member_dhcp_object['enable_fingerprint'])
            else:
                self.data['dhcp.fingerprinting'] = bool(self.cluster_dhcp_object['enable_fingerprint'])

            self.data['dhcp.utf8_hostname_encoding'] = False
            v4 = bool(self.member_dhcp_object['use_windows_code_page'])
            v6 = bool(self.member_dhcp_object['use_v6_windows_code_page'])
            if v4 or v6:
                self.data['dhcp.utf8_hostname_encoding'] = True
            self.data['dhcp.override_boot_file'] = bool(self.member_dhcp_object['use_boot_file'])
            self.data['dhcp.override_boot_server'] = bool(self.member_dhcp_object['use_boot_server'])
            self.data['dhcp.override_next_server'] = bool(self.member_dhcp_object['use_next_server'])
            self.data['dhcp.pxe_lease_time_enabled'] = bool(self.member_dhcp_object['enable_pxe_lease_time'])
            self.data['dhcp.recycle_leases'] = bool(self.member_dhcp_object['recycle_leases'])
            
            if bool(self.member_dhcp_object['use_deny_bootp']):
                self.data['dhcp.deny_bootp'] = bool(self.member_dhcp_object['deny_bootp'])
            else: 
                self.data['dhcp.deny_bootp'] = bool(self.cluster_dhcp_object['deny_bootp'])

            self.data['dhcp.enable_ifmap'] = bool(self.member_dhcp_object['enable_ifmap'])
            self.data['dhcp.overload_bootp'] = bool(self.member_dhcp_object['overload_bootp'])

            if bool(self.member_dhcp_object['use_dns_update_style']):
                self.data['dhcp.dns_update_style'] = str(self.member_dhcp_object['dns_update_style'])
            else:
                self.data['dhcp.dns_update_style'] = str(self.cluster_dhcp_object['dns_update_style'])

            self.data['dhcp.virtual_node'] = self.virtual_node

            if bool(self.member_dhcp_object['use_enable_gss_tsig']):
                self.data['dhcp.enable_gss_tsig'] = bool(self.member_dhcp_object['enable_gss_tsig'])
            else:
                self.data['dhcp.enable_gss_tsig'] = bool(self.cluster_dhcp_object['enable_gss_tsig'])

            self.data['dhcp.use_gss_tsig_keys'] = bool(self.member_dhcp_object['use_gss_tsig_keys'])

            if bool(self.member_dhcp_object['use_v6_enable_gss_tsig']):
                self.data['dhcp.v6_enable_gss_tsig'] = bool(self.member_dhcp_object['v6_enable_gss_tsig'])
            else:
                self.data['dhcp.v6_enable_gss_tsig'] = bool(self.cluster_dhcp_object['v6_enable_gss_tsig'])

            if bool(self.member_dhcp_object['use_v6_leases_scavenging']):
                self.data['dhcp.v6_leases_scavenging_enabled'] = bool(self.member_dhcp_object['v6_leases_scavenging_enabled'])
                self.data['dhcp.v6_leases_scavenging_grace_period'] = int(self.member_dhcp_object['v6_leases_scavenging_grace_period'])
            else:
                self.data['dhcp.v6_leases_scavenging_enabled'] = bool(self.cluster_dhcp_object['v6_leases_scavenging_enabled'])
                self.data['dhcp.v6_leases_scavenging_grace_period'] = int(self.cluster_dhcp_object['v6_leases_scavenging_grace_period'])

            self.data = common.fill_up_count_options(self.db, d=self.data, k='dhcp.total_leases', \
                    q='?dns.lease', o={'node_id':self.virtual_node}, dv=0)
            self.data = common.fill_up_count_options(self.db, d=self.data, k='dhcp.active_leases', \
                    q='?dns.lease', o={'node_id':self.virtual_node, 'binding_state':"active"}, dv=0)
        else:
            ilog.log('Error: Member DHCP object not found for virtual node %d', self.virtual_node)

    # DNS specific data
    def feature_dns_data(self):
        if self.member_dns_object is not None:
            self.data['dns.service_enabled'] = bool(self.member_dns_object['enable_service'])
            if bool(self.member_dns_object['use_blacklist']):
                self.data['dns.blacklist_enabled'] = bool(self.member_dns_object['enable_blacklist'])
            else:
                self.data['dns.blacklist_enabled'] = bool(self.cluster_dns_object['enable_blacklist'])

            if bool(self.member_dns_object['use_recursive_query_setting']):
                self.data['dns.enable_recursion'] = bool(self.member_dns_object['recursion_enabled'])
            else:
                self.data['dns.enable_recursion'] = bool(self.cluster_dns_object['recursion_enabled'])

            if bool(self.member_dns_object['use_log_categories']):
                self.data['dns.log_queries'] = bool(self.member_dns_object['log_queries'])
            else:
                self.data['dns.log_queries'] = bool(self.cluster_dns_object['log_queries'])

            if bool(self.member_dns_object['use_enable_gss_tsig']):
                self.data['dns.enable_gss_tsig'] = bool(self.member_dns_object['enable_gss_tsig'])
            else:
                self.data['dns.enable_gss_tsig'] = bool(self.cluster_dns_object['enable_gss_tsig'])

            if bool(self.member_dns_object['use_update_setting']):
                self.data['dns.allow_gss_tsig_zone_updates'] = bool(self.member_dns_object['allow_gss_tsig_zone_updates'])
            else:
                self.data['dns.allow_gss_tsig_zone_updates'] = bool(self.cluster_dns_object['allow_gss_tsig_zone_updates'])

            if bool(self.member_dns_object['use_dns64']):
                self.data['dns.enable_dns64'] = bool(self.member_dns_object['enable_dns64'])
            else:
                self.data['dns.enable_dns64'] = bool(self.cluster_dns_object['enable_dns64'])

            if bool(self.member_dns_object['use_dns_health_check']):
                self.data['dns.dns_health_check_enabled'] = bool(self.member_dns_object['dns_health_check_enabled'])
            else:
                self.data['dns.dns_health_check_enabled'] = bool(self.cluster_dns_object['dns_health_check_enabled'])

            self.data['dns.virtual_node'] = self.virtual_node

            if common.get_db_count(self.db, '?dns.zone_grid_primary', {'grid_member':self.virtual_node}) != 0 or \
                common.get_db_count(self.db, '?dns.zone_cluster_secondary_server', {'member_address':self.virtual_node}) != 0:
                zone_dnssec_count = 0
                zones = self.db.call('?dns.zone',{'is_dnssec_signed':'true'})
                for zone in zones:
                    zone_pri = self.db.call('?dns.zone_grid_primary',
                        {'grid_member':self.virtual_node, 'zone':zone['__key']})
                    if zone_pri:
                        zone_dnssec_count += 1
                    else:
                        zone_sec = self.db.call('?dns.zone_cluster_secondary_server',
                            {'member_address':self.virtual_node, 'zone':zone['__key']})
                        if zone_sec:
                            zone_dnssec_count += 1
                self.data['zone.signed_zone'] = zone_dnssec_count
            else:
                self.data['zone.signed_zone'] = 0

            if bool(self.member_dns_object['use_dnssec']):
                self.data['dns.dnssec'] = bool(self.member_dns_object['enable_dnssec'])
            else:
                self.data['dns.dnssec'] = bool(self.cluster_dns_object['enable_dnssec'])

            self.data['dns.dns_over_v6_lan2'] = bool(self.member_dns_object['dns_over_v6_lan2'])
            self.data['dns.dns_over_v6_mgmt'] = bool(self.member_dns_object['dns_over_v6_mgmt'])
            self.data['dns.dns_over_v6_lan'] = bool(self.member_dns_object['dns_over_v6_lan'])


        else:
            ilog.log('Error: Member DNS object not found for virtual node %d', self.virtual_node)

    # services data
    def service_data(self):
            
            self.data = common.fill_up_bool_option(self.db, d=self.data, k='captive_portal.service_enabled', \
                        q='?one.member_captive_portal_properties', \
                            o={'service_enabled': True, 'virtual_node': self.virtual_node}, \
                                limit=1, dv=False)
            self.data = common.fill_up_bool_option(self.db, d=self.data, k='dfp.service_enabled', \
                        q='?one.member_dfp_properties', \
                            o={'service_enabled': True, 'virtual_node': self.virtual_node}, \
                                limit=1, dv=False)
            self.data = common.fill_up_bool_option(self.db, d=self.data, k='unbound.service_enabled', \
                        q='?dns.member_dns_properties', \
                            o={'dns_resolver_type':'UNBOUND', 'virtual_node': self.virtual_node}, \
                                limit=1, dv=False)

    # DTC data 
    def feature_dtc_data(self):
        vnode = str(self.virtual_node)
        self.data['dtc.lbdn'] = len(self.vnode_lbdn[vnode]) if vnode in self.vnode_lbdn else 0
        if self.data['dtc.lbdn'] == 0:
            self.data['dtc.pools'] = 0
            self.data['dtc.gslb_round_robin'] = 0
            self.data['dtc.gslb_global_availability'] = 0
            self.data['dtc.gslb_all_available'] = 0
            self.data['dtc.gslb_ratio_fixed'] = 0
            self.data['dtc.gslb_ratio_dynamic'] = 0
            self.data['dtc.gslb_topology'] = 0
            self.data['dtc.servers'] = 0
            self.data['dtc.monitors'] = 0
            self.data['dtc.zones_with_lbdn'] = 0
            self.data['dtc.avg_object_count'] = 0
            self.data['dtc.health_checks'] = 0
            return
        self.data['dtc.pools'] = len(self.vnode_pool[vnode]) if vnode in self.vnode_pool else 0
        self.data['dtc.servers'] = len(self.vnode_server[vnode]) if vnode in self.vnode_server else 0
        self.data['dtc.monitors'] = len(self.vnode_monitor[vnode]) if vnode in self.vnode_monitor else 0

        gslb_round_robin = 0
        gslb_global_availability = 0
        gslb_all_available = 0
        gslb_ratio_fixed = 0
        gslb_ratio_dynamic = 0
        gslb_topology = 0
        for pool in self.vnode_pool[vnode]:
            if self.idns_pool[pool] == 'ROUND_ROBIN':
                gslb_round_robin += 1
            if self.idns_pool[pool] == 'GLOBAL_AVAILABILITY':
                gslb_global_availability += 1
            if self.idns_pool[pool] == 'ALL_AVAILABLE':
                gslb_all_available += 1
            if self.idns_pool[pool] == 'RATIO':
                gslb_ratio_fixed += 1
            if self.idns_pool[pool] == 'DYNAMIC_RATIO':
                gslb_ratio_dynamic += 1
            if self.idns_pool[pool] == 'TOPOLOGY':
                gslb_topology += 1

        self.data['dtc.gslb_round_robin'] = gslb_round_robin
        self.data['dtc.gslb_global_availability'] = gslb_global_availability
        self.data['dtc.gslb_all_available'] = gslb_all_available
        self.data['dtc.gslb_ratio_fixed'] = gslb_ratio_fixed
        self.data['dtc.gslb_ratio_dynamic'] = gslb_ratio_dynamic
        self.data['dtc.gslb_topology'] = gslb_topology

        self.data['dtc.zones_with_lbdn'] = 0
        auth_zones_count = common.get_db_count(self.db, '?dns.zone', {'zone_type':'Authoritative'})

        zones = []
        lbdns = self.db.call('dns.get_idns_lbdn_zone_links_assigned_to_member',
            {'member_oid': self.virtual_node, 'disabled': False}, factory=onedb.todict)
        for lbdn in lbdns:
            zones.append(lbdn['zone'])
        # unique_zones_with_lbdn = list(set(zones))
        zones_with_lbdn = len(set(zones))
        self.data['dtc.zones_with_lbdn'] = zones_with_lbdn 

        self.data['dtc.avg_object_count'] = 0
        if zones_with_lbdn > 0 and auth_zones_count > 0:
            self.data['dtc.avg_object_count'] = float(zones_with_lbdn)/float(auth_zones_count)

        health_checks = 0
        self.data['dtc.health_checks'] = 0
        for pool in self.vnode_pool[vnode]:
              if pool in  self.pool_monitor:
                pool_monitors = self.pool_monitor[pool]
                health_checks += len(pool_monitors)
        self.data['dtc.health_checks'] = health_checks
        
    # NI feature data
    def feature_ni_data(self):
        managed_devices = 0
        interfaces = 0
        discovery = self.db.call('?discovery.statistics',
            {'parent': self.virtual_node}, single = True)
        if discovery:
            managed_devices = int(discovery['hosts_managed'])
            interfaces = int(discovery['networks_managed'])
        self.data['ni.managed_devices'] = managed_devices
        self.data['ni.interfaces'] = interfaces

    # Node feature data
    def feature_node_data(self):
        pnode_data = self.db.call('?one.physical_node',
                    {'physical_oid':int(self.pnode['physical_oid'])}, single = True)
        vnode_data = pnode_data['virtual_node'].fetch()
        virtual_ip_data = self.db.call('?one.member_virtual_ip',{'virtual_node':self.virtual_node})
        lan1_ipv4_count = 0
        lan1_ipv6_count = 0
        mgmt_ipv4_count = 0
        mgmt_ipv6_count = 0
        lan2_ipv4_count = 0
        lan2_ipv6_count = 0
        loopback_ipv4_count = 0
        loopback_ipv6_count = 0

        if vnode_data['virtual_ip'] != None:
            lan1_ipv4_count += 1
        if vnode_data['gateway'] != None:
            lan1_ipv4_count += 1

        # Node1 HA (IPv4)
        if pnode_data['ha_ip_address'] != None:
            lan1_ipv4_count += 1

        # Node1 LAN1 (IPv4)
        if pnode_data['public_ip_address'] != None and vnode_data['virtual_ip'] != None:
            if pnode_data['public_ip_address'] != vnode_data['virtual_ip']:
                # For HA cluster
                lan1_ipv4_count += 1

        if vnode_data['v6_virtual_ip'] != None:
            lan1_ipv6_count += 1
        if vnode_data['v6_gateway'] != None:
            lan1_ipv6_count += 1

        #MGMT for ipv4 and ipv6
        if pnode_data['mgmt_port_address'] != None:
            mgmt_ipv4_count += 1
        if pnode_data['mgmt_port_gateway'] != None:
            mgmt_ipv4_count += 1

        if pnode_data['v6_mgmt_port_address'] != None:
            mgmt_ipv6_count += 1
        if pnode_data['v6_mgmt_port_gateway'] != None:
            mgmt_ipv6_count += 1

        # Node1 LAN1 (IPv6)
        if pnode_data['v6_public_ip_address'] != None and vnode_data['v6_virtual_ip'] != None:
            if pnode_data['v6_public_ip_address'] != vnode_data['v6_virtual_ip']:
                lan1_ipv6_count += 1


        # +2 indicates ip + gateway address
        for item in virtual_ip_data:
            # below check is usefull for member and LAN_HA
            if item['interface_type'] == 'LAN_HA':
                if item['cidr'] <= 32:
                    is_ipv4 = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", item['v_ip'])
                    if is_ipv4:
                        lan1_ipv4_count += 2
                    else:
                        lan1_ipv6_count += 2
                else:
                    lan1_ipv6_count += 2

            # LAN2
            if item['interface_type'] == 'LAN2':
                if item['cidr'] <= 32:
                    is_ipv4 = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", item['v_ip'])
                    if is_ipv4:
                        lan2_ipv4_count += 2
                    else:
                        lan2_ipv6_count += 2
                else:
                    lan2_ipv6_count += 2

            # LOOPBACK
            if item['interface_type'] == 'LOOPBACK':
                if item['cidr'] <= 32:
                    is_ipv4 = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", item['v_ip'])
                    if is_ipv4:
                        loopback_ipv4_count += 1
                    else:
                        loopback_ipv6_count += 1
                else:
                    loopback_ipv6_count += 1

        self.data['vnode.lan1_ipv4_count'] = lan1_ipv4_count
        self.data['vnode.lan1_ipv6_count'] = lan1_ipv6_count
        self.data['vnode.mgmt_ipv4_count'] = mgmt_ipv4_count
        self.data['vnode.mgmt_ipv6_count'] = mgmt_ipv6_count
        self.data['vnode.lan2_ipv4_count'] = lan2_ipv4_count
        self.data['vnode.lan2_ipv6_count'] = lan2_ipv6_count
        self.data['vnode.loopback_ipv4_count'] = loopback_ipv4_count
        self.data['vnode.loopback_ipv6_count'] = loopback_ipv6_count

        self.data['virtual_ip.is_v6'] = False
        if lan1_ipv6_count > 0:
            self.data['virtual_ip.is_v6'] = True

        self.data['vnode.auto_lan1_enabled'] = bool(pnode_data['enable_auto_lan'])
        self.data['vnode.auto_lan2_enabled'] = bool(pnode_data['enable_auto_lan2'])
        self.data['vnode.ha_enabled'] = bool(vnode_data['ha_enabled'])
        self.data['vnode.auto_mgmt_enabled'] = bool(pnode_data['enable_auto_mgmt'])

        self.data['vnode.mgmt_has_address'] = False
        if pnode_data['mgmt_port_address'] != None or pnode_data['v6_mgmt_port_address'] != None:
            self.data['vnode.mgmt_has_address'] = True

        self.data['vnode.lan1_has_address'] = False
        if vnode_data['virtual_ip'] != None or vnode_data['v6_virtual_ip'] != None:
            self.data['vnode.lan1_has_address'] = True

        self.data['vnode.lan2_has_address'] = False
        for item in virtual_ip_data:
            if item['interface_type'] == 'LAN2':
                self.data['vnode.lan2_has_address'] = True
                break

        self.data['vnode.nic_failover_enabled'] = bool(vnode_data['nic_failover_enabled'])
        self.data['vnode.ha_active_position'] = int(vnode_data['active_position'])
        self.data['vnode.nat_enabled'] = bool(vnode_data['nat_enabled'])

    def dump(self):
        try:
            if (self.cluster_dhcp_object is None) or (self.cluster_dns_object is None):
                ilog.log('Error: Cluster object not found')
                return({'error':'Cluster Object not found'})
            #DHCP feature data
            self.feature_dhcp_data()
            #DNS feature data
            self.feature_dns_data()	
            #Services data
            self.service_data()
            #DTC feature data
            self.feature_dtc_data()
            #NI feature data
            self.feature_ni_data()
            #Node data
            self.feature_node_data()

            return self.data
        except Exception as e:
            ilog.log('Error occurred while fetch member feature data : %s' % e)
            return ({'error': str(e)})
        
    def init(self, node):
        self.pnode = node
        self.virtual_node = int(node['virtual_node'])

        #Member DHCP object
        self.member_dhcp_object = self.db.call('?dns.member_dhcp_properties',
                     {'virtual_node' : self.virtual_node},
                     single = True)

        #Member DNS object
        self.member_dns_object = self.db.call('?dns.member_dns_properties',
                     {'virtual_node' : self.virtual_node},
                     single = True)

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

        # Fetch all necessary data from the database once to optimize performance.
        self.fetch_data()

    def fetch_data(self):
        self.IDNS_LBDN = '?dns.idns_lbdn'
        self.IDNS_LBDN_POOL='?dns.idns_lbdn_pool'
        self.IDNS_LBDN_ZONE = '?dns.idns_lbdn_zone'
        self.IDNS_POOL='?dns.idns_pool'
        self.IDNS_SERVER='?dns.idns_server'
        self.IDNS_POOL_SERVER='?dns.idns_pool_server'
        self.IDNS_POOL_MONITOR='?dns.idns_pool_monitor'
        self.IDNS_LBDN_POOL_MONITOR='?dns.idns_pool_monitor'
        self.NS_GROUP_GRID_PRIMARY = '?dns.ns_group_grid_primary'
        self.ZONE_GRID_PRIMARY='?dns.zone_grid_primary'
        
        # Fetch LBDNs
        self.lbdns = self.db.call(self.IDNS_LBDN, factory = onedb.todict)
    
        # Fetch and group LBDN zones by zone name
        self.lbdnzones = {}
        lbdn_zones = self.db.call(self.IDNS_LBDN_ZONE, factory = onedb.todict)
        for zone in lbdn_zones:
            zone_name = zone['zone']
            if zone_name not in self.lbdnzones:
                self.lbdnzones[zone_name] = set()
            self.lbdnzones[zone_name].add(zone['parent'])
        
        # Fetch name server groups and group virtual nodes by name server group
        self.vnode_nsg = {}
        self.nsg_pris = self.db.call(self.NS_GROUP_GRID_PRIMARY, factory = onedb.todict)
        for nsg in self.nsg_pris:
            if nsg['ns_group'] not in self.vnode_nsg:
                self.vnode_nsg[nsg['ns_group']] = set()
            self.vnode_nsg[nsg['ns_group']].add(nsg['grid_member'])
      
        # Fetch and group zones (created using nameservers) by virtual node
        self.vnode_lbdn = {}
        self.prizones = self.db.call(self.ZONE_GRID_PRIMARY, factory = onedb.todict)
        for zone in self.prizones:
            zone_name = zone['zone']
            if zone_name in self.lbdnzones:
                if zone['grid_member'] not in self.vnode_lbdn:
                    self.vnode_lbdn[zone['grid_member']] = set()
                self.vnode_lbdn[zone['grid_member']].update(self.lbdnzones[zone_name])

        # Fetch and group zones (created using name server groups) by virtual node
        self.zones = self.db.call('?dns.zone', {'primary_type' : 'Grid'}, factory=onedb.todict)
        for zone in self.zones: 
            if zone['__key'] not in self.lbdnzones:
                continue
            if 'ns_group' in zone and zone['ns_group'] in self.vnode_nsg:
                vnodes = self.vnode_nsg[zone['ns_group']] 
                for vnode in vnodes:
                    if vnode not in self.vnode_lbdn:
                        self.vnode_lbdn[vnode] = set()
                    self.vnode_lbdn[vnode].update(self.lbdnzones[zone['__key']])

        # Fetch DNS pools and store their preferred methods
        self.idns_pool = {}
        self.idnspools = self.db.call(self.IDNS_POOL, factory = onedb.todict)
        for pool in self.idnspools: 
            self.idns_pool[pool['name']] = pool['preferred_method']

        # Fetch and group LBDN pools by lbdn
        self.lbdn_pools = {}
        self.pools = self.db.call(self.IDNS_LBDN_POOL, factory = onedb.todict)
        for pool in self.pools:
            if pool['parent'] not in self.lbdn_pools:
                self.lbdn_pools[pool['parent']] = set()
            self.lbdn_pools[pool['parent']].add(pool['idns_pool'])

        # Group all pools by virtual node
        self.vnode_pool = {}
        for node, pools in self.vnode_lbdn.items():
            self.vnode_pool[node] = set()
            for lbdn in pools:
                self.vnode_pool[node].update(self.lbdn_pools[lbdn])
        
        # Fetch and group servers by pool
        self.pool_server = {}
        self.servers = self.db.call(self.IDNS_POOL_SERVER, factory = onedb.todict)
        for server in self.servers:
            if server['parent'] not in self.pool_server:
                self.pool_server[server['parent']] = set()
            self.pool_server[server['parent']].add(server['server'])

        # Group all servers by virtual node
        self.vnode_server = {}
        for node, pools in self.vnode_pool.items():
            self.vnode_server[node] = set()
            for pool in pools:
                self.vnode_server[node].update(self.pool_server[pool])

        # Fetch and group monitors by pool
        self.pool_monitor = {}
        self.monitors = self.db.call(self.IDNS_POOL_MONITOR, factory = onedb.todict)
        for monitor in self.monitors:
            if monitor['parent'] not in self.pool_monitor:
                self.pool_monitor[monitor['parent']] = set()
            self.pool_monitor[monitor['parent']].add(monitor['monitor'])

         # Group all monitors by virtual node
        self.vnode_monitor = {}
        for node, pools in self.vnode_pool.items():
            self.vnode_monitor[node] = set()
            for pool in pools:
                if pool in self.pool_monitor:
                    self.vnode_monitor[node].update(self.pool_monitor[pool])
