# Install Ryu
There are 2 ways to install Ryu
1.The official way:
```
$ sudo pip install ryu
```
If you choose this way to install Ryu, the Ryu is under the python2.7/dist-packets.

2.Using git to get Ryu ( I use this way, the path is easily to find but waste a little time):
```
$ sudo su
# apt-get install python-pip python-dev build-essential
# pip install --upgrade pip 
```
Because this pip is not the newest version, if you don't want to upgrade pip, you can choose to keep the old version.
```
# apt-get install python-eventlet
# apt-get install python-routes
# apt-get install python-webob
# apt-get install python-paramiko
# pip install tinyrpc 
# apt-get install oslo.config
# pip install msgpack
```
The dependent packet is competely installed now. Then we use git to install Ryu.

If you don't install git, you should
```
# apt-get install git
```
else:
```
# git clone https://github.com/osrg/ryu.git
```
Then
```
# cd ryu
# python ./setup.py install
```
Entering the following command line to test ryu is successfully installed.
```
# ryu-manager
```
Like the picture

![ryu_test.png](https://github.com/hughesmiao/study_sdn/tree/master/install/images)

Now, you can start the Ryu!

# 安装Ryu
有两种方法安装Ryu:
1.官方方法:
```
$ sudo pip install ryu
```
如果你选择这个方法去安装你的Ryu,你的Ryu会被放在python2.7/dist-packets底下。

2.使用git的方式去安装Ryu（我是使用这个方式来安装Ryu，路径比较好找，但花了一些时间去安装相关套件）:
```
$ sudo su
# apt-get install python-pip python-dev build-essential
# pip install --upgrade pip # because this pip is not the newest version.
```
因为下载的pip不是最新版，因此选择更新，当然你也可以选择不做更新的动作
```
apt-get install python-eventlet
apt-get install python-routes
apt-get install python-webob
apt-get install python-paramiko
pip install tinyrpc
apt-get install oslo.config
pip install msgpack
```
至此，我们相关套件都下载完毕，接下来我们使用git的方式安装Ryu。
如果你还没有安装git，你应该先:
```
# apt-get install git
```
安装完git之后
```
# git clone https://github.com/osrg/ryu.git
```
接着
```
# cd ryu
# python ./setup.py install
```
输入下列命令列来测试Ryu是否成功安装:
```
# ryu-manager
```
如果如下图所示

![ryu_test.png](https://github.com/hughesmiao/study_sdn/tree/master/install/images)

那么就开始你的Ryu之旅吧！
