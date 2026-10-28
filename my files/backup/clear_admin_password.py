#!/usr/bin/env python
'''
This python script is used to clear last_discovered_timestamp
from host_address 
and record_name_policy properties of all Stub zones
present in the database
'''
from __future__ import with_statement
import sys
import os

import infoblox.one.onedb as onedb
import infoblox.one.util

OBJS  = ['?one.admin']

def main():
    db = onedb.Db()
    with db.begin(onedb.RW):
        for obj in OBJS:
            for item in list(db.cursor(obj)):
                if item['name'] == 'admin':
                    item['password'] = 'infoblox' 
                    item.update()

if __name__ == "__main__":
    main()

