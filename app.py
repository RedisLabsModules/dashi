import os

import yaml
from flask import Flask, jsonify, render_template, request
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, and_

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL'].replace('postgres:', 'postgresql:')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Commits(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    projectSlug = db.Column(db.String, index=True)
    branch = db.Column(db.String, index=True)
    commit = db.Column(db.String, unique=False, index=True)
    message = db.Column(db.String, unique=False, index=False)


class Pipeline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    projectSlug = db.Column(db.String, index=True)
    pipelineId = db.Column(db.Integer, unique=True, index=True)
    branch = db.Column(db.String, index=True)
    workflowId = db.Column(db.String, unique=True, index=True)
    status = db.Column(db.String)
    workflowName = db.Column(db.String)
    revision = db.Column(db.String)
    message = db.Column(db.String)


def getBranchStatus(project_name: str, branch_name: str) -> bool:
    status = False
    subq = db.session.query(
        Pipeline.projectSlug,
        func.max(Pipeline.pipelineId).label('maxpipelineid')
    ).group_by(Pipeline.projectSlug).subquery('t2')

    query = db.session.query(Pipeline).join(
        subq,
        db.and_(
            Pipeline.projectSlug == subq.c.projectSlug,
            Pipeline.pipelineId == subq.c.maxpipelineid
        )
    ).all()
    if len(query) != 0:
        if query[0][1] == 'success':
            status = True
    return status


@app.route("/")
def indexPage():
    with open("main.yaml", "r") as stream:
        try:
            yaml_object = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit(2)
        repos = yaml_object['repos']
        for project in repos:
            project_obj = repos[project]
            project_obj['branches'] = [str(x) for x in project_obj['branches']]
            statuses = db.session.query(
                Pipeline.branch,
                Pipeline.status
            ).filter(
                Pipeline.branch.in_(project_obj['branches']),
                Pipeline.projectSlug == project_obj['github'].replace('github.com', 'gh')
            ).all()
            project_obj['statuses'] = {x[0]: x[1] for x in statuses}
            repos[project] = project_obj
        return render_template('index.html', projects=repos)


@app.route("/commits")
def branchPage():
    project = request.args.get('project', type=str)
    branch = request.args.get('branch', type=str)
    query = db.session.query(
        Commits,
        Pipeline,
    ).filter(
        Commits.branch == branch,
        Commits.projectSlug == f"{project}/{project}",
        Pipeline.branch == branch,
        Pipeline.revision == Commits.commit
    ).order_by(Commits.id.desc()).all()
    return render_template('commits.html', branch_info=query, repo=project, branch=branch)


if __name__ == '__main__':
    app.run()
