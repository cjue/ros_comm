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

NAME = 'test_core'

import os
import sys
import unittest

import rospkg

_lastmsg = None
def printlog_cb(msg):
    global _lastmsg 
    _lastmsg = msg
def printlog_cb_exception(msg):
    raise Exception(msg)
    
## Test roslaunch.core
class TestCore(unittest.TestCase):
    def test_xml_escape(self):
        from roslaunch.core import _xml_escape
        self.assertEqual('', _xml_escape(''))
        self.assertEqual(' ', _xml_escape(' '))        
        self.assertEqual('&quot;', _xml_escape('"'))
        self.assertEqual('&quot;hello world&quot;', _xml_escape('"hello world"'))
        self.assertEqual('&gt;', _xml_escape('>'))
        self.assertEqual('&lt;', _xml_escape('<'))
        self.assertEqual('&amp;', _xml_escape('&'))
        self.assertEqual('&amp;amp;', _xml_escape('&amp;'))        
        self.assertEqual('&amp;&quot;&gt;&lt;&quot;', _xml_escape('&"><"'))
        
        
    def test_child_mode(self):
        from roslaunch.core import is_child_mode, set_child_mode
        set_child_mode(False)
        self.assertFalse(is_child_mode())
        set_child_mode(True)
        self.assertTrue(is_child_mode())        
        set_child_mode(False)
        self.assertFalse(is_child_mode())

    def test_printlog(self):
        from roslaunch.core import add_printlog_handler, add_printerrlog_handler, printlog, printlog_bold, printerrlog
        add_printlog_handler(printlog_cb)
        add_printlog_handler(printlog_cb_exception)        
        add_printerrlog_handler(printlog_cb)
        add_printerrlog_handler(printlog_cb_exception)        
            
        #can't really test functionality, just make sure it doesn't crash
        global _lastmsg
        _lastmsg = None
        printlog('foo')
        self.assertEqual('foo', _lastmsg)
        printlog_bold('bar')
        self.assertEqual('bar', _lastmsg)        
        printerrlog('baz')
        self.assertEqual('baz', _lastmsg)        
        
    def test_setup_env(self):
        from roslaunch.core import setup_env, Node, Machine
        master_uri = 'http://masteruri:1234'

        n = Node('nodepkg','nodetype')
        m = Machine('name1', '1.2.3.4')
        d = setup_env(n, m, master_uri)
        self.assertEqual(d['ROS_MASTER_URI'], master_uri)

        m = Machine('name1', '1.2.3.4')
        d = setup_env(n, m, master_uri)
        val = os.environ['ROS_ROOT']
        self.assertEqual(d['ROS_ROOT'], val)

        # test ROS_NAMESPACE
        # test stripping
        n = Node('nodepkg','nodetype', namespace="/ns2/")
        d = setup_env(n, m, master_uri)
        self.assertEqual(d['ROS_NAMESPACE'], "/ns2")

        # test node.env_args
        n = Node('nodepkg','nodetype', env_args=[('NENV1', 'val1'), ('NENV2', 'val2'), ('ROS_ROOT', '/new/root')])        
        d = setup_env(n, m, master_uri)
        self.assertEqual(d['ROS_ROOT'], "/new/root")
        self.assertEqual(d['NENV1'], "val1")
        self.assertEqual(d['NENV2'], "val2")

        
    def test_local_machine(self):
        try:
            env_copy = os.environ.copy()

            from roslaunch.core import local_machine
            lm = local_machine()
            self.assertFalse(lm is None)
            #singleton
            self.assertTrue(lm == local_machine())

            self.assertEqual(lm.name, '')
            self.assertEqual(lm.assignable, True)
            self.assertEqual(lm.env_loader, None)        
            self.assertEqual(lm.user, None)
            self.assertEqual(lm.password, None)
        finally:
            os.environ = env_copy

        
    def test_Master(self):
        from roslaunch.core import Master
        old_env = os.environ.get('ROS_MASTER_URI', None)
        try:
            os.environ['ROS_MASTER_URI'] = 'http://foo:789'
            m = Master()
            self.assertEqual(m.type, Master.ROSMASTER)
            self.assertEqual(m.uri, 'http://foo:789')
            self.assertEqual(m, m)
            self.assertEqual(m, Master())
            
            m = Master(Master.ROSMASTER, 'http://foo:1234')
            self.assertEqual(m.type, Master.ROSMASTER)
            self.assertEqual(m.uri, 'http://foo:1234')
            self.assertEqual(m, m)
            self.assertEqual(m, Master(Master.ROSMASTER, 'http://foo:1234'))

            try:
                from xmlrpc.client import ServerProxy
            except ImportError:
                from xmlrpclib import ServerProxy
            self.assertTrue(isinstance(m.get(), ServerProxy))
            m.uri = 'http://foo:567'
            self.assertEqual(567, m.get_port())
            self.assertFalse(m.is_running())

        finally:
            if old_env is None:
                del os.environ['ROS_MASTER_URI']
            else:
                os.environ['ROS_MASTER_URI'] = old_env

    def test_Executable(self):
        from roslaunch.core import Executable, PHASE_SETUP, PHASE_RUN, PHASE_TEARDOWN

        e = Executable('ls', ['-alF'])
        self.assertEqual('ls', e.command)
        self.assertEqual(['-alF'], e.args)
        self.assertEqual(PHASE_RUN, e.phase)
        self.assertEqual('ls -alF', str(e))
        self.assertEqual('ls -alF', repr(e))        

        e = Executable('ls', ['-alF', 'b*'], PHASE_TEARDOWN)
        self.assertEqual('ls', e.command)
        self.assertEqual(['-alF', 'b*'], e.args)
        self.assertEqual(PHASE_TEARDOWN, e.phase)
        self.assertEqual('ls -alF b*', str(e))
        self.assertEqual('ls -alF b*', repr(e))        

    def test_RosbinExecutable(self):
        from roslaunch.core import RosbinExecutable, PHASE_SETUP, PHASE_RUN, PHASE_TEARDOWN

        e = RosbinExecutable('ls', ['-alF'])
        self.assertEqual('ls', e.command)
        self.assertEqual(['-alF'], e.args)
        self.assertEqual(PHASE_RUN, e.phase)
        self.assertEqual('ros/bin/ls -alF', str(e))
        self.assertEqual('ros/bin/ls -alF', repr(e))        

        e = RosbinExecutable('ls', ['-alF', 'b*'], PHASE_TEARDOWN)
        self.assertEqual('ls', e.command)
        self.assertEqual(['-alF', 'b*'], e.args)
        self.assertEqual(PHASE_TEARDOWN, e.phase)
        self.assertEqual('ros/bin/ls -alF b*', str(e))
        self.assertEqual('ros/bin/ls -alF b*', repr(e))        
