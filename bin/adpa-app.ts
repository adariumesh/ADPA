#!/usr/bin/env node
import 'source-map-support/register';
import { App } from 'aws-cdk-lib';
import { AdpaDataStack } from '../lib/adpa-data-stack';

const app = new App();

// Prefer resolving account/region from your AWS profile or env vars
// Set via: export AWS_PROFILE=adpa (optional), export CDK_DEFAULT_ACCOUNT/REGION, or pass --profile at deploy time
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
};

new AdpaDataStack(app, 'AdpaDataStack', { env });