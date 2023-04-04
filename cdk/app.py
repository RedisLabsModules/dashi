#!/usr/bin/env python3

import aws_cdk as cdk
import os
from cistack.cistack_stack import DashiStack


app = cdk.App()
DashiStack(
    app,
    "dashistack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    ),
)

app.synth()
