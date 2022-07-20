import json
import os
import requests as requests
import yaml
from flask import Flask, jsonify, render_template, request
import http.client
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, and_

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL'].replace('postgres:', 'postgresql:')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)


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


@app.route("/")
def indexPage():
    subq = db.session.query(
        Pipeline.projectSlug,
        func.max(Pipeline.pipelineId).label('maxpipelineid')
    ).group_by(Pipeline.projectSlug).subquery('t2')

    query = db.session.query(Pipeline, Workflow).join(
        subq,
        db.and_(
            Pipeline.projectSlug == subq.c.projectSlug,
            Pipeline.pipelineId == subq.c.maxpipelineid
        )
    ).join(Workflow, Pipeline.pipelineId == Workflow.pipelineId).all()

    return render_template('index.html', pipelines=query)


@app.route("/commits")
def branchPage():
    pipeline_id = request.args.get('pipeline_id', type=str)

    workflows = db.session.query(Workflow, Pipeline).join(Workflow, Pipeline.pipelineId == Workflow.pipelineId).filter_by(pipelineId=pipeline_id).all()

    return render_template('commits.html', branch_info=workflows)


if __name__ == '__main__':
    app.run()
