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
        if (str(gh_branch), commit['sha'], repo) not in db_commits:
            new_commit = Commits()
            new_commit.branch = gh_branch
            new_commit.projectSlug = repo
            new_commit.commit = commit['sha']
            new_commit.message = commit['commit']['message'].split("\n\n")[0]
            db.session.add(new_commit)
            db.session.commit()


def cleanupCommits(project_name: str, branches: list):
    commits_for_project = db.session.query(Commits).filter(Commits.projectSlug == project_name).all()
    for commit in commits_for_project:
        if commit.branch not in branches:
            db.session.delete(commit)
            db.session.commit()


if __name__ == "__main__":
    print("Start collecting commits info")
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
                print(f"Get commits for {slug_name}")
                getCommits(slug_name, branch)
            print("Cleanup old commits")
            cleanupCommits(slug_name, project['branches'])
