# -*- coding: utf-8 -*-
"""
Created on Tue Apr 17 16:29:36 2018

@author: jimmybow
"""

from mydf import *
import redis
from .usecase_incl import incl
import sys
from plotly.offline import plot
import plotly.graph_objs as go
#sys.exit()

action = {'news':'新聞',
          'store':'商店',
          'support':'客服',
          'forum':'論壇',
          'sell':'銷售',
          'complaint':'客訴',
          'return':'退貨'}

def get_country_relation(country, product):
	rds   = redis.Redis(host=incl.redis_servers, password=incl.redis_pass, port=incl.redis_port)
	tr = rds.get("rules_time_range").decode('utf-8')
	rules = rds.get("rules").decode('utf-8').split(',')
	relation=""
	for rule in rules:
		if ((rule.find(country)>=0) and (rule.find(product)>=0)):
#		if (rule.find(country)>=0):
			re = rule.split(' 的 ')[1]
			relation=relation+re+'<br>'
	return({'timerange':tr, 'relation':relation})

def get_relation(key1, key2):
	rds   = redis.Redis(host=incl.redis_servers, password=incl.redis_pass, port=incl.redis_port)
	tr = rds.get("rules_time_range").decode('utf-8')
	rules = rds.get("rules").decode('utf-8').split(',')
	if key1 in action:
		key1 = action[key1]
	if key2 in action:
		key2 = action[key2]
	print("key1:"+key1+", key2:"+key2)
	relation=""
	for rule in rules:
#		if ((rule.find(key1)>=0) and (rule.find(key2)>=0)):
		if (rule.find(key1)>=0):
			relation=relation+rule+'<br>'
	return({ 'timerange':tr, 'relation':relation})
