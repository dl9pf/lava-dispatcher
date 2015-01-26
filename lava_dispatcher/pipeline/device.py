# Copyright (C) 2014 Linaro Limited
#
# Author: Neil Williams <neil.williams@linaro.org>
#
# This file is part of LAVA Dispatcher.
#
# LAVA Dispatcher is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# LAVA Dispatcher is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along
# with this program; if not, see <http://www.gnu.org/licenses>.

import os
import yaml
import collections
from yaml.composer import Composer
from yaml.constructor import Constructor
from lava_dispatcher.pipeline.action import Timeout


class DeviceTypeParser(object):
    """
    Very simple (too simple) parser for Device configuration files
    """

    # FIXME: design a schema and check files against it.

    loader = None

    def compose_node(self, parent, index):
        # the line number where the previous token has ended (plus empty lines)
        node = Composer.compose_node(self.loader, parent, index)
        return node

    def construct_mapping(self, node, deep=False):
        mapping = Constructor.construct_mapping(self.loader, node, deep=deep)
        return mapping

    def parse(self, content):
        self.loader = yaml.Loader(content)
        self.loader.compose_node = self.compose_node
        self.loader.construct_mapping = self.construct_mapping
        data = self.loader.get_single_data()
        return data


class NewDevice(object):
    """
    YAML based Device class with clearer support for the pipeline overrides
    and deployment types.
    To simplify development and prepare for the dumb dispatcher model, the
    development path is the current working directory. The system path
    is the installed location of this python module and is overridden by
    files in the development path.
    """

    def __init__(self, target):
        self.target = target
        self.__parameters__ = {}
        # development paths are within the current working directory
        device_config_path = os.getcwd()
        name = os.path.join('devices', "%s.yaml" % target)
        device_file = os.path.join(device_config_path, name)
        if not os.path.exists(device_file):
            # system paths are in the installed location of __file__
            # principally used for unit-test support
            device_config_path = os.path.join(os.path.dirname(__file__))
            sys_device_file = os.path.join(device_config_path, name)
            if not os.path.exists(sys_device_file):
                raise RuntimeError(
                    "Unable to find config file for device: %s  as %s or %s" % (
                        target, device_file, sys_device_file))
            device_file = sys_device_file

        # Parse the yaml configuration
        try:
            with open(device_file) as f_in:
                self.parameters = yaml.load(f_in)
        except yaml.parser.ParserError:
            raise RuntimeError("%s could not be parsed" % device_file)

        self.parameters = {
            'hostname': target
        }
        self.parameters.setdefault('power_state', 'off')  # assume power is off at start of job

    @property
    def parameters(self):
        return self.__parameters__

    @parameters.setter
    def parameters(self, data):
        self.__parameters__.update(data)

    def check_config(self, job):
        """
        Validates the combination of the job and the device
        *before* the Deployment actions are initialised.
        """
        raise NotImplementedError("check_config")

    @property
    def hard_reset_command(self):
        if 'commands' in self.parameters and 'hard_reset' in self.parameters['commands']:
            return self.parameters['commands']['hard_reset']
        return ''

    @property
    def power_command(self):
        if 'commands' in self.parameters and 'power_on' in self.parameters['commands']:
            return self.parameters['commands']['power_on']
        return self.hard_reset_command

    @property
    def connect_command(self):
        if 'connect' in self.parameters['commands']:
            return self.parameters['commands']['connect']
        return ''

    @property
    def power_state(self):
        """
        The power_state may appear to be a boolean (with on and off string values) but
        also copes with devices where the device has no power commands, returning an
        empty string.
        """
        if 'commands' in self.parameters and 'power_on' in self.parameters['commands']:
            return self.parameters['power_state']
        return ''

    @power_state.setter
    def power_state(self, state):
        if 'commands' not in self.parameters or 'power_off' not in self.parameters['commands']:
            raise RuntimeError("Power state not supported for %s" % self.parameters['hostname'])
        if state is '' or state is not 'on' and state is not 'off':
            raise RuntimeError("Attempting to set an invalid power state")
        self.parameters['power_state'] = state
