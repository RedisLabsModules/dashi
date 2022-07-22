import json
import os

import requests
import yaml
from flask_sqlalchemy import SQLAlchemy

from app import Pipeline, Workflow, app

db = SQLAlchemy(app)
pipeline_ids = [x[0] for x in db.session.query(Pipeline.pipelineId).all()]
workflow_ids = [x[0] for x in db.session.query(Workflow.workflowId).all()]
repos = {}


def circleCiGetPipelineId(slug: str) -> list:
    pipelines_out = []
    url = f"https://circleci.com/api/v2/project/{slug}/pipeline"
    headers = {
        'Circle-Token': os.getenv('CIRCLE_CI_TOKEN'),
    }

    response = requests.request("GET", url, headers=headers)
    if response.status_code != 200:
        return []
    response = json.loads(response.text)
    slug = slug[slug.rfind('/')+1:]
    for pipeline_item in response['items']:
        if 'branch' in pipeline_item['vcs'] and \
                pipeline_item['vcs']['branch'] in repos[slug]['branches']:
            pipelines_out += [pipeline_item]
            new_pipeline = Pipeline()
            new_pipeline.pipelineId = pipeline_item['number']
            new_pipeline.projectSlug = pipeline_item['project_slug']
            new_pipeline.branch = pipeline_item['vcs']['branch']
            new_pipeline.revision = pipeline_item['vcs']['revision']
            if 'commit' in pipeline_item['vcs']:
                new_pipeline.message = pipeline_item['vcs']['commit']['subject']
            if pipeline_item['number'] not in pipeline_ids:
                db.session.add(new_pipeline)
                db.session.commit()
    return pipelines_out


def circleCiGetWorkflowInfo(workflow_id: str) -> list:
    workflow_out = []
    url = f"https://circleci.com/api/v2/pipeline/{workflow_id}/workflow"
    headers = {
        'Circle-Token': os.getenv('CIRCLE_CI_TOKEN'),
    }

    response = requests.request("GET", url, headers=headers)
    response = json.loads(response.text)
    if len(response['items']) > 1:
        print(response, len(response['items']))
    else:
        print(response)
    response = response['items'][0]
    if response['id'] not in workflow_ids and response['status'] != 'running':
        new_workflow = Workflow()
        new_workflow.workflowId = response['id']
        new_workflow.pipelineId = int(response['pipeline_number'])
        new_workflow.name = response['name']
        new_workflow.status = response['status']
        db.session.add(new_workflow)
        db.session.commit()
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
        pipeline_list = circleCiGetPipelineId(slug_name)
        for pipeline in pipeline_list:
            jobs = circleCiGetWorkflowInfo(pipeline['id'])
