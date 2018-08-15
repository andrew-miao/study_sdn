# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
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

# port_vlan[dpid - 1][port - 1] = vlan id
port_vlan = [[2, 3, 0], [2, 3, 0]]
# access_ports[dpid - 1] = access vlan ports
access_ports = [[1, 2], [1, 2]]
# normal_ports[dpid - 1] = normal ports
normal_ports = [[3], [3]]
# trunk_port[dpid - 1] = trunk port
trunk_ports = [4, 4]
# switch_nums = the number of switiches
switch_nums = 2
# record i and j, which is convenient to search the naive vlan vlan id
record_ij = [0, 0]
class VlanSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(VlanSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.vlan_to_port = {1: {2: {}, 3: {}}, 2: {2: {}, 3: {}}}
        self.trunk_to_port = {}
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

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
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    def SetVlanTag(self, ev, datapath, in_port):
        dpid = datapath.id
        vlan_tag = port_vlan[dpid - 1][in_port - 1]
        msg = ev.msg
        pkt = packet.Packet(msg.data)
        pkt.add_protocol(vlan.vlan(vid=vlan_tag,
                                   ethertype=ether.ETH_TYPE_8021Q))
        print "add vlan tag"
        return pkt

    def Set_Trunk_Vlan(self, ev, datapath, in_port, src):
        dpid = datapath.id
        msg = ev.msg
        pkt = packet.Packet(msg.data)
        for i in range(0, len(trunk_ports)):
            if i == dpid - 1:
                continue
            else:
                # search the vlan tag
                for j in port_vlan[i]:
                    # for the naive vlan
                    print(" the vlan to port is", self.vlan_to_port)
                    print(" the mac to port is", self.mac_to_port)
                    if j != 0:
                        if src in self.vlan_to_port[i + 1][j]:
                            check_port = self.vlan_to_port[i + 1][j][src]
                            vlan_tag = port_vlan[i][check_port - 1]
                            pkt.add_protocol(vlan.vlan(vid=vlan_tag,
                                                    ethertype=ether.ETH_TYPE_8021Q))
                            print "add the trunk vlan tag"
                            # dpid = i + 1
                            # src_vlan = j
                            record_ij[0] = i + 1
                            record_ij[1] = j
                            return pkt
                    # for the normal
                    else:
                        if src in self.mac_to_port[i + 1]:
                            check_port = self.mac_to_port[i + 1][src]
                            vlan_tag = 0
                            pkt.add_protocol(vlan.vlan(vid=vlan_tag,
                                                       ethertype=ether.ETH_TYPE_8021Q))
                            print "add the trunk normal tag"
                            return pkt

    def _send_vlan_packet_(self, datapath, msg, src, dst, src_vlan, in_port, priority,actions, out_port_type):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        if out_port_type == 'ACCESS':
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst,
                                eth_src=src, vlan_vid=(0x1000 | src_vlan))
            actions.append(parser.OFPActionPopVlan())
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, priority, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, priority, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = parser.OFPPacketOut(datapath, buffer_id=msg.buffer_id,
                                    in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    def _send_normal_packet_(self, datapath, msg, src, dst, in_port, priority, actions, out_port_type):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        if out_port_type == 'NORMAL':
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, priority, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, priority, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = parser.OFPPacketOut(datapath, buffer_id=msg.buffer_id,
                                    in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        #print("the message is ", msg," and the type of msg is ", type(msg))
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id

        self.mac_to_port.setdefault(dpid, {})
       # self.vlan_to_port.setdefault(dpid, {})
        self.trunk_to_port.setdefault(dpid, {})

        print(" the in port is", in_port)
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        if in_port in access_ports[dpid - 1]:
            pkt = self.SetVlanTag(ev, datapath, in_port)
            eth = pkt.get_protocols(ethernet.ethernet)[0]
            dst = eth.dst
            src = eth.src
            the_vlan_id = port_vlan[dpid - 1][in_port - 1]
            print(" the vlan id is", the_vlan_id)
            self.vlan_to_port[dpid][the_vlan_id][src] = in_port
        elif in_port == trunk_ports[dpid - 1]:
            pkt = self.Set_Trunk_Vlan(ev, datapath, in_port, src)
            eth = pkt.get_protocols(ethernet.ethernet)[0]
            dst = eth.dst
            src = eth.src
            self.trunk_to_port[dpid][src] = in_port

        else:
            self.mac_to_port[dpid][src] = in_port

        for p in pkt.protocols:
            print(" the protocols is", p.protocol_name)
            if p.protocol_name == 'vlan':
                src_vlan = p.vid
                f = parser.OFPMatchField.make(ofproto.OXM_OF_VLAN_VID, src_vlan)
                actions = [parser.OFPActionPushVlan(33024),
                           parser.OFPActionSetField(f)]
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data
                mod = parser.OFPPacketOut(datapath, buffer_id=msg.buffer_id,
                                          in_port=in_port, actions=actions, data=data)
                datapath.send_msg(mod)
            else:
                src_vlan = 'NULL'

        print(" the src vlan = ", src_vlan)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        print(" the switch is", datapath, " the type is", type(datapath))
        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)
        print (" the dst is", dst)
        print (" the src is", src)
        if in_port in access_ports[dpid - 1]:
            actions = []
            out_port_type = 'UNK'
            if dst in self.vlan_to_port[dpid][src_vlan]:
                out_port = self.vlan_to_port[dpid][src_vlan][dst]
                out_port_type = 'ACCESS'
            elif dst in self.mac_to_port[dpid]:
                out_port = ofproto.OFPP_IN_PORT
                out_port_type = 'UNK'
            elif dst not in self.vlan_to_port[dpid][src_vlan] and dst not in self.mac_to_port[dpid] and dst != 'ff:ff:ff:ff:ff:ff':
                out_port = trunk_ports[dpid - 1]
                out_port_type = 'TRUNK'
            else:
                out_port = ofproto.OFPP_FLOOD
                out_port_type = 'UNK'
            print(" the vlan out_port is", out_port)
            actions.append(parser.OFPActionOutput(out_port))
            self._send_vlan_packet_(datapath, msg, src, dst, src_vlan, in_port, 1, actions, out_port_type)

        elif in_port in normal_ports[dpid - 1]:
            actions = []
            out_port_type = 'UNK'
            if dst in self.mac_to_port[dpid]:
                out_port = self.mac_to_port[dpid][dst]
                out_port_type = 'NORMAL'
            else:
                out_port = ofproto.OFPP_FLOOD
                out_port_type = 'UNK'
            print(" the normal out_port is", out_port)
            actions.append(parser.OFPActionOutput(out_port))

        else:
            if src_vlan != 0:
                actions = []
                out_port_type = 'UNK'
                if dst in self.vlan_to_port[dpid][src_vlan]:
                    out_port = self.vlan_to_port[dpid][src_vlan][dst]
                    out_port_type = 'ACCESS'
                elif dst in self.mac_to_port[dpid]:
                    out_port = ofproto.OFPP_IN_PORT
                    out_port_type = 'UNK'
                elif dst not in self.vlan_to_port[dpid][src_vlan] and dst not in self.mac_to_port[dpid] and dst != 'ff:ff:ff:ff:ff:ff':
                    out_port = trunk_ports[dpid - 1]
                    out_port_type = 'TRUNK'
                else:
                    out_port = ofproto.OFPP_FLOOD
                    out_port_type = 'UNK'
                print(" the trunk out_port is ", out_port)
                actions.append(parser.OFPActionOutput(out_port))
                self._send_vlan_packet_(datapath, msg, src, dst, src_vlan, in_port, 1, actions, out_port_type)

            else:
                actions = []
                out_port_type = 'UNK'
                if dst in self.mac_to_port[dpid]:
                    out_port = self.mac_to_port[dpid][dst]
                    out_port_type = 'ACCESS'
                elif dst not in self.mac_to_port[dpid] and dst != 'ff:ff:ff:ff:ff:ff':
                    out_port = trunk_ports[dpid - 1]
                    out_port_type = 'TRUNK'
                else:
                    out_port = ofproto.OFPP_FLOOD
                    out_port_type = 'UNK'
                print(" the trunk out_port is ", out_port)
                actions.append(parser.OFPActionOutput(out_port))
                self._send_vlan_packet_(datapath, msg, src, dst, src_vlan, in_port, 1, actions, out_port_type)


