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

import colander
import deform

from ninjasysop.validators import ip_validator


class ProxySchema(colander.Schema):
    proxy_to = colander.SchemaNode(colander.String(),
                                    missing='')
    ssl = colander.SchemaNode(colander.Boolean(),
                              default=False,
                              widget=deform.widget.CheckboxWidget(),
                              missing=False)


class FileSchema(colander.Schema):
    file = colander.SchemaNode(colander.String(),
                        validator=colander.Length(max=-1),
                        widget=deform.widget.TextAreaWidget(rows=30, cols=300),
                        description='Enter some text',
                        missing='')

class SiteSchema(colander.TupleSchema):
    name = colander.SchemaNode(
                colander.String(),
                widget = deform.widget.HiddenWidget(),
                )
    comment = colander.SchemaNode(colander.String(),
                                  missing=unicode(""))
    proxy = ProxySchema()
    file = FileSchema()


class CustomSiteSchema(colander.Schema):
    name = colander.SchemaNode(
                colander.String(),
                widget = deform.widget.HiddenWidget(),
                )

    content = colander.SchemaNode(colander.String(),
                        validator=colander.Length(max=-1),
                        widget=deform.widget.TextAreaWidget(rows=30, cols=300),
                        description='Config file content',
                        missing='')



class SiteValidator:

    def __init__(self, group, new=False):
        self.group = group
        self.new = False

    def __call__(self, form, value):
        pass