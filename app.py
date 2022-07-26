import os
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
    revision = db.Column(db.String)
    message = db.Column(db.String)


class Workflow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workflowId = db.Column(db.String, unique=True, index=True)
    pipelineId = db.Column(db.Integer, db.ForeignKey('pipeline.pipelineId'))
    status = db.Column(db.String)
    name = db.Column(db.String)


def getBranchStatus(project_name: str, branch_name: str) -> bool:
    status = False
    subq = db.session.query(
        Pipeline.projectSlug,
        func.max(Pipeline.pipelineId).label('maxpipelineid')
    ).filter(Pipeline.branch == branch_name, Pipeline.projectSlug == f"gh/{project_name}").group_by(Pipeline.projectSlug).subquery('t2')

    query = db.session.query(Pipeline, Workflow.status).join(
        subq,
        db.and_(
            Pipeline.projectSlug == subq.c.projectSlug,
            Pipeline.pipelineId == subq.c.maxpipelineid
        )
    ).filter(
        Pipeline.projectSlug == f"gh/{project_name}",
    ).join(
        Workflow,
        Pipeline.pipelineId == Workflow.pipelineId
    ).all()
    if len(query) != 0:
        if query[0][1] == 'success':
            status = True
    return status


@app.route("/")
def indexPage():
    repo_info = db.session.query(Commits).all()
    project_branches = {}
    for item in repo_info:
        branch_status = getBranchStatus(item.projectSlug, item.branch)
        if item.projectSlug not in project_branches:
            project_branches[item.projectSlug] = [{
                'branch': item.branch,
                'status': branch_status
            }]
        if {'branch': item.branch, 'status': branch_status} not in project_branches[item.projectSlug]:
            project_branches[item.projectSlug] += [{
                'branch': item.branch,
                'status': branch_status
            }]

    return render_template('index.html', projects=project_branches)


@app.route("/commits")
def branchPage():
    project = request.args.get('project', type=str)
    subq = db.session.query(
        Pipeline.projectSlug,
        func.max(Pipeline.pipelineId).label('maxpipelineid'),
        Pipeline.revision,
    ).filter(Pipeline.projectSlug == project).group_by(Pipeline.projectSlug, Pipeline.revision).subquery('t2')

    query = db.session.query(Pipeline, Workflow).join(
        subq,
        db.and_(
            Pipeline.projectSlug == subq.c.projectSlug,
            Pipeline.pipelineId == subq.c.maxpipelineid,
            Pipeline.revision == subq.c.revision,
        )
    ).join(Workflow, Pipeline.pipelineId == Workflow.pipelineId).order_by(Workflow.id.desc()).all()

    return render_template('commits.html', branch_info=query)


if __name__ == '__main__':
    app.run()
