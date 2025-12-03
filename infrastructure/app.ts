#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { AdpaStack } from './adpa-stack';

const app = new cdk.App();

// Environment configuration
const projectName = 'adpa';
const account = process.env.CDK_DEFAULT_ACCOUNT || '083308938449';
const region = process.env.CDK_DEFAULT_REGION || 'us-east-2';

// Development Environment
new AdpaStack(app, `${projectName}-dev-stack`, {
  env: { account, region },
  environment: 'dev',
  projectName,
  description: 'ADPA Development Environment - Autonomous Data Pipeline Agent',
  tags: {
    Project: 'ADPA',
    Environment: 'development',
    Team: 'ML-Engineering',
    CostCenter: 'research',
  },
});

// Staging Environment
new AdpaStack(app, `${projectName}-staging-stack`, {
  env: { account, region },
  environment: 'staging',
  projectName,
  description: 'ADPA Staging Environment - Pre-production testing',
  tags: {
    Project: 'ADPA',
    Environment: 'staging',
    Team: 'ML-Engineering',
    CostCenter: 'testing',
  },
});

// Production Environment
new AdpaStack(app, `${projectName}-prod-stack`, {
  env: { account, region },
  environment: 'prod',
  projectName,
  description: 'ADPA Production Environment - Autonomous Data Pipeline Agent',
  tags: {
    Project: 'ADPA',
    Environment: 'production',
    Team: 'ML-Engineering',
    CostCenter: 'production',
  },
});

app.synth();