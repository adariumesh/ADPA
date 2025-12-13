#!/usr/bin/env node
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
require("source-map-support/register");
const cdk = require("aws-cdk-lib");
const simple_stack_1 = require("./simple-stack");
const app = new cdk.App();
new simple_stack_1.SimpleAdpaStack(app, 'adpa-prod-simple-stack', {
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
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoic2ltcGxlLWFwcC5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbInNpbXBsZS1hcHAudHMiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6Ijs7O0FBQ0EsdUNBQXFDO0FBQ3JDLG1DQUFtQztBQUNuQyxpREFBaUQ7QUFFakQsTUFBTSxHQUFHLEdBQUcsSUFBSSxHQUFHLENBQUMsR0FBRyxFQUFFLENBQUM7QUFFMUIsSUFBSSw4QkFBZSxDQUFDLEdBQUcsRUFBRSx3QkFBd0IsRUFBRTtJQUNqRCxHQUFHLEVBQUU7UUFDSCxPQUFPLEVBQUUsY0FBYztRQUN2QixNQUFNLEVBQUUsV0FBVztLQUNwQjtJQUNELFdBQVcsRUFBRSwwREFBMEQ7SUFDdkUsSUFBSSxFQUFFO1FBQ0osT0FBTyxFQUFFLE1BQU07UUFDZixXQUFXLEVBQUUsWUFBWTtRQUN6QixPQUFPLEVBQUUsS0FBSztRQUNkLGNBQWMsRUFBRSxtQkFBbUI7S0FDcEM7Q0FDRixDQUFDLENBQUM7QUFFSCxHQUFHLENBQUMsS0FBSyxFQUFFLENBQUMiLCJzb3VyY2VzQ29udGVudCI6WyIjIS91c3IvYmluL2VudiBub2RlXG5pbXBvcnQgJ3NvdXJjZS1tYXAtc3VwcG9ydC9yZWdpc3Rlcic7XG5pbXBvcnQgKiBhcyBjZGsgZnJvbSAnYXdzLWNkay1saWInO1xuaW1wb3J0IHsgU2ltcGxlQWRwYVN0YWNrIH0gZnJvbSAnLi9zaW1wbGUtc3RhY2snO1xuXG5jb25zdCBhcHAgPSBuZXcgY2RrLkFwcCgpO1xuXG5uZXcgU2ltcGxlQWRwYVN0YWNrKGFwcCwgJ2FkcGEtcHJvZC1zaW1wbGUtc3RhY2snLCB7XG4gIGVudjoge1xuICAgIGFjY291bnQ6ICcwODMzMDg5Mzg0NDknLFxuICAgIHJlZ2lvbjogJ3VzLWVhc3QtMicsXG4gIH0sXG4gIGRlc2NyaXB0aW9uOiAnQURQQSBQcm9kdWN0aW9uIFN0YWNrIC0gU2ltcGxpZmllZCBFbnRlcnByaXNlIERlcGxveW1lbnQnLFxuICB0YWdzOiB7XG4gICAgUHJvamVjdDogJ0FEUEEnLFxuICAgIEVudmlyb25tZW50OiAncHJvZHVjdGlvbicsXG4gICAgVmVyc2lvbjogJzIuMCcsXG4gICAgRGVwbG95bWVudFR5cGU6ICdlbnRlcnByaXNlLXNpbXBsZScsXG4gIH0sXG59KTtcblxuYXBwLnN5bnRoKCk7Il19