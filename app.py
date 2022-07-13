import json
import os

import requests as requests
import yaml
from flask import Flask, jsonify, render_template, request
import http.client
app = Flask(__name__)


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
    repos = {}
    with open("main.yaml", "r") as stream:
        try:
            yaml_object = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit(2)
        if 'repos' in yaml_object:
            for slug in yaml_object['repos']:
                for repo in yaml_object['repos'][slug]:
                    repos[f"{slug}/{repo}"] = {}
    for repo in repos:
        url = f"https://circleci.com/api/v2/pipeline?org-slug={repo}"

        headers = {
            'Circle-Token': os.getenv('CIRCLE_CI_TOKEN'),
        }

        response = requests.request("GET", url, headers=headers)
        branches = []
        for item in json.loads(response.text)['items']:
            branches += [item['vcs']['branch']]
        repos[repo]['branches'] = branches
        print(response.text)

    return render_template('index.html', repos=repos)


@app.route("/pr")
def prJobs():
    repository = request.args.get('repository', type=str)
    branch = request.args.get('branch', type=str)

    return jsonify({'repo': repository, 'branch': branch})


if __name__ == '__main__':
    app.run()
