#!/usr/bin/env python3
import aws_cdk as cdk

from cdk_stack.pharmalabel_stack import PharmaLabelStack

app = cdk.App()
stack = PharmaLabelStack(app, "PharmaLabelStack",
    env=cdk.Environment(region="us-east-1")
)

app.synth()
