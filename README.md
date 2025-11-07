# Welcome to your CDK TypeScript project

This is a blank project for CDK development with TypeScript.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

## Useful commands

* `npm run build`   compile typescript to js
* `npm run watch`   watch for changes and compile
* `npm run test`    perform the jest unit tests
* `npx cdk deploy`  deploy this stack to your default AWS account/region
* `npx cdk diff`    compare deployed stack with current state
* `npx cdk synth`   emits the synthesized CloudFormation template


# 0) Configure AWS credentials (choose ONE)
# Using default profile
aws configure
# OR using a named profile
aws configure --profile adpa

Outputs to note (after deploy):

RawBucketName, CuratedBucketName, ArtifactsBucketName

GlueDatabaseName, GlueCrawlerName


```bash
# 1) Create and enter a workspace
mkdir adpa-day1-2 && cd adpa-day1-2

# 2) Initialize CDK TypeScript app
npx cdk init app --language typescript

# 3) Replace the generated files with the code in this document (see file sections below)
#    - package.json, cdk.json, bin/adpa-app.ts, lib/adpa-data-stack.ts

# 4) Install deps
npm install

# 5) Bootstrap (first time per account/region)
# If you use a named profile, add: --profile adpa
cdk bootstrap

# 6) Deploy the data stack (add --profile if you used one)
cdk deploy

# 7) Create & upload sample datasets
python3 scripts/generate_and_upload.py --bucket <RAW_BUCKET_NAME_OUTPUT_FROM_CDK>

# 8) (Optional) Start Glue crawler so Athena sees tables
aws glue start-crawler --name <CrawlerNameFromOutputs>

# 1) Create and enter a workspace
mkdir adpa-day1-2 && cd adpa-day1-2

# 2) Initialize CDK TypeScript app
npx cdk init app --language typescript

# 3) Replace the generated files with the code in this document (see file sections below)
#    - package.json, cdk.json, bin/adpa-app.ts, lib/adpa-data-stack.ts

# 4) Install deps
npm install

# 5) Bootstrap (first time per account/region)
cdk bootstrap

# 6) Deploy the data stack
cdk deploy

# 7) Create & upload sample datasets
python3 scripts/generate_and_upload.py --bucket <RAW_BUCKET_NAME_OUTPUT_FROM_CDK>

# 8) (Optional) Start Glue crawler so Athena sees tables
aws glue start-crawler --name <CrawlerNameFromOutputs>



 ✅  AdpaDataStack

✨  Deployment time: 117.65s

Outputs:
AdpaDataStack.ArtifactsBucketName = adpadatastack-artifactsbucket2aac5544-usu6mmtjs1tf
AdpaDataStack.CuratedBucketName = adpadatastack-curatedbucket6a59c97e-csypjbbtlgtd
AdpaDataStack.GlueCrawlerName = adpa-raw-crawler
AdpaDataStack.GlueDatabaseName = adpa_raw_db
AdpaDataStack.RawBucketName = adpadatastack-rawbucket0c3ee094-46betroebefa
Stack ARN:
arn:aws:cloudformation:us-east-1:337909748531:stack/AdpaDataStack/0efaa9a0-bc1c-11f0-9025-0eda7caa0761