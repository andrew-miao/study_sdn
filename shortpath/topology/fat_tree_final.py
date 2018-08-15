from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.term import makeTerm
from mininet.node import OVSSwitch
if '__main__' == __name__:
	k=4

	hosts = []
	coreswitches = []
	aggrswitches = []
	edgeswitches = []

	host_number = (k*pow((k/2),2))
	core_sw_number = pow((k/2),2)
	aggr_sw_number = core_sw_number + ((k/2)*k)
	edge_sw_number = aggr_sw_number + ((k/2)*k)

        net = Mininet(controller=RemoteController)
        c0 = net.addController('c0',ip='192.168.0.162', port=6633)

	#add switches and hosts
	for i in range(1,host_number+1):
		host_name = 'h'+str(i)
		hosts.append(net.addHost(host_name))#,mac=mac_addr))

	for i in range(1,core_sw_number+1):
		switch_name = 's'+str(i)
		coreswitches.append(net.addSwitch(switch_name))

	for i in range(core_sw_number+1,aggr_sw_number+1):
		switch_name = 's'+str(i)
		aggrswitches.append(net.addSwitch(switch_name))
			
	for i in range(aggr_sw_number+1,edge_sw_number+1):
		switch_name = 's'+str(i)
		edgeswitches.append(net.addSwitch(switch_name))


	#core--link--aggr
	count = k/2
	b=0
	for c in range(k/2):
		for i in range(count-k/2,count):
			for j in range(b,((k/2)*k),k/2):
				net.addLink(coreswitches[i],aggrswitches[j])
		b=b+1
		count=count+k/2


	#aggr--link--edge
	count1 = k/2
	for c in range (k):
		for i in range(count1-k/2,count1):
			for j in range(count1-k/2,count1):
				net.addLink(aggrswitches[i],edgeswitches[j])
		count1=count1+k/2


	#edgeswitches--link--host
	f=1
	count2 = k/2
	for c in range((k/2)*k):
		for i in range(f-1,f):
			for j in range(count2-k/2,count2):
				net.addLink(edgeswitches[i],hosts[j])
		f=f+1
		count2 = count2 + k/2


        net.build()
        c0.start()	
	for i in range(len(coreswitches)):
        	coreswitches[i].start([c0])
	for i in range(len(aggrswitches)):
		aggrswitches[i].start([c0])
	for i in range(len(edgeswitches)):
		edgeswitches[i].start([c0])
        CLI(net)
        net.stop()


