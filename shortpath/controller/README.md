# 最短路径
对于环状拓扑而言，找到最短路径首先需要解决的问题便是Arp风暴的问题，由于解决手法的不同，
这里会介绍三种不同的方式。

## 使用控制器修改Arp封包
shortpath_arp.py的方法基于同一个LAN底下ip位址都不同的原理而开发的。实际上是在host发送
Arp Request时，控制器将这个封包获取，接着根据自身记录的ip_to_mac来根据目的地ip,获取对
应mac。控制器再发送一则Arp Reply给host,使得host认为对方有回复，发送icmp封包，此时再根
据icmp封包来规划flow。
下面是核心代码片段：
```

```
结果如下图所示，需要多ping几次，因为第一次会有主机没有register, register的意涵是登记
host的ip与mac的关系。

![]

## 使用控制器来管理端口
shortpath_banport.py是模仿stp的做法，根据stp的做法，禁用一些端口来达到避免Arp风暴的目
的。其中核心代码是mac_learning这段函数，它会根据来源mac位址第一次进来的Arp来确定为该来
源mac位址的Arp封包可以通过的端口，其余端口若收到同一个来源mac位址的Arp封包则丢弃。
下面是核心代码片段：
```

```
结果是可以一次pingall成功，其结果和stp的做法的结果一致，会在接下来和stp的结果一起展示。

## 使用stp协议
在controller下stp的相关命令，stp是解决环状回路的大杀器。
其结果如图所示：

![]
