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
import re
import subprocess
import shutil

import deform

from ninjasysop.backends import Backend, BackendApplyChangesException

from forms import EntrySchema, EntryValidator
from texts import texts
from datetime import datetime

# SERIAL = yyyymmddnn ; serial
PARSER_RE = {
    'serial':re.compile(r'(?P<serial>\d{10}) *; *serial'),
    'record':re.compile(r'^(?P<name>(?:[a-zA-Z0-9-.]*|@)) *(?:(?P<ttl>\d+)'
                        r' *|)(?:IN *|)(?P<type>A|CNAME)'
                        r' *(?P<target>[a-zA-Z0-9-.]*)'
                        r'(?:(?: *|);(?P<comment>.*)$|)'),
}

MATCH_RE_STR = {
    'record':r'^{name} *(?:\d+ *|)(?:IN *|){rtype}',
    'serial':r'(?: *)(?P<serial>\d{10}) *;(?: *)serial',
}

RELOAD_COMMAND = "/usr/sbin/rndc reload"



class Item(object):
    def __init__(self, name, type, target, ttl=0, comment=''):
        self.name = name
        self.type = type
        self.target = target
        self.ttl = ttl or 0
        self.comment = comment or ''

    def __str__(self):
        return self.name

    def todict(self):
        return dict(name = self.name,
                    type = self.type,
                    target = self.target,
                    ttl = self.ttl,
                    comment = self.comment)


class ZoneFile(object):
    def __init__(self, filename):
        self.filename = filename

    def readfile(self):
        serial = None
        names = {}
        with open(self.filename, 'r') as zonefile:
            for line in zonefile.readlines():
                serial_line = PARSER_RE['serial'].search(line)
                if serial_line:
                    serial = serial_line.group('serial')
                    continue
                record_line = PARSER_RE['record'].search(line)
                if record_line:
                    record = Item(**record_line.groupdict())
                    names[str(record)] = record
        return (serial, names)

    def __str_record(self, record):
        recordstr = record.name
        if record.ttl:
            recordstr += " {0}".format(str(record.ttl))

        recordstr += " {type} {target}".format(type=record.type,
                                              target=record.target)
        if record.comment:
            recordstr += " ;{0}".format(record.comment)

        recordstr += '\n'
        return recordstr

    def __str_serial(self, serial):
        return "%s ;serial aaaammdd\n" % serial

    def add_record(self, record):
        with open(self.filename, 'r') as zonefile:
            lines = zonefile.readlines()
            lines.append(self.__str_record(record))

        with open(self.filename, 'w') as zonefile:
            zonefile.writelines(lines)

    def save_record(self, old_record, record):
        match = re.compile(MATCH_RE_STR['record'].format(name=old_record.name,
                                                         rtype=old_record.type))
        zonefile = open(self.filename, 'r')
        lines = zonefile.readlines()
        zonefile.close()
        n = 0
        while n < len(lines) and not match.match(lines[n]):
            n += 1

        if n == len(lines):
            raise(KeyError, "Record %s not found" % record.name)
        else:
            lines[n] = self.__str_record(record)

        zonefile = open(self.filename, 'w')
        print lines
        zonefile.writelines(lines)
        zonefile.close()


    def remove_record(self, record):
        match = re.compile(MATCH_RE_STR['record'].format(name=record.name,
                                                         rtype=record.type))
        zonefile = open(self.filename, 'r')
        lines = zonefile.readlines()
        zonefile.close()
        n = 0
        while n < len(lines) and not match.match(lines[n]):
            n += 1

        if n == len(lines):
            raise KeyError("Not Found, %s can't be deleted" % record.name)
        else:
            del lines[n]

        zonefile = open(self.filename, 'w')
        zonefile.writelines(lines)
        zonefile.close()

    def save_serial(self, serial):
        match = re.compile(MATCH_RE_STR['serial'])

        zonefile = open(self.filename, 'r')
        lines = zonefile.readlines()
        zonefile.close()

        n = 0
        while n < len(lines) and not match.match(lines[n]):
            n += 1

        if n == len(lines):
            raise KeyError("Serial not found in file %s" % self.filename)
        else:
            serial_re = re.search(MATCH_RE_STR['serial'], lines[n])
            serial = serial_re.group('serial')
            lines[n] = self.__str_serial(serial)

        zonefile = open(self.filename, 'w')
        zonefile.writelines(lines)
        zonefile.close()


class Bind9(Backend):
    def __init__(self, name, filename):
        super(Bind9, self).__init__(name, filename)
        self.groupname = name
        self.zonefile = ZoneFile(filename)
        (self.serial, self.items) = self.zonefile.readfile()
        assert self.serial, "ERROR: Serial is undefined on %s" % self.filename

    def del_item(self, name):
        self.zonefile.remove_record(self.items[name])
        del self.items[name]

    def get_item(self, name):
        return self.items[name]

    def get_items(self, name=None, type=None, target=None,
                    name_exact=None):
        filters = []

        if name:
            def filter_name(r):
                return r.name.find(name) >= 0
            filters.append(filter_name)

        if type:
            def filter_type(r):
                return r.type == type
            filters.append(filter_type)

        if target:
            def filter_target(r):
                return r.target == target
            filters.append(filter_target)

        if name_exact:
            def filter_name_exact(r):
                return r.name == name >= 0
            filters.append(filter_name)

        if filters:
            return filter(lambda item: all([f(item) for f in filters]),
                         self.items.values())
        else:
            return self.items.values()

    def add_item(self, obj):
        if obj["name"].endswith(self.groupname):
            entry = obj["name"].replace(".%s" % self.groupname, "")
        elif obj["name"].endswith('.'):
            entry = obj["name"][:-1]
        else:
            entry = obj["name"]

        record = Item(name=entry,
                        type=obj["type"],
                        target=obj["target"],
                        comment=obj["comment"],
                        ttl=obj["ttl"])

        self.zonefile.add_record(record)
        self.items[str(record)] = record


    def save_item(self, old_record, data):
        if data["name"].endswith(self.groupname):
            entry = data["name"].replace(".%s" % self.groupname, "")
        elif data["name"].endswith('.'):
            entry = data["name"][:-1]
        else:
            entry = data["name"]

        record = Item(name=entry,
                        type=data["type"],
                        target=data["target"],
                        comment=data["comment"],
                        ttl=data["ttl"])

        self.zonefile.save_record(old_record, record)
        self.items[str(record)] = record



    def __update_serial(self):
        today = datetime.now()
        today_str = today.strftime("%Y%m%d")
        if self.serial.startswith(today_str):
            change = self.serial[8:]
            inc_change = int(change) + 1
            serial = long("%s%02d" % (today_str, inc_change))
        else:
            serial = long("%s01" % today_str)
        self.zonefile.save_serial(self.serial)
        self.serial = serial

    def freeze_file(self, username):
        # generate a copy of actual file with username.serial extension
        pass

    def apply_changes(self, username):
        cmd=RELOAD_COMMAND
        self.__update_serial()
        save_filename = "%s.%s.%s" % (self.filename, self.serial, username)
        shutil.copy(self.filename, save_filename)
        try:
            subprocess.check_output("%s %s" % (cmd, self.groupname),
                                    stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError, e:
            raise BackendApplyChangesException(e.output)

    def get_edit_schema(self, name):
        return EntrySchema(validator=EntryValidator(self))

    def get_add_schema(self):
        schema = EntrySchema(validator=EntryValidator(self))
        for field in schema.children:
            if field.name == 'name':
                field.widget = deform.widget.TextInputWidget()
        return EntrySchema(validator=EntryValidator(self))

    @classmethod
    def get_edit_schema_definition(self):
        return EntrySchema

    @classmethod
    def get_add_schema_definition(self):
        return EntrySchema

    @classmethod
    def get_texts(self):
        return texts
