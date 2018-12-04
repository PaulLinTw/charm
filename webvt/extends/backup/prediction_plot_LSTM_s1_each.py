# -*- coding: utf-8 -*-
"""
Created on Tue Apr  3 11:05:12 2018

@author: jimmybow
"""

from mydf import *
from sklearn.feature_extraction import DictVectorizer
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
import sys
from extends.usecase_incl import incl
import torch
import torch.nn as nn
from torch.autograd import Variable
import torch.utils.data as Data
import pickle
import redis

GMT = pytz.timezone('GMT')
init_time = datetime(2018,3,27,8,0,0, tzinfo = GMT)

class lstm_reg_seq_to_one(nn.Module):
    def __init__(self, input_size=66, hidden_size=30, output_size=1, num_layers=2):
        super(lstm_reg_seq_to_one, self).__init__()
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)  
        self.reg = nn.Linear(hidden_size, output_size) 
        
    def forward(self, x):
        x, (h_n, c_n) = self.lstm(x) 
        # LSTM 輸入資料的格式 (sample size, seq_len, input_size) = (mini_batch, 10, 66)
        # LSTM 輸出的格式 (sample size, seq_len, hidden_size * num_directions) = (mini_batch, 10, 30)
        x = x[:, -1, :]    # 取出序列的最後一個時間步的值   (mini_batch, 30)
        x = self.reg(x)  # (mini_batch, 1)
        return x

def load_model(): 
    rds = redis.Redis(host=incl.redis_servers, password=incl.redis_pass, port=incl.redis_port)
    vec = pickle.loads(rds.get('prediction_vec_LSTM_s1'))
    net = lstm_reg_seq_to_one(len(vec.get_feature_names()))
    para = pickle.loads(rds.get('prediction_LSTM_s1'))
    net.load_state_dict(para)  
    return net

def time_to_str(t): 
    s = datetime.strftime(init_time + timedelta(minutes = t), '%Y-%m-%d day %H hour %M minute')
    return(s.replace('day', '日').replace('hour', '點').replace('minute', '分'))
    
def read_data(product='a-tv', country='China', site = 'Beijing', action='sell'):
    rds = redis.Redis(host=incl.redis_servers, password=incl.redis_pass, port=incl.redis_port)
    now = int((datetime.now(GMT)-init_time).total_seconds()/60)
    
    client = MongoClient(incl.mongo_connector)
    db = client.demo
    coll = db.minutes
    
    data_range = 25
    time_range = [init_time + timedelta(minutes = now-1 - data_range + 1),
                  init_time + timedelta(minutes = now-1 )  ]
    
    query = coll.find({'minute': {'$gte': now - 1  - data_range + 1,
                                  '$lte': now - 1   },
                       'product':product,
                       'country':country,
                       'site':site,
                       'action':action})
    
    df = pd.DataFrame([i for i in query])
    df >>= drop('_id')
    df_mean = pickle.loads(rds.get('df_mean')) >> mask(X['product']==product,X['country']==country,X['site']==site,X['action']==action)
    df = pd.concat([df_mean  >> left_join(df[df.minute==i]) >> mutate(minute=i) for i in range(now-1 - data_range + 1, now)]).reset_index(drop = True)
    ww = df['count'].isnull()
    df['count'][ww] = df['mean'][ww]
    df >>= drop('mean')
    
    time_step = 10
    
    df >>= (rename(action_type = 'action', counts = 'count')
     >> arrange('minute') 
     >> group_by('country', 'product', 'site', 'action_type') 
     >> mutate(**{'counts_t-%02.f'%i : X.counts.shift(i) for i in range(1,time_step+1)})
     >> r(X.dropna().reset_index(drop=True))
    )
    return df

def Forcast(df, model, k=10):
    rds = redis.Redis(host=incl.redis_servers, password=incl.redis_pass, port=incl.redis_port)
    vec = pickle.loads(rds.get('prediction_vec_LSTM_s1'))
    t_name = 'minute'
    time_step = 10
    
    df_feature = df >> select('site', 'product', 'country', 'action_type', 'counts_t-01')
    data_feature = vec.transform(df_feature.to_dict('records'))
    counts_index = int(where(pd.Series(vec.get_feature_names()) == 'counts_t-01'))
    
    df_x = df.iloc[:,6:] 
    df_x = df_x[df_x.columns.sort_values(ascending=False)]
    data_x = df_x.as_matrix().reshape(df_x.shape[0], df_x.shape[1], 1)
    
    data_feature = data_feature.reshape(data_feature.shape[0], 1, data_feature.shape[1])
    data_feature = np.concatenate([data_feature for i in range(10)],axis = 1)
    data_feature[:,:,counts_index] = data_x[:,:,0] 
    
    pre_value = []
    t_value = []
    current_feature = pd.Series(data_feature[-1,:,counts_index]).shift(-1).fillna(df.counts.iloc[-1])
    for i in range(k):
        data_input = data_feature[[-1],:,:].copy()
        data_input[-1,:,counts_index] = current_feature
        p = model(Variable(torch.FloatTensor(data_input))).data.numpy()[0,0]
        pre_value.append(p)
        t_value.append( df[t_name].astype(int).iloc[-1] + i+1 )
        current_feature = current_feature.shift(-1).fillna(p)
        current_feature.fillna(p)
        
    df_true = df.iloc[:,:6]
    df_pre = df_true >> mutate(counts = model(Variable(torch.FloatTensor(data_feature))).data.numpy()[:,0]) 
    df_fu_pre = pd.DataFrame({t_name:t_value,
                         'action_type': df.action_type.iloc[0],
                         'site' : df.site.iloc[0],
                         'product' : df['product'].iloc[0],
                         'country' : df.country.iloc[0],
                         'counts' : pre_value})
    
    from sklearn.metrics import mean_squared_error
    from math import sqrt
    return {'df_true': df_true, 
            'df_pre':df_pre >> bind_rows(df_fu_pre),
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

def draw2Dplotly(dict_pre, output_type = 'file'):
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

def Forcast_and_Plot(model, product='a-tv', country='China', site = 'Beijing', action = 'sell'):
    df = read_data(country=country, site = site, product= product, action=action)
    dict_pre = Forcast(df, model)
    return {'div':draw2Dplotly(dict_pre, output_type = 'div'),
            'RMSE_15':dict_pre['RMSE_15']}

# df = read_data(product='a-tv', country='China', site = 'Beijing', action = 'sell')
# dict_pre = Forcast(df, load_model())
# div = draw2Dplotly(dict_pre)
# g=Forcast_and_Plot(model=load_model())

