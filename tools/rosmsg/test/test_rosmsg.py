#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import sys 
import unittest
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import time

import rospkg
        
import rosmsg

from subprocess import Popen, PIPE, check_call, call

#TODO: currently have an extra copy of msg and srv files in local dir
# for historical/porting reasons.  Ideally there would only be one copy
# in test_ros instead.
def get_test_path():
    return os.path.abspath(os.path.dirname(__file__))

class TestRosmsg(unittest.TestCase):

    def setUp(self):
        pass

    def test_fullusage(self):
        from rosmsg import MODE_MSG
        text = rosmsg.fullusage(MODE_MSG)
        self.assertTrue("Commands" in text)
        cmds = ['show', 'md5', 'package', 'packages']
        for c in cmds:
            self.assertTrue(c in text)

    def test_get_msg_text(self):
        d = get_test_path()
        msg_d = os.path.join(d, 'msg')
        
        test_message_package = 'diagnostic_msgs'
        rospack = rospkg.RosPack()
        msg_raw_d = os.path.join(rospack.get_path(test_message_package), 'msg')
        t = 'KeyValue'
        with open(os.path.join(msg_d, '%s.msg'%t), 'r') as f:
            text = f.read()
        with open(os.path.join(msg_raw_d, '%s.msg'%t), 'r') as f:
            text_raw = f.read()

        type_ = test_message_package+'/'+t
        self.assertEqual(text, rosmsg.get_msg_text(type_, raw=False))
        self.assertEqual(text_raw, rosmsg.get_msg_text(type_, raw=True))
            
        # test recursive types
        t = 'DiagnosticStatus'
        with open(os.path.join(d, '%s_raw.txt'%t), 'r') as f:
            text = f.read()
        with open(os.path.join(msg_raw_d, '%s.msg'%t), 'r') as f:
            text_raw = f.read()
        type_ = test_message_package+'/'+t
        
        self.assertEqual(text, rosmsg.get_msg_text(type_, raw=False))
        self.assertEqual(text_raw, rosmsg.get_msg_text(type_, raw=True))

    def test_iterate_packages(self):
        from rosmsg import iterate_packages, MODE_MSG, MODE_SRV
        import rospkg
        rospack = rospkg.RosPack()
        found = {}
        for p, path in iterate_packages(rospack, MODE_MSG):
            found[p] = path
            assert os.path.basename(path) == 'msg', path
            # make sure it's a package
            assert rospack.get_path(p)
        assert found
        for p, path in iterate_packages(rospack, MODE_SRV):
            found[p] = path
            assert os.path.basename(path) == 'srv', path
            # make sure it's a package
            assert rospack.get_path(p)
        assert found
        
    def test_list_types(self):
        try:
            l = rosmsg.list_types('rosmsg', '.foo')
            self.fail("should have failed on invalid mode")
        except ValueError: pass

        # test msgs
        l = rosmsg.list_types('rospy', mode='.msg')
        self.assertEqual([], l)
        l = rosmsg.list_types('diagnostic_msgs', mode='.msg')
        for t in ['diagnostic_msgs/DiagnosticArray',
                  'diagnostic_msgs/DiagnosticStatus',
                  'diagnostic_msgs/KeyValue']:
            assert t in l
        
        l = rosmsg.list_types('rospy', mode='.srv')
        self.assertEqual([], l)        
        l = rosmsg.list_types('diagnostic_msgs', mode='.srv')
        for t in ['diagnostic_msgs/AddDiagnostics', 'diagnostic_msgs/SelfTest']:
            assert t in l

    def test_get_srv_text(self):
        d = get_test_path()
        srv_d = os.path.join(d, 'srv')
        
        test_srv_package = 'diagnostic_msgs'
        rospack = rospkg.RosPack()
        srv_raw_d = os.path.join(rospack.get_path(test_srv_package), 'srv')
        for t in ['AddDiagnostics', 'SelfTest']:
            with open(os.path.join(srv_d, '%s.srv'%t), 'r') as f:
                text = f.read()
            with open(os.path.join(srv_raw_d, '%s.srv'%t), 'r') as f:
                text_raw = f.read()
                
            type_ = test_srv_package+'/'+t
            self.assertEqual(text, rosmsg.get_srv_text(type_, raw=False))
            self.assertEqual(text_raw, rosmsg.get_srv_text(type_, raw=True))

    def test_rosmsg_cmd_packages(self):
        from rosmsg import rosmsg_cmd_packages, MODE_MSG, MODE_SRV
        with fakestdout() as b:
            rosmsg_cmd_packages(MODE_MSG, 'foo', ['packages'])
            val = b.getvalue().strip()
            packages1 = val.split('\n')
            assert 'std_msgs' in packages1
        with fakestdout() as b:
            rosmsg_cmd_packages(MODE_MSG, 'foo', ['packages', '-s'])
            val = b.getvalue().strip()
            packages2 = val.split(' ')
            assert 'std_msgs' in packages2
        assert set(packages1) == set(packages2), "%s vs. %s"%(packages1, packages2)

    def test_rosmsg_cmd_list(self):
        from rosmsg import rosmsg_cmd_list, MODE_MSG, MODE_SRV
        with fakestdout() as b:
            rosmsg_cmd_list(MODE_MSG, 'messages', ['list'])
            val = b.getvalue().strip()
            packages1 = val.split('\n')
            assert 'std_msgs/String' in packages1

    
from contextlib import contextmanager
@contextmanager
def fakestdout():
    realstdout = sys.stdout
    fakestdout = StringIO()
    sys.stdout = fakestdout
    yield fakestdout
    sys.stdout = realstdout
        
