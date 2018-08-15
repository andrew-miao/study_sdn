#-*-coding:utf8-*-
# the author is BAI
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib import dpid as dpid_lib
from ryu.topology import event, switches
from ryu.topology.api import get_link
import networkx as nx
from ryu.lib.ovs import vsctl
#stp setting
OVSDB_ADDR = 'tcp:192.168.0.162:6640'
ovs_vsctl = vsctl.VSCtl(OVSDB_ADDR)
G = nx.DiGraph()
#-----------------------------vsctl(stp setting)-------------------------------#
class vsctltest (vsctl.VSCtlCommand):
        x=""
        for i in range(1,21):
                x="s"+str(i)
                command = vsctl.VSCtlCommand('set' ,('Bridge' ,x,'stp_enable=true') )
                ovs_vsctl.run_command([command])
                print(command)
#------------------------------------------------------------------------------#


class SHORTPATHSTP(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SHORTPATHSTP, self).__init__(*args, **kwargs)
        self.topology_api_app = self

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,ofproto.OFPCML_NO_BUFFER)]
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


    def get_topo(self,ev):
        links_list = get_link(self.topology_api_app, None)
        links = []
	#記錄實體links
	for link in links_list:
		links.append((link.src.dpid, link.dst.dpid, {'port': link.src.port_no}))
		#srcdpid須與G.edge同長度
		G.add_edges_from(links)


     #add switch and host(mac) to nodes
    def add_host_link_switch(self,ev,dpid,src,in_port):
         if src not in G.nodes():
                G.add_nodes_from([src])
                G.add_edges_from([(src,dpid,{'port':in_port})])
                G.add_edges_from([(dpid,src,{'port':in_port})])
         if dpid not in G.nodes():
                G.add_nodes_from(dpid)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']        
	pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src
        dpid = datapath.id
	self.add_host_link_switch(ev,dpid,src,in_port)
	self.get_topo(ev)
	#最短路徑算法
        if dst in G.nodes():
                        print 'show shortpath'
                        actions=[]
			path=nx.shortest_path(G,source=src,target=dst)
                        print 'path:',path
                        next = path[path.index(dpid) + 1]
                        out_port = G[dpid][next]['port']
                        print 'out_port:',out_port
                        actions.append(parser.OFPActionOutput(out_port))
        else:
                        print 'flodding'
                        actions=[]
                        out_port = ofproto.OFPP_FLOOD
                        actions.append(parser.OFPActionOutput(out_port))
	if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions)
	    print 'add flow'

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)






