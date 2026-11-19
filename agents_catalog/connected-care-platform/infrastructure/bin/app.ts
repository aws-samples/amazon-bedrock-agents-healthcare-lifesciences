#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { PatientMonitoringAgentStack } from '../lib/patient-monitoring-agent-stack';
import { DeviceManagementAgentStack } from '../lib/device-management-agent-stack';
import { PatientEngagementAgentStack } from '../lib/patient-engagement-agent-stack';
import { InventoryManagementAgentStack } from '../lib/inventory-management-agent-stack';
import { FieldServiceAgentStack } from '../lib/field-service-agent-stack';
import { OrchestratorAgentStack } from '../lib/orchestrator-agent-stack';
import { AgentCoreStack } from '../lib/agentcore-stack';
import { getResourcePrefix, getResourceNames } from '../lib/resource-names';

const app = new cdk.App();

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
};

// Resolve resource prefix from CDK context (default: "connected-care")
const prefix = getResourcePrefix(app);
const names = getResourceNames(prefix);

new PatientMonitoringAgentStack(app, 'PatientMonitoringAgentStack', {
  env, tags: { Project: 'ConnectedCarePlatform', Module: 'PatientMonitoring', ManagedBy: 'CDK' },
  resourcePrefix: prefix,
  resourceNames: names,
});

new DeviceManagementAgentStack(app, 'DeviceManagementAgentStack', {
  env, tags: { Project: 'ConnectedCarePlatform', Module: 'DeviceManagement', ManagedBy: 'CDK' },
  resourcePrefix: prefix,
  resourceNames: names,
});

new PatientEngagementAgentStack(app, 'PatientEngagementAgentStack', {
  env, tags: { Project: 'ConnectedCarePlatform', Module: 'PatientEngagement', ManagedBy: 'CDK' },
  resourcePrefix: prefix,
  resourceNames: names,
});

new InventoryManagementAgentStack(app, 'InventoryManagementAgentStack', {
  env, tags: { Project: 'ConnectedCarePlatform', Module: 'InventoryManagement', ManagedBy: 'CDK' },
  resourcePrefix: prefix,
  resourceNames: names,
});

new FieldServiceAgentStack(app, 'FieldServiceAgentStack', {
  env, tags: { Project: 'ConnectedCarePlatform', Module: 'FieldService', ManagedBy: 'CDK' },
  resourcePrefix: prefix,
  resourceNames: names,
});

new OrchestratorAgentStack(app, 'OrchestratorAgentStack', {
  env, tags: { Project: 'ConnectedCarePlatform', Module: 'Orchestrator', ManagedBy: 'CDK' },
  resourcePrefix: prefix,
  resourceNames: names,
});

// AgentCore deployment — runs alongside existing Lambda + WebSocket stacks
// Does NOT modify or replace any existing infrastructure
new AgentCoreStack(app, 'ConnectedCareAgentCoreStack', {
  env,
  tags: { Project: 'ConnectedCarePlatform', Module: 'AgentCore', ManagedBy: 'CDK' },
  resourcePrefix: prefix,
  resourceNames: names,
});
