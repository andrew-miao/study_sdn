#! /usr/bin/env python
# -*- coding: utf-8 -*-
# the author is MIAO
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import array
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import vlan
from ryu.ofproto import ether
from ryu.lib.packet import arp
from ryu.lib.packet import ipv4
from ryu.lib.packet import icmp
from ryu.topology.api import get_link
from ryu.topology import event
import networkx as nx
class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.topology_get = self
        self.net = nx.DiGraph()
        self.switches = []
        self.sw_num = 0
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        #dpid = datapath.id
        #if not dpid in self.switches:
        #    self.switches.append(dpid)
        #    self.net.add_node(dpid)
        #self.sw_num = len(self.switches)
        #print "the switches are", self.switches
        #print "the tot number is", self.sw_num
        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match, instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    events = [event.EventSwitchEnter,
              event.EventSwitchLeave, event.EventPortAdd,
              event.EventPortDelete, event.EventPortModify,
              event.EventLinkAdd, event.EventLinkDelete]
    @set_ev_cls(events)
    def get_topo(self, ev):
        links_list = get_link(self.topology_get, None)
        for link in links_list:
            self.net.add_edge(link.src.dpid, link.dst.dpid, port=link.src.port_no)

    def mac_learning(self, dpid, src, in_port):
        self.mac_to_port.setdefault(dpid, {})
        if src in self.mac_to_port[dpid]:
            if in_port != self.mac_to_port[dpid][src]:
                return False
        else:
            self.mac_to_port[dpid][src] = in_port
            return True

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match['in_port']
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        #print(" the in port is", in_port)
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        if eth.ethertype == ether_types.ETH_TYPE_IPV6:
            match = parser.OFPMatch(eth_type=eth.ethertype)
            actions = []
            self.add_flow(datapath, 5, match, actions)
            return
        dst = eth.dst
        src = eth.src
        #for p in pkt:
        #    print(" the protocol is", p.protocol_name)
        #    if p.protocol_name == 'vlan':
        #        print(" the vlan id is ", p.vid)
        dpid = datapath.id
        if dpid not in self.switches:
            self.switches.append(dpid)
            self.net.add_node(dpid)
        sw_test = len(self.switches)
        print "the sw_test = ", sw_test
        if src not in self.net.node():
            self.net.add_node(src)
            self.net.add_edge(src, dpid, port=in_port)
            self.net.add_edge(dpid, src, port=in_port)
        #self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)
        self.mac_learning(dpid, src, in_port)
        actions = []
        out_port_type = 'UNK'
        if dst in self.net.node():
            out_port = self.get_path(datapath, src, dst)
            actions.append(parser.OFPActionOutput(out_port))
            out_port_type = 'SHORT PATH'
        else:
            if self.mac_learning(dpid, src, in_port) is False:
                out_port = ofproto.OFPPC_NO_FWD
                actions.append(parser.OFPActionOutput(out_port))
                out_port_type = 'UNK'
                self.logger.info("Start drop the bad arp")
            else:
                out_port = ofproto.OFPP_FLOOD
                actions.append(parser.OFPActionOutput(out_port))
                out_port_type = 'FLOOD'
                self.logger.info("Start flooding")
        if out_port_type == 'SHORT PATH':
            match = parser.OFPMatch(in_port, eth_dst=dst)
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 7, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 7, match, actions)
            self.logger.info("Adding short path flows")
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
                                  actions=actions, data=data)
        datapath.send_msg(out)
    def get_path(self, datapath, src, dst):
        if src not in self.net.nodes() or dst not in self.net.nodes():
            return
        dpid = datapath.id
        path = nx.shortest_path(self.net, src, dst)
        print "the dpid is", dpid
        print "the path is", path
        if dpid in path:
            next_stat = path[path.index(dpid) + 1]
            out_port = self.net[dpid][next_stat]['port']
            return out_port
        else:
            return None


