# -*- coding: utf-8 -*-
# Copyright (c) <2012> Antonio Pérez-Aranda Alcaide (ant30) <ant30tx@gmail.com>
#                      Antonio Pérez-Aranda Alcaide (Yaco Sistemas SL) <aperezaranda@yaco.es>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of copyright holders nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL COPYRIGHT HOLDERS OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# 

from datetime import datetime
import re
import shutil
import subprocess
from ipaddr import IPv4Network, IPv4Address


from ninjasysop.backends import Backend, BackendApplyChangesException
from ninjasysop.validators import IntegrityException
import deform

from texts import texts
from forms import HostSchema, DhcpHostValidator

# SERIAL = yyyymmddnn ; serial
PARSER_RE = {
    'partition':re.compile(r"(?P<sub>subnet[^\}]*}) *(?P<hosts>.*)$"),
    'header': re.compile("subnet (?P<subnet>[\d.]+) netmask (?P<netmask>[\d\.]+)(?: *|)\{(?: *|)range (?P<start>[\d\.]+) (?P<end>[\d\.]+)"),
    'hosts': re.compile(r"host (?P<hostname>[^ ]*) *{ *hardware ethernet (?P<mac>[^\;]*); *fixed-address (?P<ip>[^\;]*)"),
    'router': re.compile(r"option routers (?P<router>[\d.]+)")
}

MATCH_RE_STR = {
    'record':r'^{name} *(?:\d+ *|)(?:IN *|){rtype}',
}

RELOAD_COMMAND = "/etc/init.d/isc-dhcpd-server reload"



class DhcpHost(object):
    def __init__(self, name, mac, ip, comment=''):
        self.ip = ip
        self.mac = mac
        self.name = name
        self.comment = comment or ''

    def __str__(self):
        return self.name

    def todict(self):
        return dict(name = self.name,
                    mac = self.mac,
                    ip = self.ip,
                    comment = self.comment)


class NetworkFile(object):
    def __init__(self, filename):
        self.filename = filename

    def readfile(self):
        serial = ''
        items = {}
        with open(self.filename, 'r') as networkfile:
            content = networkfile.read()
            partition = PARSER_RE['partition'].search(content.replace("\n",""))
            if not partition:
                raise IOError("Bad File Format")
            (header, hosts) = partition.groups()

            parsed_header = PARSER_RE['header'].search(header)
            route_header = PARSER_RE['router'].search(header)
            network = dict(network=IPv4Network("%s/%s" % (parsed_header.group('subnet'),
                                                        parsed_header.group('netmask'),
                                                       )),
                           start=IPv4Address(parsed_header.group('start')),
                           end=IPv4Address(parsed_header.group('end')),
                           router=IPv4Address(route_header.group('router')),
                           )

            parsed_hosts = PARSER_RE['hosts'].findall(hosts)
            for (name, mac, ip) in parsed_hosts:
                item = DhcpHost(name, mac, ip)
                items[name] = item

        return (network, items)

    def __str_item(self, item):
        itemstr = ''
        if item.comment:
            itemstr = "#{0}\n".format(item.comment)

        itemstr += "host {name} {{\n hardware ethernet {mac};\n fixed-address {ip};\n}}\n".format(
                                    name=item.name, mac=item.mac, ip=item.ip)

        return itemstr


    def add_item(self, item):

        with open(self.filename, 'r') as filecontent:

            item_str = self.__str_item(item)
            content = filecontent.read()
            content = content + item_str

        with open(self.filename, 'w') as filecontent:
            filecontent.write(content)


    def save_item(self, old_item, item):

        with open(self.filename, 'r') as filecontent:

            item_str = self.__str_item(item)
            content = filecontent.read()
            content_1 = re.sub(r"host %s [^\{]*{.*[^\}]*} *\n" % (old_item.name),
                    item_str, content)
            if content == content_1:
                raise KeyError("host %s not found" % item.name)
            else:
                content = content_1

        with open(self.filename, 'w') as filecontent:
            filecontent.write(content)

    def remove_item(self, item):
        with open(self.filename, 'r') as filecontent:

            content = filecontent.read()
            content_1 = re.sub(r"host %s [^\{]*{.*[^\}]*} *\n" % (item.name),
                               "", content)
            if content == content_1:
                raise KeyError("host %s not found" % item.name)
            else:
                content = content_1

        with open(self.filename, 'w') as filecontent:
            filecontent.write(content)


class Dhcpd(Backend):

    def __init__(self, name, filename):
        super(Dhcpd, self).__init__(name, filename)
        self.networkfile = NetworkFile(filename)
        (self.network, self.items) = self.networkfile.readfile()

    def del_item(self, name):
        self.networkfile.remove_item(self.items[name])
        del self.items[name]

    def get_item(self, name):
        if name in self.items:
            return self.items[name]
        else:
            return None

    def get_items(self, **kwargs):
        filters = []

        if 'name' in kwargs:
            def filter_name(r):
                return r.name.find(kwargs['name']) >= 0
            filters.append(filter_name)

        if 'mac' in kwargs:
            def filter_mac(r):
                return r.mac == kwargs['mac']
            filters.append(filter_type)

        if 'ip' in kwargs:
            def filter_target(r):
                return r.ip == kwargs['ip']
            filters.append(filter_target)

        if 'name_exact' in kwargs:
            def filter_name_exact(r):
                return r.name == kwargs['name']
            filters.append(filter_name_exact)

        if filters:
            return filter(lambda item: all([f(item) for f in filters]),
                         self.items.values())
        else:
            return self.items.values()

    def get_free_ip(self):
        # A free IP is:
        #   * Not asigned IP
        #   * Not in DHCPD start/end range (not ip collisions)
        #   * A IP in network (subnet/netmask) range
        start_ip = self.network['network'].ip
        ip = start_ip + 1
        while (not (ip > self.network['start'] and ip < self.network['start']) and
               not (self.get_items(ip=ip.exploded)) and
               ip in self.network['network']):
            ip += 1

        if ip not in self.network['network']:
            return ""
        else:
            return ip.exploded

    def add_item(self, obj):
        item = DhcpHost(name=obj['name'],
                    mac=obj['mac'],
                    ip=obj['ip'],
                    #comment=obj['comment'],
                    )

        self.networkfile.add_item(item)
        self.items[str(item)] = item

    def save_item(self, old_item, obj):
        item = DhcpHost(name=obj['name'],
                    mac=obj['mac'],
                    ip=obj['ip'],
                    #comment=obj['comment'],
                    )

        self.networkfile.save_item(old_item, item)
        self.items[str(old_item)] = item

    def get_edit_schema(self, name):
        return HostSchema(validator=DhcpHostValidator(self))

    def get_add_schema(self):
        schema = HostSchema(validator=DhcpHostValidator(self, new=True))
        for field in schema.children:
            if field.name == 'name':
                field.widget = deform.widget.TextInputWidget()
            if field.name == 'ip':
                free_ip = self.get_free_ip()
                if free_ip:
                    field.default = self.get_free_ip()
                    field.description = "You can use %s as available IP" % free_ip
                else:
                    field.description = "There aren't available IPs"

        return schema


    def _timestamp(self):
        today = datetime.now()
        return today.strftime("%Y%m%d%H%M%S")


    def apply_changes(self, username):
        cmd=RELOAD_COMMAND
        save_filename = "%s.%s.%s" % (self.filename, self._timestamp(), username)
        shutil.copy(self.filename, save_filename)
        try:
            subprocess.check_output("%s" % cmd,
                                    stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError, e:
            raise BackendApplyChangesException(e.output)

    @classmethod
    def get_edit_schema_definition(self):
        return HostSchema

    @classmethod
    def get_add_schema_definition(self):
        return HostSchema

    @classmethod
    def get_texts(self):
        return texts
