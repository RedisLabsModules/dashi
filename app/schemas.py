from marshmallow import Schema, fields

class ReportSchema(Schema):
    repo_name = fields.Str(required=True)
    commit_sha = fields.Str(required=True)
    workflow_run_id = fields.Str(required=True)
