# 使用单个交换机架构vlan
这是一个利用官方所提供simple_switch_13.py所改编的vlanswitch.py，所使用的OpenFlow的版本是OpenFlow13.

vlanswitch.py是关于交换机主要的代码，vlanswitch保留原始switch的功能，增加了vlan的功能。其中有一句src_vlan = 5000即是没有携带vlan tag，因为vlan id的取值范围是0~4096的整数，因此采用大于4096的整数来表示没有vlan tag的封包。

mytopology.py是根据mininet所写的，其拓扑图如下图所示：

![vlan_topology01.png](https://github.com/hughesmiao/study_sdn.github.io/blob/master/ryu/vlan/singleswitch/images/vlan_topology01.png)

我的架构是要将host 1, host 2的vlan id设定成2，host 3, host 4的vlan id设定成9，host 5, host 6没有vlan tag.
设定vlan的方法：
先进入自己存放vlanswitch.py的文档底下，建议存放在ryu的文档下,执行vlanswitch.py:
```
# ryu-manager vlanswitch.py
```
在进入自己存放的mytopology.py的文档底下，建议存放在mininet的文档下，执行mytopology.py:
```
# python mytopology.py
```

进入mininet的CLI界面
```
mininet>xterm h1
mininet>xterm h2
mininet>xterm h3
mininet>xterm h4
```
在h1的xterm中执行
```
# ip addr del 10.0.0.1/8 dev h1-eth0
# ip link add link h1-eth0 name h1-eth0.2 type vlan id 2
# ip addr add 10.0.0.1/8 dev h1-eth0.2
# ip link set dev h1-eth0.2 up
```
在h2的xterm中执行
```
# ip addr del 10.0.0.2/8 dev h2-eth0
# ip link add link h2-eth0 name h2-eth0.2 type vlan id 2
# ip addr add 10.0.0.2/8 dev h2-eth0.2
# ip link set dev h2-eth0.2 up
```
在h3的xterm中执行
```
# ip addr del 10.0.0.3/8 dev h3-eth0
# ip link add link h3-eth0 name h3-eth0.9 type vlan id 9
# ip addr add 10.0.0.3/8 dev h3-eth0.9
# ip link set dev h3-eth0.9 up
```
在h4的xterm中执行
```
# ip addr del 10.0.0.4/8 dev h4-eth0
# ip link add link h4-eth0 name h4-eth0.9 type vlan id 9
# ip addr add 10.0.0.4/8 dev h4-eth0.9
# ip link set dev h4-eth0.9 up
```
xterm设定情况如下图所示：

![vlan_singleswitch_vlantag.png](https://github.com/hughesmiao/study_sdn.github.io/blob/master/ryu/vlan/singleswitch/images/vlan_singleswitch_vlantag.png)

接着，我们再回到mininet的CLI底下执行pingall
```
mininet>pingall
```
当出现如下图所示的结果：

![vlan_singleswitch_result.png](https://github.com/hughesmiao/study_sdn.github.io/blob/master/ryu/vlan/singleswitch/images/vlan_singleswitch_result.png)

证明我们的vlan架构成功！

现在介绍另外一种方法添加vlan tag，这种方法也会在multiplevlanswitch上使用。
我们将vlan tag直接写在ryu controller里面，直接执行。如果需要修改vlan or ports
只需要更改port_vlan, access_ports, normal_ports, self.vlan_to_port即可，较为
简便。
相关代码为vlanswitch02.py

以下是拓扑图：

![vlan_topology02.py](https://github.com/hughesmiao/study_sdn.github.io/blob/master/ryu/vlan/singleswitch/images/vlan_topology02.png)

其中host 1, host 2, host 4是一组vlan, vlan id = 2， host 3, host 5是normal port,
host 6, host7是一组vlan, vlan id = 3.

下图是ping的结果：

![ping_result02.png](https://github.com/hughesmiao/study_sdn.github.io/blob/master/ryu/vlan/singleswitch/images/ping_result02.png)

singlevlanswitch_renew.py是针对于iperf测试所做的更新。
vlan_monitor.py可以观测封包error or drop的情况。
