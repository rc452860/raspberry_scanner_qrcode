#!/usr/bin/env python
# -*- coding:utf-8 -*-

import logging, logging.config
import threading

import time
import yaml
import sys,os

logging.config.dictConfig(yaml.load(open('logging.conf', 'r')))

journal_log = logging.getLogger("journal.log")
journal_data = logging.getLogger("journal.data")


if __name__ == '__main__':
    #print os.path.getsize("journal/log.log")

    for i in range(0,100):
        journal_log.debug(i)
        print sys.getsizeof(i)

    # for i in range(0,100):
    #     journal_data.debug(i)
    #     time.sleep(1)






