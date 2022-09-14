import os
import yaml
from flask import Flask, render_template, request
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, func

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
                last_pipeline_commit = db.session.query(
                    Pipeline.revision
                ).filter(
                    Pipeline.branch == str(branch),
                    Pipeline.projectSlug == project_obj['github'].replace('github.com', 'gh')
                ).order_by(Pipeline.pipelineId.desc()).first()
                if last_pipeline_commit is not None and len(last_pipeline_commit) != 0:
                    workflows = db.session.query(
                        Pipeline.status,
                        Pipeline.workflowName
                    ).filter(
                        Pipeline.revision == last_pipeline_commit[0],
                    ).order_by(Pipeline.pipelineId.desc()).all()
                    tmp_statuses = {}
                    for workflow_status in workflows:
                        if workflow_status[1] not in tmp_statuses:
                            tmp_statuses[workflow_status[1]] = workflow_status[0]
                    if 'failed' in tmp_statuses.values():
                        fail_count = 1
                    else:
                        fail_count = 0
                else:
                    fail_count = 1
                if fail_count != 0 and not None:
                    project_obj['statuses'][branch] = 'failed'
                else:
                    project_obj['statuses'][branch] = 'success'
            repos[project] = project_obj
        return render_template('index.html', projects=repos)


@app.route("/commits")
def commitsPage():
    project = request.args.get('project', type=str)
    project = project.replace('github.com/', '')
    branch = request.args.get('branch', type=str)
    out = {}

    subq = db.session.query(
        Pipeline.projectSlug,
        func.max(Pipeline.pipelineId).label('maxpipelineid'),
        Pipeline.revision,
        Pipeline.workflowName,
    ).filter(
        Pipeline.projectSlug == f"gh/{project}",
        Pipeline.branch == branch,
    ).group_by(Pipeline.projectSlug, Pipeline.revision, Pipeline.workflowName).subquery('t2')

    query = db.session.query(Commits, Pipeline).join(
        subq,
        db.and_(
            Pipeline.projectSlug == subq.c.projectSlug,
            Pipeline.pipelineId == subq.c.maxpipelineid,
            Pipeline.revision == subq.c.revision,
        )
    ).join(
        Commits,
        Pipeline.revision == Commits.commit
    ).filter(
        Commits.projectSlug == project,
        Commits.branch == branch,
    ).order_by(
        Commits.date.desc()
    )
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


if __name__ == '__main__':
    app.run()
