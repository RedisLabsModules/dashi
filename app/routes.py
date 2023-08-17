import re
from http import HTTPStatus

from flask import Blueprint, jsonify, render_template, request
from marshmallow import ValidationError
from sqlalchemy import and_, desc, func

from . import db
from .callback import Callback
from .models import Benchmark, Branch, Commit, Pipeline, PipelineStatus, Repository
from .schemas import ReportSchema
from .utils import (
    fetch_github_module_tests_workflow,
    fetch_github_module_tests_workflow_jobs,
)

main = Blueprint("main", __name__)

FAIL_STATUSES = [
    "failure",
    "timed_out",
    "infrastructure_fail",
    "failed",
    "failing",
    "cancelled",
    "canceled",
]
SUCCESS_STATUSES = ["completed", "success", "fixed", "neutral"]
RUNNING_STATUSES = ["queued", "in_progress", "action_required", "scheduled", "running"]
WORKFLOW_RUN_EVENT_TYPE = "workflow_run"
QA_TEST_PIPELINES_NAME = "module-tests"


@main.route("/")
def index():
    """
    Retrieve repository information, including the last pipeline status for each branch.

    Returns:
        str: Rendered HTML template displaying repository titles, URLs, branches, and their pipeline statuses.

        Example:
        {
            "Repository Title 1": {
                "Branch 1": "success",
                "Branch 2": "failure",
                "Branch 3": "pending",
                ...
            },
            "Repository Title 2": {
                "Branch 1": "success",
                "Branch 2": "No pipeline statuses found",
                ...
            },
            ...
        }
    """
    data = {}

    query = db.session.query(Repository)

    # get all branches for each repo and cumulative pipeline status for each branch
    for repo in query:
        data[repo.title] = {
            "url": repo.url,
            "branches": {},
        }

        branch_query = db.session.query(Branch).filter(Branch.repository_id == repo.id)

        for branch in branch_query:
            # Get the latest commit of the branch
            latest_commit = (
                db.session.query(Commit)
                .join(PipelineStatus, PipelineStatus.commit_id == Commit.id)
                .filter(Commit.branch_id == branch.id)
                .order_by(desc(Commit.date))
                .first()
            )

            if latest_commit:
                # Get all distinct pipeline types for the repository
                pipelines = [pipeline.name for pipeline in repo.pipelines]

                # Fetch the latest status for each pipeline type for the latest commit
                status_list = []
                for pipeline in pipelines:
                    pipeline_status = (
                        db.session.query(PipelineStatus)
                        .join(Pipeline)
                        .filter(
                            and_(
                                Pipeline.name == pipeline,
                                PipelineStatus.commit_id == latest_commit.id,
                            )
                        )
                        .order_by(desc(PipelineStatus.timestamp))
                        .first()
                    )

                    if (
                        pipeline_status is None
                    ):  # No pipeline status found for this pipeline type
                        status_list.append("No statuses found")
                    else:
                        status_list.append(pipeline_status.status)
                # Determine the final status
                if any(status in status_list for status in FAIL_STATUSES):
                    final_status = "failed"
                elif any(status in status_list for status in RUNNING_STATUSES):
                    final_status = "running"
                elif any(status in status_list for status in SUCCESS_STATUSES):
                    final_status = "success"
                else:
                    final_status = "error getting status"

                data[repo.title]["branches"][branch.name] = final_status
            else:
                data[repo.title]["branches"][branch.name] = "no active pipelines"

    return render_template("index.html", data=data)


@main.route("/commits")
def commits():
    """
    Retrieve commits and pipeline statuses for a given repository and branch.

    Args:
        title (str): The title of the repository.
        branch (str): The name of the branch.

    Returns:
        str: Rendered HTML template displaying the commits and pipeline statuses.

    """
    title = request.args.get("title")
    branch_name = request.args.get("branch")

    repo = Repository.query.filter_by(title=title).first()
    branch = Branch.query.filter_by(name=branch_name, repository_id=repo.id).first()
    commits = (
        Commit.query.filter_by(branch_id=branch.id).order_by(desc(Commit.date)).all()
    )
    pipelines = Pipeline.query.filter_by(repository_id=repo.id).all()

    data = []
    for commit in commits:
        commit_data = {
            "hash": commit.hash,
            "message": commit.message,
            "author": commit.author,
            "date": commit.date,
            "pipeline_status": [],
        }
        for pipeline in pipelines:
            pipeline_status = (
                PipelineStatus.query.filter_by(
                    commit_id=commit.id, pipeline_id=pipeline.id
                )
                .order_by(PipelineStatus.timestamp.desc())
                .first()
            )
            if pipeline_status is not None:
                commit_data["pipeline_status"].append(
                    {
                        "status": pipeline_status.status,
                        "workflow_id": pipeline_status.workflow_id,
                        "run_number": pipeline_status.run_number,
                        "name": pipeline.name,
                        "url": pipeline_status.html_url,
                        "is_qa_pipeline": pipeline.name == QA_TEST_PIPELINES_NAME,
                    }
                )
        data.append(commit_data)
    return render_template(
        "commits.html",
        tags=False,
        data=data,
        project=f"{title}/{branch_name}",
        owner=repo.owner,
        name=repo.name,
    )


@main.route("/tags")
def tags():
    """
    Retrieve commits and pipeline statuses for a given repository tag's.

    Args:
        title (str): The title of the repository.

    Returns:
        str: Rendered HTML template displaying the commits and pipeline statuses.
    """
    title = request.args.get("title")

    repo = Repository.query.filter_by(title=title).first()

    tag_prefix = repo.name.lower()
    commits = (
        Commit.query.filter(
            func.lower(Commit.tag).like(f'%{tag_prefix}/%') 
        )
        .order_by(desc(Commit.date))
        .all()
    )
    pipelines = Pipeline.query.filter_by(repository_id=repo.id).all()

    data = []
    for commit in commits:
        commit_data = {
            "hash": commit.hash,
            "tag": commit.tag.split("/")[1],
            "message": commit.message,
            "author": commit.author,
            "date": commit.date,
            "pipeline_status": [],
        }
        for pipeline in pipelines:
            pipeline_status = (
                PipelineStatus.query.filter_by(
                    commit_id=commit.id, pipeline_id=pipeline.id
                )
                .order_by(PipelineStatus.timestamp.desc())
                .first()
            )
            if pipeline_status is not None:
                commit_data["pipeline_status"].append(
                    {
                        "status": pipeline_status.status,
                        "workflow_id": pipeline_status.workflow_id,
                        "run_number": pipeline_status.run_number,
                        "name": pipeline.name,
                        "url": pipeline_status.html_url,
                        "is_qa_pipeline": pipeline.name == QA_TEST_PIPELINES_NAME,
                    }
                )
        data.append(commit_data)
    return render_template(
        "commits.html",
        tags=True,
        data=data,
        project=f"{title}/tags",
        owner=repo.owner,
        name=repo.name,
    )


@main.route("/commits/module-tests", methods=["GET"])
def module_tests():
    """
    Show the details of the QA pipelines
    """
    workflow_id = request.args.get("workflow_id", type=str)
    run_number = request.args.get("run_number", type=str)
    pipeline_status = (
        db.session.query(PipelineStatus)
        .filter_by(
            workflow_id=str(workflow_id),
            run_number=str(run_number),
        )
        .first()
    )
    raw_data = fetch_github_module_tests_workflow_jobs(pipeline_status.workflow_run_id)

    # "test (version, os_name) / test_name" format
    tests_pattern = re.compile(r"test \(([\d\.]+), (\w+)\) / (\w+)")

    # "os_name test_name version Results" format
    results_pattern = re.compile(r"(\w+) (\w+) ([\d\.]+) Results")

    patterns = [tests_pattern, results_pattern]

    data = {}
    for job in raw_data["jobs"]:
        for pattern in patterns:
            match = pattern.match(job["name"])
            if match:
                if pattern == tests_pattern:
                    test_name = match.group(3)
                    version = match.group(1)
                    os_name = match.group(2)
                elif pattern == results_pattern:
                    test_name = match.group(2)
                    version = match.group(3)
                    os_name = match.group(1)

                if os_name not in data:
                    data[os_name] = {}

                if version not in data[os_name]:
                    data[os_name][version] = {}

                # use test_name as key and store status and html_url
                data[os_name][version][test_name] = {
                    "status": job["conclusion"] if job["conclusion"] else job["status"],
                    "html_url": job["html_url"],
                }
                break  # no need to check the remaining patterns

    os_names = list(data.keys())
    return render_template("workflows.html", data=data, os_names=os_names)


@main.route("/webhook", methods=["POST"])
def webhook():
    event_type = request.headers.get("X-GitHub-Event")

    if event_type == WORKFLOW_RUN_EVENT_TYPE:
        payload = request.json
        workflow_run_id = payload["workflow_run"]["id"]
        workflow_conclusion = payload["workflow_run"]["conclusion"]
        workflow_status = payload["workflow_run"]["status"]
        pipeline_status = (
            db.session.query(PipelineStatus)
            .filter_by(
                workflow_run_id=str(workflow_run_id),
            )
            .first()
        )
        if pipeline_status:
            pipeline_status.status = (
                workflow_conclusion if workflow_conclusion else workflow_status
            )
            db.session.commit()
    return jsonify({"message": "Webhook received"}), 200


@main.route("/report", methods=["POST"])
def report():
    """
    Register QA pipeline
    """
    payload = request.get_json()

    try:
        data = ReportSchema().load(payload)
        repo_name = data["repo_name"]
        commit_sha = data["commit_sha"]
        workflow_run_id = data["workflow_run_id"]

        # Query for the repository with the given name
        repo = Repository.query.filter_by(title=repo_name).first()
        if not repo:
            return jsonify({"message": "Repository not found"}), 404

        # Query for the pipeline with the given name for a selected repo
        pipeline = (
            db.session.query(Pipeline)
            .filter_by(
                name="module-tests", platform="githubactions", repository_id=repo.id
            )
            .first()
        )
        if not pipeline:
            return jsonify({"message": "Pipeline not found"}), 404

        # Query for the commit with the given SHA in the found repository
        commit = Commit.query.filter(
            Commit.hash == commit_sha,
            Commit.branch_id.in_([branch.id for branch in repo.branches]),
        ).first()
        if not commit:
            return jsonify({"message": "Commit not found in the given repository"}), 404

        workflow = fetch_github_module_tests_workflow(workflow_run_id)
        existing_pipeline_status = (
            db.session.query(PipelineStatus)
            .filter_by(
                workflow_id=str(workflow["workflow_id"]),
                run_number=str(workflow["run_number"]),
            )
            .first()
        )
        if existing_pipeline_status:
            return jsonify({"message": "Workflow run id already exists"}), 400
        else:
            pipeline_status = PipelineStatus(
                pipeline_id=pipeline.id,
                commit_id=commit.id,
                workflow_run_id=workflow_run_id,
                **workflow,
            )
            db.session.add(pipeline_status)
            db.session.commit()
        return jsonify({"message": "Success"}), 200
    except ValidationError as e:
        return jsonify(e.messages), 400


# todo legacy, should be updated
@main.route("/callback")
def callbackFunc():
    if request.headers.get("Github-Token") is None:
        return jsonify({"code": "Unauthorized request"}), HTTPStatus.UNAUTHORIZED

    githubObj = Callback(request.headers.get("Github-Token"))

    if not githubObj.checkToken():
        return jsonify({"code": "Unauthorized request"}), HTTPStatus.UNAUTHORIZED
    missing_args = githubObj.argsCheck(request.args)
    if len(missing_args) != 0:
        return (
            jsonify({"code": f"Missing args: {','.join(missing_args)}"}),
            HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    if not githubObj.checkRepo():
        return (
            jsonify(
                {
                    "code": f"Repo '{request.args.get('repository')}' is out of token access"
                }
            ),
            HTTPStatus.FORBIDDEN,
        )

    if not githubObj.checkStatus():
        return (
            jsonify(
                {
                    "code": f"wrong status {githubObj.status}. available statuses: {githubObj.available_statuses}"
                }
            ),
            HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    githubObj.pushToDB(db, Benchmark)

    return jsonify({})
