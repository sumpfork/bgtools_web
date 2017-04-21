# Credit goes to https://bitbucket.org/spookylukey/django-fabfile-starter/src

import os
import datetime as dt

import posixpath
from fabric.api import env, run, cd, task, local, prefix, lcd
from fabric.contrib.files import exists, upload_template
from fabric.contrib.project import rsync_project
from fabric.context_managers import settings
import requests

from fabsettings import (USER, HOST, DJANGO_APP_NAME,
                         DJANGO_APPS_DIR, LOGS_ROOT_DIR,
                         APP_PORT, GUNICORN_WORKERS, DJANGO_PROJECT_NAME,
                         STAGING_APP_PORT)

env.hosts = ['{}@{}'.format(USER, HOST)]


def venv():
    """
    Runs a command in a virtualenv (which has been specified using
    the virtualenv context manager
    """
    return prefix("source {}/bin/activate".format(env.VENV_DIR))


def install_dependencies():
    ensure_virtualenv()
    with venv(), cd(env.SRC_DIR):
        run("pip install -U -r requirements.txt")


def ensure_virtualenv():
    ensure_dir(env.SRC_DIR)
    if exists(env.VENV_DIR):
        return

    with cd(env.DJANGO_APP_ROOT):
        run("virtualenv --no-site-packages --python={} {}".format(
            env.PYTHON_BIN, env.VENV_SUBDIR))
        run("echo {} > {}/lib/{}/site-packages/projectsource.pth".format(
            env.SRC_DIR, env.VENV_SUBDIR, env.PYTHON_BIN))


def ensure_dir(d):
    if not exists(d):
        # note that the parent directory needs to already exist, usually by making a custom app
        # with the correct name in the webfaction control panel
        run("mkdir -p {}".format(d))


def copy_settings():
    print env.hosts
    with lcd(env.LOCAL_DIR):
        fname = 'settings_{}.py'.format(env.MODE)
        local('cp {} bgtools/bgtools/private_settings.py'.format(fname))


def rsync_source():
    """
    rsync the source over to the server
    """
    rsync_project(local_dir=os.path.join(env.LOCAL_DIR, 'bgtools'),
                  remote_dir=env.DJANGO_APP_ROOT)


def collect_static():
    """
    Collect django static content on server
    """
    with venv(), cd(env.SRC_DIR):
        run('python manage.py collectstatic --no-input')


def checkout_and_install_libs():
    libs = {
        'domdiv': {
            'owner': 'sumpfork',
            'repo': 'dominiontabs',
            'branch': 'master',
            'extras': [('fonts/', 'domdiv/fonts/')]
        }
    }
    ensure_dir(env.CHECKOUT_DIR)
    with cd(env.CHECKOUT_DIR):
        for lib, params in libs.iteritems():
            libdir = params['repo']
            github_url = 'https://github.com/{}/{}'.format(params['owner'], params['repo'])
            if not exists(libdir):
                run('git clone {}.git'.format(github_url))
            with cd(libdir):
                run('git fetch origin')
                if env.MODE == 'debug' or env.GIT_TAG == 'head':
                    run('git checkout {}'.format(params['branch']))
                    run('git pull')
                    version = run('git rev-parse {}'.format(params['branch']))
                    version_url = '{}/commits/{}'.format(github_url, version)
                elif env.MODE == 'release':
                    tag = env.GIT_TAG
                    if tag == 'latest':
                        tag = run('git tag -l "v*"  --sort=-v:refname').split()[0]
                    run('git checkout {}'.format(tag))
                    version = tag
                    version_url = '{}/releases/tag/{}'.format(github_url, tag)
                for src, target in params['extras']:
                    rsync_project(local_dir=posixpath.join(env.LOCAL_DIR, 'extras', lib, src),
                                  remote_dir=posixpath.join(env.CHECKOUT_DIR, libdir, target))
                with venv():
                    run('pip install -U .')
            with cd(env.SRC_DIR):
                r = requests.get('https://api.github.com/repos/{}/{}/releases'.format(params['owner'],
                                                                                      params['repo']))
                changelog = r.json()
                changelog = [{'url': c['html_url'],
                              'date': dt.datetime.strptime(c['published_at'][:10], '%Y-%m-%d').date(),
                              'name': c['name'],
                              'tag': c['tag_name'],
                              'description': c['body']}
                             for c in changelog]
                for tname, context in [('version', {'version': version, 'url': version_url}),
                                       ('changelog', {'changelog': changelog})]:
                    upload_template('{}_template.html'.format(tname),
                                    posixpath.join(env.SRC_DIR,
                                                   DJANGO_APP_NAME,
                                                   'templates',
                                                   DJANGO_APP_NAME,
                                                   '{}.html'.format(tname)),
                                    context=context,
                                    template_dir=posixpath.join(env.LOCAL_DIR, 'templates'),
                                    use_jinja=True)


@task
def webserver_stop(mode='debug', tag='latest', staging=True):
    """
    Stop the webserver that is running the Django instance
    """
    populate_env(mode, tag, staging)
    run("kill $(cat {})".format(env.GUNICORN_PIDFILE))


def _webserver_command():
    return ('{venv_dir}/bin/gunicorn '
            '--error-logfile={error_logfile} '
            '--access-logfile={access_logfile} '
            '--capture-output '
            '-b 127.0.0.1:{port} '
            '-D -w {workers} --pid {pidfile} '
            '{wsgimodule}:application').format(
                **{'venv_dir': env.VENV_DIR,
                   'pidfile': env.GUNICORN_PIDFILE,
                   'wsgimodule': env.WSGI_MODULE,
                   'port': APP_PORT if not env.STAGING else STAGING_APP_PORT,
                   'workers': GUNICORN_WORKERS,
                   'error_logfile': env.GUNICORN_ERROR_LOGFILE,
                   'access_logfile': env.GUNICORN_ACCESS_LOGFILE}
            )


@task
def webserver_start(mode='debug', tag='latest', staging=True):
    """
    Starts the webserver that is running the Django instance
    """
    populate_env(mode, tag, staging)
    run(_webserver_command(), pty=False)
    run('cat {}'.format(env.GUNICORN_PIDFILE))


@task
def webserver_restart(mode='debug', tag='latest', staging=True):
    """
    Restarts the webserver that is running the Django instance
    """
    populate_env(mode, tag, staging)
    if exists(env.GUNICORN_PIDFILE):
        with settings(warn_only=True):
            run("kill -HUP $(cat {})".format(env.GUNICORN_PIDFILE))
    if not exists(env.GUNICORN_PIDFILE):
        webserver_start(mode, tag, staging)


def populate_env(mode, tag, staging):
    env.MODE = mode
    env.GIT_TAG = tag
    env.STAGING = staging

    env.use_ssh_config = True

    project = DJANGO_PROJECT_NAME
    if env.STAGING:
        project += '_staging'
    env.DJANGO_APP_ROOT = posixpath.join(DJANGO_APPS_DIR, project)

    # Subdirectory of DJANGO_APP_ROOT in which virtualenv will be stored
    env.VENV_SUBDIR = 'venv'

    # Python version
    env.PYTHON_BIN = "python2.7"
    env.PYTHON_PREFIX = ""  # e.g. /usr/local  Use "" for automatic
    env.PYTHON_FULL_PATH = (posixpath.join(env.PYTHON_PREFIX, 'bin', env.PYTHON_BIN)
                            if env.PYTHON_PREFIX else env.PYTHON_BIN)

    env.GUNICORN_PIDFILE = posixpath.join(env.DJANGO_APP_ROOT, 'gunicorn.pid')
    env.GUNICORN_ERROR_LOGFILE = posixpath.join(LOGS_ROOT_DIR,
                                                'gunicorn_error_{}.log'.format(project))
    env.GUNICORN_ACCESS_LOGFILE = posixpath.join(LOGS_ROOT_DIR,
                                                 'gunicorn_access_{}.log'.format(project))

    env.SRC_DIR = posixpath.join(env.DJANGO_APP_ROOT, DJANGO_PROJECT_NAME)
    env.VENV_DIR = posixpath.join(env.DJANGO_APP_ROOT, env.VENV_SUBDIR)
    env.CHECKOUT_DIR = posixpath.join(env.DJANGO_APP_ROOT, 'checkouts')

    env.WSGI_MODULE = '{}.wsgi'.format(DJANGO_PROJECT_NAME)

    env.LOCAL_DIR = os.path.dirname(os.path.realpath(env.real_fabfile))


@task
def deploy(mode='debug', tag='latest', staging=True):
    staging = staging in ['True', 'true', 1]
    print(staging)
    populate_env(mode, tag, staging)
    copy_settings()
    rsync_source()
    install_dependencies()
    checkout_and_install_libs()
    collect_static()
    webserver_restart(mode, tag, staging)
