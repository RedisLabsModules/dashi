from http import HTTPStatus

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import and_, desc

from . import db
from .callback import Callback
from .models import Benchmark, Branch, Commit, Pipeline, PipelineStatus, Repository

main = Blueprint("main", __name__)


FAIL_STATUSES = [
    "failure",
    "timed_out",
    "infrastructure_fail",
    "failed",
    "failing",
    "cancelled",
]
SUCCESS_STATUSES = ["completed", "success", "fixed", "neutral"]
RUNNING_STATUSES = ["queued", "in_progress", "action_required", "scheduled", "running"]


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
            "status": [],
        }
        for pipeline in pipelines:
            status = (
                PipelineStatus.query.filter_by(
                    commit_id=commit.id, pipeline_id=pipeline.id
                )
                .order_by(PipelineStatus.timestamp.desc())
                .first()
            )
            if status is not None:
                commit_data["status"].append(
                    {
                        "status": status.status,
                        "name": pipeline.name,
                        "url": status.html_url,
                    }
                )
        data.append(commit_data)
    return render_template(
        "commits.html",
        data=data,
        project=f"{title}/{branch_name}",
        owner=repo.owner,
        name=repo.name,
    )


@main.route("/webhook", methods=["POST"])
def webhook():
    event_type = request.headers.get("X-GitHub-Event")

    if event_type == "workflow_run":
        payload = request.json
        workflow_run_id = payload["workflow_run"]["id"]
        status = payload["workflow_run"]["status"]
        commit_sha = payload["workflow_run"]["head_sha"]

    return "Webhook received", 200


# todo legacy, thould be updated
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
