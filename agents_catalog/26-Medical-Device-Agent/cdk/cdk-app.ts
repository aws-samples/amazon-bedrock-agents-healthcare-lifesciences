#!/usr/bin/env node
import { App, Aspects } from "aws-cdk-lib";
import { MedicalDeviceFargateStack } from "./stacks/medical-device-fargate-stack";
import { AwsSolutionsChecks } from 'cdk-nag';
import { projectName, EnvNameType } from "./constant";

const app = new App();

const envName: EnvNameType = app.node.tryGetContext('envName') || 'dev';

const fargateStack = new MedicalDeviceFargateStack(app, `${projectName}FargateStack`, {
  envName: envName,
});

Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));