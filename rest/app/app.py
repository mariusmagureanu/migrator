import atexit
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
import warnings
from httplib import (
    ACCEPTED,
    BAD_REQUEST,
    GONE,
    INTERNAL_SERVER_ERROR,
    NOT_FOUND,
    OK,
    SEE_OTHER,
)

from flask.exthook import ExtDeprecationWarning
warnings.simplefilter('ignore', ExtDeprecationWarning)

import flask
from flask import Flask, request, send_from_directory
from flask.views import MethodView
from flask_restful import Api
from flask_restful_swagger import swagger
from swagger_doc import (
    get_vcl,
    migrate_vcl_3_to_4,
    migrate_vcl_3_to_5,
    migration_task_status,
)


app = Flask(__name__)
api = swagger.docs(Api(app), apiVersion='0.1',
                   description="Varnish configuration language migration service.")

app.config.from_pyfile('default.cfg', silent=True)

try:
    file_handler = logging.FileHandler(app.config['LOG_FILE'])
except IOError as ioe:
    print(ioe.args[0])
    sys.exit(1)

file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]'
))

app.logger.addHandler(file_handler)
app.logger.setLevel(logging.DEBUG)


def log(text, level=logging.DEBUG, exception=None):

    req_id = None
    if flask.request:
        req_id = flask.g.reqid

    req_id_log = req_id if req_id else "N/A"

    if level == logging.ERROR:
        if exception:
            app.logger.exception("ReqId %s - Exception: %s\n"
                                 % (req_id_log,
                                    exception.args[0]))
        else:
            app.logger.error("ReqId %s - Error: %s\n" % (req_id_log,
                                                         text))
    elif level == logging.WARNING:
        app.logger.warning("Reqid: %s - %s\n " % (req_id_log, text))
    elif level == logging.INFO:
        app.logger.info("Reqid: %s - %s\n" % (req_id_log, text))
    else:
        app.logger.debug("Reqid: %s - %s\n " % (req_id_log, text))


# dictionary that holds a file name as key
# and the running migration process as value.
running_procs = dict()

# create a temporary working folder.
# this folder gets deleted at app's exit time.
cwd = tempfile.mkdtemp()


def at_exit():
    """
    Delete the working temp folder at exit time.
    :return:
    """
    log("Migrator app has stopped. %s will be deleted" % cwd)
    shutil.rmtree(cwd)


def save_input_vcl():
    """
    Get the vcl file from the incoming request.
    Check its extension and save it in the cwd.
    :return:
    """
    vcl_file = request.files['file']

    if vcl_file is None:
        raise ValueError("VCL input file not found on the request.")

    extension = os.path.splitext(vcl_file.filename)[1]

    if extension.lower() != ".vcl":
        raise ValueError("Invalid input file, vcl format expected.")

    vcl_file.save(os.path.join(cwd, vcl_file.filename))

    return vcl_file.filename


def create_migration_task_response(file_name):
    """
    Creates a response with status set as ACCEPTED.
    This means that the vcl file has been saved and its
    migration process has started.

    The client will query the migration status following
    the link specified in the Location header.

    See @MigrationStatus resource.

    :param file_name: The name of the temp migrated vcl.
    :return:
    """
    js = json.dumps({"filename": file_name})
    resp = app.make_response((js, ACCEPTED))

    resp.headers['Location'] = '/task/' + file_name
    resp.headers['Content-Type'] = 'application/json'
    return resp


def migrate_3to4(input_file):
    """
    Dummy test implementation.
    TODO: Replace this with actual migration call.

    :param input_file:
    :return:
    """
    env = dict(os.environ)
    migrate_proc = subprocess.Popen(['sleep', '20'],
                                    cwd=cwd,
                                    env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
    running_procs[input_file] = migrate_proc
    log("Started migration process from 3 to 4 with pid: %d." % migrate_proc.pid)


def migrate_3to5(input_file):
    log("Dummy migration from 3 to 5.")


@app.before_request
def before_request():
    """
    Add a unique request id for each incoming
    request. Makes it a bit easier to debug.
    :return:
    """
    flask.g.reqid = str(uuid.uuid4().hex)


class VclMigrator3To4Resource(MethodView):

    def __init__(self):
        MethodView.__init__(self)

    @swagger.operation(**migrate_vcl_3_to_4)
    def post(self):
        """
        Migrate VCL from 3 to 4.

        :return:
        """
        try:
            input_file = save_input_vcl()
            log("Received %s for migration." % input_file)
            migrated_file_name = str(uuid.uuid4()) + "-" + input_file

            # do a copy of the vcl, to be removed
            # when actual migration is in place.
            shutil.copyfile(
                os.path.join(
                    cwd, input_file), os.path.join(
                    cwd, migrated_file_name))

            migrate_3to4(migrated_file_name)
            return create_migration_task_response(migrated_file_name)
        except ValueError as ve:
            log(ve.args[0], logging.ERROR, ve)
            return ve.args[0], BAD_REQUEST
        except Exception as ex:
            log(ex.args[0], logging.ERROR, ex)
            return ex.args[0], INTERNAL_SERVER_ERROR


class VclMigrator3To5Resource(MethodView):

    def __init__(self):
        MethodView.__init__(self)

    @swagger.operation(**migrate_vcl_3_to_5)
    def post(self):
        """
        Migrate VCL from 3 to 5.

        :return:
        """
        try:
            input_file = save_input_vcl()
            log("Received %s for migration." % input_file)
            migrated_file_name = str(uuid.uuid4()) + "-" + input_file

            migrate_3to5(input_file)
            return create_migration_task_response(migrated_file_name)
        except ValueError as ve:
            log(ve.args[0], logging.ERROR, ve)
            return ve.args[0], BAD_REQUEST
        except Exception as ex:
            log(ex.args[0], logging.ERROR, ex)
            return ex.args[0], INTERNAL_SERVER_ERROR


class MigrationStatus(MethodView):

    def __init__(self):
        MethodView.__init__(self)

    @swagger.operation(**migration_task_status)
    def get(self, file_name):
        """
        Check migration process status.

        :param file_name: The name of the migrating
        vcl file.
        :return:
        200 - Migration process is still running.
        303 - Migration has finished, a link to the migrated
              file is set on the Location header.
        410 - Migration task is no longer available.
        500 - Unexpected error occured while migrating the
              vcl file.
        """
        proc = running_procs.get(file_name)

        if proc:
            proc.poll()

            if proc.returncode is None:
                log("Migration still running for %s." % file_name)
                return "Still working.", OK
            elif proc.returncode != 0:
                log("Migration failed for %s with exit code %d." %
                    (file_name, proc.returncode))
                running_procs.pop(file_name)
                return "Something went wrong", INTERNAL_SERVER_ERROR
            else:
                log("Migration has successfully finished for %s." % file_name)
                running_procs.pop(file_name)
                js = json.dumps({"filename": file_name})
                resp = app.make_response((js, SEE_OTHER))

                resp.headers['Location'] = '/vcl/' + file_name
                resp.headers['Content-Type'] = 'application/json'
                return resp

        else:
            log("Migration is no longer available for %s." % file_name)
            return "Task no longer available", GONE


class GetMigratedVclResource(MethodView):

    def __init__(self):
        MethodView.__init__(self)

    @swagger.operation(**get_vcl)
    def get(self, file_name):
        """
        Get a migrated vcl.

        :param file_name:
        :return:
        """
        migrated_file = os.path.join(cwd, file_name)

        if os.access(migrated_file, os.R_OK):

            accept_header = request.headers.get("Accept")

            if accept_header:
                if accept_header.lower() == 'text/plain':
                    with open(migrated_file, 'r') as myfile:
                        migrated_content = myfile.read()
                        return migrated_content, OK

            return send_from_directory(directory=cwd,
                                       filename=file_name,
                                       as_attachment=True)

        return "Not found.", NOT_FOUND


api.add_resource(VclMigrator3To4Resource, '/3to4')
api.add_resource(VclMigrator3To5Resource, '/3to5')
api.add_resource(GetMigratedVclResource, '/vcl/<string:file_name>')
api.add_resource(MigrationStatus, '/task/<string:file_name>')

atexit.register(at_exit)


def start_server(port):
    log("Flask application has started.")
    log("Current working directory: %s" % cwd)
    app.run(host='0.0.0.0', port=port, threaded=True)


if __name__ == "__main__":
    start_server(8001)
