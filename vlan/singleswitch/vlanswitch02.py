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
port_vlan = [[2, 2, 0, 2, 0, 3, 3]]
# access_ports[dpid - 1] = access vlan ports
access_ports = [[1, 2, 4, 6, 7]]
# normal_ports[dpid - 1] = normal ports
normal_ports = [[3, 5]]

class VlanSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(VlanSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.vlan_to_port = {1:{2: {}, 3: {}}}
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
        else:
            self.mac_to_port[dpid][src] = in_port

        for p in pkt.protocols:
            print(" the protocols is", p.protocol_name)
            if p.protocol_name == 'vlan':
                src_vlan = p.vid
                self.vlan_to_port[dpid][src_vlan][src] = in_port
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
#        dst = eth.dst
#        src = eth.src

#        self.mac_to_port.setdefault(dpid, {})
#        self.vlan_to_port.setdefault(dpid, {})
        print(" the switch is", datapath, " the type is", type(datapath))
        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)
        print (" the dst is", dst)
        print (" the src is", src)
        # learn a mac address to avoid FLOOD next time.
        if src_vlan != 'NULL':
            actions = []
            print(" the vlan table is", self.vlan_to_port[dpid][src_vlan])
          #  if dst in self.vlan_to_port[dpid]:
            if dst in self.vlan_to_port[dpid][src_vlan]:
                out_port = self.vlan_to_port[dpid][src_vlan][dst]
            elif dst not in self.vlan_to_port[dpid] and dst != 'ff:ff:ff:ff:ff:ff':
                out_port = ofproto.OFPP_IN_PORT
            else:
                out_port = ofproto.OFPP_FLOOD
            print(" the vlan out port is", out_port)
            actions.append(parser.OFPActionOutput(out_port))
            if out_port != ofproto.OFPP_FLOOD and out_port != ofproto.OFPP_IN_PORT:
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst,
                                        eth_src=src, vlan_vid=(0x1000 | src_vlan))
                actions.append(parser.OFPActionPopVlan())
                actions.append(parser.OFPActionOutput(out_port))
                if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                    self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                    return
                else:
                    self.add_flow(datapath, 1, match, actions)
            data = None
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data = msg.data
            out = parser.OFPPacketOut(datapath, buffer_id=msg.buffer_id,
                                        in_port=in_port, actions=actions, data=data)
            datapath.send_msg(out)

        else:
            actions = []
            print(" the normal table is", self.mac_to_port)
            if dst in self.mac_to_port[dpid]:
                out_port = self.mac_to_port[dpid][dst]
            #elif dst in self.vlan_to_port[dpid]:
            #elif dst in self.vlan_to_port[dpid][src_vlan]:
             #   out_port = ofproto.OFPP_IN_PORT
            else:
                out_port = ofproto.OFPP_FLOOD
            print(" the normal out port is", out_port)
            actions.append(parser.OFPActionOutput(out_port))
            if out_port != ofproto.OFPP_FLOOD and out_port != ofproto.OFPP_IN_PORT:
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
                if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                    self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                    return
                else:
                    self.add_flow(datapath, 1, match, actions)
            data = None
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data - msg.data
            out = parser.OFPPacketOut(datapath, buffer_id=msg.buffer_id,
                                        in_port=in_port, actions=actions, data=data)
            datapath.send_msg(out)

