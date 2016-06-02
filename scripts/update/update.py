"""
Deployment for Mozillians in production.

Requires commander (https://github.com/oremj/commander) which is installed on
the systems that need it.
"""

import os
import random
import re
import sys
import urllib
import urllib2

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from commander.deploy import task, hostgroups  # noqa
import commander_settings as settings  # noqa


# Setup venv path.
venv_bin_path = os.path.join(settings.SRC_DIR, '..', 'venv', 'bin')
os.environ['PATH'] = venv_bin_path + os.pathsep + os.environ['PATH']

NEW_RELIC_URL = 'https://rpm.newrelic.com/deployments.xml'
GITHUB_URL = 'https://github.com/mozilla/mozillians/compare/{oldrev}...{newrev}'


@task
def update_code(ctx, tag):
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('git fetch')
        ctx.local('git checkout -f %s' % tag)
        ctx.local("find . -type f -name '.gitignore' -or -name '*.pyc' -delete")


@task
def update_locales(ctx):
    with ctx.lcd(os.path.join(settings.SRC_DIR, 'locale')):
        ctx.local('find . -name "*.mo" -delete')
        ctx.local('git pull')
        ctx.local('./compile.sh .')


@task
def update_assets(ctx):
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('which python')
        ctx.local('LANG=en_US.UTF-8 python manage.py collectstatic --noinput --no-default-ignore -i .git')  # noqa
        ctx.local('LANG=en_US.UTF-8 python manage.py compress --engine jinja2')
        ctx.local('LANG=en_US.UTF-8 python manage.py update_product_details')


@task
def database(ctx):
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('python manage.py migrate --noinput')


@task
def update_revision_files(ctx):
    with ctx.lcd(settings.SRC_DIR):
        global OLDREV, NEWREV
        NEWREV = ctx.local('git rev-parse HEAD').out.strip()
        OLDREV = ctx.local('cat media/revision.txt').out.strip()
        ctx.local('mv media/revision.txt media/prev-revision.txt')
        ctx.local("echo '%s' > media/revision.txt" % NEWREV)


@task
def ping_newrelic(ctx):
    if settings.NEW_RELIC_API_KEY and settings.NEW_RELIC_APP_ID:
        with ctx.lcd(settings.SRC_DIR):
            log_cmd = 'git log --oneline {0}..{1}'.format(OLDREV, NEWREV)
            changelog = ctx.local(log_cmd).out.strip()

        print 'Post deployment to New Relic'
        desc = generate_desc(OLDREV, NEWREV, changelog)
        if changelog:
            github_url = GITHUB_URL.format(oldrev=OLDREV, newrev=NEWREV)
            changelog = '{0}\n\n{1}'.format(changelog, github_url)
        data = urllib.urlencode({
            'deployment[description]': desc,
            'deployment[revision]': NEWREV,
            'deployment[app_id]': settings.NEW_RELIC_APP_ID,
            'deployment[changelog]': changelog,
        })
        headers = {'x-api-key': settings.NEW_RELIC_API_KEY}
        try:
            request = urllib2.Request(NEW_RELIC_URL, data, headers)
            urllib2.urlopen(request)
        except urllib.URLError as exp:
            print 'Error notifying New Relic: {0}'.format(exp)


@task
def update_es_indexes(ctx):
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('python manage.py cron index_all_profiles &')


@task
def validate_fun_facts(ctx):
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('python manage.py cron validate_fun_facts')


@task
def generate_humanstxt(ctx):
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('python manage.py cron generate_humanstxt &')


# @task
# def install_cron(ctx):
#    with ctx.lcd(settings.SRC_DIR):
#        ctx.local("python ./scripts/crontab/gen-crons.py -k %s -u apache > /etc/cron.d/.%s" %
#                  (settings.WWW_DIR, settings.CRON_NAME))
#        ctx.local("mv /etc/cron.d/.%s /etc/cron.d/%s" % (settings.CRON_NAME, settings.CRON_NAME))


@task
def checkin_changes(ctx):
    ctx.local(settings.DEPLOY_SCRIPT)


@hostgroups(settings.WEB_HOSTGROUP, remote_kwargs={'ssh_key': settings.SSH_KEY})
def deploy_app(ctx):
    ctx.remote(settings.REMOTE_UPDATE_SCRIPT)
    ctx.remote('/bin/touch %s' % settings.REMOTE_WSGI)


@hostgroups(settings.WEB_HOSTGROUP, remote_kwargs={'ssh_key': settings.SSH_KEY})
def prime_app(ctx):
    for http_port in range(80, 82):
        ctx.remote("for i in {1..10}; do curl -so /dev/null -H 'Host: %s' -I http://localhost:%s/ & sleep 1; done" % (settings.REMOTE_HOSTNAME, http_port))  # noqa


@hostgroups(settings.CELERY_HOSTGROUP, remote_kwargs={'ssh_key': settings.SSH_KEY})
def update_celery(ctx):
    ctx.remote(settings.REMOTE_UPDATE_SCRIPT)
    ctx.remote('/sbin/service %s restart' % settings.CELERY_SERVICE)
    ctx.remote('/sbin/service %s restart' % settings.CELERYBEAT_SERVICE)


@task
def update_info(ctx, tag):
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('date')
        ctx.local('git branch')
        ctx.local('git log -3')
        ctx.local('git status')
        ctx.local('which python')
        ctx.local('python manage.py migrate --list')
        with ctx.lcd('locale'):
            ctx.local('git remote -v')
            ctx.local('git log -1')
            ctx.local('git status')


@task
def setup_dependencies(ctx):
    with ctx.lcd(settings.SRC_DIR):
        # Creating a venv tries to open virtualenv/bin/python for
        # writing, but because venv is using it, it fails.
        # So we delete it and let virtualenv create a new one.
        ctx.local('rm -f venv/bin/python venv/bin/python2.7')
        ctx.local('virtualenv-2.7 --no-site-packages venv')

        # Activate venv to append to the correct path to $PATH.
        activate_env = os.path.join(venv_bin_path, 'activate_this.py')
        execfile(activate_env, dict(__file__=activate_env))

        # Make sure pip >= 8.x is installed
        ctx.local('python scripts/pipstrap.py')
        ctx.local('pip --version')
        ctx.local('pip install --require-hashes --no-deps -r requirements/prod.txt')
        # Make the venv relocatable
        ctx.local('virtualenv-2.7 --relocatable venv')

        # Fix lib64 symlink to be relative instead of absolute.
        ctx.local('rm -f venv/lib64')
        with ctx.lcd('venv'):
            ctx.local('ln -s lib lib64')


@task
def pre_update(ctx, ref=settings.UPDATE_REF):
    update_code(ref)
    setup_dependencies()
    update_info(ref)


@task
def update(ctx):
    update_assets()
    update_locales()
    database()


@task
def deploy(ctx):
    # install_cron()
    update_revision_files()
    checkin_changes()
    deploy_app()
    prime_app()
    update_celery()
    # Things run below here should not break the deployment if they fail.
    if OLDREV != NEWREV:
        # On dev, this script runs every 15 minutes. If we're pushing the same
        # revision we don't need to churn the index, ping new relic, or any of this.
        ping_newrelic()
        update_es_indexes()
        validate_fun_facts()
        generate_humanstxt()


@task
def update_mozillians(ctx, tag):
    """Do typical mozillians update"""
    pre_update(tag)
    update()


# utility functions #
# shamelessly stolen from https://github.com/mythmon/chief-james/


def get_random_desc():
    return random.choice([
        'No bugfixes--must be adding infinite loops.',
        'No bugfixes--must be rot13ing function names for code security.',
        'No bugfixes--must be demonstrating our elite push technology.',
        'No bugfixes--must be testing james.',
    ])


def extract_bugs(changelog):
    """Takes output from git log --oneline and extracts bug numbers."""
    bug_regexp = re.compile(r'\bbug (\d+)\b', re.I)
    bugs = set()
    for line in changelog:
        for bug in bug_regexp.findall(line):
            bugs.add(bug)

    return sorted(list(bugs))


def generate_desc(from_commit, to_commit, changelog):
    """Figures out a good description based on what we're pushing out."""
    if from_commit.startswith(to_commit):
        desc = 'Pushing {0} again'.format(to_commit)
    else:
        bugs = extract_bugs(changelog.split('\n'))
        if bugs:
            bugs = ['bug #{0}'.format(bug) for bug in bugs]
            desc = 'Fixing: {0}'.format(', '.join(bugs))
        else:
            desc = get_random_desc()
    return desc
