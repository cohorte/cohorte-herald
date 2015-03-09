#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Package providing the tunneling feature

:author: Thomas Calmant
:copyright: Copyright 2015, isandlaTech
:license: Apache License 2.0
:version: 0.0.4
:status: Alpha

..

    Copyright 2015 isandlaTech

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

# Module version
__version_info__ = (0, 0, 4)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

SERVICE_TUNNEL = "herald.tunnel"
""" Specification of the tunnel input handler """

SERVICE_TUNNEL_OUTPUT = "herald.tunnel.output"
""" Specification of the tunnel output handler """

SERVICE_TUNNEL_INPUT_CREATOR = "herald.tunnel.input.creator"
""" Specification of a tunnel input creator """

SERVICE_TUNNEL_OUTPUT_CREATOR = "herald.tunnel.output.creator"
""" Specification of a tunnel output creator """

# ------------------------------------------------------------------------------

_INPUT_PATTERN = "herald/tunnel/input/{0}"
""" Pattern for input herald tunnel subjects """

_OUTPUT_PATTERN = "herald/tunnel/output/{0}"
""" Pattern for output herald tunnel subjects """

MATCH_INPUT_SUBJECTS = _INPUT_PATTERN.format("*")
""" Filter to match all tunnel subjects """

MATCH_OUTPUT_SUBJECTS = _OUTPUT_PATTERN.format("*")
""" Filter to match all tunnel subjects """

SUBJECT_CREATE_OUTPUT_TUNNEL = _OUTPUT_PATTERN.format("create-tunnel")
""" Input -> Output: Request the creation of the tunnel output """

SUBJECT_CREATE_OUTPUT_LINK = _OUTPUT_PATTERN.format("create-link")
""" Input -> Output: Request the creation of an output link """

SUBJECT_CLOSE_INPUT_TUNNEL = _INPUT_PATTERN.format("close-tunnel")
""" Output -> Input: Output notifies the input that it must close a tunnel """

SUBJECT_CLOSE_OUTPUT_TUNNEL = _OUTPUT_PATTERN.format("close-tunnel")
""" Input -> Output: Input notifies the OUPUT that it must close a tunnel """

SUBJECT_CLOSE_INPUT_LINK = _INPUT_PATTERN.format("close-link")
""" Output -> Input: Output notifies the input that it must close a link """

SUBJECT_CLOSE_OUTPUT_LINK = _OUTPUT_PATTERN.format("close-link")
""" Input -> Output: Input notifies the OUPUT that it must close a link """

SUBJECT_DATA_FROM_INPUT = _OUTPUT_PATTERN.format("data-from-input")
""" Input -> Output: Data coming back from output to input """

SUBJECT_DATA_FROM_OUTPUT = _INPUT_PATTERN.format("data-from-output")
""" Output -> Input: Data coming back from output to input """
