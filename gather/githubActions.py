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


def getGhRuns(repo: str):
    repo = repo.replace('github/', '')
    url = f"https://api.github.com/repos/{repo}/actions/runs"

    payload = {}
    headers = {
        'Authorization': os.getenv('GH_TOKEN'),
        'Accept': 'application/vnd.github+json'
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    response_json = json.loads(response.text)
    if response.status_code != 200:
        print(f"Got not 200 response for repo: {repo}")
        print(f"Response code: {response.status_code} with body: {response.text}")
        return
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


if __name__ == "__main__":
    print("Start collecting pipelines and jobs info")
    with open("main.yaml", "r") as stream:
        try:
            yaml_object = yaml.load(stream, Loader=yaml.BaseLoader)
        except yaml.YAMLError as exc:
            print(exc)
            exit(2)
        repos = yaml_object['repos']
        for project in yaml_object['repos']:
            project = yaml_object['repos'][project]
            slug_name = project['github']
            slug_name = slug_name.replace('.com', '')
            slug_name = slug_name.replace('https://', '')
            if len([x for x in project['tests'] if 'githubactions' in x]) != 0:
                print(f"Get github actions for {slug_name}")
                getGhRuns(slug_name)
