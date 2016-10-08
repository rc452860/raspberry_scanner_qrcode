#!/usr/bin/env python
# -*- coding:utf-8 -*-


import RPi.GPIO as GPIO
import time


__instance = None
__pin = 16

# BOARD编号方式，基于插座引脚编号
GPIO.setwarnings(False)
# GPIO.cleanup()
GPIO.setmode(GPIO.BCM)
# 输出模式
GPIO.setup(__pin, GPIO.OUT)


def bibi(duration=0.3, num=1, sleep=0):
    """
    蜂鸣器报警
    :param duration:持续时间
    :param num:次数
    :return:
    """
    if num > 1 and sleep == 0:
        sleep = duration
    for i in range(num):
        GPIO.output(__pin, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(__pin, GPIO.LOW)
        time.sleep(sleep)


def reset(self):
    """
    GPIO口复位避免异常时不停响,估计没啥用
    :return:
    """
    GPIO.output(__pin, GPIO.LOW)

if __name__ == '__main__':
    pass