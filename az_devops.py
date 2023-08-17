import requests
import os
import json
import urllib
import read_config as cfg
import argparse

parser = argparse.ArgumentParser(description='My awesome script')
parser.add_argument(
    "-c", "--conf", action="store", dest="conf_file",
    help="Path to config file"
)

args = parser.parse_args()
cfg = cfg.parse_config(path="config.yml")

access_token = cfg['azure']['access token']
username = cfg['azure']['email']
team = cfg['azure']['team']


def get_work_item(personal_access_token):
    authorization = requests.get('https://dev.azure.com', headers={'Authorization': personal_access_token})
    assert authorization.status_code == 200

    try:
        url = "https://dev.azure.com/jacksonlaboratory/teams/_apis/wit/workitems/152715?api-version=7.0"

        payload = {}
        headers = {
            'Authorization': 'Basic Y2hlbnQ6b2FrdzU3NzRoZ3JjNXpmem1vdHd6eDNyeWV0dHdxdndvZnRwZnF4d2Fud2hiMmJzdzR2YQ==',
            'Cookie': 'VstsSession=%7B%22PersistentSessionId%22%3A%2294312618-a858-49a7-bb56-cee3572d3af3%22%2C'
                      '%22PendingAuthenticationSessionId%22%3A%2200000000-0000-0000-0000-000000000000%22%2C'
                      '%22CurrentAuthenticationSessionId%22%3A%2200000000-0000-0000-0000-000000000000%22%2C'
                      '%22SignInState%22%3A%7B%7D%7D; X-VSS-UseRequestRouting=True'
        }

        response = requests.request("GET", url, headers=headers, data=payload)
        print(response.json())

    except Exception as e:
        print(e)


def create_work_item(personal_access_token,
                     type,
                     title,
                     state,
                     comment,
                     assign_to,
                     team):
    authorization = requests.get('https://dev.azure.com', headers={'Authorization': personal_access_token})
    assert authorization.status_code == 200

    url = f"https://dev.azure.com/jacksonlaboratory/teams/_apis/wit/workitems/${type}?api-version=7.0"
    print(url)
    payload = json.dumps([
        {
            "op": "add",
            "path": "/fields/System.Title",
            "from": None,
            "value": title
        },
        {
            "op": "add",
            "path": "/fields/System.State",
            "from": None,
            "value": state
        },
        {
            "op": "add",
            "path": "/fields/System.History",
            "from": None,
            "value": comment
        },
        {
            "op": "add",
            "path": "/fields/System.AssignedTo",
            "from": None,
            "value": assign_to
        },
        {
            "op": "add",
            "path": "/fields/System.AreaPath",
            "from": None,
            "value": team
        }
    ])
    headers = {
        'Content-Type': 'application/json-patch+json',
        'Authorization': 'Basic Om9ha3c1Nzc0aGdyYzV6Znptb3R3engzcnlldHR3cXZ3b2Z0cGZxeHdhbndoYjJic3c0dmE=',
        'Cookie': 'VstsSession=%7B%22PersistentSessionId%22%3A%2294312618-a858-49a7-bb56-cee3572d3af3%22%2C'
                  '%22PendingAuthenticationSessionId%22%3A%2200000000-0000-0000-0000-000000000000%22%2C'
                  '%22CurrentAuthenticationSessionId%22%3A%2200000000-0000-0000-0000-000000000000%22%2C%22SignInState'
                  '%22%3A%7B%7D%7D'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    assert response.status_code == 200



