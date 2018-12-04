from celery import Celery
import threading
import time

class MonitorThread(object):
    def __init__(self, app, celery_app, interval=1):
        self.celery_app = celery_app
        self.interval = interval
        self.state = self.celery_app.events.State()

        app.thread = threading.Thread(target=self.run, args=())
        app.thread.daemon = True
        app.thread.start()

    def catchall(self, event):
        if event['type'] != 'worker-heartbeat':
            self.state.event(event)
            print("EVENT HAPPENED: %s" % event)

        # logic here

    def run(self):
        while True:
            try:
                with self.celery_app.connection() as connection:
                    recv = self.celery_app.events.Receiver(connection, handlers={
                        '*': self.catchall
                    })
                    recv.capture(limit=None, timeout=None, wakeup=True)

            except (KeyboardInterrupt, SystemExit):
                raise

            except Exception as exce:
                print("unable to capture: %s" % exce)
                pass

            time.sleep(self.interval)


'''
class MonitorThread(object):
    def __init__(self, celery_app, interval=1):
        self.celery_app = celery_app
        self.interval = interval

        self.state = self.celery_app.events.State()

        self.thread = threading.Thread(target=self.run, args=())
        self.thread.daemon = True
        self.thread.start()

    def catchall(self, event):
        if event['type'] != 'worker-heartbeat':
            self.state.event(event)
            print("EVENT HAPPENED: %s" % event)

        # logic here

    def run(self):
        while True:
            try:
                with self.celery_app.connection() as connection:
                    recv = self.celery_app.events.Receiver(connection, handlers={
                        '*': self.catchall
                    })
                    recv.capture(limit=None, timeout=None, wakeup=True)

            except (KeyboardInterrupt, SystemExit):
                raise

            except Exception as exce:
                print("unable to capture: %s" % exce)
                pass

            time.sleep(self.interval)
'''
