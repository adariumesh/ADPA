# ADPA Infrastructure - Production-Ready AWS CDK

This directory contains the complete AWS CDK infrastructure for the Autonomous Data Pipeline Agent (ADPA), designed for production-grade deployments across multiple environments.

## 🏗️ Infrastructure Components

### Core Stacks
- **`adpa-stack.ts`** - Main infrastructure stack with all AWS resources
- **`lambda-layers.ts`** - Lambda layer management and versioning
- **`dynamodb-config.ts`** - DynamoDB auto-scaling and backup configuration
- **`deployment-pipeline.ts`** - CI/CD pipeline with CodePipeline and CodeBuild

### Features Included

#### ✅ **Security & Compliance**
- Least-privilege IAM roles for all services
- API Gateway request validation and rate limiting
- S3 bucket encryption and access controls
- VPC isolation ready (configurable)
- AWS Backup integration with encryption

#### ✅ **Scalability & Performance**
- DynamoDB auto-scaling (read/write capacity)
- Lambda layer optimization for faster cold starts
- API Gateway throttling and caching
- S3 lifecycle policies for cost optimization

#### ✅ **Monitoring & Observability**
- Comprehensive CloudWatch alarms
- Custom metrics for business KPIs
- Distributed tracing with X-Ray
- Centralized logging with structured format

#### ✅ **DevOps & Automation**
- Multi-environment support (dev/staging/prod)
- Automated CI/CD pipeline with approvals
- Blue-green deployment capability
- Infrastructure drift detection

#### ✅ **Cost Optimization**
- Resource tagging for cost allocation
- S3 intelligent tiering and lifecycle rules
- DynamoDB on-demand billing
- Lambda memory optimization

#### ✅ **Disaster Recovery**
- Automated backups for DynamoDB
- Cross-region replication ready
- Point-in-time recovery enabled
- Data retention policies

## 🚀 Quick Start

### Prerequisites
```bash
npm install -g aws-cdk@2.87.0
aws configure
```

### Installation
```bash
cd infrastructure
npm install
npm run build
```

### Deploy Development Environment
```bash
# Bootstrap CDK (first time only)
npm run bootstrap

# Deploy to development
npm run deploy:dev
```

### Deploy All Environments
```bash
npm run deploy:all
```

## 📋 Available Commands

```bash
# Development
npm run build          # Compile TypeScript
npm run watch          # Watch for changes
npm run test           # Run CDK tests

# Deployment
npm run deploy:dev      # Deploy dev environment
npm run deploy:staging  # Deploy staging environment  
npm run deploy:prod     # Deploy production environment
npm run deploy:all      # Deploy all environments

# Utilities
npm run diff:dev        # Show diff for dev environment
npm run diff:staging    # Show diff for staging environment
npm run diff:prod       # Show diff for production environment
npm run synth          # Synthesize CloudFormation templates
npm run destroy:dev     # Destroy dev environment (careful!)
```

## 🌍 Environment Configuration

### Development Environment
- **Stack Name**: `adpa-dev-stack`
- **Resources**: Minimal capacity, short retention periods
- **Cost**: ~$5-20/month
- **Purpose**: Development and testing

### Staging Environment  
- **Stack Name**: `adpa-staging-stack`
- **Resources**: Production-like but smaller scale
- **Cost**: ~$20-50/month
- **Purpose**: Pre-production testing and validation

### Production Environment
- **Stack Name**: `adpa-prod-stack`
- **Resources**: Full scale with high availability
- **Cost**: ~$50-200/month (usage dependent)
- **Purpose**: Live production workloads

## 📊 Resource Overview

| Service | Development | Staging | Production |
|---------|------------|---------|------------|
| **Lambda** | 512MB, 5min timeout | 1024MB, 10min timeout | 1024MB, 15min timeout |
| **DynamoDB** | 1-100 capacity units | 5-500 capacity units | 5-4000 capacity units |
| **S3** | 30-day lifecycle | 60-day lifecycle | 90-day lifecycle |
| **Backups** | Weekly, 2 weeks retention | Daily, 1 month retention | Daily + Monthly, 1 year retention |
| **Monitoring** | Basic alarms | Enhanced monitoring | Full observability |

## 🔐 Security Features

### IAM Roles & Policies
- **Lambda Execution Role**: Minimal permissions for DynamoDB, S3, Step Functions
- **SageMaker Execution Role**: ML training permissions with S3 access
- **Step Functions Role**: Orchestration permissions for Lambda and SageMaker
- **Backup Service Role**: Automated backup management

### API Gateway Security
- Request validation with JSON schemas
- Rate limiting: 1000 req/sec, 2000 burst
- CORS configuration (environment-specific origins)
- CloudWatch logging enabled

### Data Protection
- S3 encryption at rest (AWS managed keys)
- DynamoDB encryption at rest
- Point-in-time recovery enabled
- Automated backup with encryption

## 📈 Monitoring & Alerting

### CloudWatch Alarms
- **Lambda Errors**: >5 errors in 5 minutes
- **API Gateway 4XX**: >20 errors in 5 minutes  
- **DynamoDB Throttles**: Any throttling detected
- **High Capacity Utilization**: >85% for DynamoDB
- **Pipeline Failures**: Step Functions execution failures
- **Cost Alerts**: SageMaker training costs >$100/hour

### Custom Metrics
- Pipeline execution duration
- API response times
- Data processing volume
- Concurrent executions
- Error rates by component

### Dashboards
- **Performance Metrics**: Response times, execution duration
- **Error Tracking**: Error rates by component and type
- **Resource Utilization**: DynamoDB, Lambda, S3 usage
- **Cost Monitoring**: Training costs, resource usage
- **Recent Errors**: Log aggregation and filtering

## 🚀 CI/CD Pipeline

### Pipeline Stages
1. **Source**: GitHub webhook trigger
2. **Build**: Compile, test, package Lambda functions
3. **Deploy Dev**: Automatic deployment to development
4. **Approval**: Manual approval for staging
5. **Deploy Staging**: Staging environment deployment
6. **Approval**: Manual approval for production
7. **Deploy Production**: Production deployment

### Build Process
- TypeScript compilation
- Python dependency packaging
- Lambda layer creation
- CDK synthesis and validation
- Unit test execution
- Security scanning

### Deployment Features
- Blue-green deployment ready
- Rollback capability
- Health checks after deployment
- SNS notifications for status
- CloudWatch integration

## 💰 Cost Optimization

### Automatic Cost Controls
- **S3 Lifecycle Rules**: Transition to IA after 30 days, Glacier after 90 days
- **DynamoDB On-Demand**: Pay per request, no pre-provisioning
- **Lambda Right-Sizing**: Environment-appropriate memory allocation
- **Log Retention**: 2 weeks for Lambda logs, configurable retention
- **Backup Retention**: Environment-appropriate backup schedules

### Cost Monitoring
- Resource tagging for cost allocation
- CloudWatch cost alarms
- Monthly cost reports
- SageMaker training cost tracking

### Estimated Monthly Costs
- **Development**: $5-20 (minimal usage)
- **Staging**: $20-50 (testing workloads)
- **Production**: $50-200 (depends on ML training frequency)

## 🔧 Customization

### Environment Variables
Set these in your environment or CI/CD system:
```bash
export CDK_DEFAULT_ACCOUNT=083308938449
export CDK_DEFAULT_REGION=us-east-2
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx  # Store in AWS Secrets Manager
```

### Configuration Options
Edit `app.ts` to customize:
- Account and region settings
- Environment-specific configurations
- Resource tagging strategy
- Cost allocation tags

## 🆘 Troubleshooting

### Common Issues

**CDK Bootstrap Required**
```bash
cdk bootstrap aws://083308938449/us-east-2
```

**Permission Denied**
- Ensure AWS credentials are configured
- Check IAM permissions for CDK deployment
- Verify account and region settings

**Stack Drift**
```bash
npm run diff:prod  # Check for drift
npm run deploy:prod  # Apply changes
```

**Pipeline Failures**
- Check CodeBuild logs in AWS Console
- Verify GitHub token in Secrets Manager
- Ensure all dependencies are installed

### Getting Help
1. Check AWS CloudWatch logs
2. Review CDK diff output
3. Validate IAM permissions
4. Consult AWS documentation

## 📚 Additional Resources

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [ADPA Architecture Guide](../docs/ARCHITECTURE.md)
- [Security Best Practices](../docs/SECURITY.md)
- [Cost Optimization Guide](../docs/COST_OPTIMIZATION.md)

---

**Infrastructure Version**: 2.0.0  
**CDK Version**: 2.87.0  
**Last Updated**: December 3, 2025  
**Maintained by**: ADPA DevOps Team