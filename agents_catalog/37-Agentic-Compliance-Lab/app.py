#!/usr/bin/env python3
import aws_cdk as cdk

from cdk_stack.medicine_label_stack import MedicineLabelComplianceStack

app = cdk.App()
MedicineLabelComplianceStack(app, "MedicineLabelComplianceStack")

app.synth()
