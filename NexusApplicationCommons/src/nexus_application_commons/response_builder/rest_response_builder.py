import json

"""
Helper method to create a JSON serializable REST style response.
"""


def create_response(status_code, json_body):
    response = {
        "statusCode": status_code,
        "body": json.dumps(json_body),
        "headers": {"Content-Type": "application/json"},
    }
    return json.dumps(response)
