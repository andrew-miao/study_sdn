Yen's algorithm是一个很好的来解决无环状以及无负权重的拓扑中k-th shortest paths问题的很棒的算法。
接下来是我个人对于Yen's algorithm的理解:
首先,设定k值，然后制造两个集合一个为A，记录最短路径(k-th shortest paths)，另一个集合为B，记录迭代路径(potential k-th shortest paths)。
再利用dijkstra算出一条最短路径，P(1)，将这条P(1)记录至A[1].
接下来将这条path中的除了起点和终点外做偏移，举例来说第1点到第n点的最短路径P(1)是1->2->3->...-> n,
那么接下来偏移的话，则是将1, 2之间权重设为无穷大，偏移之后的结果如，1->3->5->...-> n,将这条路径称为P(2),记录至B集合，称为B[1]，
继续迭代这个过程产生k条最小圈中的路径，B集合记录至B[k],完成这一轮。
挑选出B集合中最小路径，B[x]加入至A，记录为A[2]，接下来的偏移路径则是A[2]，继续和A[1]一样的迭代过程，但如果产生的路径已在B集合，
则不加入B集合，如果是新路径才可以加入B集合，这样持续迭代，产生新一轮的B.
迭代上述过程直到A达到A[k]，则结束算法。

代码方面展现的是k=2的Yen's algorithm的实现，拓扑图如下所示：

![yen_graph.png](https://github.com/hughesmiao/study_sdn/blob/master/multipath/topology/yen_graph.png)

