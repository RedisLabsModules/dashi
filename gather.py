import json
import os

import requests
import yaml
from flask_sqlalchemy import SQLAlchemy

from app import Pipeline, app, Commits, Job

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
    return response['items'][0]


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


def getGhRuns(repo: str):
    repo = repo.replace('github/', '')
    url = f"https://api.github.com/repos/{repo}/actions/runs"

    payload = {}
    headers = {
        'Authorization': os.getenv('GITHUB_TOKEN'),
        'Accept': 'application/vnd.github+json'
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    response_json = json.loads(response.text)
    for workflow in response_json['workflow_runs']:
        if (workflow['head_branch'], workflow['head_sha'], repo) in db_commits:
            new_pipeline = Pipeline()
            new_pipeline.pipelineId = workflow['id']
            new_pipeline.projectSlug = f"gh/{repo}"
            new_pipeline.branch = workflow['head_branch']
            new_pipeline.revision = workflow['head_sha']
            new_pipeline.workflowId = str(workflow['id'])
            new_pipeline.workflowName = workflow['name']
            new_pipeline.status = workflow['conclusion']
            new_pipeline.message = workflow['head_commit']['message']
            if workflow['id'] not in pipeline_ids and workflow['conclusion'] in allowed_statuses:
                db.session.add(new_pipeline)
                db.session.commit()
            new_job = Job()
            new_job.name = workflow['name']
            new_job.status = workflow['conclusion']
            new_job.workflowId = workflow['id']
            if not bool(db.session.query(Job).filter(
                    Job.workflowId == str(workflow['id'], Job.name == workflow['name'])).first()):
                db.session.add(new_job)
                db.session.commit()


def checkPipeline(pipeline4check: dict, job4check: dict) -> bool:
    if pipeline4check['number'] not in pipeline_ids and job4check['status'] in allowed_statuses:
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
    db.session.add(new_pipeline)
    db.session.commit()


def pushJobsToDB(jobs_list: list, jobWorkflow: dict):
    for job in jobs_list:
        if job['status'] != 'running':
            new_job = Job()
            new_job.name = job['name']
            new_job.status = job['status']
            new_job.workflowId = jobWorkflow['id']
            if not bool(db.session.query(Job).filter(Job.workflowId == str(jobWorkflow['id'])).first()):
                db.session.add(new_job)
                db.session.commit()


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
        for branch in project['branches']:
            getCommits(slug_name, branch)
        cleanupCommits(slug_name, project['branches'])
        # if project is GitHub
        if len([x for x in project['tests'] if 'githubactions' in x]) != 0:
            getGhRuns(slug_name)
        if len([x for x in project['tests'] if 'circleci' in x]) != 0:
            pipeline_list = circleCiGetPipelineId(slug_name)
            for pipeline in pipeline_list:
                workflow = circleCiGetWorkflowInfo(pipeline['id'])
                if checkPipeline(pipeline, workflow):
                    branch = circleCiBranchName(pipeline['vcs'])
                    pushPipelineToDB(pipeline, workflow, branch)
                    jobs = circleCiGetJobs(workflow['id'])
                    pushJobsToDB(jobs, workflow)
