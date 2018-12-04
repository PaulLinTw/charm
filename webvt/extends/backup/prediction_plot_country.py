# -*- coding: utf-8 -*-
"""
Created on Tue Apr  3 11:05:12 2018

@author: jimmybow
"""

from mydf import *
from sklearn import datasets, metrics
from sklearn.feature_extraction import DictVectorizer
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
import sys
from .usecase_incl import incl
import pickle
import redis
from sklearn.externals import joblib

GMT = pytz.timezone('GMT')
init_time = datetime(2018,3,27,8,0,0, tzinfo = GMT)

def load_model(): 
    return joblib.load('/models/Tree_country')

def time_to_str(t): 
    s = datetime.strftime(init_time + timedelta(minutes = t), '%Y-%m-%d day %H hour %M minute')
    return(s.replace('day', '日').replace('hour', '點').replace('minute', '分'))
    
def read_data_country(product='a-tv', country='China', action = 'sell'):
    rds = redis.Redis(host=incl.redis_servers, password=incl.redis_pass, port=incl.redis_port)
    now = int((datetime.now(GMT)-init_time).total_seconds()/60)
    
    client = MongoClient(incl.mongo_connector)
    db = client.demo
    coll = db.minutes
    
    data_range = 20
    time_range = [init_time + timedelta(minutes = now-1 - data_range + 1),
                  init_time + timedelta(minutes = now-1 )  ]
    
    query = coll.find({'minute': {'$gte': now - 1  - data_range + 1,
                                  '$lte': now - 1   },
                       'product':product,
                       'country':country,
                       'action':action})
    
    df = pd.DataFrame([i for i in query])
    df >>= drop('_id')
    df_mean = pickle.loads(rds.get('df_mean')) >> mask(X['product']==product,X['country']==country,X['action']==action)
    df = pd.concat([df_mean  >> left_join(df[df.minute==i]) >> mutate(minute=i) for i in range(now-1 - data_range + 1, now)]).reset_index(drop = True)
    ww = df['count'].isnull()
    df['count'][ww] = df['mean'][ww]
    df >>= drop('mean')

    df >>= (rename(action_type = 'action', counts = 'count') 
     >> group_by('country', 'product', 'action_type', 'minute') 
     >> summarize(counts = X.counts.sum())
     >> group_by('country', 'product', 'action_type')
     >> select('minute', 'action_type', 'country', 'product', 'counts')
     >> mutate(
            **{'counts_t-1': X.counts.shift(1),
               'counts_t-2': X.counts.shift(2),
               'counts_t-3': X.counts.shift(3),
               'counts_t-4': X.counts.shift(4),
               'counts_t-5': X.counts.shift(5)} )
     >> ungroup() >> r(X.dropna().reset_index(drop=True))
    )
    return df

def Forcast_country(df, model, k=10):
    rds = redis.Redis(host=incl.redis_servers, password=incl.redis_pass, port=incl.redis_port)
    vec = pickle.loads(rds.get('prediction_vec_country'))
    t_name = 'minute'
    Tree = model
    
    ddf = df >> arrange(t_name) 
    pre_value = []
    t_value = []
    current_feature = ddf >> tail(1) >> r(X.iloc[0,4:])
    for i in range(k):
        current_feature = current_feature.shift(1)
        data = current_feature.iloc[1:].to_dict()
        data.update(df >> tail(1) >> select('action_type', 'country', 'product') >> r(X.iloc[0].to_dict()))
        p = Tree.predict(vec.transform(data))[0]
        pre_value.append(p)
        t_value.append(df >> tail(1) >> r(X[t_name].astype(int).iloc[0] + i+1 ))
        current_feature.iloc[0] = p
    df_true = ddf.iloc[:,:5]    
    df_pre = df_true >> mutate(counts = Tree.predict(vec.transform(ddf.to_dict('record')))) 
    df_fu_pre = pd.DataFrame({t_name:t_value,
                         'action_type': ddf.action_type.iloc[0],
                         'product' : ddf['product'].iloc[0],
                         'country' : ddf.country.iloc[0],
                         'counts' : pre_value})
    from sklearn.metrics import mean_squared_error
    from math import sqrt
    return {'df_true': df_true, 
            'df_pre':df_pre>> bind_rows(df_fu_pre),
            'RMSE_15':sqrt(mean_squared_error(df_true.counts, df_pre.counts))}

### plotly 畫圖 ###
from plotly.offline import plot
import plotly.graph_objs as go

to_chinese = {
    'forum':'論壇拜訪量',
    'news': '新聞拜訪量',
    'store':'商店拜訪量',
    'support': '客服拜訪量',
    'complaint': '客訴量',
    'return':'退貨量',
    'sell':  '銷售量'}    

def draw2Dplotly_country(dict_pre, output_type = 'file'):
    t_name = 'minute'
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
    
    current_t = dict_pre['df_true'][t_name].max()
    ww = where(dict_pre['df_true'][t_name]==current_t)[0]
    
    trace = go.Scatter(
        name = '實際值',    
        x = dict_pre['df_true'][t_name],
        y = dict_pre['df_true'].counts,
        mode = 'lines+markers',
        hoverinfo = 'text',
        text = dict_pre['df_true'][t_name].apply(time_to_str) + '<br>實際值: ' + dict_pre['df_true'].counts.astype(int).astype(str),
        line = dict(color = 'rgb(0, 0, 255)')
    )
    
    trace_pre = go.Scatter(
        name = '未來預測值',    
        x = dict_pre['df_pre'][t_name][ww+1:],
        y = dict_pre['df_pre'].counts[ww+1:],
        mode = 'lines+markers',
        hoverinfo = 'text',
        text = dict_pre['df_pre'][t_name][ww+1:].apply(time_to_str) + '<br>未來預測值: ' + dict_pre['df_pre'].counts[ww+1:].astype(str),
        line = dict(color = 'rgb(255, 0, 0)',
                    dash = 'dot')
    )
        
    trace_b = go.Scatter(
        name = '歷史預測值',    
        x = dict_pre['df_pre'][t_name][:ww+1],
        y = dict_pre['df_pre'].counts[:ww+1],
        mode = 'lines+markers',
        hoverinfo = 'text',
        text = dict_pre['df_pre'][t_name][:ww+1].apply(time_to_str) + '<br>歷史預測值: ' + dict_pre['df_pre'].counts[:ww+1].astype(str),
        line = dict(color = 'rgb(0, 255, 0)',
                    dash = 'dot')
    )    
        
    trace_con = go.Scatter(   
        x = dict_pre['df_pre'][t_name].iloc[ww:ww+2],
        y = dict_pre['df_pre'].counts.iloc[ww:ww+2],
        mode = 'lines',
        line = dict(color = 'rgb(255, 0, 0)',
                    dash = 'dot')
    )     
    
    layout= go.Layout(
#        title= '{}-{} 的 {} 之{}預測'.format(df_pre.country.iloc[0],
#                                                        df_pre.site.iloc[0],
#                                                        df_pre['product'].iloc[0],
#                                                        to_chinese[df_pre.action_type.iloc[0]]),
#        titlefont=dict(
#            size=30
#        ),
        dragmode = 'pan',
        hovermode= 'closest',
        showlegend=False,
        xaxis= dict(
            title= '時間 ({})'.format(t_name),
            titlefont=dict(
                size=18
            ),
            tickvals = dict_pre['df_pre'][t_name],
            ticktext = dict_pre['df_pre'][t_name].apply(lambda t: datetime.strftime(init_time + timedelta(minutes = t), '%H:%M'))
            
        ),
        yaxis=dict(
            title= to_chinese[dict_pre['df_pre'].action_type.iloc[0]],
            titlefont=dict(
                size=18
            )
        ),
        margin=dict(l=60,r=30,t=30,b=60)    
    )
    
    fig= {'data':[trace_con, trace_b, trace_pre, trace], 'layout':layout}
    div = plot(fig, output_type = output_type, config=conf)
    return(div)

def Forcast_and_Plot_Country(model, country = 'China', product='a-tv', action = 'sell'):
    df = read_data_country(country=country, product= product, action= action)
    dict_pre = Forcast_country(df, model = model)
    return {'div':draw2Dplotly_country(dict_pre, output_type = 'div'),
            'RMSE_15':dict_pre['RMSE_15']}

# df = read_data_country(product='a-tv', country='China', action = 'sell')
# df_pre = Forcast_country(df, load_model())
# div = draw2Dplotly_country(df_pre)
# g=Forcast_and_Plot_Country(model = load_model())
# print(g, file = open('abc.txt', 'w'))

