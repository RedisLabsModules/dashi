import json
import os

import requests
import yaml
from app import Pipeline, Workflow


pipelines = Pipeline.query.all()
print(pipelines)
repos = {}


def getPipelineId(slug: str) -> list:
    pipelines_out = []
    url = f"https://circleci.com/api/v2/project/{slug}/pipeline"
    headers = {
        'Circle-Token': os.getenv('CIRCLE_CI_TOKEN'),
    }

    response = requests.request("GET", url, headers=headers)
    response = json.loads(response.text)
    slug = slug[slug.rfind('/')+1:]
    for workflow in response['items']:
        if workflow['vcs']['branch'] in repos[slug]['branches']:
            pipelines_out += [workflow]
    return pipelines_out


def getWorkflowInfo(workflow_id: str) -> list:
    workflow_out = []
    url = f"https://circleci.com/api/v2/pipeline/{workflow_id}/workflow"
    headers = {
        'Circle-Token': os.getenv('CIRCLE_CI_TOKEN'),
    }

    response = requests.request("GET", url, headers=headers)
    response = json.loads(response.text)
    print(response)
    return workflow_out


with open("main.yaml", "r") as stream:
    try:
        yaml_object = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        exit(2)
    repos = yaml_object['repos']
    for project in yaml_object['repos']:
        project = yaml_object['repos'][project]
        slug_name = project['github']
        slug_name = slug_name.replace('.com', '')
        print(slug_name)
        pipeline_list = getPipelineId(slug_name)
        for pipeline in pipeline_list:
            jobs = getWorkflowInfo(pipeline['id'])
