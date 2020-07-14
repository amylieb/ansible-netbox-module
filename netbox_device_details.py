#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2020, Amy Liebowitz (@amylieb) <amylieb@umich.edu>

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: netbox_device_details
short_description: Get device details from netbox

description:
    - Gets details about a device in netbox as specified by the user.
    - You will always get interface information (data from the 'interfaces' endpoint)
    - Optionally, you can get:
        - IP addresses tied to each interface (data from the 'ip-addresses' endpoint)
        - Devices connected to this device (data from the 'connections' endpoint)
        - VRF detail for the VRFs on IPs tied to the device ('vrfs' endpoint)
        - VLAN detail for VLANs on interfaces tied to the device ('vlans' endpoint)
notes:
    - This should be run with connection C(local) and hosts C(localhost)
author:
    - Amy Liebowitz (@amylieb)
requirements:
  - pynetbox
  - netaddr
  - regex

options:
    netbox_url:
        description:
            - URL of the Netbox instance resolvable by Ansible control host
        required: true
    netbox_token:
        description:
            - The token created within Netbox to authorize API access
        required: true
    device:
        description:
            - Name of the device in netbox
        required: true
    get_ip_addresses:
        description:
            - Boolean indicating if you want IP information for interfaces tied
              to this device. Defaults to 'true'
        required: False
    get_connections:
        description:
            - Boolean indicating if you want connection information for interfaces tied
              to this device. Defaults to 'true'
        required: False
    get_vrfs:
        description:
            - Boolean indicating if you want detailed info for VRFs tied
              to this device. Defaults to 'true'
        required: False
    get_vlans:
        description:
            - Boolean indicating if you want detailed info for the VLANs tied
              to this device. Defaults to 'true'
        required: False
'''

RETURN = r'''
TBD
'''


from ansible.module_utils.basic import AnsibleModule, missing_required_lib
import traceback


## Try to import all non-standard dependencies
failed_import = False
try:
    import pynetbox
except ImportError:
    failed_import = 'pynetbox'
    IMP_ERR = traceback.format_exc()
try:
    from netaddr import *
except ImportError:
    failed_import = 'netaddr'
    IMP_ERR = traceback.format_exc()
try:
    import re
except ImportError:
    failed_import = 'regex'
    IMP_ERR = traceback.format_exc()


def main():
    '''
    Main entry point for module execution
    '''
    argument_spec = dict(
        netbox_url=dict(type="str", required=True),
        netbox_token=dict(type="str", required=True, no_log=True),
        device=dict(type="str", required=True),
        get_ip_addresses=dict(type="bool",default=True,required=False),
        get_connections=dict(type="bool",default=True,required=False),
        get_vrfs=dict(type="bool",default=True,required=False),
        get_vlans=dict(type="bool",default=True,required=False)
        )

    global module
    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    # Fail if a required dependency isn't installed
    if failed_import:
        module.fail_json(msg=missing_required_lib(failed_import),exception=IMP_ERR)

    # Fail if device name is not given
    if not module.params.get("device"):
        module.fail_json(msg="missing device name")

    # Assign variables to be used with module
    url = module.params["netbox_url"]
    token = module.params["netbox_token"]
    device = module.params["device"]
    get = {
           'ip_addresses': module.params["get_ip_addresses"],
           'connections': module.params["get_connections"],
           'vrfs': module.params["get_vrfs"],
           'vlans': module.params["get_vlans"]
          }

    # Attempt to create Netbox API object
    try:
        nb = pynetbox.api(url=url, token=token)
    except Exception:
        module.fail_json(msg="Failed to establish connection to Netbox API")
    # Try looking up device
    try:
        nb_d = nb.dcim.devices.get(name=device)
    except Exception:
        module.fail_json(msg="Could not find device {} in Netbox!".format(device))

    results = {}

    # We always want interface information
    pynb_interfaces = nb.dcim.interfaces.filter(device=device)
    results['interfaces'] = [ dict(i) for i in pynb_interfaces ]
    interfaces = results['interfaces']

    # If VRF detail was requested we need to get ip addresses
    # so we can identify which VRFs are configured on this device
    if get['vrfs']:
        get['ip_addresses'] == True

    # Get IP addresses if indicated
    if get['ip_addresses']:
        pynb_addrs = nb.ipam.ip_addresses.filter(device=device)

        # Save IP information as interface sub-entries
        for i in interfaces:
 
            # Pull list of IPs tied to this interface
            i['ip_addresses'] = [ dict(a) for a in pynb_addrs if a.interface.id == i['id'] ]

            # Save the VRF assignment of the first IP at
            # the interface level for easier configuration templating
            # TODO: Add a check that verifies VRF assignment is the same
            # across all IPs
            if len(i['ip_addresses']):
                i['vrf'] = i['ip_addresses'][0].get('vrf',None)

    # Get connections if indicated
    if get['connections']:
        pynb_conns = nb.dcim.interface_connections.filter(device=device)

        for c in pynb_conns:
            if c.interface_a.device.name == device:
                i['conn'] = dict(c.interface_b)
            elif c.interface_b.device.name == device:
                i['conn'] = dict(c.interface_a)

    # Grab VRF detail if requested
    if get['vrfs']:
        results['vrfs'] = []
        vrf_db_ids = set()

        vrf_db_ids.update([i['vrf']['id'] for i in interfaces 
                    if len(i['ip_addresses']) and i['vrf'] != None])
            
        for id in vrf_db_ids:
            results['vrfs'].append(dict(nb.ipam.vrfs.get(id)))

    # Get VLAN detail if indicated
    if get['vlans']:
        results['vlans'] = []

        vlan_db_ids = set()

        # Pull list of unique VLANs from the interfaces (tagged and untagged)
        for i in interfaces:
            vlan_db_ids.update([ v['id'] for v in i['tagged_vlans'] ])
            if i['untagged_vlan']:
                vlan_db_ids.add(i['untagged_vlan']['id'])
        
        # Pull netbox vlan endpoint detail for each vlan id
        for id in vlan_db_ids:
            results['vlans'].append(dict(nb.ipam.vlans.get(id)))

    module.exit_json(**results)

if __name__ == "__main__":
    main()



