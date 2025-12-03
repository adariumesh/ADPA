#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { SimpleAdpaStack } from './simple-stack';

const app = new cdk.App();

new SimpleAdpaStack(app, 'adpa-prod-simple-stack', {
  env: {
    account: '083308938449',
    region: 'us-east-2',
  },
  description: 'ADPA Production Stack - Simplified Enterprise Deployment',
  tags: {
    Project: 'ADPA',
    Environment: 'production',
    Version: '2.0',
    DeploymentType: 'enterprise-simple',
  },
});

app.synth();