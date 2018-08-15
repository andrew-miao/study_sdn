# Multiple vlan switch
This experience is to bulid a multiple vlan switch and the protocol is Openflow 13.
The topology is:

![topology.png](https://github.com/hughesmiao/study_sdn.github.io/blob/master/ryu/vlan/multipleswitch/images/topology.png)

host 1, host 4 in the same vlan group, the vlan id = 2
host 2, host 5 in the same vlan group, the vlan id = 3
host 3, host 6 don't have vlan tags.
The port 4 is the trunk port for these switches.
multi_vlan_topo.py is a code file about topology.

Multiple switch should use the trunk technology so that the normal packets that
we add the pvid = 0 for them. You just change the port_vlan, access_ports, normal_ports,
trunk_ports, self.vlan_to_port, and self.trunk_ports to adapt the new topology that
it changed.

The result of the experiment is:

![ping_result.png](https://github.com/hughesmiao/study_sdn.github.io/blob/master/ryu/vlan/multipleswitch/images/ping_result.png)

This figure shows that our vlan switches are work out!

The multivlanswitch_renew.py fixed a bug to do the iperf test.

The vlan_monitor.py can observe the information about packets such as error, dropped.

# 使用多个vlan switch
本次实验是使用多个交换机进行，所使用的OpenFlow协议是OpenFlow 13。
实验的拓扑图如下图所示：

![topology.png](https://github.com/hughesmiao/study_sdn.github.io/blob/master/ryu/vlan/multipleswitch/images/topology.png)

其中host 1, host 4为一组vlan, vlan id = 2， host 2, host 5为一组vlan,
vlan id = 3, host 3, host 6则是normal，两个交换机的port 4都是trunk port.
multi_vlan_topo.py是拓扑相关代码。

vlanmultipleswitch13.py是vlan switch的相关代码。
多个交换机则需要使用trunk技术，normal的封包我们所添加的pvid一律为0，如果
需要更改拓扑，只需要代码中port_vlan, access_ports, normal_ports, trunk_ports
和self.vlan_to_port, self.trunk_to_port这几个参数，就可以适应新的拓扑图。
以下为本次实验结果：

![ping_result.png](https://github.com/hughesmiao/study_sdn.github.io/blob/master/ryu/vlan/multipleswitch/images/ping_result.png)

如上图所示则证明vlan设定成功!

multivlanswitch_renew.py修正了一个bug以及为iperf测试做了一些调整。

vlan_monitor.py可以观测封包error dropped的情况。
