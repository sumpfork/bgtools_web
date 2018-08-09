

# Credit goes to https://bitbucket.org/spookylukey/django-fabfile-starter/src

import os
import datetime as dt
from io import StringIO
import json

import posixpath
import fabric
import requests

from fabsettings import (USER, HOST, DJANGO_APP_NAME,
                         DJANGO_APPS_DIR, LOGS_ROOT_DIR,
                         APP_PORT, GUNICORN_WORKERS, DJANGO_PROJECT_NAME,
                         STAGING_APP_PORT)


def upload_template(c, filename, destination, context=None, template_dir=None):
    """
    Render and upload a template text file to a remote host.
    """

    text = None
    template_dir = template_dir or os.getcwd()
    from jinja2 import Environment, FileSystemLoader
    jenv = Environment(loader=FileSystemLoader(template_dir))
    context = context if context is not None else {}
    text = jenv.get_template(filename).render(**context)
    # Force to a byte representation of Unicode, or str()ification
    # within Paramiko's SFTP machinery may cause decode issues for
    # truly non-ASCII characters.
    # text = text.encode('utf-8')

    # Upload the file.
    return c.put(
        StringIO(text),
        destination,
    )


def venv(c):
    """
    Runs a command in a virtualenv (which has been specified using
    the virtualenv context manager
    """
    return c.prefix("source {}/bin/activate".format(c.config.bgtools.VENV_DIR))


def install_dependencies(c):
    ensure_virtualenv(c)
    with venv(c), c.cd(c.config.bgtools.SRC_DIR):
        c.run("pip install -U -r requirements.txt")


def file_exists(c, path):
    print('checking existence of: {}: {}'.format(path, bool(c.run('stat {}'.format(path), hide=True, warn=True))))
    return c.run('stat {}'.format(path), hide=True, warn=True).ok


def ensure_virtualenv(c):
    args = c.config.bgtools
    ensure_dir(c, args.SRC_DIR)
    if file_exists(c, args.VENV_DIR):
        return

    with c.cd(args.DJANGO_APP_ROOT):
        c.run("virtualenv --no-site-packages --python={} {}".format(
            args.PYTHON_BIN, args.venv_subdir))
        c.run("echo {} > {}/lib/{}/site-packages/projectsource.pth".format(
            args.SRC_DIR, args.venv_subdir, args.PYTHON_BIN))


def ensure_dir(c, d):
    print('checking existence of {} on {}'.format(d, c))
    if not file_exists(c, d):
        # note that the parent directory needs to already exist, usually by making a custom app
        # with the correct name in the webfaction control panel
        print('making {}'.format(d))
        c.run("mkdir -p {}".format(d))


def copy_settings(c):
    args = c.config.bgtools
    with c.cd(args.LOCAL_DIR):
        fname = 'settings_{}.py'.format(args.mode)
        c.local('cp {} bgtools/bgtools/private_settings.py'.format(fname))
        c.local('echo STAGING={} >> bgtools/bgtools/private_settings.py'.format('True' if args.staging else False, fname))


def rsync(c, src, dest):
    args = c.config.bgtools
    c.local('rsync -avz {} {}:{}'.format(src,
                                         args.host,
                                         dest))


def rsync_source(c):
    """
    rsync the source over to the server
    """
    args = c.config.bgtools
    rsync(c, os.path.join(args.LOCAL_DIR, 'bgtools'), args.DJANGO_APP_ROOT)


def collect_static(c):
    """
    Collect django static content on server
    """
    with venv(c), c.cd(c.config.bgtools.SRC_DIR):
        c.run('python manage.py collectstatic --no-input')


def checkout_and_install_libs(c):
    args = c.config.bgtools
    libs = json.load(open('libs.json'))
    ensure_dir(c, args.CHECKOUT_DIR)
    with c.cd(args.CHECKOUT_DIR):
        for lib, params in libs.items():
            print('handling ' + lib)
            if lib == 'domdiv':
                # right now only domdiv accepts the global branch override
                params['branch'] = args.branch
            libdir = params['repo']
            if libdir == 'local':
                with c.cd(args.LOCAL_DIR):
                    rsync(c, posixpath.join(params['path'], params['name']),
                          args.CHECKOUT_DIR)
                with c.cd(params['name']), venv(c):
                    c.run('pip install -U .')
                continue
            github_url = 'https://github.com/{}/{}'.format(params['owner'], params['repo'])
            if not file_exists(c, libdir):
                c.run('git clone {}.git'.format(github_url))
            with c.cd(libdir):
                c.run('git fetch origin')
                if args.mode == 'debug' or args.tag == 'head':
                    c.run('git checkout {}'.format(params['branch']))
                    c.run('git pull')
                    version = c.run('git rev-parse {}'.format(params['branch'])).stdout
                    version_url = '{}/commits/{}'.format(github_url, version)
                elif args.mode == 'release':
                    tag = args.tag
                    if tag == 'latest':
                        tag = c.run('git tag -l "v*"  --sort=-v:refname').stdout.split()[0]
                    c.run('git checkout {}'.format(tag))
                    version = tag
                    version_url = '{}/releases/tag/{}'.format(github_url, tag)
                for src, target in params['extras']:
                    with c.cd(args.LOCAL_DIR):
                        rsync(c, posixpath.join(args.LOCAL_DIR, 'extras', lib, src),
                              posixpath.join(args.CHECKOUT_DIR, libdir, target))
                with venv(c):
                    c.run('pip install -U .')
            with c.cd(args.SRC_DIR):
                r = requests.get('https://api.github.com/repos/{}/{}/releases'.format(params['owner'],
                                                                                      params['repo']))
                changelog = r.json()
                changelog = [{'url': ch['html_url'],
                              'date': dt.datetime.strptime(ch['published_at'][:10], '%Y-%m-%d').date(),
                              'name': ch['name'],
                              'tag': ch['tag_name'],
                              'description': ch['body']}
                             for ch in changelog]
                for tname, context in [('version', {'version': version, 'url': version_url}),
                                       ('changelog', {'changelog': changelog})]:
                    upload_template(c, '{}_template.html'.format(tname),
                                    posixpath.join(args.SRC_DIR,
                                                   DJANGO_APP_NAME,
                                                   'templates',
                                                   DJANGO_APP_NAME,
                                                   '{}.html'.format(tname)),
                                    context=context,
                                    template_dir=posixpath.join(args.LOCAL_DIR, 'templates'))


@fabric.task
def stop_webserver(c, mode='debug', tag='latest', staging=True, branch='master'):
    """
    Stop the webserver that is running the Django instance
    """
    populate_args(c, mode=mode, tag=tag, staging=staging, branch=branch)
    c.run("kill $(cat {})".format(c.config.bgtools.GUNICORN_PIDFILE))


def _webserver_command(c):
    args = c.config.bgtools
    return ('{venv_dir}/bin/gunicorn '
            '--error-logfile={error_logfile} '
            '--access-logfile={access_logfile} '
            '--capture-output '
            '-b 127.0.0.1:{port} '
            '-D -w {workers} --pid {pidfile} '
            '{wsgimodule}:application').format(
                **{'venv_dir': args.VENV_DIR,
                   'pidfile': args.GUNICORN_PIDFILE,
                   'wsgimodule': args.WSGI_MODULE,
                   'port': APP_PORT if not args.staging else STAGING_APP_PORT,
                   'workers': GUNICORN_WORKERS,
                   'error_logfile': args.GUNICORN_ERROR_LOGFILE,
                   'access_logfile': args.GUNICORN_ACCESS_LOGFILE}
            )


@fabric.task
def start_webserver(c, mode='debug', tag='latest', staging=True, branch='master'):
    """
    Starts the webserver that is running the Django instance
    """
    populate_args(c, mode=mode, tag=tag, staging=staging, branch=branch)
    start_webserver_internal(c)


def start_webserver_internal(c):
    print('starting new webserver: "{}"'.format(_webserver_command(c)))
    with c.cd(c.config.bgtools.SRC_DIR):
        c.run(_webserver_command(c), pty=False, echo=True)


@fabric.task(hosts=[HOST])
def restart_webserver(c, mode=None, tag=None, staging=None, branch=None):
    """
    Restarts the webserver that is running the Django instance
    """
    populate_args(c, mode=mode, staging=staging, tag=tag, branch=branch)
    restart_webserver_internal(c)


def restart_webserver_internal(c):
    args = c.config.bgtools
    if file_exists(c, args.GUNICORN_PIDFILE):
        print('killing existing webserver')
        c.run("kill -HUP $(cat {})".format(args.GUNICORN_PIDFILE), echo=True)
    else:
        start_webserver_internal(c)


def populate_arg(args, existing, argname):
    return existing if existing is not None else args[argname]


def populate_args(c, **kwargs):

    args = c.config.bgtools

    # env.use_ssh_config = True
    for k, v in kwargs.items():
        print('setting {} to {}'.format(k, populate_arg(args, v, k)))
        setattr(args, k, populate_arg(args, v, k))

    project = DJANGO_PROJECT_NAME
    if args.staging:
        project += '_staging'
    args.DJANGO_APP_ROOT = posixpath.join(DJANGO_APPS_DIR, project)

    # Python version
    args.PYTHON_BIN = "python3.5"
    # env.PYTHON_PREFIX = ""  # e.g. /usr/local  Use "" for automatic
    # env.PYTHON_FULL_PATH = (posixpath.join(env.PYTHON_PREFIX, 'bin', env.PYTHON_BIN)
    #                        if env.PYTHON_PREFIX else env.PYTHON_BIN)

    args.GUNICORN_PIDFILE = posixpath.join(args.DJANGO_APP_ROOT, 'gunicorn.pid')
    args.GUNICORN_ERROR_LOGFILE = posixpath.join(LOGS_ROOT_DIR,
                                                 'gunicorn_error_{}.log'.format(project))
    args.GUNICORN_ACCESS_LOGFILE = posixpath.join(LOGS_ROOT_DIR,
                                                  'gunicorn_access_{}.log'.format(project))

    args.SRC_DIR = posixpath.join(args.DJANGO_APP_ROOT, DJANGO_PROJECT_NAME)
    args.VENV_DIR = posixpath.join(args.DJANGO_APP_ROOT, args.venv_subdir)
    args.CHECKOUT_DIR = posixpath.join(args.DJANGO_APP_ROOT, 'checkouts')

    args.WSGI_MODULE = '{}.wsgi'.format(DJANGO_PROJECT_NAME)

    args.LOCAL_DIR = os.path.dirname(os.path.realpath(__file__))


@fabric.task(hosts=[HOST])
def deploy(c, mode=None, staging=True, tag=None, branch=None):
    populate_args(c, mode=mode, staging=staging, tag=tag, branch=branch)
    print(c.config.bgtools)
    copy_settings(c)
    rsync_source(c)
    install_dependencies(c)
    checkout_and_install_libs(c)
    collect_static(c)
    restart_webserver_internal(c)
