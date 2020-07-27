###
#
# Lenovo Redfish examples - add/import LDAP certificate to BMC (Note: Need to restart BMC to activate it)
#
# Copyright Notice:
#
# Copyright 2020 Lenovo Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
###

import sys, os, struct
import redfish
import json
import lenovo_utils as utils


def lenovo_ldap_certificate_add(ip, login_account, login_password, certfile):
    """ Add LDAP certificate
        :params ip: BMC IP address
        :type ip: string
        :params login_account: BMC user name
        :type login_account: string
        :params login_password: BMC user password
        :type login_password: string
        :params certfile: certificate file by user specified
        :type certfile: string
        :returns: returns get successful result when succeeded or error message when failed
        """

    result = {}

    # check file existing
    if not os.path.exists(certfile):
        result = {'ret': False, 'msg': "Specified file %s does not exist. Please check your certificate file path." % (certfile)}
        return result

    # Create a REDFISH object
    login_host = "https://" + ip
    REDFISH_OBJ = redfish.redfish_client(base_url=login_host, username=login_account,
                                         password=login_password, default_prefix='/redfish/v1')

    # Login into the server and create a session
    try:
        REDFISH_OBJ.login(auth="session")
    except:
        result = {'ret': False, 'msg': "Please check the username, password, IP is correct\n"}
        return result

    try:
        # Get response_base_url
        response_base_url = REDFISH_OBJ.get('/redfish/v1', None)
        if response_base_url.status != 200:
            error_message = utils.get_extended_error(response_base_url)
            result = {'ret': False, 'msg': "Url '%s' response Error code %s\nerror_message: %s" % (
                '/redfish/v1', response_base_url.status, error_message)}
            return result

        # Use Oem API /redfish/v1/Managers/1/Oem/Lenovo/Security
        managers_url = response_base_url.dict['Managers']['@odata.id']
        response_managers_url = REDFISH_OBJ.get(managers_url, None)
        if response_managers_url.status != 200:
            error_message = utils.get_extended_error(response_managers_url)
            result = {'ret': False, 'msg': "Url '%s' response Error code %s\nerror_message: %s" % (
                managers_url, response_managers_url.status, error_message)}
            return result
        for request in response_managers_url.dict['Members']:
            # Access /redfish/v1/Managers/1
            request_url = request['@odata.id']
            response_url = REDFISH_OBJ.get(request_url, None)
            if response_url.status != 200:
                error_message = utils.get_extended_error(response_url)
                result = {'ret': False, 'msg': "Url '%s' response Error code %s\nerror_message: %s" % (
                    request_url, response_url.status, error_message)}
                return result
            # Check /redfish/v1/Managers/1/Oem/Lenovo/Security existing
            if "Oem" not in response_url.dict:
                continue
            if "Lenovo" not in response_url.dict["Oem"]:
                continue
            if "Security" not in response_url.dict["Oem"]["Lenovo"]:
                continue
            if "@odata.id" not in response_url.dict["Oem"]["Lenovo"]["Security"]:
                continue

            # Access /redfish/v1/Managers/1/Oem/Lenovo/Security to confirm current index
            security_url = response_url.dict["Oem"]["Lenovo"]["Security"]['@odata.id']
            response_security_url = REDFISH_OBJ.get(security_url, None)
            if response_security_url.status != 200:
                error_message = utils.get_extended_error(response_security_url)
                result = {'ret': False, 'msg': "Url '%s' response Error code %s\nerror_message: %s" % (
                    security_url, response_security_url.status, error_message)}
                return result
            if "PublicKeyCertificates" not in response_security_url.dict:
                continue
            index = 1
            for cert in response_security_url.dict["PublicKeyCertificates"]:
                if 'Subject' in cert and cert['Subject'] == 'LDAP_Server':
                    index = index + 1

            # Create request body
            target_url = security_url + "/Actions/LenovoSecurityService.ImportCertificate"
            request_body = {"Title":"ImportCertificate", "Service":"LDAP_Server", "ImportCertificateType": "TrustedCertificate", "Index":index}
            request_body["Target"] = target_url
            request_body["SignedCertificates"] = read_cert_file(certfile) 

            # Perform post to add the certificate
            response_url = REDFISH_OBJ.post(target_url, body=request_body)
            if response_url.status not in [200, 201, 202, 204]:
                error_message = utils.get_extended_error(response_url)
                result = {'ret': False, 'msg': "Url '%s' response Error code %s\nerror_message: %s" % (
                    target_url, response_url.status, error_message)}
            else:
                result = {'ret': True,
                          'msg':"The certificate has been added successfully. You must restart BMC to activate it."}
            REDFISH_OBJ.logout()
            return result

        # No LDAP certificate resource found
        result = {'ret': False, 'msg': 'LDAP certificate is not supported'}
        return result

    except Exception as e:
        result = {'ret': False, 'msg': 'exception msg %s' % e}
        return result
    finally:
        REDFISH_OBJ.logout()


def read_cert_file(der_cert):
    size = os.path.getsize(der_cert)
    fhandle = open(der_cert, 'rb')
    bytelist = list()
    for i in range(size):
        data = fhandle.read(1)
        elem = struct.unpack("B", data)[0]
        bytelist.append(elem)
    fhandle.close()
    return bytelist


def add_helpmessage(parser):
    parser.add_argument('--certfile', type=str, required=True, help='An file that contains the trusted certificate. Note: The certificate format should be DER, not PEM.')
 

def add_parameter():
    """Add parameter"""
    parameter_info = {}
    argget = utils.create_common_parameter_list()
    add_helpmessage(argget)
    args = argget.parse_args()
    parameter_info = utils.parse_parameter(args)
    parameter_info["certfile"] = args.certfile
    return parameter_info


if __name__ == '__main__':
    # Get parameters from config.ini or command line
    parameter_info = add_parameter()
    ip = parameter_info['ip']
    login_account = parameter_info["user"]
    login_password = parameter_info["passwd"]
    certfile = parameter_info["certfile"]

    # Get ldap certificate information and check result
    result = lenovo_ldap_certificate_add(ip, login_account, login_password, certfile)
    if result['ret'] is True:
        del result['ret']
        sys.stdout.write(json.dumps(result['msg'], sort_keys=True, indent=2))
    else:
        sys.stderr.write(result['msg'])

