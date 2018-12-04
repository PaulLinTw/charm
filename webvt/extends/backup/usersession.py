from usecase_incl import incl
import redis
class uservars:
	global rds

	rds = redis.Redis(host=incl.redis_servers, password=incl.redis_pass, port=incl.redis_port)
	
	def getkey(key):
		x=rds.get(key)
		return str(x)
#.decode('utf-8')

	def setkey(key,value):
		x=rds.set(key,value)
		return str(x)
#.decode('utf-8')

	algorithm = getkey('algorithm')
	product   = getkey('product')
	action    = getkey('action')

	def set_algorithm(value):
		return setkey('algorithm',value)

	def set_product(value):
		return setkey('product',value)

	def set_action(value):
		return setkey('action',value)

