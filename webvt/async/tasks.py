from configs.config import LOG_FORMAT_FILE
from wsgi import make_celery, app, vt

import logging

celery = make_celery(app)

celery_logger = logging.getLogger(__name__)
new_handler = logging.FileHandler('celery.log')
new_formatter = logging.Formatter(LOG_FORMAT_FILE)
new_handler.setFormatter(new_formatter)
celery_logger.addHandler(new_handler)
celery_logger.info('celery logger configured')


# class States:
#     lock = 'LOCK'
#     failure = 'FAILURE'
#     ready = 'READY'


@celery.task(bind=True)
def endless_test_loop(self):
    from time import gmtime, strftime, sleep
    for i in range(10):
        now = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
        print(now)
        self.update_state(state='PROGRESS', meta={'time': now, 'status': '%s of 10' % i})
        sleep(10)
    return {'status': 'Task completed!', 'result': 10}


@celery.task(bind=True)
def copy_box_to(self, box_to_copy, vh_from, vh_to):
    celery_logger.info("Copying box %s from %s to %s .." % (box_to_copy['name'], vh_from['name'], vh_to['name']))
    cmdstr = "vagrant box repackage %s %s %s" % (box_to_copy['name'], box_to_copy['provider'], box_to_copy['tag'])
    self.update_state(state='PROGRESS', meta={'status': cmdstr})
    celery_logger.debug(l for l in vt.tool.ssh.run(vh_from, cmdstr))
    self.update_state(state='PROGRESS', meta={'status': 'Copy from %s to webvt' % vh_from})
    celery_logger.debug(l for l in vt.tool.ssh.copy(vh_from, "./package.box", None, "./"))
    self.update_state(state='PROGRESS', meta={'status': 'Copy from webvt to %s' % vh_to})
    celery_logger.debug(l for l in vt.tool.ssh.copy(None, "./package.box", vh_to, "./"))
    cmdstr = "vagrant box add --force --provider %s --name %s ./package.box" \
             % (box_to_copy['provider'], box_to_copy['name'])
    self.update_state(state='PROGRESS', meta={'status': cmdstr})
    celery_logger.debug(l for l in vt.tool.ssh.run(vh_to, cmdstr))
    # self.update_state(state='PROGRESS', meta={'status': 'Reload box information'})
    # box.reload(vh_to)
    return {'status': 'Task completed!'}


@celery.task(bind=True)
def delete_box(self, box_to_delete, vh_from):
    celery_logger.info("Deleting box %s from %s .." % (box_to_delete['name'], vh_from['name']))
    cmdstr = "vagrant box remove --force %s --provider %s --box-version %s"\
             % (box_to_delete['name'], box_to_delete['provider'], box_to_delete['tag'])
    self.update_state(state='PROGRESS', meta={'status': cmdstr})
    celery_logger.debug(l for l in vt.tool.ssh.run(vh_from, cmdstr))
    # vt.box.reload(vh_from)
    return {'status': 'Task completed!'}


@celery.task(bind=True)
def vagrant_action(self, act, scope, path, prj, vh_to, vm):
    celery_logger.debug(vh_to)
    if scope == "project":
        celery_logger.info("Running command %s at project %s on %s(%s).." % (act, prj, vh_to['name'], vh_to['ip']))
        cmdstr = "\"cd %s && vagrant %s\"" % (path, act)
    else:
        celery_logger.info("Running command %s at vm %s of project %s on %s(%s).." % (act, vm, prj, vh_to['name'],
                                                                                       vh_to['ip']))
        cmdstr = "\"cd %s && vagrant %s %s\"" % (path, act, vm)
    self.update_state(state='PROGRESS', meta={'status': cmdstr})
    res, err = vt.tool.ssh.run(vh_to, cmdstr)
    if err:
        self.update_state(state='FAILURE', meta={'status': '%s' % err})
        celery_logger.debug(l for l in err)
    else:
        self.update_state(state='SUCCESS', meta={'status': 'Task completed'})
        celery_logger.debug(l for l in res)
    # return {'status': 'Task completed!'}


@celery.task(bind=True)
def vagrant_box_list(self, vh):
    new_box = dict()
    new_box['name'] = vh['name']
    new_box['boxes'] = []
    try:
        tmp, err = vt.tool.ssh.run(vh, "vagrant box list | awk '{print $1$2$3}'")
        if err != '[]':
            new_box = {"vhost": vh["name"], "state": err}
        else:
            for x in tmp:
                if x != '' and x.find('==> vagrant:') < 0:
                    x = x.replace('(', ' ')
                    x = x.replace(',', ' ')
                    x = x.replace(')', '')
                    xa = x.split()
                    bx = dict()
                    bx['name'] = xa[0]
                    bx['provider'] = xa[1]
                    bx['tag'] = xa[2]
                    new_box['boxes'].append(bx)
    except:
        pass
    celery_logger.debug(new_box)
    vt.globals.set("boxes-%s" % vh['name'], new_box)
    return {'status': 'Task completed!'}


@celery.task(bind=True)
def get_nic_list(self, vh):
    new_nic = dict()
    new_nic['name'] = vh['name']
    self.update_state(state='PROGRESS', meta={'status': 'get nic list from %s' % vh['name']})
    result, err = vt.tool.ssh.run(vh, '/sbin/ifconfig | grep flag | cut -d: -f1')
    new_nic['nics'] = result
    new_nic['error'] = err
    if err:
        self.update_state(state='FAILURE', meta={'status': '%s' % err})
    else:
        self.update_state(state='SUCCESS', meta={'status': 'nic list stored in key nic-%s.' % vh['name']})
    vt.globals.set("nic-%s" % vh['name'], new_nic)  
    return {'status': 'Task completed!'}


@celery.task()
def get_vhost_metrics(vh):
    metrics = {'vhost': vh['name'], 'ip': vh['ip'], 'cpu': '', 'free': '', 'network': '', 'swap': ''}
    # vt.globals.set("metrics-%s" % vh["name"], metrics)
    errors = []
    cmdstr = "ps axo %cpu | awk '{ sum+=$1 } END { printf \"%.1f\", sum }' | tail -n 1"
    res, err = vt.tool.ssh.run(vh, cmdstr)
    if err != '' and err not in errors:
        errors.append(err)
    metrics['cpu'] = "".join([l for l in res])
    # cmdstr = "iostat -y -m -d $INTERVAL $DISK_IO_MOUNTPOINT |
    # while read line; do echo $line | awk '/[0-9.]/{ print $3 }' ; done"
    # pl = ssher.run(vh, cmdstr)
    # metrics['disk.io'] = "".join([l for l in pl])
    cmdstr = "df | awk '{ printf $1 \"-%.1f, \",$5 }'"
    devs = []
    res, err = vt.tool.ssh.run(vh, cmdstr)
    if err != '' and err not in errors:
        errors.append(err)
    s = "".join([l for l in res])
    for e in s.split(','):
        k = e.split('-')
        if "/dev/" in k[0] and "mapper" not in k[0]:
            dev = {"device": k[0], "usage": k[1]}
            devs.append(dev)
    metrics['disk'] = devs
    cmdstr = "free | awk '/Mem:/ {printf \"%.1f\", 100 - $4 / ($3 + $4) * 100}'"
    res, err = vt.tool.ssh.run(vh, cmdstr)
    if err != '' and err not in errors:
        errors.append(err)
    metrics['free'] = "".join([l for l in res])
    cmdstr = "cat /proc/net/dev | awk -v iface_regex=\"%s:\" '$0 ~ iface_regex { print $2\" \"$10 }'" \
             % vh['nic']
    res, err = vt.tool.ssh.run(vh, cmdstr)
    if err != '' and err not in errors:
        errors.append(err)
    metrics['network'] = "".join([l for l in res])
    cmdstr = "free | awk '/Swap/{ if (int($2) == 0) exit; printf \"%.1f\", $3 / $2 * 100.0 }'"
    res, err = vt.tool.ssh.run(vh, cmdstr)
    if err != '' and err not in errors:
        errors.append(err)
    metrics['swap'] = "".join([l for l in res])
    metrics['error'] = "".join([l for l in errors])

    celery_logger.debug(metrics)
    vt.globals.set("metrics-%s" % vh["name"], metrics)


@celery.task(bind=True)
def get_metrics(self):
    self.update_state(state='PROGRESS', meta={'status': 'getting metrics from all vhosts'})
    vhosts = vt.vhost.list()
    for vh in vhosts:
        if not vh['disabled']:
            get_vhost_metrics.delay(vh)
    self.update_state(state='PROGRESS', meta={'status': 'all commands deployed'})
    return {'status': 'Task completed!'}


@celery.task(bind=True)
def get_vagrant_status(self):
    self.update_state(state='PROGRESS', meta={'status': 'getting vagrant status from all vhosts'})
    vhosts = vt.vhost.list()
    for vh in vhosts:
        if not vh['disabled']:
            get_vhost_vagrant_status.delay(vh)
    self.update_state(state='PROGRESS', meta={'status': 'all vagrant status stored.'})
    return {'status': 'Task completed!'}


@celery.task()
def get_vhost_vagrant_status(vh):
    host = {"vhost": vh["name"], 'status': [], 'error': ''}
    # vt.globals.set("vagrant_status-%s" % vh["name"], host)
    cmdstr = "vagrant global-status | awk 'FNR >2 { print $2\",\"$4\",\"$5}'"
    res, err = vt.tool.ssh.run(vh, cmdstr)
    projects = []
    project_status = []
    for l in res:
        e = l.split(',')
        p = e[2].split('/')[-1]
        if e[0] == "":
            break
        else:
            if p not in projects:
                projects.append(p)
                prj = {"project": p, "path": e[2], "vms": [{"vm": e[0], "status": e[1]}]}
                project_status.append(prj)
            else:
                for ps in project_status:
                    if ps['project'] == p:
                        ps['vms'].append({"vm": e[0], "status": e[1]})
                        break
    host['status'] = project_status
    host['error'] = err
    celery_logger.debug(host)
    vt.globals.set("vagrant_status-%s" % vh["name"], host)


funcs = {'endless_test_loop': endless_test_loop,
         'copy_box_to': copy_box_to,
         'delete_box': delete_box,
         'vagrant_action': vagrant_action,
         'vagrant_box_list': vagrant_box_list,
         'get_nic_list': get_nic_list}
