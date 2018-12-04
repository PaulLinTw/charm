# -*- coding: utf-8 -*-
"""
Created on Tue Mar 27 18:00:56 2018

@author: jimmybow
"""
from mydf import *
from pymongo import MongoClient
import pytz
from datetime import datetime, timedelta
from sklearn import cluster, metrics
import sys
from .usecase_incl import incl
import pickle
import redis

rds = redis.Redis(host=incl.redis_servers, password=incl.redis_pass, port=incl.redis_port)
df = pickle.loads(rds.get('df_cluster'))
tags_map = {'k-mean':'tags_k-mean',
            'DBSCAN':'tags_DBSCAN',
            'CURE':'tags_CURE',
            'WaveCluster':'tags_WaveCluster'}

### plotly 畫圖 ###
from plotly.offline import plot
import plotly.graph_objs as go

to_chinese = {
    'visit=forum':'論壇拜訪量',
    'visit=news': '新聞拜訪量',
    'visit=store':'商店拜訪量',
    'visit=support': '客服拜訪量',
    'action=complaint': '客訴量',
    'action=return':'退貨量',
    'action=sell':  '銷售量'}   

conf = dict(scrollZoom = True,
            displaylogo= False,
            showLink = False,
            displayModeBar = False,
            modeBarButtonsToRemove = [
            'sendDataToCloud',
            'zoomIn2d',
            'zoomOut2d',
            'hoverClosestCartesian',
            'hoverCompareCartesian',
            'hoverClosest3d',
            'hoverClosestGeo',
            'resetScale2d']) 
    
def draw2Dplotly(x_name, y_name, algorithm, output_type = 'div'):    
    tags = pickle.loads(rds.get(tags_map[algorithm]))
    data = []
    for i in pd.Series(tags).sort_values().unique():
        ww = tags == i
        ddd = df[ww]
        if ((algorithm == 'DBSCAN') & (i == -1))|((algorithm == 'WaveCluster') & (i == 0)):
            trace = go.Scatter(
                name = '噪音點',    
                x = ddd[x_name],
                y = ddd[y_name],
                mode = 'markers',
                hoverinfo = 'text',
                text = ddd.index + '<br>是噪音點，總共 {} 個'.format(len(ddd)) ,
            )
            data.append(trace)
        else:
            trace = go.Scatter(
                name = '群 {}'.format(i),    
                x = ddd[x_name],
                y = ddd[y_name],
                mode = 'markers',
                hoverinfo = 'text',
                text = ddd.index + '<br>位於第 {} 群<br>群大小: {}'.format(i, len(ddd)),
            )
            data.append(trace)
        
    layout= go.Layout(
			height=720,
#        title= '{} 與 {} 之分布'.format(to_chinese[x_name], to_chinese[y_name]),
#        titlefont=dict(
#            size=30
#        ),
        dragmode = 'pan',
        hovermode= 'closest',
        xaxis= dict(
            title= to_chinese[x_name],
            titlefont=dict(
                size=18
            )
        ),
        yaxis=dict(
            title= to_chinese[y_name],
            titlefont=dict(
                size=18
            )
        )
    )
    
    fig= {'data':data,'layout':layout}
    div = plot(fig, output_type = output_type, config=conf)
    return(div)

def draw3Dplotly(x_name, y_name, z_name, algorithm, output_type = 'div'):      
    tags = pickle.loads(rds.get(tags_map[algorithm]))
    data = []
    for i in pd.Series(tags).sort_values().unique():
        ww = tags == i
        ddd = df[ww]
        xyz_info = ('<br>此產品'
                    '<br>'+ to_chinese[x_name] +': ' + ddd[x_name].astype(str) +
                    '<br>'+ to_chinese[y_name] +': ' + ddd[y_name].astype(str) +
                    '<br>'+ to_chinese[z_name] +': ' + ddd[z_name].astype(str)    )
        if ((algorithm == 'DBSCAN') & (i == -1))|((algorithm == 'WaveCluster') & (i == 0)):
            trace = go.Scatter3d(
                name = '噪音點',    
                x = ddd[x_name],
                y = ddd[y_name],
                z = ddd[z_name],
                mode = 'markers',
                hoverinfo = 'text',
                text = ddd.index + '<br>是噪音點，總共 {} 個'.format(len(ddd)) + xyz_info,
                marker=dict(
                    size = 5,
                    opacity=0.5
                )
            )
            data.append(trace)
        
        else:
            trace = go.Scatter3d(
                name = '群 {}'.format(i),    
                x = ddd[x_name],
                y = ddd[y_name],
                z = ddd[z_name],
                mode = 'markers',
                hoverinfo = 'text',
                text = ddd.index + '<br>位於第 {} 群<br>群的大小: {}'.format(i, len(ddd)) + xyz_info,
                marker=dict(
                    size = 5,
                    opacity=0.5
                )
            )
            data.append(trace)
        
    layout= go.Layout(
			height=720,
#        title= '{} 與 {} 與 {} 之分布'.format(to_chinese[x_name], to_chinese[y_name], to_chinese[z_name]),
#        titlefont=dict(
#            size=30
#        ),
        margin=dict(
            l=0,
            r=0,
            b=0,
            t=50
        ),    
        scene=dict(        
            xaxis=dict(
                title= to_chinese[x_name],
                titlefont=dict(
                    size=18
                ),
                range=[0, df[x_name].max()]
            ),
            yaxis=dict(
                title= to_chinese[y_name],
                titlefont=dict(
                    size=18
                ),
                range=[0, df[y_name].max()]
            ),
            zaxis=dict(
                title= to_chinese[z_name],
                titlefont=dict(
                    size=18
                ),
                range=[0, df[z_name].max()]
            )     
        )
    )
    
    fig= {'data':data,'layout':layout}
    div = plot(fig, output_type = output_type, config=conf)
    return(div)

