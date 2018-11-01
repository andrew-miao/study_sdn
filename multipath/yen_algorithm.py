#! usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

def my_reverse(a):
    return a[::-1]

#init
inf = 999999
n = 6
raw_weig_mat = np.zeros((n, n), dtype=np.int64, order='C')
help_mat = np.zeros((n, n), dtype=np.int64, order='C')
for i in range(0, n):
    for j in range(0, n):
        if i == j:
            raw_weig_mat[i][j] = 0
        else:
            raw_weig_mat[i][j] = inf
raw_weig_mat[0][1] = 3
raw_weig_mat[0][2] = 2

raw_weig_mat[1][3] = 4

raw_weig_mat[2][1] = 1
raw_weig_mat[2][3] = 2
raw_weig_mat[2][4] = 3

raw_weig_mat[3][4] = 2
raw_weig_mat[3][5] = 1

raw_weig_mat[4][5] = 2

def dijkstra(matrix, src, dst):
    check = np.zeros((len(matrix[0])), dtype=np.int64, order='C')
    dist = np.zeros((len(matrix[0])), dtype=np.int64, order='C')
    path = []
    check[0] = 1
    for i in range(len(matrix[0])):
        path.append(src)
        dist[i] = matrix[0][i]
    while 0 in check:
        u = 0
        mini = inf
        for i in range(1, len(check)):
            if check[i] == 0 and dist[i] <= mini:
                mini = dist[i]
                u = i
        for i in range(1, len(dist)):
            if dist[i] > dist[u] + matrix[u][i] and matrix[u][i] < inf:
                dist[i] = dist[u] + matrix[u][i]
                path[i] = u + 1
        check[u] = 1
    short_path = []
    pre_node = dst
    while pre_node != src:
        short_path.append(pre_node)
        pre_node = path[pre_node - 1]
    short_path.append(src)
    short_path = my_reverse(short_path)
    return [dist[dst-1], short_path]

def yen_algorithm(matrix, src, dst, k):
    # A is the list that save the shortest paths.
    A = []
    for i in range(k):
        A.append([])
    # B is the list to save the potential path.
    B = []
    A[0] = dijkstra(matrix, src, dst)
    for i in range(1, k):
        # init
        non_rootpath = []
        for j in range(1, len(A[0][1])):
            non_rootpath.append(A[0][1][j])
        m = src
        while len(non_rootpath) != 0:
            # set inf
            for j in range(k):
                if len(A[j]) != 0 and m in A[j][1]:
                    m_next = A[j][1][A[j][1].index(m) + 1]
                    help_mat[m - 1][m_next - 1] = matrix[m - 1][m_next - 1]
                    matrix[m - 1][m_next - 1] = inf
                else:
                    continue
            # get the shortest path
            new_path = dijkstra(matrix, src, dst)
            # append to B
            if new_path not in B:
                B.append(new_path)
            # recover the raw matrix
            for x in range(len(help_mat[0])):
                for y in range(len(help_mat[0])):
                    if help_mat[x][y] != 0:
                        matrix[x][y] = help_mat[x][y]
                        help_mat[x][y] = 0
            m = m_next
            non_rootpath.pop(0)
        mini = B[0][0]
        u = 0
        for j in range(len(B)):
            if B[j][0] < mini:
                mini = B[j][0]
                u = j
        A[i] = B[u]
        B.pop(u)
    return A

test = yen_algorithm(raw_weig_mat, 1, 6, 3)
print "the result is", test
