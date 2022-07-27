import json
import os

import requests
import yaml
from flask_sqlalchemy import SQLAlchemy

from app import Pipeline, app, Commits

db = SQLAlchemy(app)
allowed_statuses = ['success', 'failed']
pipeline_ids = [x[0] for x in db.session.query(Pipeline.pipelineId).all()]
db_commits = db.session.query(Commits.branch, Commits.commit, Commits.projectSlug).all()
repos = {}


def getCommits(repo: str, gh_branch: str):
    repo = repo.replace('github/', '')
    url = f"https://api.github.com/repos/{repo}/commits?sha={gh_branch}"

    payload = {}
    headers = {
        'Authorization': os.getenv('GITHUB_TOKEN'),
        'Accept': 'application/vnd.github+json'
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    response_json = json.loads(response.text)
    for commit in response_json:
        print(commit['sha'], commit['commit']['message'])
        if (str(gh_branch), commit['sha'], repo) not in db_commits:
            new_commit = Commits()
            new_commit.branch = gh_branch
            new_commit.projectSlug = repo
            new_commit.commit = commit['sha']
            new_commit.message = commit['commit']['message']
            db.session.add(new_commit)
            db.session.commit()


def cleanupCommits(project_name: str, branches: list):
    branches = [str(x) for x in branches]
    commits_for_project = db.session.query(Commits).filter(Commits.projectSlug == project_name).all()
    for commit in commits_for_project:
        if commit.branch not in branches:
            db.session.delete(commit)
            db.session.commit()


def circleCiGetPipelineId(slug: str) -> list:
    url = f"https://circleci.com/api/v2/project/{slug}/pipeline"
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
    response = json.loads(response.text)
    if len(response['items']) > 1:
        print(response, len(response['items']))
    else:
        print(response)
    return response['items'][0]


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
        print(slug_name)
        for branch in project['branches']:
            getCommits(slug_name, branch)
        cleanupCommits(slug_name, project['branches'])
        pipeline_list = circleCiGetPipelineId(slug_name)
        for pipeline in pipeline_list:
            job = circleCiGetWorkflowInfo(pipeline['id'])
            if 'branch' in pipeline['vcs'] and \
                    pipeline['vcs']['branch'] in project['branches']:
                new_pipeline = Pipeline()
                new_pipeline.pipelineId = pipeline['number']
                new_pipeline.projectSlug = pipeline['project_slug']
                new_pipeline.branch = pipeline['vcs']['branch']
                new_pipeline.revision = pipeline['vcs']['revision']
                new_pipeline.workflowId = job['id']
                new_pipeline.workflowName = job['name']
                new_pipeline.status = job['status']
                if 'commit' in pipeline['vcs']:
                    new_pipeline.message = pipeline['vcs']['commit']['subject']
                if pipeline['number'] not in pipeline_ids and job['status'] in allowed_statuses:
                    db.session.add(new_pipeline)
                    db.session.commit()
