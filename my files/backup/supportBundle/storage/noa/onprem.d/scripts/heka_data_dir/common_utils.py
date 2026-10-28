#!/usr/bin/python

import json
import os
import re
import infoblox.one.onedb as onedb
import infoblox.one.util as ou

# This is the python script will be used by HEKA to fetch data from DB and
# send the data to cloud endpoint.

def get_db_count(db, obj, o=None):
    if obj[0] == '?':
        obj = obj[1:]
    query = "SELECT count(*) AS counter FROM {0}".format(obj)
    if o:
        params = ""
        for key in o:
            params = params + ("(%s = '${%s}') " % ( key, key))
        if len(o) > 1:
            condition = " WHERE (& {0})".format(params)
        else:
            condition = " WHERE {0}".format(params)
        query = query + condition
        result = db.call(query, o)
    else:
        result = db.call(query)
    return int(result[0]['counter'])

def get_db_data(db, obj):
    return db.call(obj, factory=onedb.todict)

def get_db_data_options(db, q, o): 
    return db.call(q, o, factory=onedb.todict)

def get_db_data_options_limit(db, q, o):
    return db.call(q, o, limit=1, factory=onedb.todict)

def get_time_zone(db):
    zone = ''
    dbVal= db.call('?one.cluster_time', factory=onedb.todict, single=True)
    if dbVal and 'time_zone' in dbVal:
        result = re.search('\((.*)\)(.*)', dbVal['time_zone'])
    else:
        result = None

    if result:
        timeZone = result.group(1).split()
    else:
        timeZone = []

    if len(timeZone) > 1:
        sign = timeZone[1]
        hh, mm = timeZone[2].split(':')
        mm = mm.rstrip(')')
        zone = "{0}{1:02d}:{2:02d}".format(sign, int(hh), int(mm))
    return zone

# db takes database object
# d takes dictionary
# k takes k in the d
# q takes query string into db
# dv is the default value 
def fill_up(db, d, k, q, dv=[]):
    v = get_db_data(db, q)
    if v:
        d[k] = v
    else:
        d[k] = dv

    return d

# db takes database object
# d takes dictionary
# k takes k in the d
# q takes query string into db
# dv is the default value 
def fill_up_count(db, d, k, q, dv=0):
    count = get_db_count(db, q)
    if count:
        d[k] = count
    else:
        d[k] = dv

    return d

# db takes database object
# d takes dictionary
# k takes k in the d
# q takes query string into db
# o takes options for the query
# dv is the default value
def fill_up_count_options(db, d, k, q, o, dv=0):
    count = get_db_count(db, q, o)
    if count:
        d[k] = count
    else:
        d[k] = dv
    return d

# db takes database object
# d takes dictionary
# k takes k in the d
# q takes query string into db
# o takes options for the query
# dv is the default bool value
def fill_up_bool_option(db, d, k, q, o, limit=0, dv=False):
    if limit == 1:
        v = get_db_data_options_limit(db, q, o)
    else:
        v = get_db_data_options(db, q, o)
    if v:
        d[k] = True
    else:
        d[k] = bool(dv)
    return d

# returns version of NIOS in format '905'
def nios_version():
    nios_version = ou.get_external_version() # nios version format 8.6.3-51135-1241097029df
    matches = re.findall(r'\d+', nios_version) #matches format ['8', '6', '3', '51135', '1241097029']
    nios_version_str = '0'
    if len(matches) > 3:
        first_three_ints = matches[:3] #first_three_ints format ['8', '6', '3']
        nios_version_str = ''.join(first_three_ints)
    return nios_version_str
