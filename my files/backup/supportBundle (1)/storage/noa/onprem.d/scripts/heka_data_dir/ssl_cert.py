#!/usr/bin/python
import os
import sys
import json
import datetime
import infoblox.one.util as ou
import infoblox.one.onedb as onedb
import infoblox.one.one_include as oi
import infoblox.one.certificate as cert
import OpenSSL as osl
import infoblox.one.superuser as superuser
import infoblox.one.data_if as data_if
import infoblox.one.data_handlers as dh
import infoblox.common.util as cu
import infoblox.one.cert_util as crtu
import infoblox.common.ilog as ilog
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import base64
import ssl
import infoblox.one.ca as ca
import tempfile

INFOBLOX_INC = "Infoblox"
VNODE_NONE = -1

class SSLCert():

    def cert_load(self, pem_data, vnode):
        crt = osl.crypto.load_certificate(osl.crypto.FILETYPE_PEM, pem_data)
        issuer = crt.get_issuer()
        exp_time = datetime.datetime.strptime(crt.get_notAfter().decode('ascii'), '%Y%m%d%H%M%SZ').isoformat() + 'Z'
        if issuer.O == INFOBLOX_INC:
            ilog.debug('SSL certificate is issued by Infoblox : %s. Returning', issuer.CN)
            return None

        cert_entry = {}
        cert_entry['expiry'] = exp_time
        cert_entry['name'] = issuer.CN
        if vnode != VNODE_NONE:
            cert_entry['virtual_oid'] = vnode
        
        return cert_entry

    def get_http_cert_expiry(self, vnode_ref):
        vnode = vnode_ref.fetch()
        vnode_oid = vnode['virtual_oid']
        try:
            cert = self.db.call('?one.apache_certificate',
                    { 'virtual_node' : vnode_oid },
                        single=True)
            if cert:
                if sys.version_info[0] == 3:
                    pem_data = bytes(cert['pem_data'], encoding='utf8')
                else:
                    pem_data = bytes(cert['pem_data'])

                cert_entry = self.cert_load(pem_data, vnode_oid)
                if cert_entry != None:
                    self.data['http'].append(cert_entry)

        except Exception as e:
            ilog.log('Error occurred while fetching HTTP ssl cert data : %s' % e)

    def get_captive_portal_cert_expriy(self, vnode_ref):
        vnode = vnode_ref.fetch()
        vnode_oid = vnode['virtual_oid']
        try:
            cert = self.db.call('?one.member_captive_portal_properties',
                    {'virtual_node' : vnode_oid },
                        single=True)
            if (cert['encryption'] == 'SSL'):
                svr_cert_obj = cert['cert'].fetch()
                pem_data = svr_cert_obj['pem_data']
                cert_entry = self.cert_load(pem_data, vnode_oid)
                if cert_entry != None:
                    self.data['captive'].append(cert_entry)

        except Exception as e:
            ilog.log('Error occurred while fetching Captive Portal ssl cert data : %s' % e)

    def get_ca_cert_expiry(self):
        certs = self.db.call('?one.eap_ca_cert', factory=onedb.todict) 
        for cert in certs:
            subject = cert['subject'].split(',')
            subject_name = subject[0].split('=')
            common_name = subject_name[1] 
            if INFOBLOX_INC in common_name or INFOBLOX_INC in cert['subject']:
                ilog.log('CA certificate (CN = %s) is issued by Infoblox. Continue', common_name)
                continue

            selfsigned_cert = {}
            selfsigned_cert['name'] = common_name
            selfsigned_cert['expiry'] = cert['exp_datetime'] + 'Z'
            self.data['ca_cert'].append(selfsigned_cert)

    def get_sfnt_server_cert_expiry(self):
        try:
            sfnt_server_cert = self.db.call('?one.safenet_hsm')
            for crt in sfnt_server_cert:
                pem_data = base64.b64decode(crt['server_cert_string'])
                cert_entry = self.cert_load(pem_data, VNODE_NONE)
                if cert_entry != None:
                    self.data['sfnt_server'].append(cert_entry)

        except Exception as e:
            ilog.log('Error occurred while fetching safenet server data : %s' % e)

    def get_endpoint_certificate(self, type):
        cert_entry = []
        cert_key = 'client_certificate'
        cert = self.db.call('?one.endpoint', {'type' : type }, factory=onedb.todict)
        for item in cert:
            if cert_key in item:
                obj_hash = item[cert_key]
                x509_crt = self.db.call('?one.x509_certificate',
                    {'obj_hash' : obj_hash}, factory=onedb.todict, single=True)
                pem_data = crtu.topem(x509_crt['certificate'], 'CERT')
                entry = self.cert_load(pem_data, VNODE_NONE)
                if entry != None:
                    cert_entry.append(entry)
        return cert_entry

    def get_x509_certificate(self, db_entry, cert_key):
        cert_entry = []
        cert = self.db.call(db_entry, factory=onedb.todict)
        for item in cert:
            if cert_key in item:
                obj_hash = item[cert_key]
                x509_crt = self.db.call('?one.x509_certificate',
                    {'obj_hash' : obj_hash}, factory=onedb.todict, single=True)
                pem_data = crtu.topem(x509_crt['certificate'], 'CERT')
                entry = self.cert_load(pem_data, VNODE_NONE)
                if entry != None:
                    cert_entry.append(entry)
        return cert_entry

    def get_ocsp_cert_expiry(self):
        try:
            cert_entry = self.get_x509_certificate('?one.ocsp_auth_responder', 'certificate')
            if cert_entry:
                self.data['ocsp_server'] = cert_entry
        except Exception as e:
            ilog.log('Error occurred while fetching ocsp data : %s' % e)

    def get_idns_cert_expiry(self):
        try:
            cert_entry = self.get_x509_certificate('?dns.idns_certificate', 'cert')
            if cert_entry:
                self.data['idns_cert'] = cert_entry
        except Exception as e:
            ilog.log('Error occurred while fetching IDNS health monitor data : %s' % e)

    def get_endpoint_rest_api_cert_expiry(self):
        try:
            cert_entry = self.get_endpoint_certificate('TYPE_RESTAPI')
            if cert_entry:
                self.data['endpoint_rest_api_cert'] = cert_entry
        except Exception as e:
            ilog.log('Error occurred while fetching endpoint certificate expiry : %s' % e)

    def get_endpoint_ciscoise_cert_expiry(self):
        try:
            cert_entry = self.get_endpoint_certificate('TYPE_PXGRID')
            if cert_entry:
                self.data['endpoint_cisco_ise_cert'] = cert_entry
        except Exception as e:
            ilog.log('Error occurred while fetching endpoint CISCO ISE certificate expiry : %s' % e)

    def get_endpoint_syslog_expiry(self):
        try:
            cert_entry = self.get_x509_certificate('?one.endpoint_syslog_server', 'certificate')
            if cert_entry:
                self.data['endpoint_syslog_cert'] = cert_entry
        except Exception as e:
            ilog.log('Error occurred while fetching endpoint syslog server certificate expiry : %s' % e)

    def get_endpoint_dxl_expiry(self):
        try:
            cert_entry = self.get_endpoint_certificate('TYPE_DXL')
            if cert_entry:
                self.data['endpoint_dxl_cert'] = cert_entry
        except Exception as e:
            ilog.log('Error occurred while fetching endpoint dxl server certificate expiry : %s' % e)
    
    def get_saml_auth_idp_expiry(self):
        try:
            SAML_SETTINGS_FILE = '/infoblox/var/saml/settings.json'
            data = []
            if os.path.isfile(SAML_SETTINGS_FILE):
                fd = open(SAML_SETTINGS_FILE)
                data = json.load(fd)
                fd.close()
                if data['idp']['x509cert']:
                    begin = '-----BEGIN CERTIFICATE-----\n'
                    end = '-----END CERTIFICATE-----'
                    cert = data['idp']['x509cert'].strip()
                    pem_data = begin + cert + '\n' + end
                    cert_entry = self.cert_load(pem_data, VNODE_NONE)
                    if cert_entry:
                        self.data['saml_auth_idp'].append(cert_entry)
        except Exception as e:
            ilog.log('Error occurred while fetching saml certificate expiry : %s' % e)

    def get_vnode_syslog_server_expiry(self):
        try:
            cert_entry = self.get_x509_certificate('?one.vnode_syslog_server', 'certificate')
            if cert_entry:
                self.data['vnode_syslog_server'] = cert_entry
        except Exception as e:
            ilog.log('Error occurred while fetching vnode syslog server certificate expiry : %s' % e)

    def get_cluster_syslog_server_expiry(self):
        try:
            cert_entry = self.get_x509_certificate('?one.cluster_syslog_server', 'certificate')
            if cert_entry:
                self.data['cluster_syslog_server'] = cert_entry
        except Exception as e:
            ilog.log('Error occurred while fetching cluster syslog server certificate expiry : %s' % e)

    def get_http_proxy_server_expiry(self):
        try:
            proxy_server_cert = self.db.call('?one.http_proxy_server_setting')
            for crt in proxy_server_cert:
                pem_data = crtu.topem(crt['cacert'], 'CERT')
                cert_entry = self.cert_load(pem_data, VNODE_NONE)
                if cert_entry != None:
                    self.data['proxy_server'].append(cert_entry)

        except Exception as e:
            ilog.log('Error occurred while fetching safenet server data : %s' % e)

    def get_ifmap_cert_expiry(self):
        try:
            cert_db = 'ifmap.ca_cert'
            cert_db_member = 'cert'
            chunk_type = 'one.ca_cert_chunk'
            cert_pemstring = ''
            objects = self.db.cursor('?%s' % cert_db,{})
            for item in objects:
                # cert handling
                cert_key = item[cert_db_member]
                if not cert_key:
                    continue
                cert_string = ''
                for cert_chunk in list(self.db.cursor('?%s' % chunk_type,
                                             {'cert' : cert_key,
                                              }, order_by='seq_no')):
                    cert_string += str(cert_chunk['certificate_chunk'])
                if sys.version_info[0] == 3:
                    cert_seq = base64.b64decode(cert_string.encode('utf-8'))
                else:
                    cert_seq = base64.decodestring(cert_string)
                file = tempfile.NamedTemporaryFile(dir='/tmpfs')
                ou.ipki_cert_bin_to_pem(file.name, cert_seq)
                if sys.version_info[0] == 3:
                    cert_pemstring += file.read().decode('utf-8')
                else :
                    cert_pemstring += file.read()
                file.close()
                cert_entry = self.cert_load(cert_pemstring, VNODE_NONE)
                if cert_entry != None:
                    self.data['ifmap_cert'].append(cert_entry)
        except Exception as e:
            ilog.log('Error occurred while fetching IFMAP certificate data : %s' % e)

    def get_x509_certs_expiry(self):
        self.get_ocsp_cert_expiry()
        self.get_idns_cert_expiry()
        self.get_endpoint_rest_api_cert_expiry()
        self.get_endpoint_ciscoise_cert_expiry()
        self.get_endpoint_syslog_expiry()
        self.get_endpoint_dxl_expiry()
        self.get_saml_auth_idp_expiry()
        self.get_vnode_syslog_server_expiry()
        self.get_cluster_syslog_server_expiry()

    def get_expiry(self):
        try:
            self.get_ca_cert_expiry()
            self.get_sfnt_server_cert_expiry()
            self.get_x509_certs_expiry()
            self.get_http_proxy_server_expiry()
            self.get_ifmap_cert_expiry()

            for vnode in self.db.cursor('?one.virtual_node', factory=onedb.DBRecord):
                self.get_http_cert_expiry(vnode.ref())
                self.get_captive_portal_cert_expriy(vnode.ref())

            return self.data

        except Exception as e:
            ilog.log('Error occurred while fetching ssl data : %s' % e)
            return ({'error': str(e)}) # Return code 1 on failure

    def __init__(self, db):
        self.data = {}
        self.data['http'] = []
        self.data['captive'] = []
        self.data['ca_cert'] = []
        self.data['sfnt_server'] = []
        self.data['ocsp_server'] = []
        self.data['idns_cert'] = []
        self.data['endpoint_rest_api_cert'] = []
        self.data['endpoint_cisco_ise_cert'] = []
        self.data['endpoint_syslog_cert'] = []
        self.data['endpoint_dxl_cert'] = []
        self.data['saml_auth_idp'] = []
        self.data['vnode_syslog_server'] = []
        self.data['cluster_syslog_server'] = []
        self.data['proxy_server'] = []
        self.data['ifmap_cert'] = []
        self.db = db

