#!/usr/bin/env node
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
require("source-map-support/register");
const cdk = require("aws-cdk-lib");
const adpa_stack_1 = require("./adpa-stack");
const app = new cdk.App();
// Environment configuration
const projectName = 'adpa';
const account = process.env.CDK_DEFAULT_ACCOUNT || '083308938449';
const region = process.env.CDK_DEFAULT_REGION || 'us-east-2';
// Development Environment
new adpa_stack_1.AdpaStack(app, `${projectName}-dev-stack`, {
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
new adpa_stack_1.AdpaStack(app, `${projectName}-staging-stack`, {
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
new adpa_stack_1.AdpaStack(app, `${projectName}-prod-stack`, {
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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiYXBwLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiYXBwLnRzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7OztBQUNBLHVDQUFxQztBQUNyQyxtQ0FBbUM7QUFDbkMsNkNBQXlDO0FBRXpDLE1BQU0sR0FBRyxHQUFHLElBQUksR0FBRyxDQUFDLEdBQUcsRUFBRSxDQUFDO0FBRTFCLDRCQUE0QjtBQUM1QixNQUFNLFdBQVcsR0FBRyxNQUFNLENBQUM7QUFDM0IsTUFBTSxPQUFPLEdBQUcsT0FBTyxDQUFDLEdBQUcsQ0FBQyxtQkFBbUIsSUFBSSxjQUFjLENBQUM7QUFDbEUsTUFBTSxNQUFNLEdBQUcsT0FBTyxDQUFDLEdBQUcsQ0FBQyxrQkFBa0IsSUFBSSxXQUFXLENBQUM7QUFFN0QsMEJBQTBCO0FBQzFCLElBQUksc0JBQVMsQ0FBQyxHQUFHLEVBQUUsR0FBRyxXQUFXLFlBQVksRUFBRTtJQUM3QyxHQUFHLEVBQUUsRUFBRSxPQUFPLEVBQUUsTUFBTSxFQUFFO0lBQ3hCLFdBQVcsRUFBRSxLQUFLO0lBQ2xCLFdBQVc7SUFDWCxXQUFXLEVBQUUsK0RBQStEO0lBQzVFLElBQUksRUFBRTtRQUNKLE9BQU8sRUFBRSxNQUFNO1FBQ2YsV0FBVyxFQUFFLGFBQWE7UUFDMUIsSUFBSSxFQUFFLGdCQUFnQjtRQUN0QixVQUFVLEVBQUUsVUFBVTtLQUN2QjtDQUNGLENBQUMsQ0FBQztBQUVILHNCQUFzQjtBQUN0QixJQUFJLHNCQUFTLENBQUMsR0FBRyxFQUFFLEdBQUcsV0FBVyxnQkFBZ0IsRUFBRTtJQUNqRCxHQUFHLEVBQUUsRUFBRSxPQUFPLEVBQUUsTUFBTSxFQUFFO0lBQ3hCLFdBQVcsRUFBRSxTQUFTO0lBQ3RCLFdBQVc7SUFDWCxXQUFXLEVBQUUsbURBQW1EO0lBQ2hFLElBQUksRUFBRTtRQUNKLE9BQU8sRUFBRSxNQUFNO1FBQ2YsV0FBVyxFQUFFLFNBQVM7UUFDdEIsSUFBSSxFQUFFLGdCQUFnQjtRQUN0QixVQUFVLEVBQUUsU0FBUztLQUN0QjtDQUNGLENBQUMsQ0FBQztBQUVILHlCQUF5QjtBQUN6QixJQUFJLHNCQUFTLENBQUMsR0FBRyxFQUFFLEdBQUcsV0FBVyxhQUFhLEVBQUU7SUFDOUMsR0FBRyxFQUFFLEVBQUUsT0FBTyxFQUFFLE1BQU0sRUFBRTtJQUN4QixXQUFXLEVBQUUsTUFBTTtJQUNuQixXQUFXO0lBQ1gsV0FBVyxFQUFFLDhEQUE4RDtJQUMzRSxJQUFJLEVBQUU7UUFDSixPQUFPLEVBQUUsTUFBTTtRQUNmLFdBQVcsRUFBRSxZQUFZO1FBQ3pCLElBQUksRUFBRSxnQkFBZ0I7UUFDdEIsVUFBVSxFQUFFLFlBQVk7S0FDekI7Q0FDRixDQUFDLENBQUM7QUFFSCxHQUFHLENBQUMsS0FBSyxFQUFFLENBQUMiLCJzb3VyY2VzQ29udGVudCI6WyIjIS91c3IvYmluL2VudiBub2RlXG5pbXBvcnQgJ3NvdXJjZS1tYXAtc3VwcG9ydC9yZWdpc3Rlcic7XG5pbXBvcnQgKiBhcyBjZGsgZnJvbSAnYXdzLWNkay1saWInO1xuaW1wb3J0IHsgQWRwYVN0YWNrIH0gZnJvbSAnLi9hZHBhLXN0YWNrJztcblxuY29uc3QgYXBwID0gbmV3IGNkay5BcHAoKTtcblxuLy8gRW52aXJvbm1lbnQgY29uZmlndXJhdGlvblxuY29uc3QgcHJvamVjdE5hbWUgPSAnYWRwYSc7XG5jb25zdCBhY2NvdW50ID0gcHJvY2Vzcy5lbnYuQ0RLX0RFRkFVTFRfQUNDT1VOVCB8fCAnMDgzMzA4OTM4NDQ5JztcbmNvbnN0IHJlZ2lvbiA9IHByb2Nlc3MuZW52LkNES19ERUZBVUxUX1JFR0lPTiB8fCAndXMtZWFzdC0yJztcblxuLy8gRGV2ZWxvcG1lbnQgRW52aXJvbm1lbnRcbm5ldyBBZHBhU3RhY2soYXBwLCBgJHtwcm9qZWN0TmFtZX0tZGV2LXN0YWNrYCwge1xuICBlbnY6IHsgYWNjb3VudCwgcmVnaW9uIH0sXG4gIGVudmlyb25tZW50OiAnZGV2JyxcbiAgcHJvamVjdE5hbWUsXG4gIGRlc2NyaXB0aW9uOiAnQURQQSBEZXZlbG9wbWVudCBFbnZpcm9ubWVudCAtIEF1dG9ub21vdXMgRGF0YSBQaXBlbGluZSBBZ2VudCcsXG4gIHRhZ3M6IHtcbiAgICBQcm9qZWN0OiAnQURQQScsXG4gICAgRW52aXJvbm1lbnQ6ICdkZXZlbG9wbWVudCcsXG4gICAgVGVhbTogJ01MLUVuZ2luZWVyaW5nJyxcbiAgICBDb3N0Q2VudGVyOiAncmVzZWFyY2gnLFxuICB9LFxufSk7XG5cbi8vIFN0YWdpbmcgRW52aXJvbm1lbnRcbm5ldyBBZHBhU3RhY2soYXBwLCBgJHtwcm9qZWN0TmFtZX0tc3RhZ2luZy1zdGFja2AsIHtcbiAgZW52OiB7IGFjY291bnQsIHJlZ2lvbiB9LFxuICBlbnZpcm9ubWVudDogJ3N0YWdpbmcnLFxuICBwcm9qZWN0TmFtZSxcbiAgZGVzY3JpcHRpb246ICdBRFBBIFN0YWdpbmcgRW52aXJvbm1lbnQgLSBQcmUtcHJvZHVjdGlvbiB0ZXN0aW5nJyxcbiAgdGFnczoge1xuICAgIFByb2plY3Q6ICdBRFBBJyxcbiAgICBFbnZpcm9ubWVudDogJ3N0YWdpbmcnLFxuICAgIFRlYW06ICdNTC1FbmdpbmVlcmluZycsXG4gICAgQ29zdENlbnRlcjogJ3Rlc3RpbmcnLFxuICB9LFxufSk7XG5cbi8vIFByb2R1Y3Rpb24gRW52aXJvbm1lbnRcbm5ldyBBZHBhU3RhY2soYXBwLCBgJHtwcm9qZWN0TmFtZX0tcHJvZC1zdGFja2AsIHtcbiAgZW52OiB7IGFjY291bnQsIHJlZ2lvbiB9LFxuICBlbnZpcm9ubWVudDogJ3Byb2QnLFxuICBwcm9qZWN0TmFtZSxcbiAgZGVzY3JpcHRpb246ICdBRFBBIFByb2R1Y3Rpb24gRW52aXJvbm1lbnQgLSBBdXRvbm9tb3VzIERhdGEgUGlwZWxpbmUgQWdlbnQnLFxuICB0YWdzOiB7XG4gICAgUHJvamVjdDogJ0FEUEEnLFxuICAgIEVudmlyb25tZW50OiAncHJvZHVjdGlvbicsXG4gICAgVGVhbTogJ01MLUVuZ2luZWVyaW5nJyxcbiAgICBDb3N0Q2VudGVyOiAncHJvZHVjdGlvbicsXG4gIH0sXG59KTtcblxuYXBwLnN5bnRoKCk7Il19