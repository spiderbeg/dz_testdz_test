# -*- coding:utf8 -*-
# 正常导入
import copy
from urllib.parse import quote # 中文转 url 编码
#外部启动django脚本-----------------------------------------------------
import os 
import sys
import requests
import time
import random
from requests_html import HTMLSession
import smtplib
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
import pandas as pd
# from fake_useragent import UserAgent
import datetime
import dzaccount
import logging
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',handlers=[logging.FileHandler('dzinfo.log', 'a+', 'utf-8')]) # 字符串格式
LOGGER = logging.getLogger("django_timing")
LOGGER.setLevel(logging.DEBUG)


class MonitorDZ:
    """监测大众点评排名并发送邮件"""

    def __init__(self,refer='https://m.baidu.com/from=844b/bd_page_type=1/ssid=0/uid=0/pu=usm%409%2Csz%40320_1001%2Cta%40iphone_2_6.0_24_77.0/baiduid=980B6CDC3E14B7C7FBCB66913295563C/w=0_10_/t=iphone/l=1/tc?clk_type=1&vit=osres&l=1&baiduid=980B6CDC3E14B7C7FBCB66913295563C&w=0_10_%E7%82%B9%E8%AF%84&t=iphone&ref=www_iphone&from=844b&ssid=0&uid=0&lid=8850393628761261721&bd_page_type=1&pu=usm%409%2Csz%40320_1001%2Cta%40iphone_2_6.0_24_77.0&order=3&fm=alop&isAtom=1&waplogo=1&is_baidu=0&tj=www_normal_3_0_10_title&waput=1&cltj=normal_title&asres=1&nt=wnor&title=%E8%A5%BF%E5%AE%81%E7%BE%8E%E9%A3%9F_%E7%94%9F%E6%B4%BB_%E5%9B%A2%E8%B4%AD_%E6%97%85%E6%B8%B8_%E7%94%B5%E5%BD%B1_%E4%BC%98%E6%83%A0%E5%88%B8-%E5%A4%A7%E4%BC%97%E7%82%B9%E8%AF%84%E7%BD%91&dict=-1&wd=&eqid=7ad2ea1d2cb20800100000005d808ab7&w_qd=IlPT2AEptyoA_ykyvhcp-AS&bdver=2&tcplug=1&sec=41551&di=cfb7d14f2d88cce7&bdenc=1&tch=124.0.204.567.2.2067&nsrc=KqxSCeW84rCi4XtcoIOZPg3dG9zHHREXgYRLqNCM%2FcQbSNxyQWqXWFbncD%2BuXjak9uCQ2loygLVNcMiATWrS1w%3D%3D&clk_info=%7B%22srcid%22%3A205%2C%22tplname%22%3A%22www_normal%22%2C%22t%22%3A1568705216457%2C%22xpath%22%3A%22div-article-header-div-a-h3-span%22%7D'):
        self.refer = self.get_refer()

    @classmethod
    def send_email(cls, title, content, receivers):
        """ qq 邮箱发送"""
        mail_host = 'smtp.qq.com' #设置服务器
        mail_user = dzaccount.qqhost # qq 号码
        mail_pass = 'eiikjnnlbcsgcida' # qq 邮箱为授权码
        sender = dzaccount.qqhost + '@qq.com' # 邮件发送方邮箱地址
        receivers = receivers # 邮件接受方邮箱地址，可写多个邮件地址群发

        #设置email信息
        message = MIMEText(content,'plain','utf-8') # 'content' 邮件内容
        message['Subject'] = title # 邮件标题
        message['From'] = sender # 发送方信息
        message['To'] = receivers[0] # 接受方信息

        #登录并发送邮件
        try:
            smtpObj = smtplib.SMTP_SSL(mail_host) # 连接服务器
            smtpObj.login(mail_user,mail_pass) # 登录到服务器
            smtpObj.sendmail(sender,receivers,message.as_string()) # 发送邮件
            smtpObj.quit() # 退出
            return (cls.get_time(), 'email success')
        except smtplib.SMTPException as e:
            return (cls.get_time(),'email error 邮件发送失败',e) #打印错误

    @classmethod
    def get_time(cls)-> str:
        """获得字符串格式时间表示"""
        timestamp = int(time.time())
        time_local = time.localtime(timestamp) # 时间戳 转 时间数组
        dt = time.strftime("%Y-%m-%d %H:%M:%S",time_local) # 时间数组 转 新的时间格式(2016-05-05 20:28:54)
        return dt

    @classmethod
    def get_refer(cls):
        """获取 refer"""
        with open('refer.txt', 'r', encoding='utf8') as f:
            res = f.readlines()
        refer = random.choice(res).replace('\n','')
        return refer

    @classmethod
    def get_ua(cls):
        """获取 ua"""
        with open('useragent.txt', 'r', encoding='utf8') as f:
            res = f.readlines()
        ua = random.choice(res).replace('\n','')
        return ua

    def to_csv(self, n):
        edf = pd.DataFrame(n)
        edf = edf.T
        edf.to_csv(os.path.abspath('.') + r'/dz_rank.csv', mode='a', encoding='utf_8_sig', index=False, header=False)

    def get_rank(self, url, proxies, shopname="千禧聖黛"):
        """ 获取店铺排名状态。
        :param url: 大众点评搜索关键词页面的 url.
        :param proxies: 使用的代理. 
        :param shopname: 监测的店铺名.
        :return: 检测店铺排名及前20店铺名。其中检测店铺排名：bug: -1, 1-20: 1-20, >20: 100
        :rtype: touple. 
        """

        User_Agent = self.get_ua()
        refer = self.get_refer()
        LOGGER.info('function: get_rank -> u-a 头部： %s ', User_Agent)
        LOGGER.info('function: get_rank -> refer %s .', refer)
        headers = {
        'Referer': refer,
        'User-Agent': User_Agent,
        }
        try:
            r = requests.get(url, headers=headers, proxies=proxies, timeout=30)
            r.encoding = 'utf8'
        except requests.exceptions.RequestException as e:
            return (-1, e)
        res = BeautifulSoup(r.text, features="lxml")
        if res.find_all(class_="list-search"): # 是否正常
            res2 = res.find_all(class_="list-search")[0].find_all(class_="item-shop-name")
        else:
            if r.text.find('验证') != -1:
                return ('验证码', str(res) + '\n验证码')
            elif r.status_code == 403:
                return (403, str(res) + '\n403')
            else:
                return (-1, str(res) + '\n其他情况')
        shops = [ es.text for i,es in enumerate(res2)] # 第一页店铺（20）排名情况
        for i,es in enumerate(res2):
            if shopname in str(es):
                return (i+1, shops)
        return (100, shops)

    def get_rank_by_render(self, url, proxies, shopname="千禧聖黛"):
        """ 获取店铺排名状态。
        :param url: 大众点评搜索关键词页面的 url.
        :param proxies: 使用的代理. 
        :param shopname: 监测的店铺名.
        :return: 检测店铺排名及前20店铺名。其中检测店铺排名：bug: -1, 1-20: 1-20, >20: 100
        :rtype: touple. 
        """
        
        User_Agent = self.get_ua()
        refer = self.get_refer()
        LOGGER.info('function: get_rank_by_render -> u-a 头部： %s ', User_Agent)
        LOGGER.info('function: get_rank_by_render -> refer %s .', refer)
        url3 = 'http://wap.dianping.com'
        try:
            session = HTMLSession()
            h = {
                'Referer': refer,
                'User-Agent': User_Agent,
            }
            r = session.get(url3, headers=h)
            r.html.render()

            r2 = session.get(url, headers=h)
            page = r2.html.html
        except:
            return ('requests error', '\n请求错误') 

        res = BeautifulSoup(page, features="lxml")
        if res.find_all(class_="list-search"): # 是否正常
            res2 = res.find_all(class_="list-search")[0].find_all(class_="item-shop-name")
        else:
            if r2.text.find('验证') != -1:
                return ('验证码', str(res) + '\n验证码')
            elif r2.status_code == 403:
                return (403, str(res) + '\n403')
            else:
                return (-1, str(res) + '\n其他情况')
        shops = [ es.text for i,es in enumerate(res2)] # 第一页店铺（20）排名情况
        for i,es in enumerate(res2):
            if shopname in str(es):
                return (i+1, shops)
        return (100, shops)
    	
    @classmethod
    def get_ip(cls):
        """"获取代理IP"""
        url = 'http://dps.kdlapi.com/api/getdps/?orderid=976817712394420&num=1&pt=1&dedup=1&format=json&sep=1' # 获取代理IP
        ip = "spiderbeg:pythonbe@106.52.85.210:8000" # 默认IP
        for _ in range(2):
            try:
                r = requests.get(url)
                res = r.json()
                LOGGER.info('function: get_ip -> 请求返回格式：%s .', res)
                if res['code'] == 0:
                    ip = res['data']['proxy_list'][0] # ip
                    left_count = res['data']['order_left_count'] # 剩余次数
                    if left_count <= 20:
                        cls.send_email('当前ip数 %d' %left_count, 'nothing', ['1968473206@qq.com'])
                    LOGGER.info('function: get_ip -> ip: %s , 剩余次数 %s .', ip, left_count)
                    break
            except requests.exceptions.RequestException as e:
                LOGGER.info('get_ip -》 requests error %s .', e)
        proxies = {
            "http": "http://" + dzaccount.ipaccount + ip,
            "https": "http://" + dzaccount.ipaccount + ip,
        }
        return proxies

    @staticmethod
    def work(cityid='16', shopname='薇拉上善',proxies = {}) -> None:
        dz = MonitorDZ()  # 实例化
        # '''执行信息抓取任务, 三个关键词'''
        # 1、城市 2、关键词
        basepath = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(basepath,'dzinfo.txt')
        proxies = {
            "http": "http://spiderbeg:pythonbe@106.52.85.210:8000",
            "https": "http://spiderbeg:pythonbe@106.52.85.210:8000",
        }
        kwz = {'婚纱礼服':quote('婚纱礼服'), "婚纱租赁":quote('婚纱租赁'), '化妆造型':quote('化妆造型')}
        for t,kwu in enumerate(kwz): # 搜索关键
            # if t > 0:
            #    break
            results = []
            for i in range(3): # 五次机会
                url = 'http://m.dianping.com/shoplist/' + cityid +'/search?from=m_search&keyword=' + kwz[kwu]
                if i==2:
                    result = dz.get_rank_by_render(url,proxies,shopname)
                    LOGGER.info('第 %d 次检测 关键词 %s 检测结果：%s 代理 %s\n 详细信息：\n %s.', i+1,kwu,result[0],proxies.get('http','无'), result[1])
    
                    if result[0] not in [-1,403,'验证码','requests error']:
                        with open(path, 'a+', encoding='utf8') as f:
                            f.write('%s 第 %d 次成功 关键词 %s 检测结果为：%s 代理 %s .\n'%(dz.get_time(),i+1,kwu,result[0], proxies.get('http','无')))
                    else:
                        results.append(result[0])
                        with open(path, 'a+', encoding='utf8') as f:
                            f.write('%s 共 %d 次失败 关键词 %s 检测结果为：%s 代理 %s .\n'%(dz.get_time(),i+1,kwu,results, proxies.get('http','无')))
                    break
                result = dz.get_rank(url, proxies, shopname) # 获取排名机会1
                # time.sleep(0.5)
            
                LOGGER.info('第 %d 次检测 关键词 %s 检测结果：%s 代理 %s\n 详细信息：\n %s.', i+1,kwu,result[0],proxies.get('http','无'), result[1])
                if result[0] not in [-1,403,"验证码"]:
                    with open(path, 'a+', encoding='utf8') as f:
                        f.write('%s 第 %d 次成功 关键词 %s 检测结果为：%s 代理 %s .\n'%(dz.get_time(),i+1,kwu,result[0], proxies.get('http','无')))
                    break
                elif i==0:
                    proxies = dz.get_ip() # 获取代理 IP
                    pass
                    
                results.append(result[0])
            
                                        


if __name__ == '__main__':
    LOGGER.info('\n------------------------------\n')
    MonitorDZ.work()

    # test 测试
    # dz = MonitorDZ()  # 实例化
    # url2='http://m.dianping.com/shoplist/6/search?from=m_search&keyword=%E5%A9%9A%E7%BA%B1%E7%A4%BC%E6%9C%8D'
    # a = dz.get_rank(url2,{})
    # print(a)
