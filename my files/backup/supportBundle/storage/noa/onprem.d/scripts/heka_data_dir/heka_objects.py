#!/usr/bin/python

import json
import os
import re
import infoblox.one.util as ou
import infoblox.one.onedb as onedb
import infoblox.common.ilog as ilog
import infoblox.one.base as base
import common_utils as common
from grid_feature_usage import grid_feature_usage
from member_feature_usage import member_feature_usage
from ssl_cert import SSLCert
import infoblox.reporting.reporting_common as rc
import infoblox.reporting.splunk_lib as sl


Permitted_driver_type_list = ['AWS', 'Azure','GCP']
NIOS_VERSION = int(common.nios_version())

LICENSE_USAGE_PER_INDEX = 'index=_internal source="*license_usage.log" \
                           type=usage (idx=*) earliest=-1d@d latest=@d | \
                           timechart span=1d sum(b) by idx | addtotals '

LICENSE_CAPACITY = 'index=_internal "type=RolloverSummary" earliest=-1d@d \
                    latest=@d | stats sum(b) as LicenseUsage  max(poolsz) \
                    as LicenseCapacity by _time | table _time, LicenseUsage, LicenseCapacity'



def fetch_reporting_data():

    data = {}
    if NIOS_VERSION < 904:
        data['reporting'] = {}
        return data
    db = onedb.Db()
    indexes = {
        'ib_audit' : 0,
        'ib_dns' : 0,
        'ib_dns_capture': 0,
        'ib_dhcp': 0,
        'ib_dhcp_lease_history': 0,
        'ib_ipam': 0,
        'ib_discovery': 0,
        'ib_security': 0,
        'ib_dtc': 0,
        'ib_cloud': 0,
        'ib_syslog': 0,
        'ib_system_capacity': 0,
        'ib_system': 0,
        'ib_ecosystem_subscription': 0,
        'ib_ecosystem_publish': 0,
        'ib_license': 0
    }
    with db.begin():
        reporting_obj = db.call('?reporting.cluster_reporting_properties', single=True, factory=onedb.todict)
        reporting_member = db.call('?reporting.member_reporting_properties',{"role":"SEARCH_HEAD_INDEXER"},single=True ,factory=onedb.todict)
        if reporting_obj == None or reporting_member == None:
            return data
        password = rc.splunk_password(db)
    connection = sl.SplunkConnection
    reporting = {}
    usage_dict = {}
    reporting['reporting_configuration'] = reporting_obj['cluster_mode']

    if reporting_member['use_enable'] == True and reporting_member['enable'] == False:
        data['reporting'] = reporting
        return data
    elif reporting_member['use_enable'] == False and reporting_obj['enable'] == False:
        data['reporting'] = reporting
        return data

    try :
        with connection(password=password) as sc:
            try:
                for result in sc.search(LICENSE_CAPACITY):
                    if result and 'LicenseUsage' in result and 'LicenseCapacity' in result:
                        reporting['reporting_license_capacity_mb'] = round(int(result['LicenseCapacity']) / (1024 * 1024), 2)
                        reporting['total_daily_usage_mb'] = round(int(result['LicenseUsage']) / (1024 * 1024), 2)
            except base.IBDataError as e:
                ilog.log('License capactiy and total daily usage not available for reporting data: %s' % e)
            except Exception as e:
                ilog.log('Error occurred from license capacity search : %s' % e)
            try:
                for usage in sc.search(LICENSE_USAGE_PER_INDEX):
                    if usage:
                        usage_dict = usage
            except base.IBDataError as e:
                ilog.log('License usage per index not available for reporting data : %s' % e)
            except Exception as e:
                ilog.log('Error occurred from license usage per index : %s' % e)
    except base.IBDataError as e:
        ilog.log('Not able to establish splunk connection : %s' % e)
    except Exception as e:
        ilog.log('Error occurred while connecting to splunk : %s' % e)

    for index in usage_dict:
        if index in indexes:
            indexes[index] = round(int(usage_dict[index]) / (1024 * 1024), 2)
    reporting['license_usage_per_index_mb'] = indexes
    data['reporting'] = reporting
    return data


def initialize_counts(platforms):
    platform_dict = {}
    for platform in platforms:
        platform_dict[platform] = 0
    return platform_dict

def count_items(items, key, platforms):
    counts = initialize_counts(platforms)
    for item in items:
        if item[key] in counts:
            counts[item[key]] += 1
    return counts

def get_dns_accounts(db):
    dns_account = []
    zones_query = "SELECT DISTINCT(provider_account) FROM .com.infoblox.dns.zone_provider_primary"
    zones_pr = db.call(zones_query, factory=onedb.todict)
    for tenant in zones_pr:
        pattern = r'^(.*?)@'
        match = re.search(pattern, tenant['__key'])
        if not match:
            continue
        zone = match.group(1)
        params = {
            "object": ".com.infoblox.dns.zone$" + zone,
            "tag_tenant_id": ".DNS Source",
            "amazon": "AWS R53",
            "azure": "Azure DNS",
        }
        ten_query = "select object,tag,value from one.extensible_attributes_value where\
                    (&\
                        (&(tag='${tag_tenant_id}')(object='${object}'))\
                        (|(value='${azure}')(value='${amazon}'))\
                    )"
        ten_ea_dict = db.call(ten_query, params, factory=onedb.todict)
        dns_account += ten_ea_dict
    return dns_account

def get_number_of_cloud_accounts(db):
    cloud_tenants = []
    all_tenants = db.call('?dns.tenant', factory=onedb.todict)
    for tenant in all_tenants:
        params = {
            "tenant_id": tenant['unique_id'],
            "tag_tenant_id": ".Tenant ID",
            "tag_cmp_type": ".CMP Type",
            "amazon": "Amazon",
            "azure": "Azure",
            "gcp": "GCP",
        }
        ten_query = "SELECT object,tag,value FROM one.extensible_attributes_value WHERE (|(|(|(&(tag='${tag_tenant_id}')(value='${tenant_id}'))(&(tag='${tag_cmp_type}')(value='${amazon}')))(&(tag='${tag_cmp_type}')(value='${azure}')))(&(tag='${tag_cmp_type}')(value='${gcp}')))"
        ten_ea_dict = db.call(ten_query, params, factory=onedb.todict)
        ten_asso_objs = set()
        obj_to_cmp_type = {}
        for ext in ten_ea_dict:
            tag = ext['tag']
            value = ext['value']
            obj = ext['object']
            if tag == '.Tenant ID' and value == tenant['unique_id']:
                ten_asso_objs.add(obj)
            if tag == '.CMP Type':
                obj_to_cmp_type[obj] = value
        platform = ''
        for obj in ten_asso_objs:
            cmp_type = obj_to_cmp_type.get(obj)
            if cmp_type:
                platform = cmp_type
                break
        if platform:
            cloud_tenants.append({'platform': platform})
    return cloud_tenants


def get_total_number_of_subnets(db):
    q_teanant_ids = "SELECT DISTINCT(vmi_tenant_id) FROM dns.discovery_data"
    
    tenant_ids = db.call(q_teanant_ids, single=False,factory=onedb.todict)
    tenant_ids = [item.get('vmi_tenant_id') for item in tenant_ids]

    nw_objs = set()
    cmp_type = []
    for tenant_id in tenant_ids:
        params= {
            'tag_tenant_id': '.Tenant ID',
            'tag_is_shared': '.Is Shared',
            'tag_is_external': '.Is External',
            'tag_cmp_type': '.CMP Type',
            'is_sh_ext': 'True',
            'tag_vm_id' : '.VM ID',
        }
        q = "SELECT object,tag,value FROM one.extensible_attributes_value "\
            "WHERE (|(|(|(tag='${tag_tenant_id}')(tag='${tag_vm_id}'))" \
            "(&(tag='${tag_is_shared}')(value='${is_sh_ext}')))" \
            "(&(tag='${tag_is_external}')(value='${is_sh_ext}')))"
        ext_vals = db.call(q, params, factory=onedb.todict)
        for ext_val in ext_vals:
            tag = ext_val.get('tag')
            value = ext_val.get('value')
            obj = ext_val.get('object')
            network_type = '.com.infoblox.dns.network$'
            if (tag == '.Tenant ID' and value == tenant_id) or \
               (tag in ('.Is Shared', '.Is External')):
                if network_type in obj:
                    args = {
                        'tenant_id': obj,
                        'tag': '.CMP Type'
                    }
                    query = "SELECT value FROM one.extensible_attributes_value " \
                    "WHERE (&(object='${tenant_id}')(tag='${tag}'))"
                    subnets_platfrom = db.call(query, args, factory=onedb.todict)
                    for subnet in subnets_platfrom:
                        cmp_type.append({'value': subnet.get('value')})
                    nw_objs.add(obj)
    return cmp_type

def get_count_of_networks_with_routing_reals(db):
    query = "SELECT COUNT(DISTINCT(parent)) AS record_count FROM .com.infoblox.dns.federated_realm_association"
    l = db.call(query, {})
    return l[0]['record_count']

def get_total_number_of_vpc():
    db = onedb.Db()
    q = "SELECT object FROM one.extensible_attributes_value WHERE (tag='${vpc_tag}')"
    vpc_objects = db.call(q,{'vpc_tag':'.VPC Name'},single=False,factory=onedb.todict)
    vpc = []
    for vpc_object in vpc_objects :
        params= {
                "object": vpc_object['object'],
                "tag":".CMP Type"
        }
        query = "SELECT value FROM one.extensible_attributes_value WHERE (&(object='${object}')(tag='${tag}'))"
        vpc += db.call(query,params,factory=onedb.todict)
    return vpc

def get_total_number_of_vms(db):

    q_teanant_ids = "SELECT DISTINCT(vmi_tenant_id) FROM dns.discovery_data"
    tenant_ids = db.call(q_teanant_ids, single=False,factory=onedb.todict)
    tenant_ids = [item.get('vmi_tenant_id') for item in tenant_ids]

    cmp_type = []
    vm_ids = set()
    for tenant_id in tenant_ids:
        args = {'tenant_id': tenant_id}
        query = "SELECT vmi_id,cmp_type FROM dns.discovery_data " \
                "WHERE vmi_tenant_id='${tenant_id}'"
        for item in db.call(query, args=args, factory=onedb.todict):
            vm_id = item.get('vmi_id')
            if vm_id is not None:
                if vm_id in vm_ids:
                    continue
                else :
                    vm_ids.add(vm_id)
                    cmp_type.append({'platform':item.get('cmp_type')})
    return cmp_type

def get_total_number_of_used_ips(db):
    q_teanant_ids = "SELECT DISTINCT(vmi_tenant_id) FROM dns.discovery_data"
    tenant_ids = db.call(q_teanant_ids, single=False,factory=onedb.todict)
    tenant_ids = [item.get('vmi_tenant_id') for item in tenant_ids]
    ip_address = []
    for tenant_id in tenant_ids:
        q = "SELECT ip_address, cmp_type FROM dns.discovery_data WHERE vmi_tenant_id = '${tenant_id}'"
        params = {'tenant_id': tenant_id}
        ips = db.call(q, params, single=False, factory=onedb.todict)
        ip_address += ips
    return (ip_address)

def fetch_pnode():
    data = {}
    db = onedb.Db()
    with db.begin(onedb.RO) as txn:
        pnode = common.get_db_data(db, '?one.physical_node')
        if pnode:
            data['pnode'] = pnode
            heka_flag = False
            public_ip = {}
            passive_member = []
            obj = member_feature_usage(db)
            for i, node in enumerate(pnode):
                if NIOS_VERSION >= 905:
                    heka_stat = "/storage/noa/onprem.d/heka/heka_stat_%s"%node['physical_oid']
                else:
                    heka_stat = "/storage/heka/heka_stat_%s"%node['physical_oid']
                if os.path.isfile(heka_stat):
                    try:
                        with open(heka_stat) as f:
                            data['pnode'][i]['member_data'] = json.load(f)
                            virtual_oid = node['virtual_node']
                            data['pnode'][i]['member_data']['virtual_oid'] = virtual_oid
                            if 'public_ip_enabled' in data['pnode'][i]['member_data']:
                                public_ip[virtual_oid] = data['pnode'][i]['member_data']['public_ip_enabled']
                            else: #stat file for passive will not have public_ip_enabled key
                                passive_member.append(data['pnode'][i]['member_data'])
                            if 'heka' in data['pnode'][i]['member_data']:
                                heka_flag = True
                    except Exception as e:
                        ilog.log('Error occurred while reading heka_stat file : %s' % e)
                else:
                    data['pnode'][i]['member_data'] = {}
                    data['pnode'][i]['member_data']['current_version'] = "Pending"
                if  NIOS_VERSION >= 905:
                    paygo_details = db.call('?one.cloud_platform_details',{'parent': data['pnode'][i]['physical_oid']}, single=True)
                    if paygo_details:
                        data['pnode'][i]['cloud_vendor_region'] = paygo_details['cloud_vendor_region']
                        data['pnode'][i]['cloud_instance_type'] = paygo_details['cloud_instance_type']
                        data['pnode'][i]['cloud_image_id'] = paygo_details['cloud_image_id']
                        data['pnode'][i]['cloud_product_code'] = paygo_details['cloud_product_code']
                index = int(node['virtual_node'])
                obj.init(node)
                member_feature_data = obj.dump()
                data['pnode'][i]['member_feature_usage'] = dict(member_feature_data)
                vnode_obj = db.call('?one.virtual_node',{'virtual_oid' : index }, single = True)
                if vnode_obj is not None:
                    data['pnode'][i]['member_data']['member_type'] = vnode_obj['member_type']
                    data['pnode'][i]['member_data']['virtual_oid'] = int(vnode_obj['virtual_oid'])
                else:
                    ilog.log('Error : Virtual node schema not present for %s', i)
                    data['pnode'][i]['member_data']['member_type'] = 'Unknown'
                    data['pnode'][i]['member_data']['virtual_oid'] = 0
            for node in passive_member:
                node['public_ip_enabled'] = public_ip.get(str(node['virtual_oid']), False)
            if not heka_flag:
                return {'info':'User not accessed HEKA EULA page'}
        else:
            data['pnode'] = []
    return data

def fetch_vnode():
    data = {}
    db = onedb.Db()
    with db.begin(onedb.RO) as txn:
        data = common.fill_up(db, d=data, k='vnode', q='?one.virtual_node', dv=[])
    return data

def fetch_federation():
    data = {}
    db = onedb.Db()
    with db.begin(onedb.RO) as txn:
        if NIOS_VERSION >= 904:
            grid = db.call('?one.cluster', {'cluster_oid': ou.get_my_cluster_id()}, factory=onedb.todict, single=True)
            federation = {'federation_enabled': grid['federation_enabled'],
                            'routing_realms_count': int(get_count_of_networks_with_routing_reals(db))}
        else:
            federation = {'federation_enabled':False, 'routing_realms_count': 0}
        data['federation'] = federation

    return data

def fetch_multicloud():
    data = {}
    db = onedb.Db()
    with db.begin(onedb.RO) as txn:
        if NIOS_VERSION >= 904:
            cdns_features = {}
            cdns_service_object = db.call('?one.member_cloud_dns_sync_properties', factory=onedb.todict)
            aws_task_groups = db.call('?one.aws_rte53_task_group', factory=onedb.todict)
            aws_tasks = db.call('?one.aws_rte53_task', factory=onedb.todict)
            dns_accounts = get_dns_accounts(db)
            grouped_accounts = {
                "Amazon" : 0,
                "Azure" : 0
            }
            for account in dns_accounts:
                if account['value'] == 'AWS R53':
                    grouped_accounts["Amazon"] += 1
                elif account['value'] == 'Azure DNS':
                    grouped_accounts["Azure"] += 1
            cdns_features['cdns_feature_enabled'] = False
            cdns_features['aws_rte53_zone_info'] = common.get_db_count(db,'?dns.aws_rte53_zone_info')
            cdns_features['aws_rte53_record_info'] = common.get_db_count(db,'?dns.aws_rte53_record_info')
            cdns_features['number_of_accounts'] = grouped_accounts
            cdns_features['cloud_providers'] = []
            for i, item in enumerate(aws_task_groups):
                cloud_info = {}
                cloud_info['cloud_provider'] = "AWS"
                cloud_info['sync_child_accounts'] = item['sync_child_accounts']
                cloud_info['multiple_accounts_sync_policy'] = item['multiple_accounts_sync_policy']
                for j, task in enumerate(aws_tasks):
                    parent = task['__key'].split('.')[0]
                    if parent == item['__key']:
                        cloud_info['cloud_provider_sync_interval'] = task['sync_interval']
                        break
                cdns_features['cloud_providers'].append(cloud_info)
            azure_tasks = db.call('?one.azure_dns_task', factory=onedb.todict)
            azure_task_groups = db.call('?one.azure_dns_task_group', factory=onedb.todict)
            cdns_features['azure_dns_zone_info'] = common.get_db_count(db,'?dns.azure_dns_zone_info')
            cdns_features['azure_dns_record_info'] = common.get_db_count(db,'?dns.azure_dns_record_info')
            for i, item in enumerate(azure_task_groups):
                cloud_info = {}
                cloud_info['cloud_provider'] = "Azure"
                cloud_info['sync_child_accounts'] = item['sync_child_subscriptions']
                cloud_info['multiple_accounts_sync_policy'] = item['multiple_subscriptions_sync_policy']
                for j, task in enumerate(azure_tasks):
                    parent = task['__key'].split('.')[0]
                    if parent == item['__key']:
                        cloud_info['cloud_provider_sync_interval'] = task['sync_interval']
                        break
                cdns_features['cloud_providers'].append(cloud_info)
            if cdns_service_object:
                if cdns_service_object[0]['cloud_dns_sync_enabled'] and (aws_tasks or azure_tasks) :
                    cdns_features['cdns_feature_enabled'] = True
            data['multi_cloud'] = cdns_features
        else:
            cdns_features = {}
            cdns_features['cloud_providers'] = []
            data['multi_cloud'] = cdns_features
    return data

def fetch_vdiscovery():
    data = {}
    db = onedb.Db()
    with db.begin(onedb.RO) as txn:
        if NIOS_VERSION >= 904:
            cdiscovery_task = db.call('?dns.cdiscovery_task')
            permitted_driver_type_exists = False
            vdiscovery_feature = {}
            vdiscovery_feature['cloud_vdiscovery_feature_enabled'] = False

            vms_platform = ['Amazon', 'Azure', 'GCP', 'OpenStack']
            vpc_platform = ['Amazon', 'Azure', 'GCP']

            vms = get_total_number_of_vms(db)
            vpc_tenants = get_total_number_of_vpc()
            subnets = get_total_number_of_subnets(db)
            cloud_tenants = get_number_of_cloud_accounts(db)
            ip_address = get_total_number_of_used_ips(db)

            number_of_vms = count_items(vms, 'platform', vms_platform)
            number_of_vpc = count_items(vpc_tenants, 'value', vpc_platform)
            number_of_subnets = count_items(subnets, 'value', vms_platform)
            number_of_cloud = count_items(cloud_tenants, 'platform', vpc_platform)
            number_of_used_ips = count_items(ip_address, 'cmp_type', vms_platform)

            vdiscovery_feature['number_of_cloud_accounts'] = number_of_cloud
            vdiscovery_feature['total_number_of_vpc'] = number_of_vpc
            vdiscovery_feature['total_number_of_subnets'] = number_of_subnets
            vdiscovery_feature['total_number_of_vms'] = number_of_vms
            vdiscovery_feature['total_number_of_used_ips'] = number_of_used_ips
            vdiscovery_feature['vdiscovery_providers'] = []
            weekday_map = {
                        "MON": "Monday",
                        "TUE": "Tuesday",
                        "WED": "Wednesday",
                        "THU": "Thursday",
                        "FRI": "Friday",
                        "SAT": "Saturday",
                        "SUN": "Sunday"
                    }
            for _, item in enumerate(cdiscovery_task):
                vdiscovery_info = {}
                if permitted_driver_type_exists == False:
                    if item['driver_type'] in Permitted_driver_type_list:
                        permitted_driver_type_exists = True
                vdiscovery_info['vdiscovery_cloud_provider'] = item['driver_type']
                vdiscovery_info['vdiscovery_sync_child_account'] = item['sync_child_accounts']
                vdiscovery_info['vdiscovery_sync_interval'] = db.call('?one.schedule_setting', {'parent': item.ref()}, single=True,factory=onedb.todict)
                if vdiscovery_info['vdiscovery_sync_interval']['disabled']:
                    vdiscovery_info['vdiscovery_sync_interval'] = {}
                    vdiscovery_info['vdiscovery_sync_interval']['weekdays'] = []
                if 'weekdays' in vdiscovery_info['vdiscovery_sync_interval']:
                    weekday_list = []
                    for abbrev, fullname in weekday_map.items():
                        if abbrev in vdiscovery_info['vdiscovery_sync_interval']['weekdays']:
                            weekday_list.append(fullname)
                    vdiscovery_info['vdiscovery_sync_interval']['weekdays'] = weekday_list
                vdiscovery_feature['vdiscovery_providers'].append(vdiscovery_info)
            cdns_service_object = db.call('?one.member_cloud_dns_sync_properties', factory=onedb.todict)
            if cdns_service_object:
                if cdns_service_object[0]['cloud_dns_sync_enabled'] and permitted_driver_type_exists:
                    vdiscovery_feature['cloud_vdiscovery_feature_enabled'] = True
            data['vdiscovery'] = vdiscovery_feature
        else:
            vdiscovery_feature = {}
            vdiscovery_feature['vdiscovery_providers'] = []
            data['vdiscovery'] = vdiscovery_feature
    return data

def fetch_grid_feature_usage(object_name):
    data = {}
    grid_feature_data = {}
    db = onedb.Db()
    with db.begin(onedb.RO) as txn:
        obj = grid_feature_usage(db)
        if object_name == "grid_feature":
            grid_feature_data = obj.dump()
        elif object_name == "dns_data":
            grid_feature_data = obj.dump_dns_data()
        elif object_name == "network_data":
            grid_feature_data = obj.dump_network_data()
        elif object_name == "nios_data":
            grid_feature_data = obj.dump_nios_data()
        elif object_name == "dns_records":
            grid_feature_data = obj.dump_dns_records()
        elif object_name == "zone_data":
            grid_feature_data = obj.dump_zone_data()
        elif object_name == "ipv4_ipv6_data":
            grid_feature_data = obj.dump_ipv4_ipv6_data()
        elif object_name == 'grid_feature_debug':
            grid_feature_data = obj.dump()
            grid_feature_data.update(obj.dump_dns_data())
            grid_feature_data.update(obj.dump_network_data())
            grid_feature_data.update(obj.dump_nios_data())
            grid_feature_data.update(obj.dump_dns_records())
            grid_feature_data.update(obj.dump_zone_data())
            grid_feature_data.update(obj.dump_ipv4_ipv6_data())
        data['grid_feature_usage'] = dict(grid_feature_data)
    return data

def fetch_grid():
    data = {}
    db = onedb.Db()
    with db.begin(onedb.RO) as txn:
        data = common.fill_up(db, d=data, k='grid', q='?one.cluster', dv=[])
    return data

def fetch_ssl_cert():
    data = {}
    db = onedb.Db()
    with db.begin(onedb.RO) as txn:
        ssl_cert = SSLCert(db)
        data['ssl_certs'] = ssl_cert.get_expiry()
    return data