from configparser import SafeConfigParser
import sys

class incl:

	parser = SafeConfigParser()
	parser.read('tester.conf')

	countrylist = ["China", "India", "USA", "Indonesia", "Japan", "UK", "France", "Germany", "Russia", "Mexico"]
	broker_list= parser.get('kafka', 'brokers')
	redis_servers= parser.get('redis', 'server')
	redis_port= parser.get('redis', 'port')
	redis_pass= parser.get('redis', 'pass')

	mongo_datebase= parser.get('mongodb', 'datebase')
	mongo_connector= parser.get('mongodb', 'connector')
	mongo_bulksize= parser.get('mongodb', 'bulksize')
	mongo_group= parser.get('mongodb', 'storegrp')

	activities_topic= parser.get('activities', 'topic')
	activities_groupid= parser.get('activities', 'groupid')

	records_topic= parser.get('records', 'topic')
	records_groupid= parser.get('records', 'groupid')

	productlist = ["a-pad", "a-watch", "a-phone", "a-tv", "a-bike", "a-camera", "a-bot"]
	plotlycode = {	'China':'CHN',
						'India':'IND',
						'USA': 'USA',
						'Indonesia':'IDN',
						'Japan':'JPN',
						'UK':'GBR',
						'France':'FRA',
						'Germany':'DEU',
						'Russia':'RUS',
						'Mexico':'MEX' }
	countrycode = {	'China':'cn',
						'India':'in',
						'USA': 'us',
						'Indonesia':'id',
						'Japan':'jp',
						'UK':'gb',
						'France':'fr',
						'Germany':'de',
						'Russia':'ru',
						'Mexico':'mx' }
	sitelist ={ 	'China': ['Shanghai', 'Beijing', 'Guangzhou', 'Shenzhen', 'Tianjin'],
					'India': ['Mumbai', 'Delhi', 'Kolkata'],
					'USA': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Philadelphia'],
					'Indonesia': ['Jakarta', 'Bali', 'Semarang'],
					'Japan': ['Tokyo', 'Keihanshin', 'Nagoya', 'Fukuoka'],
					'UK': ['London', 'Birmingham', 'Liverpool', 'Bristol', 'Sheffield'],
					'France': ['Paris', 'Marseille', 'Lyon', 'Toulouse'],
					'Germany': ['Berlin', 'Munich', 'Frankfurt', 'Hamburg'],
					'Russia': ['Moscow', 'St Petersburg', 'Novosibirsk', 'Yekaterinburg'],
					'Mexico': ['Mexico City', 'Iztapalapa', 'Guadalajara', 'Tijuana']
				}
	actionlist = ["sell", "complaint", "return"]
	visitlist = ["news", "store", "support", "forum"]

	batchtotal = int(parser.get('tester', 'batchtotal'))
	interval = int(parser.get('tester', 'interval'))

	chart_width = float(parser.get('chart', 'width'))
	chart_height = float(parser.get('chart', 'height'))

	charts_prediction = str(parser.get('analysis', 'prediction')).replace(" ", "").split(",")
	charts_cluster = str(parser.get('analysis', 'cluster')).replace(" ", "").split(",")
	charts_interval = int(parser.get('analysis', 'interval'))
	charts_datarange = str(parser.get('analysis', 'datarange'))

	mlp_epoch = int(parser.get('MLP', 'epoch'))
	mlp_lr = float(parser.get('MLP', 'lr'))
	mlp_mini_batch = int(parser.get('MLP', 'mini_batch'))
    
	aptimer = {"set1":["create_model", "create_model_LSTM"],
               "set2":["create_model_LSTM_seq_to_one", "create_model_MLP"]}
	aptimer_next_run_time = {"create_model":                "datetime(2018,3,21,0,5)",
                             "create_model_LSTM":           "datetime(2018,3,21,0,15)",
                             "create_model_LSTM_seq_to_one":"datetime(2018,3,21,0,30)",
                             "create_model_MLP":            "datetime(2018,3,21,0,10)"}   
	aptimer_datarange = {"create_model":            60,
                        "create_model_LSTM":       60,
                        "create_model_LSTM_seq_to_one":60,
                        "create_model_MLP":           60}               
	aptimer_interval = {"create_model":            3600,
                         "create_model_LSTM":       3600,
                         "create_model_LSTM_seq_to_one":3600,
                         "create_model_MLP":           3600}                                

