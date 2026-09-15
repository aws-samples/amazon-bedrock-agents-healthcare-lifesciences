#!/usr/bin/env python3
import aws_cdk as cdk
from omop_ontology_stack import OMOPOntologyStack

app = cdk.App()
OMOPOntologyStack(app, "OMOPOntologyStack")

app.synth()