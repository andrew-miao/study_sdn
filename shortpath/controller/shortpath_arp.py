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
        self.ip_to_port = {}
        self.mac_to_port = {}
        self.trunk_to_port = {}
        self.ip_to_mac = {}
        self.topology_get = self
        self.net = nx.DiGraph()
        self.switches = []
        self.sw_num = 0
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        print "dpid is", dpid
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
        if dpid not in self.switches:
            self.switches.append(dpid)
            self.net.add_node(dpid)
            self.ip_to_port.setdefault(dpid, {})
            self.ip_to_mac.setdefault(dpid, {})
        print "the switches are", self.switches
        self.sw_num = len(self.switches)
        print "sw_num is", self.sw_num
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
        #print(" the in port is", in_port)
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
#        dst = eth.dst
        src = eth.src
        pkt_ether = pkt.get_protocol(ethernet.ethernet)
        #for p in pkt:
        #    print(" the protocol is", p.protocol_name)
        #    if p.protocol_name == 'vlan':
        #        print(" the vlan id is ", p.vid)
        dpid = datapath.id
        arp_pkt = pkt.get_protocol(arp.arp)
        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)
        if arp_pkt:
            ip_src = arp_pkt.src_ip
            ip_dst = arp_pkt.dst_ip
            print "the ip is", ip_src
            self.ip_to_port[dpid][ip_src] = in_port
            self.ip_to_mac[dpid][ip_src] = src
            if ip_src not in self.net.node():
                self.net.add_node(ip_src)
                self.net.add_edge(ip_src, dpid, port=in_port)
                self.net.add_edge(dpid, ip_src, port=in_port)
            self._handle_arp(datapath, in_port, ip_src, ip_dst, pkt_ether, arp_pkt, msg)
            self.logger.info("the arp data is %s" % (pkt,))
            return
        if pkt_ipv4:
            print "now the dpid is", dpid
            ip_src = pkt_ipv4.src
            ip_dst = pkt_ipv4.dst
            self.ip_to_port[dpid][ip_src] = in_port
            self.ip_to_mac[dpid][ip_src] = src
            self._install_flow(datapath, in_port, ip_src, ip_dst, pkt_ipv4, msg)
            self.logger.info("the ipv4 data is %s" % (pkt,))

    def get_path(self, datapath, ip_src, ip_dst):
        if ip_src not in self.net.nodes() or ip_dst not in self.net.nodes():
            return
        dpid = datapath.id
        path = nx.shortest_path(self.net, ip_src, ip_dst)
        print "the dpid is", dpid
        print "the path is", path
        if dpid in path:
            next_stat = path[path.index(dpid) + 1]
            out_port = self.net[dpid][next_stat]['port']
            return out_port
        else:
            return None


    def _handle_arp(self, datapath, in_port, ip_src, ip_dst, pkt_ether, arp_pkt, msg):
        out_port = 0
        for i in range(self.sw_num):
            if ip_dst in self.ip_to_port[i + 1].keys():
                self.logger.info("start handle the arp packet")
                out_port = self.get_path(datapath, ip_src, ip_dst)
                u = i + 1
        if out_port:
            print "the out_port is", out_port
            dst_dpid = u
            self._make_arp_reply(datapath, in_port, out_port, ip_src, ip_dst,
                                pkt_ether, dst_dpid, arp_pkt, msg)
        else:
            self.logger.info("Sorry, the switch is not in the shortest_path or the switch haven't register")
            return None

    def _install_flow(self, datapath, in_port, ip_src, ip_dst, pkt_ipv4, msg):
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        out_port = self.get_path(datapath, ip_src, ip_dst)
        print "the ip out port is", out_port
        if out_port:
            src = self.ip_to_mac[dpid][ip_src]
            dst = ''
            for i in range(self.sw_num):
                if ip_dst in self.ip_to_mac[i + 1].keys():
                    dst = self.ip_to_mac[i + 1][ip_dst]
            actions = [parser.OFPActionOutput(out_port)]
            match = parser.OFPMatch(in_port=in_port, eth_src=src, eth_dst=dst)
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
            else:
                self.add_flow(datapath, 1, match, actions)
            self.logger.info("Adding first flows")
            temp1 = in_port
            in_port = out_port
            out_port = temp1
            temp2 = src
            src = dst
            dst = temp2
            actions = [parser.OFPActionOutput(out_port)]
            match = parser.OFPMatch(in_port=in_port, eth_src=src, eth_dst=dst)
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
            else:
                self.add_flow(datapath, 1, match, actions)
            self.logger.info("Adding second flows")
            return
        else:
            self.logger.info("Sorry, cannot add this flow")
            return

    def _send_packet_out(self, datapath, in_port, out_port, pkt, msg):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        actions = [parser.OFPActionOutput(out_port)]
        self.logger.info("packet-out %s" % (pkt,))
        buffer_id = msg.buffer_id
        data = None
        pkt_arp = pkt.get_protocol(arp.arp)
        if pkt_arp:
            if pkt_arp.opcode == arp.ARP_REPLY:
                buffer_id = ofproto.OFP_NO_BUFFER
        if buffer_id == ofproto.OFP_NO_BUFFER:
            data = pkt.data
        out = parser.OFPPacketOut(datapath, buffer_id=buffer_id, in_port=in_port,
                                  actions=actions, data=data)
        datapath.send_msg(out)

    def _make_arp_reply(self, datapath, in_port, out_port, ip_src, ip_dst, pkt_ether, dst_dpid, arp_pkt, msg):
        if arp_pkt.opcode != arp.ARP_REQUEST:
            return
        dpid = datapath.id
        dst_hw_addr = self.ip_to_mac[dpid][ip_src]
        src_hw_addr = self.ip_to_mac[dst_dpid][ip_dst]
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=pkt_ether.ethertype,
                                           dst=dst_hw_addr,
                                           src=src_hw_addr))
        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                 src_mac=src_hw_addr,
                                 src_ip=ip_dst,
                                 dst_mac=dst_hw_addr,
                                 dst_ip=ip_src))
        pkt.serialize()
        temp = in_port
        in_port = out_port
        out_port = temp
        self._send_packet_out(datapath, in_port, out_port, pkt, msg)
