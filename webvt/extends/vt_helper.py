from flask import flash
# import logging
from logging import getLogger, StreamHandler, Formatter, FileHandler, Logger
import yaml
import json
import os
import subprocess
from sys import getsizeof
from redis import StrictRedis
from configs.config import REDIS_HOST, REDIS_PORT

# dict_tasks = { 'fn'  : 'function name',
#                'tid' : 'task id', 
#                'desc': 'description', 
#                'url' : 'xxx', 
#                'icon': ''
#                 }


class GlobalVars:
    def __init__(self):
        self.rds = StrictRedis(host=REDIS_HOST, port=REDIS_PORT)

    def get(self, redis_id):
        json_value = self.rds.get(redis_id)
        return json.loads(json_value)

    def set(self, redis_id, redis_value):
        json_value = json.dumps(redis_value, ensure_ascii=False)
        self.rds.set(redis_id, json_value)


class Tasks:
    def __init__(self, logger: Logger):
        self.task_list = []
        self.logger = logger

    def list(self):
        return self.task_list

    def add(self, func, taskid, desc, pageurl, icon):
        tsk = {'fn': func, 'tid': taskid, 'desc': desc, 'url': pageurl, 'icon': icon}
        self.logger.debug(tsk)
        self.task_list.append(tsk)

    def revoke(self, taskid):
        self.task_list[:] = [tsk for tsk in self.task_list if tsk.get('tid') != taskid]

    def get(self, taskid):
        result = None
        for tsk in self.task_list:
            if tsk['tid'] == taskid:
                result = tsk
                break
        return result

    def list_with_status(self):
        # from async.tasks import endless_test_loop, copy_box_to, delete_box, vagrant_action
        # funcs = {'endless_test_loop': endless_test_loop,
        #          'copy_box_to': copy_box_to,
        #          'delete_box': delete_box,
        #          'vagrant_action': vagrant_action}
        from async.tasks import funcs
        task_list = self.list()
        status_list = []
        for tsk in task_list:
            status = tsk.copy()
            task = funcs[tsk['fn']].AsyncResult(tsk['tid'])
            status['state'] = task.state
            if task.state == 'PENDING':
                # job did not start yet
                status['status'] = 'Pending...'
            elif task.state != 'FAILURE':
                status['status'] = task.info.get('status', '')
                if 'result' in task.info:
                    status['result'] = task.info['result']
            else:
                # something went wrong in the background job
                status['status'] = task.info.get('status', '')
                if 'result' in task.info:
                    status['result'] = task.info['result']
            status_list.append(status)
            self.logger.debug(status)
        return status_list


class SSHer:
    def __init__(self, logger: Logger):
        self.logger = logger

    def run(self, v_host, cmd):
        cmd_str = "ssh "+v_host['sudoer']+"@"+v_host['ip']+" "+cmd
        self.logger.debug(cmd_str)
        ssh = subprocess.Popen(cmd_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = ssh.stdout.readlines()
        error = ssh.stderr.readlines()
        # if not result:
        #     error = ssh.stderr.readlines()
        #     self.logger.error([d.decode('utf-8').strip('\n') for d in error])
        return [d.decode('utf-8').strip('\n') for d in result], "".join([e.decode('utf-8') for e in error])

    def copy(self, v_host_from, file_from, v_host_to, file_to):
        if v_host_from is not None:
            src_path = v_host_from['sudoer']+"@"+v_host_from['ip']+":"+file_from
        else:
            src_path = file_from

        if v_host_to is not None:
            target_path = v_host_to['sudoer']+"@"+v_host_to['ip']+":"+file_to
        else:
            target_path = file_to
        cmd_str = "scp %s %s" % (src_path, target_path)
        self.logger.debug(cmd_str)
        scp = subprocess.Popen(cmd_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = scp.stdout.readlines()
        error = scp.stderr.readlines()
        # if not result:
        #     error = scp.stderr.readlines()
        #     self.logger.error([d.decode('utf-8').strip('\n') for d in error])
        return [d.decode('utf-8').strip('\n') for d in result], "".join([e.decode('utf-8') for e in error])


class Tool:
    def __init__(self, logger: Logger):
        # logging.basicConfig(filename='error.log', level=logging.DEBUG)
        # self.logger = getLogger()
        # logging_format = Formatter('[%(asctime)s:] %(levelname)s %(module)s %(message)s')
        # handler = FileHandler('webvt.log', encoding='UTF-8')
        # handler.setFormatter(logging_format)
        # self.logger.addHandler(handler)
        # console_format = Formatter('[%(asctime)s:] %(levelname)s %(module)s %(message)s')
        # stream = StreamHandler()
        # stream.setFormatter(console_format)
        # self.logger.addHandler(stream)
        # self.logger.info("self create logger")
        self.logger = logger
        self.task = Tasks(logger)
        self.ssh = SSHer(logger)


class Conf:
    def __init__(self):
        self.configs = dict()

    def reload(self):
        if self.configs == {}:
            with open("/var/webvt/config/config.yaml", 'r') as stream:
                try:
                    self.configs = yaml.load(stream)
                    self.tool.logger.debug('configs loaded.(%s bytes)' % getsizeof(self.configs))
                except yaml.YAMLError as exc:
                    self.tool.logger.error(exc)

    def update(self):
        os.rename("/var/webvt/config/config.yaml", "/var/webvt/config/config.yaml.backup")
        with open("/var/webvt/config/config.yaml", 'w') as outfile:
            try:
                yaml.dump(self.configs, outfile, default_flow_style=False)
                result = True
            except yaml.YAMLError as exc:
                self.tool.logger.error(exc)
                result = False
        return result               


class Profiler:
    def __init__(self, tool: Tool):
        self.dict_profiles = dict()
        self.tool = tool

    def reload(self):
        if self.dict_profiles == {}:
            with open("/var/webvt/config/profile.yaml", 'r') as stream:
                try:
                    self.dict_profiles = yaml.load(stream)
                    self.tool.logger.debug('profiles loaded. %s (%s bytes)' % (self.dict_profiles, getsizeof(self.dict_profiles)))
                except yaml.YAMLError as exc:
                    self.tool.logger.error(exc)

    def update(self):
        os.rename("/var/webvt/config/profile.yaml", "/var/webvt/config/profile.yaml.backup")
        with open("/var/webvt/config/profile.yaml", 'w') as outfile:
            try:
                yaml.dump(self.dict_profiles, outfile, default_flow_style=False)
                result = True
            except yaml.YAMLError as exc:
                self.tool.logger.error(exc)
                result = False
        return result  


class VHost:
    def __init__(self, prof: Profiler):
        # dict_profiles = dict()
        self.prof = prof

    def list(self):
        self.prof.reload()
        result = None
        # global dict_profiles
        if self.prof.dict_profiles['vhosts'] != {}:
            result = sorted(self.prof.dict_profiles['vhosts'], key=lambda k: k['name'])
        return result

    def get(self, name):
        dic_vhosts = self.list()
        result = None
        if dic_vhosts is not None:
            for vh in dic_vhosts:
                if vh['name'] == name:
                    result = vh
                    break
        return result

    def add(self, name, ip, sudoer, nic):
        new_vhost = dict()
        new_vhost['name'] = name
        new_vhost['ip'] = ip
        new_vhost['sudoer'] = sudoer
        new_vhost['nic'] = nic
        new_vhost['disabled'] = False
        self.prof.reload()
        self.prof.dict_profiles['vhosts'].append(new_vhost)
        self.prof.update()
        return True

    def update(self, dict_updated):
        cri = dict_updated.get('name')
        # global dict_profiles
        dict_vhosts = self.prof.dict_profiles['vhosts']
        dict_vhosts[:] = [d for d in dict_vhosts if d.get('name') != cri]
        dict_vhosts.append(dict_updated)
        self.prof.dict_profiles['vhosts'] = dict_vhosts
        self.prof.update()
        return True


class Nic:
    def __init__(self, vhost: VHost, tool: Tool):
        self.nic_list = []
        self.vhost = vhost
        self.tool = tool

    def reset(self):
        self.nic_list = []

    def list(self):
        return self.nic_list

    def reload(self):
        if self.nic_list is []:
            dic_hosts = self.vhost.list()
            if dic_hosts is not None:
                for vh in dic_hosts:
                    if not vh['disabled']:
                        new_nic = dict()
                        new_nic['name'] = vh['name']
                        new_nic['nics'] = self.tool.ssh.run(vh, '/sbin/ifconfig | grep flag | cut -d: -f1')
                        self.nic_list.append(new_nic)
                        self.tool.logger.debug(msg='nics loaded.(%s bytes)' % getsizeof(self.nic_list))

    def get(self, name):
        self.reload()
        result = None
        for nc in self.nic_list:
            if nc['name'] == name:
                result = nc['nics']
                break
        return result


class Box:
    def __init__(self, vh: VHost, tool: Tool):
        self.box_list = []
        self.vhost = vh
        self.tool = tool

    def reload(self, target):
        # from async.tasks import vagrant_box_list
        # bl = vagrant_box_list.delay()
        # copyer = copy_box_to.delay(box_to_copy, vh_from, vh_to)
        # self.tool.task.add('copy_box_to', copyer.id, desc, '/profiles/boxes', 'cube')
        # flash('Begin to ' + desc, 'cube')

        dic_vhosts = self.vhost.list()
        if dic_vhosts is not None:
            if target is None:
                self.box_list = []
                for h in dic_vhosts:
                    if not h['disabled']:
                        dict_box = self.vagrant_box_list(h)
                        self.box_list.append(dict_box)
                        self.tool.logger.debug('box '+h['name']+' loadded.(%s bytes)' % getsizeof(dict_box))
            else:
                self.box_list[:] = [d for d in self.box_list if d.get('name') != target]
                vh = self.vhost.get(target)
                if vh is not None and (not vh['disabled']):
                    dict_box = self.vagrant_box_list(vh)
                    self.box_list.append(dict_box)
                    self.tool.logger.debug('box '+target+' loaded.(%s bytes)' % getsizeof(dict_box))

    def vagrant_box_list(self,vh):
        new_box = dict()
        new_box['name'] = vh['name']
        new_box['boxes'] = []
        res, err = self.tool.ssh.run(vh, "vagrant box list | awk '{print $1$2$3}'")
        for x in res:
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
        return new_box

    def list(self):
        return self.box_list

    def get(self, name):
        result = None
        if self.box_list is not []:
            for bx in self.box_list:
                if bx['name'] == name:
                    result = bx['boxes']
                    break
        return result

    def delete(self, target, box_name):
        desc = "delete box %s from %s" % (box_name, target)
        vh_from = self.vhost.get(target)
        box_vh = self.get(target)
        box_to_delete = dict()
        if box_vh is not None and vh_from is not None:
            for bx in box_vh:
                if bx['name'] == box_name:
                    box_to_delete = bx
                    break
        if box_to_delete != {}:
            from async.tasks import delete_box
            deleter = delete_box.delay(box_to_delete, vh_from)
            self.tool.task.add('delete_box', deleter.id, desc, '/profiles/boxes', 'cube')
            flash('Begin to '+desc, 'cube')

    def copyto(self, box_name, v_host_from, v_host_to):
        desc = "copy box %s from %s to %s" % (box_name, v_host_from, v_host_to)
        vh_from = self.vhost.get(v_host_from)
        vh_to = self.vhost.get(v_host_to)
        box_vh = self.get(v_host_from)
        box_to_copy = dict()
        if box_vh is not None and vh_from is not None and vh_to is not None:
            for bx in box_vh:
                if bx['name'] == box_name:
                    box_to_copy = bx
                    break
        if box_to_copy != {}:
            from async.tasks import copy_box_to
            copyer = copy_box_to.delay(box_to_copy, vh_from, vh_to)
            self.tool.task.add('copy_box_to', copyer.id, desc, '/profiles/boxes', 'cube')
            flash('Begin to '+desc, 'cube')


class Git:
    def __init__(self, prof: Profiler):
        # dict_profiles = dict()
        self.prof = prof

    def list(self):
        self.prof.reload()
        result = None
        if self.prof.dict_profiles is not None:
            result = sorted(self.prof.dict_profiles['gits'], key=lambda k: k['name'])
        return result

    def get(self, name):
        dic_gits = self.list()
        result = None
        if dic_gits is not None:
            for gt in dic_gits:
                if gt['name'] == name:
                    result = gt
                    break
        return result

    def add(self, name, site, tag):
        new_git = {}
        new_git['name'] = name
        new_git['site'] = site
        new_git['tag'] = tag
        new_git['disabled'] = False
        self.prof.reload()
        self.prof.dict_profiles['gits'].append(new_git)
        self.prof.update()
        return True

    def update(self, dict_updated):
        cri = dict_updated.get('name')
        dict_gits = self.prof.dict_profiles['gits']
        dict_gits[:] = [d for d in dict_gits if d.get('name') != cri]
        dict_gits.append(dict_updated)
        self.prof.dict_profiles['gits'] = dict_gits
        self.prof.update()
        return True


class Project:
    def __init__(self, tool: Tool):
        self.project_list = []
        self.tool = tool

    def reload(self):
        basedir = "/var/webvt/projects"
        self.project_list = []
        for x in filter(lambda x: os.path.isdir(os.path.join(basedir, x)), os.listdir(basedir)):
            prj_path = os.path.join(basedir, x)
            dict_project = dict()
            dict_gbl = dict()
            if os.path.isfile(os.path.join(prj_path, 'global.yml')):
                fn = os.path.join(prj_path, 'global.yml')
                with open(fn, 'r') as stream:
                    try:
                        dict_gbl = yaml.load(stream)
                        self.tool.logger.debug(dict_gbl)
                    except yaml.YAMLError as exc:
                        self.tool.logger.debug(exc)
            elif os.path.isfile(os.path.join(prj_path, 'global.json')):
                fn = os.path.join(prj_path, 'global.json')
                with open(fn, 'r') as stream:
                    try:
                        dict_gbl = json.load(stream)
                        self.tool.logger.debug(dict_gbl)
                    except yaml.YAMLError as exc:
                        self.tool.logger.debug(exc)

            if dict_gbl == {}:
                self.tool.logger.warning("global.yml(or .json) not found in %s" % prj_path)
            else:
                self.tool.logger.info('global of %s loaded.(%s bytes)' % (x, getsizeof(dict_gbl)))
                dict_project['global'] = dict_gbl
            dict_vm = dict()
            if os.path.isfile(os.path.join(prj_path,'project.yml')):
                fn = os.path.join(prj_path, 'project.yml')
                with open(fn, 'r') as stream:
                    try:
                        dict_vm = yaml.load(stream)
                        self.tool.logger.debug(dict_vm)
                    except yaml.YAMLError as exc:
                        self.tool.logger.error(exc)
            elif os.path.isfile(os.path.join(prj_path, 'project.json')):
                fn = os.path.join(prj_path, 'project.json')
                with open(fn, 'r') as stream:
                    try:
                        dict_vm = json.load(stream)
                        self.tool.logger.debug(dict_vm)
                    except yaml.YAMLError as exc:
                        self.tool.logger.error(exc)

            if dict_vm == {}:
                self.tool.logger.warning("project.yml(or .json) not found in %s" % prj_path)
            else:
                self.tool.logger.info('project of %s loaded.(%s bytes)' % (x, getsizeof(dict_vm)))
                dict_project['vms'] = dict_vm

            if dict_gbl != {} and dict_vm != {}:
                self.project_list.append(dict_project)

    def list(self):
        return self.project_list

    def add(self,project_data):
        return True    

    def update(self,project_data):
        return True    
      
    def delete(self,project_data):
        from async.tasks import endless_test_loop
        tsk = endless_test_loop.delay()
        self.tool.task.add('endless_test_loop', "%s" % tsk.id, 'test', '/profiles/projects', 'cube')
        return True    


class Builder:
    def __init__(self, tool: Tool):
        self.builder_list = []
        self.tool = tool

    def reload(self):
        basedir="/var/webvt/builders"
        self.builder_list=[]
        for x in filter(lambda x: os.path.isdir(os.path.join(basedir, x)), os.listdir(basedir)):
            builder_path = os.path.join(basedir, x)
            dict_builder = dict()
            if os.path.isfile(os.path.join(builder_path,'builder.yml')):
                fn = os.path.join(builder_path, 'builder.yml')
                with open(fn, 'r') as stream:
                    try:
                        dict_builder = yaml.load(stream)
                        self.tool.logger.debug(dict_builder)
                    except yaml.YAMLError as exc:
                        self.tool.logger.error(exc)
            elif os.path.isfile(os.path.join(builder_path, 'builder.json')):
                fn = os.path.join(builder_path, 'builder.json')
                with open(fn, 'r') as stream:
                    try:
                        dict_builder = json.load(stream)
                        self.tool.logger.debug(dict_builder)
                    except yaml.YAMLError as exc:
                        self.tool.logger.error(exc)

            if dict_builder == {}:
                self.tool.logger.warning("builder.yml(or .json) not found in %s" % builder_path)
            else:
                self.tool.logger.info('builder %s loaded.(%s bytes)' % (x, getsizeof(dict_builder)))
                self.builder_list.append(dict_builder)

    def list(self):
        return self.builder_list

    def add(self, builder_data):
        return True    

    def update(self, builder_data):
        return True    
      
    def delete(self, project_data):
        return True    

    def build(self, builder_data):
        return True


class Actions:
    def __init__(self, vh: VHost, tool: Tool):
        self.vhost = vh
        self.tool = tool

    def act(self, act, scope, path, prj, vh, vm):
        from async.tasks import vagrant_action
        if scope == "project":
            desc = "run command %s at project %s on %s" % (act, prj, vh)
        else:
            desc = "run command %s at vm %s of project %s on %s" % (act, vm, prj, vh)
        vh_to = self.vhost.get(vh)
        actor = vagrant_action.delay(act, scope, path, prj, vh_to, vm)
        self.tool.task.add('vagrant_action', actor.id, desc, '/general/panel', 'dashboard')
        flash('Begin to '+desc, 'dashboard')


class Helper:
    def __init__(self, logger: Logger):
        self.tool = Tool(logger)
        self.profiler = Profiler(self.tool)
        self.conf = Conf()
        self.builder = Builder(self.tool)
        self.project = Project(self.tool)
        self.vhost = VHost(self.profiler)
        self.git = Git(self.profiler)
        self.nic = Nic(self.vhost, self.tool)
        self.box = Box(self.vhost, self.tool)
        self.actions = Actions(self.vhost, self.tool)
        self.globals = GlobalVars()