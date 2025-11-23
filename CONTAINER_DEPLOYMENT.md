# 🐳 ADPA Container Deployment Guide

## Overview

This guide shows you how to deploy ADPA as a containerized application on AWS using ECS (Elastic Container Service) with an Application Load Balancer. Your ADPA instance will be accessible via a web interface from anywhere in the world.

## 🚀 Quick Start

### 1. Prerequisites

Ensure you have completed the basic infrastructure setup first:

```bash
# Check deployment readiness
./check-deployment-gaps.sh

# Deploy basic infrastructure (if not already done)
./deploy/aws-deploy.sh development adpa us-east-1
```

### 2. Deploy Container to AWS

```bash
# Deploy ADPA as containers with web frontend
./deploy/container-deploy.sh development adpa us-east-1
```

This single command will:
- ✅ Create ECR repository for your container images
- ✅ Build and push Docker image to AWS
- ✅ Deploy ECS cluster with Application Load Balancer
- ✅ Configure auto-scaling and health checks
- ✅ Provide you with a public URL to access ADPA

### 3. Access Your ADPA Instance

After deployment completes, you'll get a URL like:
```
🌐 ADPA Web Interface: http://adpa-alb-development-123456789.us-east-1.elb.amazonaws.com
```

## 📊 What You Get

### Web Interface Features
- **🎨 Modern Dashboard**: Beautiful, responsive web interface
- **🚀 Pipeline Execution**: Execute ML pipelines through the browser
- **📈 Real-time Status**: Monitor system health and progress
- **📊 Project Analytics**: View completion status and recommendations
- **🔧 API Access**: RESTful API for programmatic access

### Cloud Infrastructure
- **🔄 Auto-Scaling**: Automatically scales based on CPU usage (1-10 instances)
- **🛡️ Load Balancer**: Distributes traffic across multiple containers
- **💾 Persistent Storage**: S3 integration for data and models
- **🔐 Security**: VPC isolation, IAM roles, encrypted storage
- **📊 Monitoring**: CloudWatch alarms and logging
- **🚨 Health Checks**: Automatic container health monitoring

## 📋 Architecture Overview

```
Internet → Application Load Balancer → ECS Containers → S3/SageMaker/Step Functions
                    ↓
            Auto Scaling Group (1-10 instances)
                    ↓
               CloudWatch Monitoring
```

## 🔧 Configuration Options

### Environment Variables

The container supports these environment variables:

```bash
ADPA_ENVIRONMENT=container        # Runtime environment
ADPA_LOG_LEVEL=INFO              # Logging level
ADPA_PORT=8000                   # Web server port
AWS_DEFAULT_REGION=us-east-1     # AWS region
```

### Scaling Configuration

Edit the CloudFormation template to adjust:
- **DesiredCapacity**: Default number of containers (default: 2)
- **CPU/Memory**: Container resources (default: 1024 CPU, 2048 MB)
- **Auto-scaling triggers**: CPU threshold for scaling (default: 70%)

## 🌐 API Endpoints

Your containerized ADPA provides these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/health` | GET | Health check |
| `/api/status` | GET | System status |
| `/api/pipeline/execute` | POST | Execute pipeline |
| `/api/project/status` | GET | Project status |
| `/api/project/next-task` | GET | Next recommendation |

### Example API Usage

```bash
# Check system status
curl http://your-alb-url.amazonaws.com/api/status

# Execute a pipeline
curl -X POST http://your-alb-url.amazonaws.com/api/pipeline/execute \
  -H "Content-Type: application/json" \
  -d '{
    "data_description": "customer purchase data", 
    "objective": "predict churn"
  }'
```

## 📊 Management Commands

### View Container Logs
```bash
aws logs tail /aws/ecs/adpa-development --region us-east-1 --follow
```

### Check Service Status
```bash
aws ecs describe-services \
  --cluster adpa-cluster-development \
  --services adpa-service-development \
  --region us-east-1
```

### Scale Service Manually
```bash
# Scale to 5 containers
aws ecs update-service \
  --cluster adpa-cluster-development \
  --service adpa-service-development \
  --desired-count 5 \
  --region us-east-1
```

### Update Container Image
```bash
# Build and push new image
docker build -t adpa:v2 .
docker tag adpa:v2 your-ecr-uri:v2
docker push your-ecr-uri:v2

# Update service
aws ecs update-service \
  --cluster adpa-cluster-development \
  --service adpa-service-development \
  --force-new-deployment \
  --region us-east-1
```

## 🔒 Security Features

### Network Security
- **VPC Isolation**: Containers run in private subnets
- **Security Groups**: Restrictive firewall rules
- **Load Balancer**: Public access only through ALB

### Data Security
- **KMS Encryption**: All data encrypted at rest
- **IAM Roles**: Least-privilege access policies
- **Secrets Manager**: Secure API key storage
- **TLS**: HTTPS support (configure SSL certificate)

### Container Security
- **Non-root User**: Containers run as unprivileged user
- **Health Checks**: Automatic container restart on failure
- **Resource Limits**: Prevent resource exhaustion

## 🚨 Troubleshooting

### Container Won't Start
```bash
# Check task definition
aws ecs describe-task-definition --task-definition adpa-task-development

# Check service events
aws ecs describe-services --cluster adpa-cluster-development --services adpa-service-development

# View container logs
aws logs tail /aws/ecs/adpa-development --region us-east-1
```

### Health Check Failures
```bash
# Test health endpoint locally
curl http://your-alb-url.amazonaws.com/health

# Check target group health
aws elbv2 describe-target-health --target-group-arn your-target-group-arn
```

### Performance Issues
- **Monitor CPU/Memory**: CloudWatch ECS metrics
- **Check Auto-scaling**: Verify scaling policies are working
- **Database Performance**: Monitor S3 and SageMaker usage

## 💰 Cost Optimization

### Development Environment
- Use `t3.small` instances or Fargate Spot for lower costs
- Set minimum capacity to 1 container
- Enable auto-scaling to scale down during low usage

### Production Environment
- Use reserved capacity for predictable workloads
- Monitor CloudWatch costs and set billing alarms
- Consider scheduled scaling for known traffic patterns

## 🔄 CI/CD Integration

### GitHub Actions Example
```yaml
name: Deploy ADPA Container
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to AWS
        run: ./deploy/container-deploy.sh production adpa us-east-1
```

## 🌟 Advanced Features

### Custom Domain Setup
1. **Route 53**: Create hosted zone
2. **Certificate Manager**: Request SSL certificate
3. **CloudFormation**: Add ALB listener for HTTPS

### Multi-Region Deployment
- Deploy to multiple regions for global availability
- Use CloudFront for global content delivery
- Cross-region replication for disaster recovery

### Monitoring and Alerting
- **CloudWatch Dashboards**: Custom metrics visualization
- **SNS Notifications**: Alert on service failures
- **AWS X-Ray**: Distributed tracing for debugging

## ✅ Success Checklist

After deployment, verify:

- [ ] 🌐 Web interface accessible via load balancer URL
- [ ] ✅ Health check endpoint returns 200 OK
- [ ] 🚀 Can execute pipeline through web interface
- [ ] 📊 API endpoints respond correctly
- [ ] 📈 Auto-scaling policies are active
- [ ] 🔍 CloudWatch logs are being captured
- [ ] 🔐 Security groups properly configured
- [ ] 💾 Data persists to S3 buckets

## 🎉 You're Done!

Your ADPA instance is now running in the cloud with:
- **Global accessibility** via web browser
- **Professional web interface** for easy interaction
- **Automatic scaling** based on demand
- **Enterprise security** and monitoring
- **REST API** for integration with other systems

Visit your ADPA web interface and start building autonomous ML pipelines! 🚀