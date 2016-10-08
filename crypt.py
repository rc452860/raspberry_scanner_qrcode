#!/usr/bin/env python
# -*- coding:utf-8 -*-


from Crypto.Cipher import AES
import json, base64


# _pad = lambda s: s + (AES.block_size - len(s) % AES.block_size) * chr(AES.block_size - len(s) % AES.block_size)
# _unpad = lambda s: s[0:-ord(s[-1])]
__instance = None


def _pad(s):
    """
    aes加密填充代码
    :param s:需要填充的数据
    :return:
    """
    return s + (AES.block_size - len(s) % AES.block_size) * chr(AES.block_size - len(s) % AES.block_size)


def _unpad(s):
    return s[0:-ord(s[-1])]


def _cipher():
    key = '0123456789abcdef'
    iv = '0123456789abcdef'
    return AES.new(key=key, mode=AES.MODE_CBC, IV=iv)


def encrypt_token(data):
    """
    AES加密函数
    :param data: 需要加密的数据
    :return:
    """
    return base64.b64encode(_cipher().encrypt(_pad(data)))


def decrypt_token(data):
    """
    AES解密函数
    :param data: 加密后的数据
    :return:
    """
    return _unpad(_cipher().decrypt(base64.b64decode(data)))