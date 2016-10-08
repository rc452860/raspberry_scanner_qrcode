#!/usr/bin/python
# -*- coding:utf-8 -*-
import os
import json
import time

import requests
import zbar, Image, cv2, cv, numpy as np, picamera, picamera.array
import datetime
import argparse
import io, uuid
import RPi.GPIO as GPIO
import logging, logging.config
from logging.handlers import TimedRotatingFileHandler
import re
import threading
import commands

from crypt import decrypt_token, encrypt_token
from gpio import bibi,reset
from network import post,put,get
from journal import journal_data,journal_log


class Scanner(object):
    __instance = None  # 单例模式实例
    __container = []  # 容器
    __lastData = None  # 上次提交数据
    __lastDate = time.time()  # 上次提交时间
    __mac = ""  # mac地址
    __mutex_temp = threading.Lock()  # 温度锁
    __mutex_sub = threading.Lock()  # 上传锁
    __hibernate = False
    __bind_file = 'bind.txt'

    def __init__(self):
        self._temperature = .0;

    def __new__(cls, *args, **kwargs):
        if Scanner.__instance is None:
            Scanner.__instance = object.__new__(cls, *args, **kwargs)
        return Scanner.__instance

    def measure_temp(self):
        """
        监测机器温度状况并写进temp.txt
        :return:
        """

        pattern = re.compile(r"(\d+?\S\d+?)(?=')", re.M | re.I)
        tempfile = open("temp.txt", "a+")
        while 1:
            try:
                with self.__mutex_temp:
                    temp = commands.getoutput("vcgencmd measure_temp")
                    temp = pattern.search(temp).group(1)
                    self._temperature = float(temp)
                    journal_log.info("当前记录的温度 %s" % self._temperature)
                    tempfile.write(temp + ";")
                    tempfile.flush()
                    time.sleep(5 * 60)
            except Exception, e:
                tempfile.flush()
                tempfile.close()
                journal_log.debug(e.message)
        tempfile.flush()
        tempfile.close()

    def get_mac_address(self, name="eth0"):
        """
        获得mac地址
        :param name:网卡名称
        :return: mac地址
        """

        # if self.__mac == "":
        #     self.__mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
        #     self.__mac = ":".join([self.__mac[e:e + 2] for e in range(0, 11, 2)])
        # return self.__mac

        # 使用新的方式获取mac地址避免多张网卡时mac切换
        if self.__mac == "":
            mac = os.popen("/sbin/ifconfig | grep '" + name + "'|awk '{print $5}'").read().replace("\n", '')
            journal_log.debug("MAC地址:"+mac)
            self.__mac = mac
        return self.__mac

    def decode(self, data):
        """
        解析Data并保存在容器中等待上传
        :param data:二维码数据
        :return:
        """

        if data != self.__lastData:
            self.__lastData = data
            try:
                # datab = decrypt_token(data)  # "ChXNQf9B819H/YlVUiI7LIJohyBdlYJ2+qaf+/b7pN8="
                # print datab
                # token = datab[-13:]     #因为utc目前是13位长度所以暂时用13位,可能出现千年虫问题
                # self.__container.append(encrypt_token(datab + self.__mac + token))  # 用户+mac+时间
                # with self._mutex_sub:  # 加锁防止冲突
                #     self.__lastDate = int(time.time() * 1000)
                #     self._hibernate = False  # 唤醒睡眠状态
                arg = decrypt_token(data).split('&')
                print arg
                # 参数正确且已经绑定路线才能正常扫码
                if len(arg) == 3 and arg[0] == 'A' and time.time() - int(arg[2]) < 120 and self.check_bind():
                    self.clock(arg[1], arg[2])
                    # journal_log.debug("扫码:"+arg[1])
                if len(arg) == 2 and arg[0] == 'B':
                    self.bind_line(arg[1])
                    # journal_log.debug("绑定线路:" + arg[1])

            except Exception, e:
                journal_log.debug("解码错误:"+e.message)

    def hibernate(self):
        """监测睡眠状态"""
        self.__hibernate = (time.time() - self.__lastDate) > 60

    def submit(self):
        """
           提交数据
           当前30秒内有用户刷卡则不提交数据
           否则:
           上传数据
           异常:
           把数据添丢回容器等待下一次提交
        """
        while 1:
            if self.__hibernate and len(self.__container) > 0:
                temparr = None;
                try:
                    with self.__mutex_sub:  # 切片发送
                        temparr = self.__container
                        self.__container = []
                    journal_log.debug("准备发送数据")

                    result = post("/ticket/buy",
                                            json={
                                                "device": self.get_mac_address(),
                                                "ticket_buy_items": [{"user_check": x} for x in temparr]
                                                }
                                            )
                    if result.status_code >= 400:
                        with self.__mutex_sub:  # 回滚数据
                            self.__container.extend(temparr)
                        journal_log.debug( "HTTP请求错误 状态码:%s" % result.status_code)
                    else:
                        journal_log.debug( result.text)
                except requests.exceptions.ConnectionError, e:
                    with self.__mutex_sub:  # 回滚数据
                        self.__container.extend(temparr)
                    journal_log.debug(e.message)
                except Exception, e:
                    with self.__mutex_sub:  # 回滚数据
                        self.__container.extend(temparr)
                    journal_log.debug(e.message)
            time.sleep(30)

    # 主循环
    def loop(self, camera, scanner):
        """
        扫描循环
        :param camera: picamera.PiCamera
        :param scanner: zbar.ImageScanner
        :return:
        """

        bibi(duration=0.2, num=3, sleep=0.05)
        with io.BytesIO() as stream:
            for frame in camera.capture_continuous(stream, format='jpeg', resize=(400, 400), use_video_port=True):
                data = np.fromstring(frame.getvalue(), dtype=np.uint8)
                d1 = datetime.datetime.now()
                cv2_im = cv2.imdecode(data, 1)
                gray = cv2.cvtColor(cv2_im, cv2.COLOR_BGR2GRAY)
                pil_im = Image.fromarray(gray)
                width, height = pil_im.size
                raw = pil_im.tostring()
                image = zbar.Image(width, height, 'Y800', raw)
                scanner.scan(image)
                # print len(image.symbols) #是否扫描到二维码
                for symbol in image:
                    self.decode(symbol.data)
                    # print 'decoded', symbol.type, 'symbol', '"%s"' % symbol.data      #
                del (image)
                d = datetime.datetime.now() - d1
                # print "consuming %dms" % ((d.microseconds / 1000))    #
                stream.seek(0)
                stream.truncate(0)
                self.hibernate()
                if self.__hibernate:
                    time.sleep(1)

    def initNetwork(self):
        """
        测试连接服务器,如果服务器连接不上说明网络不可用或服务器宕机。
        反正两种情况都是没办法上传数据的
        :return:
        """
        try:
            result = get("")
            return True
        except Exception, e:
            journal_log.debug(e.message)
            return False

    def initThread(self):
        """
        初始化线程:
            异步提交数据
            异步监视温度(温度写在当前目录的temp.txt文件下)
        :return:
        """
        submit = threading.Thread(target=self.submit, name="submit")
        submit.setDaemon(True)  # 设置主进程结束关闭
        submit.start()  # 线程开始运转
        temperature = threading.Thread(target=self.measure_temp, name="temperature")
        temperature.setDaemon(True)  # 当主线程停止的时候杀掉子线程
        temperature.start()

    def init_camera(self):
        """
        初始化摄像头并启动主循环
        :return:
        """
        while not self.initNetwork():
            time.sleep(1)
        while 1:
            try:
                start = time.time()
                camera = picamera.PiCamera()
                journal_log.debug("start")
                self.initThread()
                # create a reader
                scanner = zbar.ImageScanner()
                # configure the reader
                scanner.parse_config('enable')
                journal_log.debug(start - time.time())
                self.loop(camera, scanner)
            except Exception, e:
                journal_log.debug(e.message)
            finally:
                camera.close()

    def check_bind(self):
        """
        检查是否绑定路线
        :return:
        """
        return os.path.exists(self.__bind_file)

    def bind_line(self, plate_number):
        """
        绑定路线
        :param plate_number: 车牌号
        :return:
        """
        result = put("/bus/bind", json={
            'name': plate_number,
            'device': self.get_mac_address()
        })
        journal_log.debug(result.status_code)
        journal_log.debug(result.text)
        if result.text.find('success'):
            with open(self.__bind_file, 'w+') as bind_info:
                bind_info.write(plate_number)
                bibi(num=2)

    def clock(self, user_name, clock_time):
        """
        打卡上车
        :param user_name: 用户名
        :param clock_time: 打卡时间
        :return:
        """
        data = "{0}&{1}".format(user_name, clock_time)
        self.__container.append(encrypt_token(data))

        with self.__mutex_sub:  # 加锁防止冲突
            self.__lastDate = time.time()
            self.__hibernate = False  # 唤醒睡眠状态
        bibi()


if __name__ == "__main__":
    Scanner().init_camera()
    # bibi()
    # Scanner().test()
