#!/usr/bin/python
# -*- coding:utf-8 -*-
import requests


__host = "http://service.zfbus.net/"    #"http://192.168.2.162:8080"
__session = requests.Session()
__instance = None


def post( url, data=None, json=None, **kwargs):
    return __session.post(__host + url, data=data, json=json, **kwargs)

def get( url, **kwargs):
    return __session.get(__host + url, **kwargs)

def put( url, data=None, json=None, **kwargs):
    return __session.put(__host + url, data=data, json=json, **kwargs)

