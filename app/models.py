from . import db
from sqlalchemy import UniqueConstraint


class Repository(db.Model):
    __tablename__ = "repositories"

    id = db.Column(db.db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, index=True)
    owner = db.Column(db.String)
    url = db.Column(db.String)
    title = db.Column(db.String, unique=True, index=True)

    branches = db.relationship("Branch", backref="repository")
    pipelines = db.relationship("Pipeline", backref="repository")


class Branch(db.Model):
    __tablename__ = "branches"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    repository_id = db.Column(db.Integer, db.ForeignKey("repositories.id"))

    commits = db.relationship("Commit", backref="branch")


class Commit(db.Model):
    __tablename__ = "commits"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"))
    message = db.Column(db.String)
    hash = db.Column(db.String, index=True)
    tag = db.Column(db.String, index=True)
    author = db.Column(db.String)
    date = db.Column(db.DateTime)

    pipeline_statuses = db.relationship("PipelineStatus", backref="commit")


class Pipeline(db.Model):
    __tablename__ = "pipelines"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    platform = db.Column(db.String)
    repository_id = db.Column(db.Integer, db.ForeignKey("repositories.id"))

    pipeline_statuses = db.relationship("PipelineStatus", backref="pipeline")


class PipelineStatus(db.Model):
    __tablename__ = "pipeline_statuses"

    id = db.Column(db.Integer, primary_key=True)
    pipeline_id = db.Column(db.Integer, db.ForeignKey("pipelines.id"))
    commit_id = db.Column(db.Integer, db.ForeignKey("commits.id"))
    status = db.Column(db.String)  # todo github is using both conclusion and status
    html_url = db.Column(db.String)
    workflow_id = db.Column(db.String, index=True)
    run_number = db.Column(db.String, index=True)
    workflow_run_id = db.Column(db.String, index=True)
    timestamp = db.Column(db.DateTime)

    __table_args__ = (
        UniqueConstraint("workflow_id", "run_number", name="_workflow_run_uc"),
    )


class Benchmark(db.Model):
    __tablename__ = "benchmarks"

    id = db.Column(db.Integer, primary_key=True)
    commit_id = db.Column(db.Integer, db.ForeignKey("commits.id"))
    status = db.Column(db.String, nullable=False, index=True)
    test_name = db.Column(db.String, nullable=False, index=True)
