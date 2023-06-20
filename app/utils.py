import asyncio
import os

import aiohttp
import requests
from flask import current_app as app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm.exc import NoResultFound

from . import models


def fetch_github_module_tests_workflow_jobs(workflow_run_id: str) -> dict:
    """
    Fetch github workflow jobs details using workflow run id

    Args:
        run_id (str): Run Id of the specific workflow

    Returns:
        dict: Workflow details for a specific run.
    """
    headers = {
        "Authorization": f"Bearer {os.getenv('GH_TOKEN')}",
        "Accept": "application/vnd.github+json",
    }
    url = f"https://api.github.com/repos/RedisLabs/module-tests/actions/runs/{workflow_run_id}/jobs"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def fetch_github_module_tests_workflow(run_id: str) -> dict:
    """
    Fetch github workflow details using workflow run id

    Args:
        run_id (str): Run Id of the specific workflow

    Returns:
        dict: Workflow details for a specific run.
    """
    headers = {
        "Authorization": f"Bearer {os.getenv('GH_TOKEN')}",
        "Accept": "application/vnd.github+json",
    }
    url = f"https://api.github.com/repos/RedisLabs/module-tests/actions/runs/{run_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    return {
        "status": data["conclusion"] if data["conclusion"] else data["status"],
        "timestamp": data["updated_at"],
        "html_url": data["html_url"],
        "workflow_id": str(data["workflow_id"]),
        "run_number": str(data["run_number"]),
    }


async def fetch_github_commits(
    sem: asyncio.Semaphore,
    session: aiohttp.ClientSession,
    url: str,
    branch_id: int,
    branch_name: str,
) -> tuple:
    """
    Fetches the GitHub commits for a given branch.

    Args:
        sem (asyncio.Semaphore): Semaphore to control the number of concurrent requests.
        session (aiohttp.ClientSession): Client session for making HTTP requests.
        url (str): URL to fetch the commits from.
        branch_id (int): ID of the branch in the database.
        branch_name (str): Name of the branch.

    Returns:
        tuple: A tuple containing the fetched commits, branch ID, and branch name.
    """
    headers = {
        "Authorization": f"Bearer {os.getenv('GH_TOKEN')}",
        "Accept": "application/vnd.github+json",
    }
    async with sem:
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.json(), branch_id, branch_name


async def fetch_github_workflow_status(
    sem: asyncio.Semaphore,
    session: aiohttp.ClientSession,
    repo: models.Repository,
    commits: list,
    pipelines: list,
) -> list:
    """
    Fetches the GitHub workflow statuses for the given repository, commits, and pipelines.

    Args:
        sem (asyncio.Semaphore): Semaphore to control the number of concurrent requests.
        session (aiohttp.ClientSession): Client session for making HTTP requests.
        repo (models.Repository): Repository object.
        commits (list): List of Commit objects.
        pipelines (list): List of Pipeline objects.

    Returns:
        list: List of dictionaries containing the fetched workflow statuses.
    """
    statuses = []
    commits_dict = {commit.hash: commit for commit in commits}
    pipeline_dict = {pipeline.name: pipeline for pipeline in pipelines}
    headers = {
        "Authorization": f"Bearer {os.getenv('GH_TOKEN')}",
        "Accept": "application/vnd.github+json",
    }
    url = f"https://api.github.com/repos/{repo.owner}/{repo.name}/actions/runs?per_page=100"

    app.logger.info(f"Geting details for {repo.name}:{list(pipeline_dict.keys())}")
    async with sem:
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
            runs = data["workflow_runs"]
            for run in runs:
                if (
                    run["head_sha"] in commits_dict
                    and run["name"] in pipeline_dict
                    and run["repository"]["name"] == repo.name
                ):
                    pipeline = pipeline_dict[run["name"]]
                    commit = commits_dict[run["head_sha"]]
                    app.logger.info(
                        f"Details found, updating pipeline {repo.name}:{pipeline.name} commit: {commit.hash}"
                    )
                    statuses.append(
                        {
                            "status": run["conclusion"]
                            if run["conclusion"]
                            else run["status"],
                            "timestamp": run["updated_at"],
                            "commit_id": commit.id,
                            "pipeline_id": pipeline.id,
                            "html_url": run["html_url"],
                            "workflow_id": str(run["workflow_id"]),
                            "workflow_run_id": str(run["id"]),
                            "run_number": str(run["run_number"]),
                        }
                    )
            return statuses


async def fetch_circleci_pipeline_info(
    session: aiohttp.ClientSession, pipeline: dict
) -> dict:
    """
    Fetches the details of a CircleCI pipeline.

    Args:
        session (aiohttp.ClientSession): Client session for making HTTP requests.
        pipeline (dict): Pipeline information.

    Returns:
        dict: Dictionary containing the fetched pipeline details.
    """
    url = f"https://circleci.com/api/v2/pipeline/{pipeline['id']}/workflow"
    headers = {
        "Circle-Token": os.getenv("CIRCLE_CI_TOKEN"),
        "Accept": "application/json",
    }

    async with session.get(url, headers=headers) as response:
        workflows = await response.json()
        return {"pipeline": pipeline, "workflows": workflows}


async def fetch_circleci_pipelines(
    session: aiohttp.ClientSession, owner: str, repo: str, branch: str
) -> list:
    """
    Fetches the CircleCI pipelines for the given repository and branch.

    Args:
        session (aiohttp.ClientSession): Client session for making HTTP requests.
        owner (str): Repository owner.
        repo (str): Repository name.
        branch (str): Branch name.

    Returns:
        list: List of dictionaries containing the fetched pipelines.
    """
    url = f"https://circleci.com/api/v2/project/gh/{owner}/{repo}/pipeline"
    headers = {
        "Circle-Token": os.getenv("CIRCLE_CI_TOKEN"),
        "Accept": "application/json",
    }
    params = {"branch": branch}

    async with session.get(url, headers=headers, params=params) as response:
        pipelines = (await response.json()).get("items", [])

    tasks = [fetch_circleci_pipeline_info(session, pipeline) for pipeline in pipelines]
    return await asyncio.gather(*tasks)


async def populate_commits(db: SQLAlchemy) -> None:
    """
    Populates the commits in the database by fetching them from GitHub.

    Args:
        db (SQLAlchemy): Database object.
    """  # Create a semaphore to control the number of concurrent requests
    sem = asyncio.Semaphore(10)

    stats = {}
    async with aiohttp.ClientSession() as session:
        for repo in db.session.query(models.Repository).all():
            repo_stats = {}  # To hold the stats for each repo
            tasks = []
            for branch in repo.branches:
                url = f"https://api.github.com/repos/{repo.owner}/{repo.name}/commits?sha={branch.name}"
                app.logger.info(f"Pulling for new commits in {repo.name}/{branch.name}")
                tasks.append(
                    fetch_github_commits(sem, session, url, branch.id, branch.name)
                )
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    app.logger.exception(result)
                else:
                    commits, branch_id, branch_name = result
                    count = 0
                    for commit in commits:
                        try:
                            # Try to get commit from DB. If it exists, skip it.
                            db.session.query(models.Commit).filter(
                                models.Commit.hash == commit["sha"]
                            ).one()
                        except NoResultFound:
                            commit_record = models.Commit(
                                branch_id=branch_id,
                                hash=commit["sha"],
                                message=commit["commit"]["message"],
                                author=commit["commit"]["author"]["name"],
                                date=commit["commit"]["author"]["date"],
                            )
                            db.session.add(commit_record)
                            count += 1  # Increment count only if a new commit is added
                repo_stats[branch_name] = count
            stats[repo] = repo_stats
            try:
                db.session.commit()
            except Exception as e:
                app.logger.exception(e)

    # Log the stats
    for repo, repo_stats in stats.items():
        for branch_name, count in repo_stats.items():
            app.logger.info(
                f"Added {count} new commit(s) for branch {branch_name} in repo {repo.name}"
            )


def populate_repos(db: SQLAlchemy, repos: dict) -> None:
    """
    Populates the repositories and branches in the database.

    Args:
        repos (dict): Dictionary containing repository information.
        db (SQLAlchemy): Database object.
    """
    # Define the repositories, branches, and add them to the db
    for repo_title, repo_info in repos.items():
        repo_url = repo_info["github"]
        _, owner, name = repo_url.split("/")
        branches = repo_info["branches"]
        workflows = repo_info["tests"]

        # Check if the repo already exists
        repo = db.session.query(models.Repository).filter_by(title=repo_title).first()
        if not repo:
            # Create a new repo
            app.logger.info(f"Creating new repository: {repo_title}")
            repo = models.Repository(
                name=name, owner=owner, title=repo_title, url=repo_url
            )
            db.session.add(repo)

        for branch_name in branches:
            branch_name = str(branch_name)
            # Check if the branch already exists
            branch = (
                db.session.query(models.Branch)
                .filter_by(name=branch_name, repository_id=repo.id)
                .first()
            )
            if not branch:
                # Create a new branch
                app.logger.info(
                    f"Creating new branch: {branch_name} for repo: {repo_title}"
                )
                branch = models.Branch(name=branch_name, repository_id=repo.id)
                db.session.add(branch)

        for workflow in workflows:
            platform, pipeline_name = workflow.split("/")
            pipeline = (
                db.session.query(models.Pipeline)
                .filter_by(name=pipeline_name, platform=platform, repository_id=repo.id)
                .first()
            )
            if not pipeline:
                # Create a new pipeline for repo
                app.logger.info(
                    f"Creating new pipeline: {pipeline_name} for repo: {repo_title}"
                )
                pipeline = models.Pipeline(
                    name=pipeline_name, platform=platform, repository_id=repo.id
                )
                db.session.add(pipeline)

        db.session.commit()


async def save_github_statuses_to_db(
    db: SQLAlchemy, session: aiohttp.ClientSession, repo: models.Repository
) -> None:
    """
    Saves the GitHub workflow statuses to the database.

    Args:
        db (SQLAlchemy): Database object.
        session (aiohttp.ClientSession): Client session for making HTTP requests.
        repo (models.Repository): Repository object.
    """
    # Get commits and workflows for the repository
    app.logger.info(f"Gathering workflows for repo {repo.name}")
    commits = (
        db.session.query(models.Commit)
        .join(models.Branch)
        .filter(models.Branch.repository_id == repo.id)
        .all()
    )
    workflows = (
        db.session.query(models.Pipeline)
        .filter(
            models.Pipeline.repository_id == repo.id,
            models.Pipeline.platform == "githubactions",
        )
        .all()
    )
    if not commits:
        app.logger.info(f"{repo.name} missing commits, skipping update.")
        return
    if not workflows:
        app.logger.info(f"{repo.name} missing workflows, skipping update.")
        return
    sem = asyncio.Semaphore(10)
    tasks = [
        fetch_github_workflow_status(sem, session, repo, commits, workflows),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            app.logger.exception(result)
        else:
            for status in result:
                existing_pipeline_status = (
                    db.session.query(models.PipelineStatus)
                    .filter_by(
                        workflow_id=str(status["workflow_id"]),
                        run_number=str(status["run_number"]),
                    )
                    .first()
                )
                if existing_pipeline_status:
                    if existing_pipeline_status.status != status["status"]:
                        app.logger.info("Record already exists, updating status")
                        existing_pipeline_status.status = status["status"]
                    continue
                else:
                    pipeline_status = models.PipelineStatus(**status)
                    db.session.add(pipeline_status)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.exception(e)


async def save_circleci_statuses_to_db(
    db: SQLAlchemy, session: aiohttp.ClientSession, repo: models.Repository
) -> None:
    """
    Saves the CircleCI workflow statuses to the database.

    Args:
        db (SQLAlchemy): Database object.
        session (aiohttp.ClientSession): Client session for making HTTP requests.
        repo (models.Repository): Repository object.
    """
    for branch in repo.branches:
        app.logger.info(f"Requesting CircleCI pipelines for {repo.name}:{branch.name}")
        pipelines = await fetch_circleci_pipelines(
            session, repo.owner, repo.name, branch.name
        )
        app.logger.info(
            f"Retrieved {len(pipelines)} pipelines for {repo.name}:{branch.name}"
        )
        pipeline_names = {
            pipeline.name: pipeline
            for pipeline in db.session.query(models.Pipeline)
            .filter(
                models.Pipeline.repository_id == repo.id,
                models.Pipeline.platform == "circleci",
            )
            .all()
        }
        app.logger.info(
            f"Fetching workflows {list(pipeline_names.keys())} for {repo.name}:{branch.name}"
        )

        for pipeline_info in pipelines:
            pipeline = pipeline_info["pipeline"]
            workflows = pipeline_info["workflows"].get("items")
            if workflows:
                workflow = workflows[0]
                if workflow["name"] in pipeline_names:
                    commit = (
                        db.session.query(models.Commit)
                        .filter(
                            models.Commit.hash == pipeline["vcs"]["revision"]
                        )  # todo pipeline["vcs"]["revision"] or TAG
                        .first()
                    )

                    if commit:
                        existing_pipeline_status = (
                            db.session.query(models.PipelineStatus)
                            .filter_by(
                                workflow_id=str(workflow["id"]),
                                run_number=str(workflow["pipeline_number"]),
                            )
                            .first()
                        )
                        app.logger.info(
                            f"Found {workflow['name']} for commit {commit.hash}"
                        )
                        if existing_pipeline_status:
                            if existing_pipeline_status.status != workflow["status"]:
                                app.logger.info(
                                    "PipelineStatus: record already exists, updating status"
                                )
                                existing_pipeline_status.status = (workflow["status"],)
                            else:
                                app.logger.info(
                                    "PipelineStatus: record already exists, skipping"
                                )
                            continue
                        else:
                            app.logger.info("PipelineStatus: creating new record")
                            pipeline_status = models.PipelineStatus(
                                pipeline_id=pipeline_names[workflow["name"]].id,
                                commit_id=commit.id,
                                status=workflow["status"],
                                html_url=f"https://app.circleci.com/pipelines/github/{repo.owner}/{repo.name}/{workflow['pipeline_number']}/workflows/{workflow['id']}",
                                workflow_id=workflow["id"],
                                run_number=workflow["pipeline_number"],
                                timestamp=pipeline["created_at"],
                            )
                            db.session.add(pipeline_status)
            db.session.commit()


async def populate_pipelines(db: SQLAlchemy) -> None:
    """
    Populates the pipeline statuses in the database.

    Args:
        db (SQLAlchemy): Database object.
    """
    # Update github pipelines
    async with aiohttp.ClientSession() as session:
        tasks = [
            save_github_statuses_to_db(db, session, repo)
            for repo in db.session.query(models.Repository)
            .join(models.Pipeline)
            .filter(models.Pipeline.platform == "githubactions")
            .all()
        ]
        await asyncio.gather(*tasks)

    # Update circleci pipelines
    async with aiohttp.ClientSession() as session:
        tasks = [
            save_circleci_statuses_to_db(db, session, repo)
            for repo in db.session.query(models.Repository)
            .join(models.Pipeline)
            .filter(models.Pipeline.platform == "circleci")
            .all()
        ]
        await asyncio.gather(*tasks)
