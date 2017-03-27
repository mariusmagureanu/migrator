from __future__ import with_statement
import os
import subprocess

import fabric.contrib.files
from fabric import colors
from fabric.api import *


this_directory = os.path.abspath(os.path.dirname(__file__))

fab = 'fab'
pip = 'pip'
nose_tests = 'nosetests --with-coverage --cover-package=rest.app -v'


def clean():
    """
    Removes all *.pyc files.
    """
    print 'Number of .pyc files we found was: %s' % \
          local("find . -iname '*.pyc' | wc -l")
    local("find  . -iname '*.pyc' -delete", capture=False)
    local("find  . -name '_trial_temp' -prune -exec rm -r '{}' \;",
          capture=False)


def deps():
    libs = 'nose pep8 autopep8 pyresttest ' \
           'flask flask_restful flask-restful-swagger'
    local('%s install %s' % (pip, libs), capture=False)


def test():
    """
    Runs unit-tests and checks .py files
    against PEP8 standard.
    """
    env = dict(os.environ)

    p_pep8_test = subprocess.Popen(['pep8', '--config=pep8_config',
                                    '--statistics', '--format=pylint',
                                    '--benchmark',
                                    'rest', 'fabfile.py'],
                                   cwd=this_directory,
                                   env=env,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
    pep8_std_out = p_pep8_test.stdout.read()

    pep8_ec = p_pep8_test.wait()

    if pep8_ec:
        print ' PEP8 '.center(80, '-')
        print colors.red(pep8_std_out)
        print '-' * 80

    overall_status = pep8_ec
    if overall_status != 0:
        pass_ = colors.green('Pass')
        fail_ = colors.red('Fail')

        pep8_str = pass_ if not pep8_ec else fail_

        fabric.utils.error("\nPEP8: {}".format(pep8_str))

    return overall_status
