#!/bin/bash

# ADPA Deployment Gap Checker
# Comprehensive check for deployment readiness

echo "🔍 ADPA Deployment Gap Analysis"
echo "================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
WARNINGS=0

check_pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    echo -e "${RED}   Fix: $2${NC}"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
    echo -e "${YELLOW}   Note: $2${NC}"
    ((WARNINGS++))
}

echo -e "${BLUE}Phase 1: Prerequisites Check${NC}"
echo "─────────────────────────────"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    check_pass "Python 3 installed ($PYTHON_VERSION)"
else
    check_fail "Python 3 not found" "Install Python 3.8+"
fi

# Check pip
if command -v pip &> /dev/null || command -v pip3 &> /dev/null; then
    check_pass "pip package manager available"
else
    check_fail "pip not found" "Install pip: python3 -m ensurepip --upgrade"
fi

# Check AWS CLI
if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version | cut -d' ' -f1)
    check_pass "AWS CLI installed ($AWS_VERSION)"
    
    # Check AWS credentials
    if aws sts get-caller-identity &> /dev/null; then
        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        check_pass "AWS credentials configured (Account: $ACCOUNT_ID)"
    else
        check_fail "AWS credentials not configured" "Run: aws configure"
    fi
else
    check_fail "AWS CLI not installed" "Install: pip install awscli"
fi

# Check jq (needed for parsing JSON in scripts)
if command -v jq &> /dev/null; then
    check_pass "jq JSON processor available"
else
    check_warn "jq not found" "Install for better script experience: brew install jq"
fi

echo ""
echo -e "${BLUE}Phase 2: Project Structure Check${NC}"
echo "─────────────────────────────────────"

# Check if we're in the right directory
if [ -f "requirements.txt" ] && [ -f "setup.py" ] && [ -d "src" ]; then
    check_pass "In ADPA project root directory"
else
    check_fail "Not in ADPA project root" "cd to /Users/adariprasad/weapon/UMD/DATA650/Group\ Presentation/adpa"
fi

# Check key files
KEY_FILES=(
    "requirements.txt"
    "src/agent/core/master_agent.py"
    "src/pipeline/evaluation/reporter.py"
    "src/aws/stepfunctions/orchestrator.py"
    "mcp_server/server.py"
    "deploy.sh"
    "deploy/aws-deploy.sh"
    "deploy/make-global.sh"
    "deploy/cloudformation/adpa-infrastructure.yaml"
)

for file in "${KEY_FILES[@]}"; do
    if [ -f "$file" ]; then
        check_pass "Key file exists: $file"
    else
        check_fail "Missing key file: $file" "Regenerate project or check file path"
    fi
done

# Check directories
KEY_DIRS=(
    "src/aws"
    "src/agent"
    "src/pipeline"
    "data"
    "deploy"
)

for dir in "${KEY_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        check_pass "Key directory exists: $dir"
    else
        check_fail "Missing directory: $dir" "Create directory: mkdir -p $dir"
    fi
done

echo ""
echo -e "${BLUE}Phase 3: Python Dependencies Check${NC}"
echo "──────────────────────────────────────"

# Check virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    check_pass "Virtual environment active: $(basename $VIRTUAL_ENV)"
else
    check_warn "No virtual environment detected" "Consider: python3 -m venv venv && source venv/bin/activate"
fi

# Check key Python packages
PYTHON_PACKAGES=(
    "boto3"
    "pandas"
    "numpy"
    "scikit-learn"
    "requests"
    "pydantic"
)

echo "Checking Python packages..."
for package in "${PYTHON_PACKAGES[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        check_pass "Python package: $package"
    else
        check_fail "Missing Python package: $package" "pip install $package"
    fi
done

# Test core imports
echo "Testing ADPA core imports..."
if python3 -c "
import sys
sys.path.insert(0, '.')
from src.agent.core.master_agent import MasterAgenticController
from src.pipeline.evaluation.reporter import ReportingStep
from src.aws.stepfunctions import StepFunctionsOrchestrator
" 2>/dev/null; then
    check_pass "ADPA core components importable"
else
    check_fail "ADPA core import issues" "Check Python path and dependencies"
fi

echo ""
echo -e "${BLUE}Phase 4: Deployment Scripts Check${NC}"
echo "──────────────────────────────────────"

# Check script permissions
SCRIPTS=(
    "deploy.sh"
    "deploy/aws-deploy.sh"
    "deploy/make-global.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -x "$script" ]; then
        check_pass "Script executable: $script"
    else
        check_fail "Script not executable: $script" "chmod +x $script"
    fi
done

# Check CloudFormation templates syntax
if command -v aws &> /dev/null; then
    echo "Validating CloudFormation templates..."
    
    if [ -f "deploy/cloudformation/adpa-infrastructure.yaml" ]; then
        if aws cloudformation validate-template --template-body file://deploy/cloudformation/adpa-infrastructure.yaml &> /dev/null; then
            check_pass "CloudFormation template valid: adpa-infrastructure.yaml"
        else
            check_fail "Invalid CloudFormation template: adpa-infrastructure.yaml" "Check YAML syntax"
        fi
    fi
fi

echo ""
echo -e "${BLUE}Phase 5: AWS Environment Check${NC}"
echo "───────────────────────────────────"

if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null; then
    # Check AWS region
    AWS_REGION=$(aws configure get region)
    if [ -n "$AWS_REGION" ]; then
        check_pass "AWS region configured: $AWS_REGION"
    else
        check_warn "AWS region not configured" "Set default region: aws configure set region us-east-1"
    fi
    
    # Check AWS permissions (basic)
    if aws iam get-user &> /dev/null || aws sts get-caller-identity &> /dev/null; then
        check_pass "AWS IAM permissions working"
    else
        check_warn "Limited AWS permissions" "May need additional IAM policies"
    fi
    
    # Check if CloudFormation stacks exist
    if aws cloudformation describe-stacks --stack-name adpa-infrastructure-development 2>/dev/null | grep -q "StackStatus"; then
        STACK_STATUS=$(aws cloudformation describe-stacks --stack-name adpa-infrastructure-development --query 'Stacks[0].StackStatus' --output text 2>/dev/null)
        check_pass "Existing ADPA infrastructure found (Status: $STACK_STATUS)"
    else
        check_warn "No existing ADPA infrastructure" "Will be created during deployment"
    fi
else
    check_warn "Cannot check AWS environment" "AWS CLI not configured"
fi

echo ""
echo -e "${BLUE}Phase 6: MCP Integration Check${NC}"
echo "──────────────────────────────────"

# Test MCP server
if python3 -c "
import sys
sys.path.insert(0, '.')
from mcp_server.server import ADPAProjectManager
from pathlib import Path
manager = ADPAProjectManager(Path('.'))
status = manager.get_project_status()
print(f'MCP completion: {status.get(\"overall_completion\", 0)}%')
" 2>/dev/null; then
    check_pass "MCP server functional"
else
    check_fail "MCP server issues" "Check mcp_server/server.py"
fi

echo ""
echo "════════════════════════════════════════════"
echo -e "${BLUE}📊 DEPLOYMENT READINESS SUMMARY${NC}"
echo "════════════════════════════════════════════"

TOTAL=$((PASSED + FAILED + WARNINGS))
PASS_RATE=$((PASSED * 100 / TOTAL))

echo -e "✅ ${GREEN}Passed${NC}: $PASSED"
echo -e "❌ ${RED}Failed${NC}: $FAILED" 
echo -e "⚠️  ${YELLOW}Warnings${NC}: $WARNINGS"
echo -e "📈 ${BLUE}Pass Rate${NC}: $PASS_RATE%"

echo ""
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ADPA IS READY FOR DEPLOYMENT!${NC}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Local deployment: ./deploy.sh local"
    echo "2. AWS deployment: ./deploy/aws-deploy.sh development adpa us-east-1"
    echo "3. Global access: ./deploy/make-global.sh development adpa"
    echo ""
    echo "📋 Follow the complete guide: STEP_BY_STEP_DEPLOYMENT.md"
elif [ $FAILED -le 2 ]; then
    echo -e "${YELLOW}⚠️  ADPA NEEDS MINOR FIXES${NC}"
    echo "Fix the failed items above, then proceed with deployment."
else
    echo -e "${RED}❌ ADPA NEEDS SIGNIFICANT FIXES${NC}"
    echo "Address the critical issues above before attempting deployment."
fi

echo ""
echo "For detailed deployment instructions, see: STEP_BY_STEP_DEPLOYMENT.md"

exit $FAILED