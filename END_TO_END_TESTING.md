# End-to-End System Validation

## 🌐 Live URLs
- **Frontend**: http://adpa-frontend-083308938449-production.s3-website.us-east-2.amazonaws.com
- **API**: https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod

## 📋 API Endpoints Deployed

All 8 endpoints configured and deployed (Deployment ID: kl54n4):

1. ✅ **GET /health** - System health check
2. ✅ **GET /pipelines** - List all pipelines
3. ✅ **POST /pipelines** - Create new pipeline
4. ✅ **GET /pipelines/{id}** - Get pipeline details
5. ✅ **POST /pipelines/{id}/execute** - Execute pipeline
6. ✅ **GET /pipelines/{id}/status** - Get execution status
7. ✅ **POST /data/upload** - Upload dataset
8. ✅ **GET /data/uploads** - List uploaded files

## 🧪 Testing Instructions

### Option 1: Automated API Tests

Run the automated test suite:

```bash
cd /Users/adariprasad/weapon/UMD/DATA650/Group\ Presentation/adpa
python3 test_api_endpoints.py
```

This will test all 8 endpoints and report results.

### Option 2: Manual Browser Testing

1. **Open Frontend**
   ```bash
   open "http://adpa-frontend-083308938449-production.s3-website.us-east-2.amazonaws.com"
   ```

2. **Test UI Flow**:
   - Verify UI loads correctly
   - Check console for any JavaScript errors
   - Test navigation between pages
   - Verify API connectivity indicator

3. **Upload Dataset**:
   - Click "Upload Dataset" or similar button
   - Select a CSV file (or use demo: `demo_customer_churn.csv`)
   - Verify file uploads to S3 successfully
   - Check that filename appears in uploads list

4. **Create Pipeline**:
   - Click "Create Pipeline"
   - Enter dataset path: `s3://adpa-data-083308938449-production/demo_customer_churn.csv`
   - Enter objective: "Predict customer churn with high accuracy"
   - Submit and verify pipeline ID is generated

5. **Execute Pipeline**:
   - Click "Execute" on created pipeline
   - Verify Step Functions execution starts
   - Check execution ARN is returned

6. **Monitor Status**:
   - Click "Refresh Status" or auto-refresh
   - Verify status updates from RUNNING → SUCCEEDED/FAILED
   - Check execution logs and metrics

7. **View Results**:
   - Once complete, view pipeline output
   - Check model metrics, evaluation results
   - Verify CloudWatch logs are accessible

### Option 3: cURL Testing

Test individual endpoints:

```bash
# Health check
curl https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/health

# Create pipeline
curl -X POST https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/pipelines \
  -H "Content-Type: application/json" \
  -d '{"dataset_path":"s3://adpa-data-083308938449-production/demo_customer_churn.csv","objective":"Predict churn"}'

# List pipelines
curl https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/pipelines

# Get pipeline status
curl https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/pipelines/<PIPELINE_ID>/status
```

## 🔍 Expected Outcomes

### ✅ Success Criteria

1. **Frontend Loads**: UI renders without errors, all components visible
2. **API Connectivity**: Health endpoint returns 200 with `{"status": "healthy"}`
3. **Dataset Upload**: Files upload to S3 bucket successfully
4. **Pipeline Creation**: DynamoDB entry created with unique pipeline_id
5. **Pipeline Execution**: Step Functions starts, execution ARN returned
6. **Status Monitoring**: Status updates correctly (RUNNING → SUCCEEDED/FAILED)
7. **Error Handling**: Graceful error messages for invalid inputs
8. **CORS**: No CORS errors in browser console
9. **Performance**: API responses < 3s, frontend loads < 2s

### ❌ Known Issues / Limitations

1. **No Authentication**: API is publicly accessible (Cognito not yet implemented)
2. **No Input Validation**: Minimal validation on dataset paths and objectives
3. **Limited Error Details**: Generic error messages, not user-friendly
4. **No Pagination**: Pipeline list returns all items (could be slow with many pipelines)
5. **No Caching**: Every request hits backend (no CloudFront/caching layer)

## 🐛 Debugging Tips

### Frontend Issues

If frontend doesn't load:
- Check browser console for errors
- Verify S3 bucket policy allows public GetObject
- Check that `index.html` exists in bucket root
- Verify static website hosting is enabled

### API Issues

If API returns errors:
- Check Lambda logs: `aws logs tail /aws/lambda/adpa-lambda-function --follow`
- Verify Lambda has correct IAM permissions
- Check API Gateway CloudWatch logs
- Test Lambda directly in AWS Console

### Integration Issues

If frontend can't reach API:
- Check CORS headers in browser network tab
- Verify API Gateway deployment is to `prod` stage
- Check that frontend has correct API URL in config
- Test API directly with cURL first

## 📊 Success Metrics

Track these metrics during testing:

1. **API Response Times**: All endpoints < 3 seconds
2. **Error Rate**: < 5% of requests fail
3. **Frontend Load Time**: < 2 seconds
4. **Step Functions Success Rate**: > 80% of executions succeed
5. **User Flow Completion**: Can complete full pipeline creation → execution → results flow

## 🎯 Next Steps After Testing

Based on test results:

1. **If all tests pass**: Proceed to Security Hardening (Task 4)
2. **If CORS issues**: Update Lambda CORS headers, redeploy
3. **If integration issues**: Debug API Gateway → Lambda connection
4. **If performance issues**: Add caching, optimize Lambda cold starts
5. **If UX issues**: Enhance error messages, add loading states

## 📝 Test Results Log

Document your findings:

| Test | Status | Notes |
|------|--------|-------|
| Frontend loads | ⬜ | |
| Health endpoint | ⬜ | |
| Create pipeline | ⬜ | |
| List pipelines | ⬜ | |
| Execute pipeline | ⬜ | |
| Monitor status | ⬜ | |
| Upload dataset | ⬜ | |
| List uploads | ⬜ | |
| End-to-end flow | ⬜ | |

**Tester**: _________________  
**Date**: _________________  
**Overall Status**: ⬜ Pass / ⬜ Fail / ⬜ Partial
