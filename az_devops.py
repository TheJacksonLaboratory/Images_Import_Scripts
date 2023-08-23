import requests
import os
import json
import urllib
import read_config as cfg
import argparse
from base64 import b64encode

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


# Authorization token: we need to base 64 encode it
# and then decode it to acsii as python 3 stores it as a byte string
def basic_auth():
    token = b64encode(f"{username}:{access_token}".encode('utf-8')).decode("ascii")
    return f'Basic {token}'


def get_work_item(personal_access_token):
    """
    Get a list of work items assigned to a person via REST services provided by Microsoft
    :param str personal_access_token: Access token of you, for more info, see https://learn.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate?view=azure-devops&tabs=Windows
    """
    authorization = requests.get('https://dev.azure.com', headers={'Authorization': personal_access_token})
    assert authorization.status_code == 200

    try:
        url = "https://dev.azure.com/jacksonlaboratory/teams/_apis/wit/workitems/152715?api-version=7.0"

        payload = {}
        headers = {'Authorization': basic_auth()}
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
    """
    Function to create a new work item on Azure DevOps board via RESTful API.
    """

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
    headers = {'Authorization': basic_auth()}
    response = requests.request("POST", url, headers=headers, data=payload)

    assert response.status_code == 200


