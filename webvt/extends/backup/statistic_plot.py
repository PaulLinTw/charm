# -*- coding: utf-8 -*-
"""
Created on Tue Apr 17 16:29:36 2018

@author: jimmybow
"""

from mydf import *
import redis
from extends.usecase_incl import incl
import sys
from plotly.offline import plot
import plotly.graph_objs as go
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
import pickle

action = {'news':'新聞網頁訪問',
          'store':'商店網頁訪問',
          'support':'客服網頁訪問',
          'forum':'論壇網頁訪問',
          'sell':'銷售記錄',
          'complaint':'客訴記錄',
          'return':'退貨記錄'}

def get_country_plotly(country, product, act, data_range, output_type = 'div'):
    rds = redis.Redis(host=incl.redis_servers, password=incl.redis_pass, port=incl.redis_port)
    GMT = pytz.timezone('GMT')
    init_time = datetime(2018,3,27,8,0,0, tzinfo = GMT)
    now = int((datetime.now(GMT)-init_time).total_seconds()/60)
    
    client = MongoClient(incl.mongo_connector)
    db = client.demo
    coll = db.minutes
    time_range = [init_time + timedelta(minutes = now-1 - data_range + 1),
                  init_time + timedelta(minutes = now-1 )  ]
    query = coll.find({'minute': {'$gte': now - 1  - data_range + 1,
                                         '$lte': now - 1   },
                       'country':country,
                       'action':act,
                       'product':product})
    
    df = pd.DataFrame([i for i in query])
    df >>= drop('_id')
    df_mean = pickle.loads(rds.get('df_mean')) >> mask(X.country==country, X.action == act, X['product']==product)
    df = pd.concat([df_mean  >> left_join(df[df.minute==i]) >> mutate(minute=i) for i in range(now-1 - data_range + 1, now)]).reset_index(drop = True)
    ww = df['count'].isnull()
    df['count'][ww] = df['mean'][ww]
    df >>= drop('mean')

    df = (df 
     >> rename(action_type = 'action', counts = 'count')
     >> group_by('site') 
     >> summarize(counts = X.counts.sum())
    ) 
    
    ss = df.counts.astype(int)
    ss.index = df.site
    action = {'news':'新聞網頁訪問',
              'store':'商店網頁訪問',
              'support':'客服網頁訪問',
              'forum':'論壇網頁訪問',
              'sell':'銷售記錄',
              'complaint':'客訴記錄',
              'return':'退貨記錄'}
    
    title_1 = "產品 "+product+" 的「" + action[act] + "」統計數據"
    
    ### plotly 畫圖 ###
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
    dots=[]
    for i in ss.sort_values(ascending = False).index:
            trace = go.Bar(
                    name = i,
                    x = [i],
                    y = [ss[i]],
                    hoverinfo = 'text',
                    text = i + '：' + str(ss[i])
            )
            dots.append(trace)
    
    layout= go.Layout(
            showlegend=False,
            dragmode = 'pan',
            hovermode= 'closest',
            xaxis= dict(
                title= '據點', 
                titlefont=dict(
                    size=18
                )
            ),
            yaxis=dict(
                title= action[act]+'',
                titlefont=dict(
                    size=18
                )
            ),
            margin=dict(l=60,r=30,t=30,b=60)
    )
    
    fig= {'data':dots,'layout':layout}
    bar_div = plot(fig, output_type = output_type, config=conf)
    
    trace = go.Pie( 
        labels = list(ss.index),
        values = list(ss),
        hole = .4
    )
    
    layout= go.Layout(
        showlegend=False,
        margin=dict(l=0,r=0),
        annotations=[{
                "font": {
                    "size": 20
                },
                "showarrow": False,
                "text": "地區",
                "x": 0.5,
                "y": 0.5
            }]
    )
    
    fig= {'data':[trace], 'layout': layout}
    pie_div = plot(fig, output_type = output_type, config=conf)
    return({'title':title_1,
            'bar':bar_div,
            'pie':pie_div,
            'time_range':'data from [{}] to [{}]'.format(time_range[0], time_range[1])})

def cross_plotly(cross_A, cross_B, data_range, output_type = 'div'):
    rds = redis.Redis(host=incl.redis_servers, password=incl.redis_pass, port=incl.redis_port)
    GMT = pytz.timezone('GMT')
    init_time = datetime(2018,3,27,8,0,0, tzinfo = GMT)
    now = int((datetime.now(GMT)-init_time).total_seconds()/60)
    
    client = MongoClient(incl.mongo_connector)
    db = client.demo
    coll = db.minutes
    time_range = [init_time + timedelta(minutes = now-1 - data_range + 1),
                  init_time + timedelta(minutes = now-1 )  ]
    match = {'minute': {'$gte': now - 1  - data_range + 1,
                        '$lte': now - 1   }}
    group = {'_id': {key: ('$%s' % key) for key in [cross_A, cross_B]},
	          'count': {'$sum': 1}}
    query = coll.aggregate(	[
    		{'$match': match},
    		{'$group': group}
    ])
    df = pd.DataFrame([i for i in query])
    df = pd.DataFrame(list(df._id)) >>  bind_cols(df >> select('count'))
    
    df_cross_AB = (df 
     >> rename(counts = 'count')
     >> group_by(cross_A, cross_B) 
     >> summarize(counts = X.counts.sum())
    ) 
    
    df_cross_A = (df_cross_AB
     >> group_by(cross_A) 
     >> summarize(counts = X.counts.sum())
    ) 
    
    action = {'news':'新聞網頁訪問',
              'store':'商店網頁訪問',
              'support':'客服網頁訪問',
              'forum':'論壇網頁訪問',
              'sell':'銷售記錄',
              'complaint':'客訴記錄',
              'return':'退貨記錄'}
    
    ### plotly 畫圖 ###
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
    dots=[]
    for i in df_cross_AB[cross_B].unique():
        ww = df_cross_AB[cross_B] == i
        trace = go.Bar(
                name = i,
                x = list(df_cross_AB[cross_A][ww]),
                y = list(df_cross_AB['counts'][ww].astype(int)),
                hoverinfo = 'text',
                text = list(i + '：' + df_cross_AB['counts'][ww].astype(int).astype(str))
        )
        dots.append(trace)
    
    layout= go.Layout(
            showlegend=True,
            hovermode= 'closest',
            dragmode = 'pan',
            xaxis= dict(
                title= cross_A,
                titlefont=dict(
                    size=18
                )
            ),
            yaxis=dict(
                title= '次數',
                titlefont=dict(
                    size=18
                )
            ),
            barmode='group',
            margin=dict(l=60,r=30,t=30,b=60)
    )
    
    fig= {'data':dots,'layout':layout}
    bar_div = plot(fig, output_type = output_type, config=conf)
    
    ##########################################################################################################
    #########################################################################################################
    ss = df_cross_A.counts.astype(int)
    ss.index = df_cross_A[cross_A]
    
    trace = go.Pie( 
        labels = list(ss.index),
        values = list(ss),
        hole = .4
    )
    
    layout= go.Layout(
        margin=dict(l=0,r=0),
        annotations=[{
                "font": {
                    "size": 20
                },
                "showarrow": False,
                "text": cross_A,
                "x": 0.5,
                "y": 0.5
            }]
    )
    
    fig= {'data':[trace], 'layout': layout}
    pie_div = plot(fig, output_type = output_type, config=conf)
    return({'bar':bar_div,
            'pie':pie_div,
            'time_range':'data from [{}] to [{}]'.format(time_range[0], time_range[1])})

def world_map_plot(product, action, data_range, output_type = 'div'):
    conf = dict(scrollZoom = True,
		           displaylogo= False,
		           showLink = False,
		           displayModeBar = False)
    
    rds = redis.Redis(host=incl.redis_servers, password=incl.redis_pass, port=incl.redis_port)
    GMT = pytz.timezone('GMT')
    init_time = datetime(2018,3,27,8,0,0, tzinfo = GMT)
    now = int((datetime.now(GMT)-init_time).total_seconds()/60)
    
    client = MongoClient(incl.mongo_connector)
    db = client.demo
    coll = db.minutes
    time_range = [init_time + timedelta(minutes = now-1 - data_range + 1),
                  init_time + timedelta(minutes = now-1 )  ]
    match = {'minute': {'$gte': now - 1  - data_range + 1,
                        '$lte': now - 1   },
             'product':product,
             'action':action}
    group = {'_id': {'country': '$country'},
	          'count': {'$sum': 1}}
    query = coll.aggregate(	[
    		{'$match': match},
    		{'$group': group}
    ])
    df = pd.DataFrame([i for i in query])
    df = pd.DataFrame(list(df._id)) >>  bind_cols(df >> select('count'))
    
    data = [dict(type = 'choropleth',
		            locations = [incl.plotlycode[i] for i in df['country']],
		            z = df['count'],
		            colorscale = "YlOrRd",
                 hoverinfo = 'text',
                 text = df['country'] + '：' + df['count'].astype(str),
		            autocolorscale = False,
		            reversescale = True,
		            marker = dict( line = dict (color = 'rgb(180,180,180)', width = 1) ),
		            colorbar = dict(autotick = False,
                                 tickprefix = '',
                                 title = 'Count')      )]
    layout = dict(margin=dict(l=0,r=0,t=0,b=0),
             geo = dict(showframe = True,
                  showocean = True,
                  showland = True,
                  showcountries = True,
                  showcoastlines = True,
                  coastlinecolor = 'rgb(0,0,0)',
                  landcolor = 'rgb(192,192,192)',
                  countrywidth = 1,
                  projection = dict(type = 'Mercator')	)
             )
    
    fig = dict( data=data, layout=layout )
    div = plot(fig, validate = False, output_type = output_type, config=conf)
    return({'worldmap_div':div,
            'time_range':'data from [{}] to [{}]'.format(time_range[0], time_range[1])})
