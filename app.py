import os
from hashlib import md5

import yaml
from flask import Flask, render_template, request, jsonify
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, func

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL'].replace('postgres:', 'postgresql:')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TOKEN_SALT'] = os.environ.get('TOKEN_SALT')
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Commits(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    projectSlug = db.Column(db.String, index=True)
    branch = db.Column(db.String, index=True)
    commit = db.Column(db.String, unique=False, index=True)
    message = db.Column(db.String, unique=False, index=False)
    date = db.Column(db.TIMESTAMP, unique=False, index=True)


class Pipeline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    projectSlug = db.Column(db.String, index=True)
    pipelineId = db.Column(db.BigInteger, unique=False, index=True)
    branch = db.Column(db.String, index=True)
    workflowId = db.Column(db.String, unique=True, index=True)
    status = db.Column(db.String)
    workflowName = db.Column(db.String)
    revision = db.Column(db.String)
    message = db.Column(db.String)
    commitId = db.Column(db.Integer, ForeignKey("commits.id"))


@app.route("/")
def indexPage():
    with open("main.yaml", "r") as stream:
        try:
            yaml_object = yaml.load(stream, Loader=yaml.BaseLoader)
        except yaml.YAMLError as exc:
            print(exc)
            exit(2)
        repos = yaml_object['repos']
        for project in repos:
            project_obj = repos[project]
            project_obj['branches'] = [str(x) for x in project_obj['branches']]
            project_obj['statuses'] = {}
            for branch in project_obj['branches']:
                status = db.session.query(
                    Pipeline.status
                ).filter(
                    Pipeline.branch == str(branch),
                    Pipeline.projectSlug == project_obj['github'].replace('github.com', 'gh')
                ).order_by(Pipeline.pipelineId.desc()).first()
                if status is not None:
                    project_obj['statuses'][branch] = status[0]
            repos[project] = project_obj
        return render_template('index.html', projects=repos)


@app.route("/commits")
def commitsPage():
    project = request.args.get('project', type=str)
    project = project.replace('github.com/', '')
    branch = request.args.get('branch', type=str)
    query = db.session.query(Commits, Pipeline).join(Pipeline, Pipeline.revision == Commits.commit).filter(
        Commits.projectSlug == project,
        Commits.branch == branch,
    ).order_by(Commits.date.desc()).all()
    project = project.split('/')[-1]
    out = {}
    for commit, pipeline in query:
        if pipeline.revision not in out:
            out[pipeline.revision] = [pipeline, commit]
        if pipeline.status != 'success':
            out[pipeline.revision][0].status = pipeline.status
    return render_template('commits.html', branch_info=out, repo=project, branch=branch)


@app.route('/workflows')
def viewJobs():
    project = request.args.get('project', type=str)
    branch = request.args.get('branch', type=str)
    commit = request.args.get('commit', type=str)
    workflow_pipelines_ids = []
    for workflow in db.session.query(Pipeline.workflowName).filter(
            Pipeline.revision == commit,
            Pipeline.projectSlug == f"gh/{project}",
    ).distinct(Pipeline.workflowName).all():
        id = db.session.query(Pipeline).filter(
            Pipeline.revision == commit,
            Pipeline.projectSlug == f"gh/{project}",
            Pipeline.workflowName == workflow[0]
        ).order_by(Pipeline.pipelineId.desc()).first()
        workflow_pipelines_ids += [id.pipelineId]
    pipelines = db.session.query(
        Pipeline
    ).filter(
        Pipeline.revision == commit,
        Pipeline.projectSlug == f"gh/{project}",
        Pipeline.pipelineId.in_(workflow_pipelines_ids),
    ).order_by(Pipeline.pipelineId.desc()).all()
    return render_template('workflows.html', repo=project.split('/')[-1], branch=branch, commit=commit[:7],
                           pipelines=pipelines)


@app.route('/callback')
def callbackFunc():
    if request.headers.get('X-Token') is not None:
        hashes = []
        with open("main.yaml", "r") as stream:
            try:
                yaml_object = yaml.load(stream, Loader=yaml.BaseLoader)
            except yaml.YAMLError as exc:
                print(exc)
                exit(2)
            repos = yaml_object['repos']
            for project in repos:
                project_obj = repos[project]
                if project_obj.get('scripts') is not None and project_obj.get('scripts'):
                    project_name = project.split('/')[-1]
                    for branch in project_obj['branches']:
                        tmp_hash = md5(f"{project_name}-{branch}-{app.config['TOKEN_SALT']}".encode('utf-8')).hexdigest()
                        hashes.append(tmp_hash)
        return jsonify({'tokens': hashes})
    return jsonify({'code': 'Unauthorized request'}), 401


if __name__ == '__main__':
    app.run()
