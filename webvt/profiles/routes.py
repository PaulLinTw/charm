from flask import Blueprint, flash, render_template, request, redirect, url_for
from flask_login import login_required
#from extends.vt_helper import project, vhost, box, builder, git, nic, tasks
from wsgi import vt
blueprint = Blueprint(
    'profiles_blueprint',
    __name__,
    url_prefix='/profiles',
    template_folder='templates',
    static_folder='static'
)


@blueprint.route('/projects')
@login_required
def projects():
    project_list = vt.project.list()
    return render_template('projects.html', projects=project_list)


@blueprint.route('/vhosts')
@login_required
def vhosts():
    vhost_list = vt.vhost.list()
    if vhost_list is None:
        vhost_list = []
    return render_template('vhosts.html', vhosts=vhost_list, tasks=vt.tool.task.task_list)


@blueprint.route('/vhost_switch')
@login_required
def vhost_switch():
    name=request.args.get("name")
    if name is not None:
        vhostdata = vt.vhost.get(name)
        if vhostdata is not None:
            vhostdata['disabled'] = not vhostdata['disabled']
            vt.vhost.update(vhostdata)
            if vhostdata['disabled']:
                stat="disabled"
            else:
                stat="active"
            flash('vhost %s switch to %s' % (name, stat), 'laptop')
            return redirect(url_for('profiles_blueprint.vhosts'))
        else:
            return render_template('errors/page_500.html', error="V-Host "+name+" not found")
    else:
        return redirect(url_for('profiles_blueprint.vhosts'))

@blueprint.route('/vhost_editor')
@login_required
def vhost_editor():
    name=request.args.get("name")
    if name is not None:
        vhost_data = vt.vhost.get(name)
        nic_data = vt.nic.get(name)
        if vhost_data is not None:
            return render_template('vhost_editor.html', vhostdata=vhost_data, nicdata=nic_data)
        else:
            return render_template('errors/page_500.html', error="V-Host "+name+" not found")
    else:
        return render_template('vhost_editor.html', vhostdata=None, nicdata=None)


@blueprint.route('/vhost_update', methods=['POST'])
@login_required
def vhost_update():
    vhostdata={}
    vhostdata['name'] = request.form["name"]
    vhostdata['ip'] = request.form["ip"]
    vhostdata['sudoer'] = request.form["sudoer"]
    vhostdata['nic'] = request.form["nic"]
    vhostdata['disabled'] = (request.form["disabled"] == 'True')
    vt.vhost.update(vhostdata)
    flash('vhost %s updated' % vhostdata['name'], 'laptop')
    return redirect(url_for('profiles_blueprint.vhosts'))


@blueprint.route('/vhost_add', methods=['POST'])
@login_required
def vhost_add():
    name = request.form["name"]
    if vt.vhost.get(name) is not None:
        return render_template('errors/page_500.html', error="V-Host "+name+" already existed")
    ip = request.form["ip"]
    sudoer = request.form["sudoer"]
    nic = request.form["nic"]
    vt.vhost.add(name, ip, sudoer, nic)
    return redirect(url_for('profiles_blueprint.vhosts'))


@blueprint.route('/boxes')
@login_required
def boxes():
    vhost_list = vt.vhost.list()
    if vhost_list is None:
        vhost_list = []
    box_list = vt.box.list()
    if box_list is None:
        box_list = []
    only_names = []
    for bx in box_list:
        names = {'vhost': bx['name'], 'boxes':[]}
        for x in bx['boxes']:
            names['boxes'].append(x['name'])
            only_names.append(names)
    return render_template('boxes.html', vhosts=vhost_list, boxes=box_list, onlynames=only_names)


@blueprint.route('/box_editor')
@login_required
def box_editor():
    name = request.args.get("name")
    if name is None:
        dic_box = vt.box.get(name)
        return render_template('box_editor.html', box=dic_box)
    else:
        return None


@blueprint.route('/box_reload')
@login_required
def box_reload():
    vhost_name = request.args.get("name")
    if vhost_name is not None:
        vt.box.reload(vhost_name)
    return redirect(url_for('profiles_blueprint.boxes'))

@blueprint.route('/box_copyto')
@login_required
def box_copyto():
    vhost_from = request.args.get("from")
    vhost_to = request.args.get("to")
    box_name = request.args.get("box")
    if vhost_from is not None and vhost_to is not None and box_name is not None:
        vt.box.copyto(box_name,vhost_from,vhost_to)
        return redirect(url_for('profiles_blueprint.boxes'))
    else:
        return render_template('errors/page_500.html', error="Box name and source, target V-Host name must be assigned.")


@blueprint.route('/box_delete')
@login_required
def box_delete():
    vhost_name=request.args.get("vhost")
    box_name=request.args.get("box")
    if vhost_name!=None and box_name!=None:
        vt.box.delete(vhost_name,box_name)
        return redirect(url_for('profiles_blueprint.boxes'))
    else:
        return render_template('errors/page_500.html', error="Both V-Host name and box name must be assigned.")


@blueprint.route('/builders')
@login_required
def builders():
    onlynames = []
    bxs = vt.box.list()
    for bx in bxs:
        names = {'vhost': bx['name'], 'boxes':[]}
        for x in bx['boxes']:
            names['boxes'].append(x['name'])
        onlynames.append(names)
    builders = vt.builder.list()
    if builders is None:
        builders = []
    return render_template('builders.html', builders=builders, onlynames = onlynames)


@blueprint.route('/builder_reload')
@login_required
def builder_reload():
    vt.builder.reload()
    return redirect(url_for('profiles_blueprint.builders'))


@blueprint.route('/builder_editor')
@login_required
def builder_editor():
    name=request.args.get("name")
    if name==None:
        dic_builder = vt.builder.get(name)
        return render_template('builder_editor.html', builder=dic_builder)
    else:
        return None

@blueprint.route('/gits')
@login_required
def gits():
    gits = vt.git.list()
    if gits is None:
        gits = []
    return render_template('gits.html', gits = gits)

@blueprint.route('/git_switch')
@login_required
def git_switch():
    name=request.args.get("name")
    if name!=None:
        gitdata=vt.git.get(name)
        if gitdata is not None:
            gitdata['disabled'] = not gitdata['disabled']
            vt.git.update(gitdata)
            if gitdata['disabled']:
                stat="disabled"
            else:
                stat="active"
            flash('Resource %s switch to %s' % (name, stat), 'github')
            return redirect(url_for('profiles_blueprint.gits'))
        else:
            return render_template('errors/page_500.html', error="Resource "+name+" not found")
    else:
        return redirect(url_for('profiles_blueprint.gits'))

@blueprint.route('/git_editor')
@login_required
def git_editor():
    name=request.args.get("name")
    if name!=None:
        gitdata=vt.git.get(name)
        if gitdata!=None:
            return render_template('git_editor.html', gitdata = gitdata)
        else:
            return render_template('errors/page_500.html', error="Resource "+name+" not found")
    else:
        return render_template('git_editor.html', gitdata = None)

@blueprint.route('/git_update', methods=['POST'])
@login_required
def git_update():
    gitdata={}
    gitdata['name'] = request.form["name"]
    gitdata['site'] = request.form["site"]
    gitdata['tag']  = request.form["tag"]
    gitdata['disabled'] = (request.form["disabled"]=='True')
    vt.git.update(gitdata)
    return redirect(url_for('profiles_blueprint.gits'))

@blueprint.route('/git_add', methods=['POST'])
@login_required
def git_add():
    name=request.form["name"]
    if vt.git.get(name) != None:
        return render_template('errors/page_500.html', error="Resource "+name+" already existed")
    name = request.form["name"]
    site = request.form["site"]
    tag  = request.form["tag"]
    vt.git.add(name, site, tag)
    flash('Resource %s addedd.' % name, 'github')
    return redirect(url_for('profiles_blueprint.gits'))

@blueprint.route('/<template>')
@login_required
def route_template(template):
    return render_template(template + '.html')
