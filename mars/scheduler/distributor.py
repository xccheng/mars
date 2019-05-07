#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 1999-2018 Alibaba Group Holding Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from ..actors import Distributor
from ..compat import six, functools32
from ..lib.mmh3 import hash as mmh_hash
from ..utils import to_binary


class SchedulerDistributor(Distributor):
    @functools32.lru_cache(100)
    def distribute(self, uid):
        if not isinstance(uid, six.string_types) or self.n_process == 1:
            return 0
        id_parts = uid.split(':')
        if id_parts[0] == 's':
            # get process id by hashing uid
            allocate_id = mmh_hash(to_binary(uid)) % (self.n_process - 1) + 1
            return allocate_id
        else:
            return 0
