import json
import re
import requests
import yaml


class Callback:
    def __init__(self, token: str):
        self.user_orgs = []
        self.repos = []
        self.repos_branches = {}
        self.token = token
        self.branch = None
        self.repository = None
        self.workflowId = None
        self.test_name = None
        self.status = None
        self.available_statuses = [
            'started',
            'success',
            'canceled',
            'failed',
        ]
        self.commit = None
        self.required_args = [
            'branch',
            'repository',
            'workflowId',
            'commit',
            'test_name',
            'status',
        ]
        self.populateBranches()

    def checkToken(self) -> bool:
        # Check if token valid

        match = re.search(r"^w{1,40}|.*ghp_\w{36}$", self.token)
        if not match:
            return False

        resp_user = requests.get(
            'https://api.github.com/user/memberships/orgs',
            headers={
                'Authorization': f"Bearer {self.token}",
                'Accept': 'application/vnd.github+json',
            }
        )
        if resp_user.status_code != 200:
            return False
        resp_user_json = json.loads(resp_user.content)
        self.user_orgs = [x['organization']['login'] for x in resp_user_json if x['state'] == 'active']
        return True

    def checkOrgPermissions(self, org: str) -> bool:
        # Check if token access to required organisations

        if org in self.user_orgs:
            return True
        return False

    def populateBranches(self):
        with open("main.yaml", "r") as stream:
            try:
                yaml_object = yaml.load(stream, Loader=yaml.BaseLoader)
            except yaml.YAMLError as exc:
                print(exc)
                exit(2)
            repos = yaml_object['repos']
            for project in repos:
                project_obj = repos[project]
                project_name = project.split('/')[-1]
                self.repos.append(project_name)
                self.repos_branches[project_name] = [str(x) for x in project_obj['branches']]

    def argsCheck(self, args: dict) -> list:
        for key, value in args.items():
            # prepare list of missed arguments
            if key in self.required_args:
                self.required_args.remove(key)
            # populate object variables
            if key == 'branch':
                self.branch = value
            if key == 'status':
                self.status = value
            if key == 'test_name':
                self.test_name = value
            if key == 'repository':
                self.repository = value
            if key == 'commit':
                self.commit = value
            if key == 'workflowId':
                self.workflowId = value
        return self.required_args

    def checkRepo(self):
        if self.repository in self.repos:
            return True
        return False

    def checkStatus(self):
        if self.status in self.available_statuses:
            return True
        return False

    def pushToDB(self, dbObj, benchmark, commitId):
        if not self.DBRecordExists(dbObj, benchmark, commitId):
            new_bench = benchmark()
            new_bench.commitId = commitId
            new_bench.branch = self.branch
            new_bench.status = self.status
            new_bench.testName = self.test_name
            new_bench.workflowId = self.workflowId
            dbObj.session.add(new_bench)
            dbObj.session.commit()
        else:
            dbObj.session.query(benchmark). \
                filter(
                benchmark.commitId == commitId,
                benchmark.branch == self.branch,
                benchmark.testName == self.test_name,
            ).update({'status': self.status})
            dbObj.session.commit()

    def DBRecordExists(self, dbObj, benchmark, commitId):
        benchmarkId = dbObj.session.query(
            benchmark.id
        ).filter(
            benchmark.commitId == commitId,
            benchmark.branch == self.branch
        ).order_by(benchmark.id.desc()).first()
        if benchmarkId is not None:
            return True
        return False
