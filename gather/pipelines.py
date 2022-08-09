import json
import os
import requests
import yaml
from flask_sqlalchemy import SQLAlchemy
from app import Pipeline, app, Commits, Job

db = SQLAlchemy(app)
allowed_statuses = ['success', 'failed']
pipeline_ids = [x[0] for x in db.session.query(Pipeline.pipelineId).all()]
repos = {}


def circleCiGetPipelineId(slug: str, pipeline_branch: str) -> list:
    url = f"https://circleci.com/api/v2/project/{slug}/pipeline?branch={pipeline_branch}"
    headers = {
        'Circle-Token': os.getenv('CIRCLE_CI_TOKEN'),
    }

    response = requests.request("GET", url, headers=headers)
    if response.status_code != 200:
        return []
    response = json.loads(response.text)
    return response['items']


def circleCiGetWorkflowInfo(workflow_id: str) -> dict:
    url = f"https://circleci.com/api/v2/pipeline/{workflow_id}/workflow"
    headers = {
        'Circle-Token': os.getenv('CIRCLE_CI_TOKEN'),
    }

    response = requests.request("GET", url, headers=headers)
    response_json = json.loads(response.text)
    if len(response_json['items']) != 0:
        return response_json['items'][0]
    return []


def circleCiGetJobs(workflow_id):
    url = f"https://circleci.com/api/v2/workflow/{workflow_id}/job"
    headers = {
        'Circle-Token': os.getenv('CIRCLE_CI_TOKEN'),
    }

    response = requests.request("GET", url, headers=headers)
    if response.status_code == 404:
        return []
    response_json = json.loads(response.text)
    return response_json['items']


def circleCiBranchName(vcs: dict) -> str:
    if 'branch' in vcs:
        return vcs['branch']
    if 'tag' in vcs:
        return vcs['tag']


def checkPipeline(pipeline4check: dict, job4check: dict) -> bool:
    if len(job4check) == 0:
        return False
    if pipeline4check['number'] not in pipeline_ids and \
            job4check['status'] in allowed_statuses:
        return True
    return False


def pushPipelineToDB(pipeline4commit: dict, job4commit: dict, branch_name: str):
    new_pipeline = Pipeline()
    new_pipeline.pipelineId = pipeline4commit['number']
    new_pipeline.projectSlug = pipeline4commit['project_slug']
    new_pipeline.branch = branch_name
    new_pipeline.revision = pipeline4commit['vcs']['revision']
    new_pipeline.workflowId = job4commit['id']
    new_pipeline.workflowName = job4commit['name']
    new_pipeline.status = job4commit['status']
    if 'commit' in pipeline4commit['vcs']:
        new_pipeline.message = pipeline4commit['vcs']['commit']['subject']
    commits = db.session.query(Commits.id).filter(Commits.commit == pipeline4commit['vcs']['revision'], Commits.projectSlug == pipeline4commit['project_slug'].replace('gh/', '')).all()
    if len(commits) != 0:
        new_pipeline.commitId = commits[0][0]
        db.session.add(new_pipeline)
        db.session.commit()


if __name__ == "__main__":
    print("Start collecting pipelines and jobs info")
    with open("main.yaml", "r") as stream:
        try:
            yaml_object = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit(2)
        repos = yaml_object['repos']
        for project in yaml_object['repos']:
            project = yaml_object['repos'][project]
            project['branches'] = [str(x) for x in project['branches']]
            slug_name = project['github']
            slug_name = slug_name.replace('.com', '')
            if len([x for x in project['tests'] if 'circleci' in x]) != 0:
                for branch in project['branches']:
                    print(f"Get pipelines for {slug_name}: {branch}")
                    pipeline_list = circleCiGetPipelineId(slug_name, branch)
                    for pipeline in pipeline_list:
                        branch = circleCiBranchName(pipeline['vcs'])
                        print(f"Get workflows for {slug_name}: {branch}: {pipeline['id']}")
                        workflow = circleCiGetWorkflowInfo(pipeline['id'])
                        if checkPipeline(pipeline, workflow):
                            pushPipelineToDB(pipeline, workflow, branch)
