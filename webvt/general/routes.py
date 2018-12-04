from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required
# from extends.vt_helper import tasks as task_helper, actions as action_helper, project
from wsgi import vt
import os

blueprint = Blueprint(
    'general_blueprint',
    __name__,
    url_prefix='/general',
    template_folder='templates',
    static_folder='static'
)


@blueprint.route('/about')
@login_required
def about():
    return render_template('about.html')


@blueprint.route('/panel')
@login_required
def panel():
    metrics = []
    vhost_list = vt.vhost.list()
    for vh in vhost_list:
        metrics.append(vt.globals.get("metrics-%s" % vh['name']))
    # rds = StrictRedis(host=REDIS_HOST, port=6379)
    # json_value = rds.get("metrics")
    # metrics = json.loads(json_value)
    global_status = vt.globals.get("vagrant_status")
    # json_value = rds.get("vagrant_status")
    # global_status = json.loads(json_value)
    project_list = vt.project.list()

    return render_template('panel.html', refresher=60, metrics=metrics,
                           global_status=global_status, projects=project_list)


@blueprint.route('/actions')
@login_required
def actions():
    action = request.args.get("action")
    scope = request.args.get("scope")
    project = request.args.get("project")
    path = request.args.get("path")
    vhost = request.args.get("vhost")
    vm = request.args.get("vm")
    vt.actions.act(action.lower(), scope, path, project, vhost, vm)

    return redirect(url_for('general_blueprint.panel'))


@blueprint.route('/tasks')
@login_required
def tasks():
    tl = vt.tool.task.list_with_status()
    tl1 = []
    for tsk in tl:
        tsk["status"] = tsk["status"].replace('\"', '')
        tl1.append(tsk)
    vt.tool.logger.debug(tl1)
    return render_template('tasks.html', tasks=tl1)


@blueprint.route('/get_tasks')
@login_required
def get_tasks():
    tl = vt.tool.task.list_with_status()
    tl1 = []
    for tsk in tl:
        tsk["status"] = tsk["status"].replace('\"', '')
        tl1.append(tsk)
    vt.tool.logger.debug(tl1)
    return jsonify(tl1)


@blueprint.route('/copy_id')
@login_required
def copy_id():
    os.system('gnome-terminal -x ssh paul@127.0.0.1')
    tl = vt.tool.task.list_with_status()
    tl1 = []
    for tsk in tl:
        tsk["status"] = tsk["status"].replace('\"', '')
        tl1.append(tsk)
    vt.tool.logger.debug(tl1)
    return jsonify(tl1)


@blueprint.route('/<template>')
@login_required
def route_template(template):
    return render_template(template + '.html')
