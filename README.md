This is an ansible module that pulls data for a particular device in netbox.

## How to install the module
Refer to the "Adding a module locally" section of this document:
https://docs.ansible.com/ansible/latest/dev_guide/developing_locally.html
In addition to what's written there, you can also create a 'modules' folder in a particular role and save the file there as well. I like to create a 'common' role that includes this module, then I leverage [role dependencies](https://docs.ansible.com/ansible/latest/user_guide/playbooks_reuse_roles.html#role-dependencies) to make sure all my roles inherit the module that need it.

## Using the module in a playbook
Here's a quick example from a playbook that calls this module.
```
- name: get device facts from netbox
  netbox_device_details:
    netbox_url: http://0.0.0.0:8000
    netbox_token: "{{ netbox_token }}"
    device: "{{ inventory_hostname }}"
    get_connections: False
    get_vlans: False
    get_vrfs: False
    get_ip_addresses: False
  delegate_to: localhost
  register: nb
```

## Sample output
