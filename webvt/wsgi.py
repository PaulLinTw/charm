from configs.config import configs, REDIS_HOST, REDIS_PORT, REDIS_DB, LOG_FORMAT_FILE, LOG_FORMAT_STREAM, LOG_LEVEL
from flask import Flask
from flask_migrate import Migrate
from importlib import import_module
from logging import basicConfig, DEBUG, ERROR, getLogger, StreamHandler, Formatter, FileHandler
from os.path import abspath, dirname, join, pardir
import sys
from celery import Celery
# from extends.vt_helper import nic, box, project, builder
from extends.vt_helper import Helper
from database import db, create_database
from base.routes import login_manager


# prevent python from writing *.pyc files / __pycache__ folders
sys.dont_write_bytecode = True

path_source = dirname(abspath(__file__))
path_parent = abspath(join(path_source, pardir))
if path_source not in sys.path:
    sys.path.append(path_source)


def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)


def register_blueprints(app):
    for module_name in ( 'base', 'general', 'profiles'):
        module = import_module('{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)


def configure_login_manager(app, User):
    @login_manager.user_loader
    def user_loader(id):
        return db.session.query(User).filter_by(id=id).first()

    @login_manager.request_loader
    def request_loader(request):
        username = request.form.get('username')
        user = db.session.query(User).filter_by(username=username).first()
        return user if user else None


def configure_database(app):
    create_database()
    Migrate(app, db)

    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()


def configure_logs(app):
    basicConfig(filename='webvt.log', level=DEBUG, format=LOG_FORMAT_FILE)
    logger = getLogger()
    console_format = Formatter(LOG_FORMAT_STREAM)
    stream = StreamHandler()
    stream.setFormatter(console_format)
    logger.addHandler(stream)
    #
    # use --log-level=warning to run gunicorn in shell
    #
    if __name__ != '__main__':
        gunicorn_logger = getLogger('gunicorn.error')
        # logger.handlers = gunicorn_logger.handlers
        logger.setLevel(gunicorn_logger.level)
    else:
        logger.setLevel(LOG_LEVEL)

    # sql_logger = getLogger('sqlalchemy.engine')
    # sql_logger.setLevel(ERROR)
    # sql_logger.handlers = logger.handlers

def make_celery(app):
    celery = Celery(app.import_name, broker='redis://%s:%s/%s' % (REDIS_HOST, REDIS_PORT, REDIS_DB))
    celery_config = app.config['CELERY_CONFIG_MODULE']
    celery.config_from_object(celery_config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


'''
def monitor_print(event):
    print("EVENT HAPPENED: %s" % event)

def monitor(celery_app,interval):
    def catchall(event):
        if event['type'] != 'worker-heartbeat':
            monitor_print(event)
#        print("EVENT HAPPENED: %s" % event)

    while True:
        try:
            with celery_app.connection() as connection:
                recv = celery_app.events.Receiver(connection, handlers={
                    '*': catchall
                })
                recv.capture(limit=None, timeout=None, wakeup=True)
        except (KeyboardInterrupt, SystemExit):
            raise

        except Exception as exce:
            print("unable to capture: %s" % exce)
            pass
        time.sleep(interval)
'''


def create_app(config_mode='production', selenium=False):
    app = Flask(__name__, static_folder='base/static')

#    app.jinja_env.globals['config'] = configer.reload()
#    if app.jinja_env.globals['config']==None:
#         sys.exit()

#    app.jinja_env.globals['profile'] = profiler.reload()
#    if app.jinja_env.globals['profile']==None:
#         sys.exit()
#    with app.app_context():
    app.config.from_object(configs[config_mode])
#    app.config.from_object(DebugConfig)
    if selenium:
        app.config['LOGIN_DISABLED'] = True
    register_extensions(app)
    # register_blueprints(app)
    from base.models import User
    configure_login_manager(app, User)
    configure_database(app)
    configure_logs(app)

    return app


app = create_app()
vt = Helper(app.logger)
vt.nic.reset()
vt.nic.reload()
vt.box.reload(None)
vt.project.reload()
vt.builder.reload()
# register_extensions(app)
register_blueprints(app)

#celery = make_celery(app)
#thread = threading.Thread(target=monitor, args=(celery,1))
#thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
