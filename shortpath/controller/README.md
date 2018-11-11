# Shortest Path
As for loop topology, we will confront the problem that broadcast storm caused by this topology.
Therefore, we came up with 3 different kinds of methods to deal with this problem.

Topology as shown in the following figure
![FatTree.jpg](https://github.com/hughesmiao/study_sdn/blob/master/shortpath/controller/images/FatTree.jpg)

## Using the controller to modify packets
shortpath_arp.py based on the pricinple that IP addresses are different under the same LAN. Actually, the controller
will capture the packets when hose send Arp Request, and then based its own recored ip_to_mac to get the destination IP,
by this IP address to get the mac address. The controller will send Arp Reply to hosts so hosts will think peers have received
the Arp Request packet and send icmp packet. Well, we will according to the icmp packet to send flows to switches.
The important code that making an Arp Reply packet as showned in the following:
``` python
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
```
The result as shown in the following figure.

![fattreearpchange.png](https://github.com/hughesmiao/study_sdn/blob/master/shortpath/controller/images/fattreearpchange.png)

## Using the controller to control ports
shortpath_banport.py imitate STP. According to STP, we will ban some ports to avoid the broadcast storm.
The most important code is mac_learning function. It will record the port number that Arp Request packet entered.
If the other ports recevie the Arp Request packet which the same hosts sended, the switch will drop this Arp Request packet.
The most important code is shown as the following:
```python
    def mac_learning(self, dpid, src, in_port):
        self.mac_to_port.setdefault(dpid, {})
        if src in self.mac_to_port[dpid]:
            if in_port != self.mac_to_port[dpid][src]:
                return False
        else:
            self.mac_to_port[dpid][src] = in_port
            return True
```
The result is same as the STP result, so it will show in the STP section.

## Using STP
STP(Spanning Tree Protocol) is a good tool to cope with the broadcast storm, but it need people to enter the command in each switch, which is really troublesome
The result as shown in the followlling figure.

![fattreearpchange02.png](https://github.com/hughesmiao/study_sdn/blob/master/shortpath/controller/images/fattreearpchange02.png)


# 最短路径
对于环状拓扑而言，找到最短路径首先需要解决的问题便是Arp风暴的问题，由于解决手法的不同，
这里会介绍三种不同的方式。

拓扑图如下图所示
![FatTree.jpg](https://github.com/hughesmiao/study_sdn/blob/master/shortpath/controller/images/FatTree.jpg)

## 使用控制器修改Arp封包
shortpath_arp.py的方法基于同一个LAN底下ip位址都不同的原理而开发的。实际上是在host发送
Arp Request时，控制器将这个封包获取，接着根据自身记录的ip_to_mac，通过目的地ip来获取对
应mac。控制器再发送一则Arp Reply给host,使得host认为对方有回复，发送icmp封包，此时再根
据icmp封包来规划flow。
下面是核心代码片段,制造一个arp reply的封包：
``` python
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
```
结果如下图所示，需要多ping几次，因为第一次会有主机没有register, register的意涵是登记
host的ip与mac的关系。

![fattreearpchange.png](https://github.com/hughesmiao/study_sdn/blob/master/shortpath/controller/images/fattreearpchange.png)

## 使用控制器来管理端口
shortpath_banport.py是模仿stp的做法，根据stp的做法，禁用一些端口来达到避免Arp风暴的目
的。其中核心代码是mac_learning这段函数，它会根据来源mac位址第一次进来的Arp来确定为该来
源mac位址的Arp封包可以通过的端口，其余端口若收到同一个来源mac位址的Arp封包则丢弃。
下面是核心代码片段：
```python
    def mac_learning(self, dpid, src, in_port):
        self.mac_to_port.setdefault(dpid, {})
        if src in self.mac_to_port[dpid]:
            if in_port != self.mac_to_port[dpid][src]:
                return False
        else:
            self.mac_to_port[dpid][src] = in_port
            return True
```
结果是可以一次pingall成功，其结果和stp的做法的结果一致，会在接下来和stp的结果一起展示。

## 使用stp协议
在controller下stp的相关命令，stp是解决环状回路的大杀器。
其结果如图所示：

![fattreearpchange02.png](https://github.com/hughesmiao/study_sdn/blob/master/shortpath/controller/images/fattreearpchange02.png)
