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
    projectSlug = db.Column(db.String)
    pipelineId = db.Column(db.Integer, unique=True)
    branch = db.Column(db.String)
    revision = db.Column(db.String)


class Workflow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workflowId = db.Column(db.String, unique=True)
    pipelineId = db.Column(db.Integer, db.ForeignKey('pipeline.pipelineId'))
    status = db.Column(db.String)
    name = db.Column(db.String)


@app.route("/hello-world")
def hello_world():
    conn = http.client.HTTPSConnection("circleci.com")

    headers = {'Circle-Token': os.getenv('CIRCLE_CI_TOKEN')}

    conn.request("GET",
                 "/api/v2/pipeline?org-slug=github/RedisJSON",
                 headers=headers)

    res = conn.getresponse()
    data = res.read()
    data_object = json.loads(data.decode("utf-8"))
    out = []
    for pipeline in data_object['items']:
        conn.request("GET",
                     f"/api/v2/pipeline/{pipeline['id']}/workflow",
                     headers=headers)

        res = conn.getresponse()
        data = res.read()
        pipeline_data = json.loads(data.decode("utf-8"))
        if len(pipeline_data['items']) > 1:
            print(pipeline_data)
        out += [{
            'branch': pipeline['vcs']['branch'],
            'commit': pipeline['vcs']['revision'],
            'status': pipeline_data['items'][0]['status'],
        }]
    return render_template('index.html', workflows=out)


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
    repository = request.args.get('repository', type=str)
    branch = request.args.get('branch', type=str)

    branch_info = {}
    headers = {
        'Circle-Token': os.getenv('CIRCLE_CI_TOKEN'),
    }
    url = f"https://circleci.com/api/v2/pipeline?org-slug={repository}"
    request_repo = requests.request("GET", url, headers=headers)
    request_repo_dict = json.loads(request_repo.text)
    for item in request_repo_dict['items']:
        if item['vcs']['branch'] == branch and 'commit' in item['vcs']:
            url = f"https://circleci.com/api/v2/pipeline/{item['id']}/workflow"

            response = requests.request("GET", url, headers=headers)
            response_dict = json.loads(response.text)
            branch_info[item['vcs']['revision'][:7]] = {
                'status': "success",
                'message': item['vcs']['commit']['subject'],
            }
            if len(response_dict['items']) != 0:
                url = f"https://circleci.com/api/v2/workflow/{response_dict['items'][0]['id']}/job"
                workflow_response = requests.request("GET", url, headers=headers)
                workflow_response_dict = json.loads(workflow_response.text)
                for job in workflow_response_dict['items']:
                    if job['status'] == 'failed':
                        branch_info[item['vcs']['revision'][:7]] = {
                            'status': 'failed',
                            'message': item['vcs']['commit']['subject'],
                        }
    return render_template('commits.html', branch_info=branch_info)


if __name__ == '__main__':
    app.run()
