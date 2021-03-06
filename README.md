## Overview
"netbox_device_details" is an ansible module that leverages [pynetbox](https://github.com/digitalocean/pynetbox) to pull API data from netbox for a particular device. Here is a list of the data gathered and the corresponding API call used:

Always gathered:
* interfaces: http://<netbox_url>/api/dcim/interfaces/?device=<device_name>

Gathered by default, but can be skipped if specified:
* connections: http://<netbox_url>/api/dcim/interface_connections/?device=<device_name>
* ip addresses: http://<netbox_url>/api/ipam/ip_addresses/?device=<device_name>
* vlans: http://<netbox_url>/api/ipam/vlans/<vlan_id> for each VLAN found in interfaces
* vrfs: http://<netbox_url>/api/ipam/vrfs/<vrf_id> for each VRF found in ip addresses

## Data output structure
The output data is returned as a dictionary with keys mapping to netbox API endpoints. The module does very little transformation of the API respose data - you can use the API documentation to get a feel for how the output is structured. There are two key changes the module makes when returning output:
* connections and ip addresses are nested under their appropriate interface in the 'interfaces' output.
* vrf assignments from ip addresses are copied to their corresponding interface (because netbox does not assign interfaces to VRFs, it assigns IPs to VRFs). If multiple IPs are tied to an interface, the VRF assignment from the first IP found is used.

## How to install the module
Refer to the "Adding a module locally" section of this document:
https://docs.ansible.com/ansible/latest/dev_guide/developing_locally.html
Because I hate dealing with local environment variables and conf files, I like to create a 'common' role that includes this module (in a folder called 'modules', which works just as well as a folder called 'library'), then I leverage [role dependencies](https://docs.ansible.com/ansible/latest/user_guide/playbooks_reuse_roles.html#role-dependencies) to make sure that the roles that need it inherit the module.

## Using the module in a playbook
Here's a quick example from a playbook that calls this module.
```
- name: get device facts from netbox
  netbox_device_details:
    netbox_url: "{{ netbox_url }}"
    netbox_token: "{{ netbox_token }}"
    device: "{{ inventory_hostname }}"
    get_connections: True
    get_vlans: False
    get_vrfs: False
    get_ip_addresses: False
  delegate_to: localhost
  register: nb
```
## Using the results in a template
Here's a quick template that uses the results (registered as 'nb' in the corresponding task)
```
interfaces {
{% for i in nb.interfaces if i.mode %}

  {{ i.name }} {
     {% if i.description != "" %}
     description "{{ i.description }}"
     {% endif %}
     replace:
     unit 0 {
       family ethernet-switching {
     {% if i.mode.value == 'access' and i.untagged_vlan %}
        interface-mode access;
        vlan {
          members {{ i.untagged_vlan.vid }}
        }
     {% elif i.mode.value == 'tagged' %}
         interface-mode trunk;
         vlan {
           members [ {{ i.tagged_vlans | map(attribute='vid') | join(' ') }} ];
         }

     {% elif i.mode.value == 'tagged-all' %}
        interface-mode trunk;
        vlan {
          members all;
        }
     {% endif %}
       }
     }


  }
{% endfor %}
}
```
