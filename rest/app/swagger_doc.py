from flask_restful import fields
from flask_restful_swagger import swagger


@swagger.model
class VclFile:
    resource_fields = {
        'filename': fields.String,
    }


code_400_message = {
    "code": 400,
    "message": "Invalid input."
}

code_401_message = {
    "code": 401,
    "message": "Unauthorized or invalid token."
}

code_500_message = {
    "code": 500,
    "message": "Internal server error."
}

code_404_message = {
    "code": 404,
    "message": "VCL not found."
}

code_202_message = {
    "code": 202,
    "message": "Migration request has been accepted."
}

code_303_message = {
    "code": 303,
    "message": "Migration has finished, check Location header for retrieving the migrated file."
}

code_410_message = {
    "code": 410,
    "message": "Migration task is no longer available. The requested file has already been migrated."
}


migrate_vcl_3_to_4 = {
    'notes': "Migrates input VCL from 3 to 4 in terms of Varnish versions.",
    'responseClass': VclFile.__name__,
    'nickname': 'migrate vcl',
    'parameters': [
        {
            "name": "file",
            "description": "The vcl structure to be migrated. ",
            "required": True,
            "allowMultiple": False,
            "type": "file",
            "paramType": "formData"
        },
    ],
    'responseMessages': [
        code_202_message,
        code_400_message,
        code_500_message
    ]}

migrate_vcl_3_to_5 = {
    'notes': "Migrates input VCL from 3 to 5 in terms of Varnish versions.",
    'responseClass': VclFile.__name__,
    'nickname': 'migrate vcl',
    'parameters': [
        {
            "name": "file",
            "description": "The vcl structure to be migrated. ",
            "required": True,
            "allowMultiple": False,
            "type": "file",
            "paramType": "formData"
        },
    ],
    'responseMessages': [
        code_202_message,
        code_400_message,
        code_500_message
    ]}

get_vcl = {
    'notes': "Returns the content of the migrated vcl.",
    'parameters': [
        {
            "name": "Accept",
            "description": "Determines in what format is the migrated vcl returned.",
            "required": False,
            "allowMultiple": False,
            "dataType": 'string',
            "paramType": "header"
        },
        {
            "name": "file_name",
            "description": "The vcl structure which has been migrated. ",
            "required": True,
            "allowMultiple": False,
            "type": "string",
            "paramType": "path"
        },
    ],
    'responseMessages': [
        {
            "code": 200,
            "message": "Content the migrated vcl."
        },
        code_404_message,
        code_500_message
    ]
}

migration_task_status = {
    'notes': "Returns the status of a migration task. If done, a "
             "link to the migrated file is set on the Location header.",
    'parameters': [
        {
            "name": "file_name",
            "description": "The vcl name which is currently being migrated.",
            "required": True,
            "allowMultiple": False,
            "type": "string",
            "paramType": "path"
        },
    ],
    'responseMessages': [
        {
            "code": 200,
            "message": "The vcl migration is still in process."
        },
        code_303_message,
        code_410_message,
        code_500_message
    ]
}
