"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.apiService = void 0;
const axios_1 = __importDefault(require("axios"));
// Configuration - Updated to use actual deployed API Gateway
const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod';
const TIMEOUT = 60000; // 60 seconds for longer operations
class ApiService {
    api;
    constructor() {
        this.api = axios_1.default.create({
            baseURL: API_BASE_URL,
            timeout: TIMEOUT,
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
        });
        // Request interceptor for adding auth tokens, etc.
        this.api.interceptors.request.use((config) => {
            // Add any authentication headers here
            // const token = localStorage.getItem('authToken');
            // if (token) {
            //   config.headers.Authorization = `Bearer ${token}`;
            // }
            return config;
        }, (error) => Promise.reject(error));
        // Response interceptor for handling errors globally
        this.api.interceptors.response.use((response) => response, (error) => {
            console.error('API Error:', error);
            if (error.response?.status === 401) {
                // Handle unauthorized access
                localStorage.removeItem('authToken');
                window.location.href = '/login';
            }
            return Promise.reject(error);
        });
    }
    // Pipelines API
    async getPipelines() {
        try {
            const response = await this.api.get('/pipelines');
            if (response.data.pipelines) {
                // Handle the actual Lambda response format - map backend fields to frontend interface
                return response.data.pipelines.map((pipeline) => ({
                    id: pipeline.id || pipeline.pipeline_id,
                    name: pipeline.name || pipeline.objective || 'Unnamed Pipeline',
                    status: pipeline.status || 'pending',
                    createdAt: pipeline.created_at || new Date().toISOString(),
                    updatedAt: pipeline.completed_at || pipeline.updated_at || pipeline.created_at || new Date().toISOString(),
                    objective: pipeline.objective || '',
                    dataset: pipeline.dataset_path || '',
                    progress: this.calculateProgress(pipeline.status),
                    description: pipeline.description || '',
                    type: pipeline.type || 'classification',
                    // Extract metrics from result object
                    model: pipeline.result?.model_path || undefined,
                    accuracy: pipeline.result?.performance_metrics?.accuracy ||
                        pipeline.result?.metrics?.accuracy ||
                        pipeline.result?.performance_metrics?.r2_score ||
                        pipeline.result?.metrics?.r2_score || undefined,
                    // Pass through the full result object for detailed views
                    result: pipeline.result,
                    modelPath: pipeline.result?.model_path,
                    error: pipeline.error || (pipeline.result?.status === 'FAILED' ? pipeline.result?.error : undefined),
                    aiInsights: pipeline.result?.ai_insights || pipeline.result?.summary,
                }));
            }
            return response.data.data || [];
        }
        catch (error) {
            console.error('Error fetching pipelines:', error);
            // Return empty array on error to prevent UI crashes
            return [];
        }
    }
    calculateProgress(status) {
        switch (status) {
            case 'completed': return 100;
            case 'running': return 50; // Fixed value instead of random
            case 'failed': return 0;
            default: return 0;
        }
    }
    async getPipeline(id) {
        try {
            const response = await this.api.get(`/pipelines/${id}`);
            const pipeline = response.data;
            // Map backend response to frontend Pipeline interface
            return {
                id: pipeline.id || pipeline.pipeline_id,
                name: pipeline.name || pipeline.objective || 'Unnamed Pipeline',
                status: pipeline.status || 'pending',
                createdAt: pipeline.created_at || new Date().toISOString(),
                updatedAt: pipeline.completed_at || pipeline.updated_at || pipeline.created_at || new Date().toISOString(),
                objective: pipeline.objective || '',
                dataset: pipeline.dataset_path || '',
                progress: this.calculateProgress(pipeline.status),
                description: pipeline.description || '',
                type: pipeline.type || 'classification',
                model: pipeline.result?.model_path || undefined,
                accuracy: pipeline.result?.performance_metrics?.accuracy ||
                    pipeline.result?.metrics?.accuracy ||
                    pipeline.result?.performance_metrics?.r2_score ||
                    pipeline.result?.metrics?.r2_score || undefined,
                result: pipeline.result,
                modelPath: pipeline.result?.model_path,
                error: pipeline.error || (pipeline.result?.status === 'FAILED' ? pipeline.result?.error : undefined),
                aiInsights: pipeline.result?.ai_insights || pipeline.result?.summary,
            };
        }
        catch (error) {
            console.error('Error fetching pipeline:', error);
            return null;
        }
    }
    async createPipeline(pipeline) {
        try {
            // Transform to Lambda expected format
            const pipelineRequest = {
                dataset_path: pipeline.dataset || '',
                objective: pipeline.objective || '',
                use_real_aws: pipeline.useRealAws !== undefined ? pipeline.useRealAws : true, // Default to true (real AWS)
                name: pipeline.name || '',
                description: pipeline.description || '',
                type: pipeline.type || 'classification'
            };
            const response = await this.api.post('/pipelines', pipelineRequest);
            if (response.data.pipeline_id) {
                return {
                    id: response.data.pipeline_id,
                    name: pipeline.name || 'New Pipeline',
                    status: response.data.status || 'pending',
                    createdAt: response.data.timestamp || new Date().toISOString(),
                    updatedAt: response.data.timestamp || new Date().toISOString(),
                    objective: pipeline.objective || '',
                    dataset: pipeline.dataset,
                    progress: 0,
                    description: pipeline.description,
                    type: pipeline.type || 'classification'
                };
            }
            return response.data.data || null;
        }
        catch (error) {
            console.error('Error creating pipeline:', error);
            throw error;
        }
    }
    async updatePipeline(id, updates) {
        try {
            const response = await this.api.put(`/pipelines/${id}`, updates);
            return response.data.data || null;
        }
        catch (error) {
            console.error('Error updating pipeline:', error);
            throw error;
        }
    }
    async deletePipeline(id) {
        try {
            await this.api.delete(`/pipelines/${id}`);
            return true;
        }
        catch (error) {
            console.error('Error deleting pipeline:', error);
            return false;
        }
    }
    async executePipeline(id) {
        try {
            const response = await this.api.post(`/pipelines/${id}/execute`);
            return response.data.data || null;
        }
        catch (error) {
            console.error('Error executing pipeline:', error);
            throw error;
        }
    }
    // Pipeline Executions API
    async getExecution(id) {
        try {
            const response = await this.api.get(`/executions/${id}`);
            return response.data.data || null;
        }
        catch (error) {
            console.error('Error fetching execution:', error);
            return null;
        }
    }
    async getPipelineExecutions(pipelineId) {
        try {
            const response = await this.api.get(`/pipelines/${pipelineId}/executions`);
            return response.data.data || [];
        }
        catch (error) {
            console.error('Error fetching pipeline executions:', error);
            return [];
        }
    }
    // Model Results API
    async getModelResults(pipelineId) {
        try {
            const response = await this.api.get(`/pipelines/${pipelineId}/results`);
            return response.data.data || null;
        }
        catch (error) {
            console.error('Error fetching model results:', error);
            return null;
        }
    }
    async downloadModel(pipelineId) {
        try {
            const response = await this.api.get(`/pipelines/${pipelineId}/download`, {
                responseType: 'blob',
            });
            return response.data;
        }
        catch (error) {
            console.error('Error downloading model:', error);
            return null;
        }
    }
    // Data Upload API
    async uploadData(file) {
        try {
            // Read file content and convert to base64
            const fileContent = await file.text();
            const base64Content = btoa(fileContent);
            // Send as JSON payload (Lambda expects this format)
            const uploadPayload = {
                filename: file.name,
                content: base64Content,
                encoding: 'base64'
            };
            const response = await this.api.post('/data/upload', uploadPayload, {
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            // Build data upload response
            const dataUpload = {
                id: response.data.id || response.data.upload_id || `upload-${Date.now()}`,
                filename: file.name,
                size: file.size,
                uploadedAt: response.data.uploadedAt || new Date().toISOString(),
                columns: [],
                rowCount: 0,
                preview: []
            };
            // Parse CSV to get column info if it's a CSV file
            if (file.type === 'text/csv' || file.name.endsWith('.csv')) {
                const lines = fileContent.split('\n').filter(line => line.trim());
                if (lines.length > 0) {
                    const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''));
                    const preview = lines.slice(1, 6).map(line => {
                        const values = line.split(',').map(v => v.trim().replace(/"/g, ''));
                        const row = {};
                        headers.forEach((header, index) => {
                            row[header] = values[index] || '';
                        });
                        return row;
                    });
                    dataUpload.columns = headers;
                    dataUpload.rowCount = lines.length - 1;
                    dataUpload.preview = preview;
                }
            }
            return dataUpload;
        }
        catch (error) {
            console.error('Error uploading data:', error);
            throw error;
        }
    }
    async getUploadedDatasets() {
        try {
            const response = await this.api.get('/data/uploads');
            return response.data.data || [];
        }
        catch (error) {
            console.error('Error fetching uploaded datasets:', error);
            return [];
        }
    }
    // Dashboard API
    async getDashboardStats() {
        try {
            // Get real pipeline data to calculate stats
            const pipelines = await this.getPipelines();
            const totalPipelines = pipelines.length;
            const runningPipelines = pipelines.filter(p => p.status === 'running').length;
            const completedPipelines = pipelines.filter(p => p.status === 'completed').length;
            const failedPipelines = pipelines.filter(p => p.status === 'failed').length;
            const successRate = totalPipelines > 0 ? (completedPipelines / totalPipelines) * 100 : 0;
            // Calculate average execution time from completed pipelines
            const completedWithTimes = pipelines.filter(p => p.status === 'completed' && p.createdAt && p.updatedAt);
            const averageExecutionTime = completedWithTimes.length > 0
                ? completedWithTimes.reduce((sum, p) => {
                    const start = new Date(p.createdAt).getTime();
                    const end = new Date(p.updatedAt).getTime();
                    return sum + (end - start) / 1000; // Convert to seconds
                }, 0) / completedWithTimes.length
                : 0;
            return {
                totalPipelines,
                runningPipelines,
                completedPipelines,
                failedPipelines,
                averageExecutionTime,
                successRate,
            };
        }
        catch (error) {
            console.error('Error fetching dashboard stats:', error);
            return {
                totalPipelines: 0,
                runningPipelines: 0,
                completedPipelines: 0,
                failedPipelines: 0,
                averageExecutionTime: 0,
                successRate: 0,
            };
        }
    }
    // Health Check
    async healthCheck() {
        try {
            const response = await this.api.get('/health');
            return response.status === 200;
        }
        catch (error) {
            console.error('Health check failed:', error);
            return false;
        }
    }
    // Real-time pipeline monitoring - returns full pipeline data with steps and metrics
    async monitorPipeline(pipelineId) {
        try {
            const response = await this.api.get(`/pipelines/${pipelineId}`);
            const data = response.data.data || response.data || null;
            // If the pipeline has a result object with real execution data, extract it
            if (data && data.result) {
                const result = typeof data.result === 'string' ? JSON.parse(data.result) : data.result;
                return {
                    ...data,
                    steps: result.steps || data.steps,
                    logs: result.logs || data.logs,
                    performance_metrics: result.performance_metrics || data.performance_metrics,
                    feature_importance: result.feature_importance || data.feature_importance,
                    execution_time: result.execution_time || data.execution_time,
                    training_time: result.training_time || data.training_time,
                    model_type: result.model_type || data.model_type,
                };
            }
            return data;
        }
        catch (error) {
            console.error('Error monitoring pipeline:', error);
            return null;
        }
    }
    // Get real-time execution logs
    async getPipelineLogs(pipelineId) {
        try {
            const response = await this.api.get(`/pipelines/${pipelineId}/logs`);
            return response.data.logs || response.data.data || [];
        }
        catch (error) {
            console.error('Error fetching pipeline logs:', error);
            return [];
        }
    }
    // Get pipeline execution steps
    async getPipelineSteps(pipelineId) {
        try {
            const pipelineData = await this.monitorPipeline(pipelineId);
            if (pipelineData?.steps) {
                return pipelineData.steps;
            }
            // If steps are in result object
            if (pipelineData?.result?.steps) {
                return pipelineData.result.steps;
            }
            return [];
        }
        catch (error) {
            console.error('Error fetching pipeline steps:', error);
            return [];
        }
    }
    // Execute pipeline
    async executePipelineById(pipelineId, useRealAws = false) {
        try {
            const response = await this.api.post(`/pipelines/${pipelineId}/execute`, {
                use_real_aws: useRealAws
            });
            return response.data.data || response.data || null;
        }
        catch (error) {
            console.error('Error executing pipeline:', error);
            throw error;
        }
    }
    // Stop running pipeline (not implemented in current Lambda but adding for completeness)
    async stopPipeline(pipelineId) {
        try {
            await this.api.post(`/pipelines/${pipelineId}/stop`);
            return true;
        }
        catch (error) {
            console.error('Error stopping pipeline:', error);
            return false;
        }
    }
}
exports.apiService = new ApiService();
exports.default = exports.apiService;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiYXBpLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiYXBpLnRzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7Ozs7OztBQUFBLGtEQUE0RDtBQVU1RCw2REFBNkQ7QUFDN0QsTUFBTSxZQUFZLEdBQUcsT0FBTyxDQUFDLEdBQUcsQ0FBQyxpQkFBaUIsSUFBSSw2REFBNkQsQ0FBQztBQUNwSCxNQUFNLE9BQU8sR0FBRyxLQUFLLENBQUMsQ0FBQyxtQ0FBbUM7QUFFMUQsTUFBTSxVQUFVO0lBQ04sR0FBRyxDQUFnQjtJQUUzQjtRQUNFLElBQUksQ0FBQyxHQUFHLEdBQUcsZUFBSyxDQUFDLE1BQU0sQ0FBQztZQUN0QixPQUFPLEVBQUUsWUFBWTtZQUNyQixPQUFPLEVBQUUsT0FBTztZQUNoQixPQUFPLEVBQUU7Z0JBQ1AsY0FBYyxFQUFFLGtCQUFrQjtnQkFDbEMsUUFBUSxFQUFFLGtCQUFrQjthQUM3QjtTQUNGLENBQUMsQ0FBQztRQUVILG1EQUFtRDtRQUNuRCxJQUFJLENBQUMsR0FBRyxDQUFDLFlBQVksQ0FBQyxPQUFPLENBQUMsR0FBRyxDQUMvQixDQUFDLE1BQU0sRUFBRSxFQUFFO1lBQ1Qsc0NBQXNDO1lBQ3RDLG1EQUFtRDtZQUNuRCxlQUFlO1lBQ2Ysc0RBQXNEO1lBQ3RELElBQUk7WUFDSixPQUFPLE1BQU0sQ0FBQztRQUNoQixDQUFDLEVBQ0QsQ0FBQyxLQUFLLEVBQUUsRUFBRSxDQUFDLE9BQU8sQ0FBQyxNQUFNLENBQUMsS0FBSyxDQUFDLENBQ2pDLENBQUM7UUFFRixvREFBb0Q7UUFDcEQsSUFBSSxDQUFDLEdBQUcsQ0FBQyxZQUFZLENBQUMsUUFBUSxDQUFDLEdBQUcsQ0FDaEMsQ0FBQyxRQUFRLEVBQUUsRUFBRSxDQUFDLFFBQVEsRUFDdEIsQ0FBQyxLQUFLLEVBQUUsRUFBRTtZQUNSLE9BQU8sQ0FBQyxLQUFLLENBQUMsWUFBWSxFQUFFLEtBQUssQ0FBQyxDQUFDO1lBRW5DLElBQUksS0FBSyxDQUFDLFFBQVEsRUFBRSxNQUFNLEtB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IEF4aW9zSW5zdGFuY2UsIEF4aW9zUmVzcG9uc2UgfSBmcm9tICdheGlvcyc7XG5pbXBvcnQge1xuICBQaXBlbGluZSxcbiAgUGlwZWxpbmVFeGVjdXRpb24sXG4gIE1vZGVsUmVzdWx0cyxcbiAgRGF0YVVwbG9hZCxcbiAgQXBpUmVzcG9uc2UsXG4gIERhc2hib2FyZFN0YXRzXG59IGZyb20gJy4uL3R5cGVzJztcblxuLy8gQ29uZmlndXJhdGlvbiAtIFVwZGF0ZWQgdG8gdXNlIGFjdHVhbCBkZXBsb3llZCBBUEkgR2F0ZXdheVxuY29uc3QgQVBJX0JBU0VfVVJMID0gcHJvY2Vzcy5lbnYuUkVBQ1RfQVBQX0FQSV9VUkwgfHwgJ2h0dHBzOi8vY3Ixa2tqNzIxMy5leGVjdXRlLWFwaS51cy1lYXN0LTIuYW1hem9uYXdzLmNvbS9wcm9kJztcbmNvbnN0IFRJTUVPVVQgPSA2MDAwMDsgLy8gNjAgc2Vjb25kcyBmb3IgbG9uZ2VyIG9wZXJhdGlvbnNcblxuY2xhc3MgQXBpU2VydmljZSB7XG4gIHByaXZhdGUgYXBpOiBBeGlvc0luc3RhbmNlO1xuXG4gIGNvbnN0cnVjdG9yKCkge1xuICAgIHRoaXMuYXBpID0gYXhpb3MuY3JlYXRlKHtcbiAgICAgIGJhc2VVUkw6IEFQSV9CQVNFX1VSTCxcbiAgICAgIHRpbWVvdXQ6IFRJTUVPVVQsXG4gICAgICBoZWFkZXJzOiB7XG4gICAgICAgICdDb250ZW50LVR5cGUnOiAnYXBwbGljYXRpb24vanNvbicsXG4gICAgICAgICdBY2NlcHQnOiAnYXBwbGljYXRpb24vanNvbicsXG4gICAgICB9LFxuICAgIH0pO1xuXG4gICAgLy8gUmVxdWVzdCBpbnRlcmNlcHRvciBmb3IgYWRkaW5nIGF1dGggdG9rZW5zLCBldGMuXG4gICAgdGhpcy5hcGkuaW50ZXJjZXB0b3JzLnJlcXVlc3QudXNlKFxuICAgICAgKGNvbmZpZykgPT4ge1xuICAgICAgICAvLyBBZGQgYW55IGF1dGhlbnRpY2F0aW9uIGhlYWRlcnMgaGVyZVxuICAgICAgICAvLyBjb25zdCB0b2tlbiA9IGxvY2FsU3RvcmFnZS5nZXRJdGVtKCdhdXRoVG9rZW4nKTtcbiAgICAgICAgLy8gaWYgKHRva2VuKSB7XG4gICAgICAgIC8vICAgY29uZmlnLmhlYWRlcnMuQXV0aG9yaXphdGlvbiA9IGBCZWFyZXIgJHt0b2tlbn1gO1xuICAgICAgICAvLyB9XG4gICAgICAgIHJldHVybiBjb25maWc7XG4gICAgICB9LFxuICAgICAgKGVycm9yKSA9PiBQcm9taXNlLnJlamVjdChlcnJvcilcbiAgICApO1xuXG4gICAgLy8gUmVzcG9uc2UgaW50ZXJjZXB0b3IgZm9yIGhhbmRsaW5nIGVycm9ycyBnbG9iYWxseVxuICAgIHRoaXMuYXBpLmludGVyY2VwdG9ycy5yZXNwb25zZS51c2UoXG4gICAgICAocmVzcG9uc2UpID0+IHJlc3BvbnNlLFxuICAgICAgKGVycm9yKSA9PiB7XG4gICAgICAgIGNvbnNvbGUuZXJyb3IoJ0FQSSBFcnJvcjonLCBlcnJvcik7XG4gICAgICAgIFxuICAgICAgICBpZiAoZXJyb3IucmVzcG9uc2U/LnN0YXR1cyA9PT0gNDAxKSB7XG4gICAgICAgICAgLy8gSGFuZGxlIHVuYXV0aG9yaXplZCBhY2Nlc3NcbiAgICAgICAgICBsb2NhbFN0b3JhZ2UucmVtb3ZlSXRlbSgnYXV0aFRva2VuJyk7XG4gICAgICAgICAgd2luZG93LmxvY2F0aW9uLmhyZWYgPSAnL2xvZ2luJztcbiAgICAgICAgfVxuICAgICAgICBcbiAgICAgICAgcmV0dXJuIFByb21pc2UucmVqZWN0KGVycm9yKTtcbiAgICAgIH1cbiAgICApO1xuICB9XG5cbiAgLy8gUGlwZWxpbmVzIEFQSVxuICBhc3luYyBnZXRQaXBlbGluZXMoKTogUHJvbWlzZTxQaXBlbGluZVtdPiB7XG4gICAgdHJ5IHtcbiAgICAgIGNvbnN0IHJlc3BvbnNlOiBBeGlvc1Jlc3BvbnNlPEFwaVJlc3BvbnNlPFBpcGVsaW5lW10+PiA9IGF3YWl0IHRoaXMuYXBpLmdldCgnL3BpcGVsaW5lcycpO1xuICAgICAgaWYgKHJlc3BvbnNlLmRhdGEucGlwZWxpbmVzKSB7XG4gICAgICAgIC8vIEhhbmRsZSB0aGUgYWN0dWFsIExhbWJkYSByZXNwb25zZSBmb3JtYXQgLSBtYXAgYmFja2VuZCBmaWVsZHMgdG8gZnJvbnRlbmQgaW50ZXJmYWNlXG4gICAgICAgIHJldHVybiByZXNwb25zZS5kYXRhLnBpcGVsaW5lcy5tYXAoKHBpcGVsaW5lOiBhbnkpID0+ICh7XG4gICAgICAgICAgaWQ6IHBpcGVsaW5lLmlkIHx8IHBpcGVsaW5lLnBpcGVsaW5lX2lkLFxuICAgICAgICAgIG5hbWU6IHBpcGVsaW5lLm5hbWUgfHwgcGlwZWxpbmUub2JqZWN0aXZlIHx8ICdVbm5hbWVkIFBpcGVsaW5lJyxcbiAgICAgICAgICBzdGF0dXM6IHBpcGVsaW5lLnN0YXR1cyB8fCAncGVuZGluZycsXG4gICAgICAgICAgY3JlYXRlZEF0OiBwaXBlbGluZS5jcmVhdGVkX2F0IHx8IG5ldyBEYXRlKCkudG9JU09TdHJpbmcoKSxcbiAgICAgICAgICB1cGRhdGVkQXQ6IHBpcGVsaW5lLmNvbXBsZXRlZF9hdCB8fCBwaXBlbGluZS51cGRhdGVkX2F0IHx8IHBpcGVsaW5lLmNyZWF0ZWRfYXQgfHwgbmV3IERhdGUoKS50b0lTT1N0cmluZygpLFxuICAgICAgICAgIG9iamVjdGl2ZTogcGlwZWxpbmUub2JqZWN0aXZlIHx8ICcnLFxuICAgICAgICAgIGRhdGFzZXQ6IHBpcGVsaW5lLmRhdGFzZXRfcGF0aCB8fCAnJyxcbiAgICAgICAgICBwcm9ncmVzczogdGhpcy5jYWxjdWxhdGVQcm9ncmVzcyhwaXBlbGluZS5zdGF0dXMpLFxuICAgICAgICAgIGRlc2NyaXB0aW9uOiBwaXBlbGluZS5kZXNjcmlwdGlvbiB8fCAnJyxcbiAgICAgICAgICB0eXBlOiBwaXBlbGluZS50eXBlIHx8ICdjbGFzc2lmaWNhdGlvbicsXG4gICAgICAgICAgLy8gRXh0cmFjdCBtZXRyaWNzIGZyb20gcmVzdWx0IG9iamVjdFxuICAgICAgICAgIG1vZGVsOiBwaXBlbGluZS5yZXN1bHQ/Lm1vZGVsX3BhdGggfHwgdW5kZWZpbmVkLFxuICAgICAgICAgIGFjY3VyYWN5OiBwaXBlbGluZS5yZXN1bHQ/LnBlcmZvcm1hbmNlX21ldHJpY3M/LmFjY3VyYWN5IHx8IFxuICAgICAgICAgICAgICAgICAgIHBpcGVsaW5lLnJlc3VsdD8ubWV0cmljcz8uYWNjdXJhY3kgfHxcbiAgICAgICAgICAgICAgICAgICBwaXBlbGluZS5yZXN1bHQ/LnBlcmZvcm1hbmNlX21ldHJpY3M/LnIyX3Njb3JlIHx8IFxuICAgICAgICAgICAgICAgICAgIHBpcGVsaW5lLnJlc3VsdD8ubWV0cmljcz8ucjJfc2NvcmUgfHwgdW5kZWZpbmVkLFxuICAgICAgICAgIC8vIFBhc3MgdGhyb3VnaCB0aGUgZnVsbCByZXN1bHQgb2JqZWN0IGZvciBkZXRhaWxlZCB2aWV3c1xuICAgICAgICAgIHJlc3VsdDogcGlwZWxpbmUucmVzdWx0LFxuICAgICAgICAgIG1vZGVsUGF0aDogcGlwZWxpbmUucmVzdWx0Py5tb2RlbF9wYXRoLFxuICAgICAgICAgIGVycm9yOiBwaXBlbGluZS5lcnJvciB8fCAocGlwZWxpbmUucmVzdWx0Py5zdGF0dXMgPT09ICdGQUlMRUQnID8gcGlwZWxpbmUucmVzdWx0Py5lcnJvciA6IHVuZGVmaW5lZCksXG4gICAgICAgICAgYWlJbnNpZ2h0czogcGlwZWxpbmUucmVzdWx0Py5haV9pbnNpZ2h0cyB8fCBwaXBlbGluZS5yZXN1bHQ/LnN1bW1hcnksXG4gICAgICAgIH0pKTtcbiAgICAgIH1cbiAgICAgIHJldHVybiByZXNwb25zZS5kYXRhLmRhdGEgfHwgW107XG4gICAgfSBjYXRjaCAoZXJyb3IpIHtcbiAgICAgIGNvbnNvbGUuZXJyb3IoJ0Vycm9yIGZldGNoaW5nIHBpcGVsaW5lczonLCBlcnJvcik7XG4gICAgICAvLyBSZXR1cm4gZW1wdHkgYXJyYXkgb24gZXJyb3IgdG8gcHJldmVudCBVSSBjcmFzaGVzXG4gICAgICByZXR1cm4gW107XG4gICAgfVxuICB9XG5cbiAgcHJpdmF0ZSBjYWxjdWxhdGVQcm9ncmVzcyhzdGF0dXM6IHN0cmluZyk6IG51bWJlciB7XG4gICAgc3dpdGNoIChzdGF0dXMpIHtcbiAgICAgIGNhc2UgJ2NvbXBsZXRlZCc6IHJldHVybiAxMDA7XG4gICAgICBjYXNlICdydW5uaW5nJzogcmV0dXJuIDUwOyAvLyBGaXhlZCB2YWx1ZSBpbnN0ZWFkIG9mIHJhbmRvbVxuICAgICAgY2FzZSAnZmFpbGVkJzogcmV0dXJuIDA7XG4gICAgICBkZWZhdWx0OiByZXR1cm4gMDtcbiAgICB9XG4gIH1cblxuICBhc3luYyBnZXRQaXBlbGluZShpZDogc3RyaW5nKTogUHJvbWlzZTxQaXBlbGluZSB8IG51bGw+IHtcbiAgICB0cnkge1xuICAgICAgY29uc3QgcmVzcG9uc2U6IEF4aW9zUmVzcG9uc2U8YW55PiA9IGF3YWl0IHRoaXMuYXBpLmdldChgL3BpcGVsaW5lcy8ke2lkfWApO1xuICAgICAgY29uc3QgcGlwZWxpbmUgPSByZXNwb25zZS5kYXRhO1xuICAgICAgXG4gICAgICAvLyBNYXAgYmFja2VuZCByZXNwb25zZSB0byBmcm9udGVuZCBQaXBlbGluZSBpbnRlcmZhY2VcbiAgICAgIHJldHVybiB7XG4gICAgICAgIGlkOiBwaXBlbGluZS5pZCB8fCBwaXBlbGluZS5waXBlbGluZV9pZCxcbiAgICAgICAgbmFtZTogcGlwZWxpbmUubmFtZSB8fCBwaXBlbGluZS5vYmplY3RpdmUgfHwgJ1VubmFtZWQgUGlwZWxpbmUnLFxuICAgICAgICBzdGF0dXM6IHBpcGVsaW5lLnN0YXR1cyB8fCAncGVuZGluZycsXG4gICAgICAgIGNyZWF0ZWRBdDogcGlwZWxpbmUuY3JlYXRlZF9hdCB8fCBuZXcgRGF0ZSgpLnRvSVNPU3RyaW5nKCksXG4gICAgICAgIHVwZGF0ZWRBdDogcGlwZWxpbmUuY29tcGxldGVkX2F0IHx8IHBpcGVsaW5lLnVwZGF0ZWRfYXQgfHwgcGlwZWxpbmUuY3JlYXRlZF9hdCB8fCBuZXcgRGF0ZSgpLnRvSVNPU3RyaW5nKCksXG4gICAgICAgIG9iamVjdGl2ZTogcGlwZWxpbmUub2JqZWN0aXZlIHx8ICcnLFxuICAgICAgICBkYXRhc2V0OiBwaXBlbGluZS5kYXRhc2V0X3BhdGggfHwgJycsXG4gICAgICAgIHByb2dyZXNzOiB0aGlzLmNhbGN1bGF0ZVByb2dyZXNzKHBpcGVsaW5lLnN0YXR1cyksXG4gICAgICAgIGRlc2NyaXB0aW9uOiBwaXBlbGluZS5kZXNjcmlwdGlvbiB8fCAnJyxcbiAgICAgICAgdHlwZTogcGlwZWxpbmUudHlwZSB8fCAnY2xhc3NpZmljYXRpb24nLFxuICAgICAgICBtb2RlbDogcGlwZWxpbmUucmVzdWx0Py5tb2RlbF9wYXRoIHx8IHVuZGVmaW5lZCxcbiAgICAgICAgYWNjdXJhY3k6IHBpcGVsaW5lLnJlc3VsdD8ucGVyZm9ybWFuY2VfbWV0cmljcz8uYWNjdXJhY3kgfHwgXG4gICAgICAgICAgICAgICAgIHBpcGVsaW5lLnJlc3VsdD8ubWV0cmljcz8uYWNjdXJhY3kgfHxcbiAgICAgICAgICAgICAgICAgcGlwZWxpbmUucmVzdWx0Py5wZXJmb3JtYW5jZV9tZXRyaWNzPy5yMl9zY29yZSB8fCBcbiAgICAgICAgICAgICAgICAgcGlwZWxpbmUucmVzdWx0Py5tZXRyaWNzPy5yMl9zY29yZSB8fCB1bmRlZmluZWQsXG4gICAgICAgIHJlc3VsdDogcGlwZWxpbmUucmVzdWx0LFxuICAgICAgICBtb2RlbFBhdGg6IHBpcGVsaW5lLnJlc3VsdD8ubW9kZWxfcGF0aCxcbiAgICAgICAgZXJyb3I6IHBpcGVsaW5lLmVycm9yIHx8IChwaXBlbGluZS5yZXN1bHQ/LnN0YXR1cyA9PT0gJ0ZBSUxFRCcgPyBwaXBlbGluZS5yZXN1bHQ/LmVycm9yIDogdW5kZWZpbmVkKSxcbiAgICAgICAgYWlJbnNpZ2h0czogcGlwZWxpbmUucmVzdWx0Py5haV9pbnNpZ2h0cyB8fCBwaXBlbGluZS5yZXN1bHQ/LnN1bW1hcnksXG4gICAgICB9O1xuICAgIH0gY2F0Y2ggKGVycm9yKSB7XG4gICAgICBjb25zb2xlLmVycm9yKCdFcnJvciBmZXRjaGluZyBwaXBlbGluZTonLCBlcnJvcik7XG4gICAgICByZXR1cm4gbnVsbDtcbiAgICB9XG4gIH1cblxuICBhc3luYyBjcmVhdGVQaXBlbGluZShwaXBlbGluZTogUGFydGlhbDxQaXBlbGluZT4gJiB7IHVzZVJlYWxBd3M/OiBib29sZWFuIH0pOiBQcm9taXNlPFBpcGVsaW5lIHwgbnVsbD4ge1xuICAgIHRyeSB7XG4gICAgICAvLyBUcmFuc2Zvcm0gdG8gTGFtYmRhIGV4cGVjdGVkIGZvcm1hdFxuICAgICAgY29uc3QgcGlwZWxpbmVSZXF1ZXN0ID0ge1xuICAgICAgICBkYXRhc2V0X3BhdGg6IHBpcGVsaW5lLmRhdGFzZXQgfHwgJycsXG4gICAgICAgIG9iamVjdGl2ZTogcGlwZWxpbmUub2JqZWN0aXZlIHx8ICcnLFxuICAgICAgICB1c2VfcmVhbF9hd3M6IHBpcGVsaW5lLnVzZVJlYWxBd3MgIT09IHVuZGVmaW5lZCA/IHBpcGVsaW5lLnVzZVJlYWxBd3MgOiB0cnVlLCAvLyBEZWZhdWx0IHRvIHRydWUgKHJlYWwgQVdTKVxuICAgICAgICBuYW1lOiBwaXBlbGluZS5uYW1lIHx8ICcnLFxuICAgICAgICBkZXNjcmlwdGlvbjogcGlwZWxpbmUuZGVzY3JpcHRpb24gfHwgJycsXG4gICAgICAgIHR5cGU6IHBpcGVsaW5lLnR5cGUgfHwgJ2NsYXNzaWZpY2F0aW9uJ1xuICAgICAgfTtcbiAgICAgIFxuICAgICAgY29uc3QgcmVzcG9uc2U6IEF4aW9zUmVzcG9uc2U8YW55PiA9IGF3YWl0IHRoaXMuYXBpLnBvc3QoJy9waXBlbGluZXMnLCBwaXBlbGluZVJlcXVlc3QpO1xuICAgICAgXG4gICAgICBpZiAocmVzcG9uc2UuZGF0YS5waXBlbGluZV9pZCkge1xuICAgICAgICByZXR1cm4ge1xuICAgICAgICAgIGlkOiByZXNwb25zZS5kYXRhLnBpcGVsaW5lX2lkLFxuICAgICAgICAgIG5hbWU6IHBpcGVsaW5lLm5hbWUgfHwgJ05ldyBQaXBlbGluZScsXG4gICAgICAgICAgc3RhdHVzOiByZXNwb25zZS5kYXRhLnN0YXR1cyB8fCAncGVuZGluZycsXG4gICAgICAgICAgY3JlYXRlZEF0OiByZXNwb25zZS5kYXRhLnRpbWVzdGFtcCB8fCBuZXcgRGF0ZSgpLnRvSVNPU3RyaW5nKCksXG4gICAgICAgICAgdXBkYXRlZEF0OiByZXNwb25zZS5kYXRhLnRpbWVzdGFtcCB8fCBuZXcgRGF0ZSgpLnRvSVNPU3RyaW5nKCksXG4gICAgICAgICAgb2JqZWN0aXZlOiBwaXBlbGluZS5vYmplY3RpdmUgfHwgJycsXG4gICAgICAgICAgZGF0YXNldDogcGlwZWxpbmUuZGF0YXNldCxcbiAgICAgICAgICBwcm9ncmVzczogMCxcbiAgICAgICAgICBkZXNjcmlwdGlvbjogcGlwZWxpbmUuZGVzY3JpcHRpb24sXG4gICAgICAgICAgdHlwZTogcGlwZWxpbmUudHlwZSB8fCAnY2xhc3NpZmljYXRpb24nXG4gICAgICAgIH07XG4gICAgICB9XG4gICAgICBcbiAgICAgIHJldHVybiByZXNwb25zZS5kYXRhLmRhdGEgfHwgbnVsbDtcbiAgICB9IGNhdGNoIChlcnJvcikge1xuICAgICAgY29uc29sZS5lcnJvcignRXJyb3IgY3JlYXRpbmcgcGlwZWxpbmU6JywgZXJyb3IpO1xuICAgICAgdGhyb3cgZXJyb3I7XG4gICAgfVxuICB9XG5cbiAgYXN5bmMgdXBkYXRlUGlwZWxpbmUoaWQ6IHN0cmluZywgdXBkYXRlczogUGFydGlhbDxQaXBlbGluZT4pOiBQcm9taXNlPFBpcGVsaW5lIHwgbnVsbD4ge1xuICAgIHRyeSB7XG4gICAgICBjb25zdCByZXNwb25zZTogQXhpb3NSZXNwb25zZTxBcGlSZXNwb25zZTxQaXBlbGluZT4+ID0gYXdhaXQgdGhpcy5hcGkucHV0KGAvcGlwZWxpbmVzLyR7aWR9YCwgdXBkYXRlcyk7XG4gICAgICByZXR1cm4gcmVzcG9uc2UuZGF0YS5kYXRhIHx8IG51bGw7XG4gICAgfSBjYXRjaCAoZXJyb3IpIHtcbiAgICAgIGNvbnNvbGUuZXJyb3IoJ0Vycm9yIHVwZGF0aW5nIHBpcGVsaW5lOicsIGVycm9yKTtcbiAgICAgIHRocm93IGVycm9yO1xuICAgIH1cbiAgfVxuXG4gIGFzeW5jIGRlbGV0ZVBpcGVsaW5lKGlkOiBzdHJpbmcpOiBQcm9taXNlPGJvb2xlYW4+IHtcbiAgICB0cnkge1xuICAgICAgYXdhaXQgdGhpcy5hcGkuZGVsZXRlKGAvcGlwZWxpbmVzLyR7aWR9YCk7XG4gICAgICByZXR1cm4gdHJ1ZTtcbiAgICB9IGNhdGNoIChlcnJvcikge1xuICAgICAgY29uc29sZS5lcnJvcignRXJyb3IgZGVsZXRpbmcgcGlwZWxpbmU6JywgZXJyb3IpO1xuICAgICAgcmV0dXJuIGZhbHNlO1xuICAgIH1cbiAgfVxuXG4gIGFzeW5jIGV4ZWN1dGVQaXBlbGluZShpZDogc3RyaW5nKTogUHJvbWlzZTxQaXBlbGluZUV4ZWN1dGlvbiB8IG51bGw+IHtcbiAgICB0cnkge1xuICAgICAgY29uc3QgcmVzcG9uc2U6IEF4aW9zUmVzcG9uc2U8QXBpUmVzcG9uc2U8UGlwZWxpbmVFeGVjdXRpb24+PiA9IGF3YWl0IHRoaXMuYXBpLnBvc3QoYC9waXBlbGluZXMvJHtpZH0vZXhlY3V0ZWApO1xuICAgICAgcmV0dXJuIHJlc3BvbnNlLmRhdGEuZGF0YSB8fCBudWxsO1xuICAgIH0gY2F0Y2ggKGVycm9yKSB7XG4gICAgICBjb25zb2xlLmVycm9yKCdFcnJvciBleGVjdXRpbmcgcGlwZWxpbmU6JywgZXJyb3IpO1xuICAgICAgdGhyb3cgZXJyb3I7XG4gICAgfVxuICB9XG5cbiAgLy8gUGlwZWxpbmUgRXhlY3V0aW9ucyBBUElcbiAgYXN5bmMgZ2V0RXhlY3V0aW9uKGlkOiBzdHJpbmcpOiBQcm9taXNlPFBpcGVsaW5lRXhlY3V0aW9uIHwgbnVsbD4ge1xuICAgIHRyeSB7XG4gICAgICBjb25zdCByZXNwb25zZTogQXhpb3NSZXNwb25zZTxBcGlSZXNwb25zZTxQaXBlbGluZUV4ZWN1dGlvbj4+ID0gYXdhaXQgdGhpcy5hcGkuZ2V0KGAvZXhlY3V0aW9ucy8ke2lkfWApO1xuICAgICAgcmV0dXJuIHJlc3BvbnNlLmRhdGEuZGF0YSB8fCBudWxsO1xuICAgIH0gY2F0Y2ggKGVycm9yKSB7XG4gICAgICBjb25zb2xlLmVycm9yKCdFcnJvciBmZXRjaGluZyBleGVjdXRpb246JywgZXJyb3IpO1xuICAgICAgcmV0dXJuIG51bGw7XG4gICAgfVxuICB9XG5cbiAgYXN5bmMgZ2V0UGlwZWxpbmVFeGVjdXRpb25zKHBpcGVsaW5lSWQ6IHN0cmluZyk6IFByb21pc2U8UGlwZWxpbmVFeGVjdXRpb25bXT4ge1xuICAgIHRyeSB7XG4gICAgICBjb25zdCByZXNwb25zZTogQXhpb3NSZXNwb25zZTxBcGlSZXNwb25zZTxQaXBlbGluZUV4ZWN1dGlvbltdPj4gPSBhd2FpdCB0aGlzLmFwaS5nZXQoYC9waXBlbGluZXMvJHtwaXBlbGluZUlkfS9leGVjdXRpb25zYCk7XG4gICAgICByZXR1cm4gcmVzcG9uc2UuZGF0YS5kYXRhIHx8IFtdO1xuICAgIH0gY2F0Y2ggKGVycm9yKSB7XG4gICAgICBjb25zb2xlLmVycm9yKCdFcnJvciBmZXRjaGluZyBwaXBlbGluZSBleGVjdXRpb25zOicsIGVycm9yKTtcbiAgICAgIHJldHVybiBbXTtcbiAgICB9XG4gIH1cblxuICAvLyBNb2RlbCBSZXN1bHRzIEFQSVxuICBhc3luYyBnZXRNb2RlbFJlc3VsdHMocGlwZWxpbmVJZDogc3RyaW5nKTogUHJvbWlzZTxNb2RlbFJlc3VsdHMgfCBudWxsPiB7XG4gICAgdHJ5IHtcbiAgICAgIGNvbnN0IHJlc3BvbnNlOiBBeGlvc1Jlc3BvbnNlPEFwaVJlc3BvbnNlPE1vZGVsUmVzdWx0cz4+ID0gYXdhaXQgdGhpcy5hcGkuZ2V0KGAvcGlwZWxpbmVzLyR7cGlwZWxpbmVJZH0vcmVzdWx0c2ApO1xuICAgICAgcmV0dXJuIHJlc3BvbnNlLmRhdGEuZGF0YSB8fCBudWxsO1xuICAgIH0gY2F0Y2ggKGVycm9yKSB7XG4gICAgICBjb25zb2xlLmVycm9yKCdFcnJvciBmZXRjaGluZyBtb2RlbCByZXN1bHRzOicsIGVycm9yKTtcbiAgICAgIHJldHVybiBudWxsO1xuICAgIH1cbiAgfVxuXG4gIGFzeW5jIGRvd25sb2FkTW9kZWwocGlwZWxpbmVJZDogc3RyaW5nKTogUHJvbWlzZTxCbG9iIHwgbnVsbD4ge1xuICAgIHRyeSB7XG4gICAgICBjb25zdCByZXNwb25zZSA9IGF3YWl0IHRoaXMuYXBpLmdldChgL3BpcGVsaW5lcy8ke3BpcGVsaW5lSWR9L2Rvd25sb2FkYCwge1xuICAgICAgICByZXNwb25zZVR5cGU6ICdibG9iJyxcbiAgICAgIH0pO1xuICAgICAgcmV0dXJuIHJlc3BvbnNlLmRhdGE7XG4gICAgfSBjYXRjaCAoZXJyb3IpIHtcbiAgICAgIGNvbnNvbGUuZXJyb3IoJ0Vycm9yIGRvd25sb2FkaW5nIG1vZGVsOicsIGVycm9yKTtcbiAgICAgIHJldHVybiBudWxsO1xuICAgIH1cbiAgfVxuXG4gIC8vIERhdGEgVXBsb2FkIEFQSVxuICBhc3luYyB1cGxvYWREYXRhKGZpbGU6IEZpbGUpOiBQcm9taXNlPERhdGFVcGxvYWQgfCBudWxsPiB7XG4gICAgdHJ5IHtcbiAgICAgIC8vIFJlYWQgZmlsZSBjb250ZW50IGFuZCBjb252ZXJ0IHRvIGJhc2U2NFxuICAgICAgY29uc3QgZmlsZUNvbnRlbnQgPSBhd2FpdCBmaWxlLnRleHQoKTtcbiAgICAgIGNvbnN0IGJhc2U2NENvbnRlbnQgPSBidG9hKGZpbGVDb250ZW50KTtcblxuICAgICAgLy8gU2VuZCBhcyBKU09OIHBheWxvYWQgKExhbWJkYSBleHBlY3RzIHRoaXMgZm9ybWF0KVxuICAgICAgY29uc3QgdXBsb2FkUGF5bG9hZCA9IHtcbiAgICAgICAgZmlsZW5hbWU6IGZpbGUubmFtZSxcbiAgICAgICAgY29udGVudDogYmFzZTY0Q29udGVudCxcbiAgICAgICAgZW5jb2Rpbmc6ICdiYXNlNjQnXG4gICAgICB9O1xuXG4gICAgICBjb25zdCByZXNwb25zZTogQXhpb3NSZXNwb25zZTxhbnk+ID0gYXdhaXQgdGhpcy5hcGkucG9zdCgnL2RhdGEvdXBsb2FkJywgdXBsb2FkUGF5bG9hZCwge1xuICAgICAgICBoZWFkZXJzOiB7XG4gICAgICAgICAgJ0NvbnRlbnQtVHlwZSc6ICdhcHBsaWNhdGlvbi9qc29uJyxcbiAgICAgICAgfSxcbiAgICAgIH0pO1xuICAgICAgXG4gICAgICAvLyBCdWlsZCBkYXRhIHVwbG9hZCByZXNwb25zZVxuICAgICAgY29uc3QgZGF0YVVwbG9hZDogRGF0YVVwbG9hZCA9IHtcbiAgICAgICAgaWQ6IHJlc3BvbnNlLmRhdGEuaWQgfHwgcmVzcG9uc2UuZGF0YS51cGxvYWRfaWQgfHwgYHVwbG9hZC0ke0RhdGUubm93KCl9YCxcbiAgICAgICAgZmlsZW5hbWU6IGZpbGUubmFtZSxcbiAgICAgICAgc2l6ZTogZmlsZS5zaXplLFxuICAgICAgICB1cGxvYWRlZEF0OiByZXNwb25zZS5kYXRhLnVwbG9hZGVkQXQgfHwgbmV3IERhdGUoKS50b0lTT1N0cmluZygpLFxuICAgICAgICBjb2x1bW5zOiBbXSxcbiAgICAgICAgcm93Q291bnQ6IDAsXG4gICAgICAgIHByZXZpZXc6IFtdXG4gICAgICB9O1xuICAgICAgXG4gICAgICAvLyBQYXJzZSBDU1YgdG8gZ2V0IGNvbHVtbiBpbmZvIGlmIGl0J3MgYSBDU1YgZmlsZVxuICAgICAgaWYgKGZpbGUudHlwZSA9PT0gJ3RleHQvY3N2JyB8fCBmaWxlLm5hbWUuZW5kc1dpdGgoJy5jc3YnKSkge1xuICAgICAgICBjb25zdCBsaW5lcyA9IGZpbGVDb250ZW50LnNwbGl0KCdcXG4nKS5maWx0ZXIobGluZSA9PiBsaW5lLnRyaW0oKSk7XG4gICAgICAgIGlmIChsaW5lcy5sZW5ndGggPiAwKSB7XG4gICAgICAgICAgY29uc3QgaGVhZGVycyA9IGxpbmVzWzBdLnNwbGl0KCcsJykubWFwKGggPT4gaC50cmltKCkucmVwbGFjZSgvXCIvZywgJycpKTtcbiAgICAgICAgICBjb25zdCBwcmV2aWV3ID0gbGluZXMuc2xpY2UoMSwgNikubWFwKGxpbmUgPT4ge1xuICAgICAgICAgICAgY29uc3QgdmFsdWVzID0gbGluZS5zcGxpdCgnLCcpLm1hcCh2ID0+IHYudHJpbSgpLnJlcGxhY2UoL1wiL2csICcnKSk7XG4gICAgICAgICAgICBjb25zdCByb3c6IGFueSA9IHt9O1xuICAgICAgICAgICAgaGVhZGVycy5mb3JFYWNoKChoZWFkZXIsIGluZGV4KSA9PiB7XG4gICAgICAgICAgICAgIHJvd1toZWFkZXJdID0gdmFsdWVzW2luZGV4XSB8fCAnJztcbiAgICAgICAgICAgIH0pO1xuICAgICAgICAgICAgcmV0dXJuIHJvdztcbiAgICAgICAgICB9KTtcbiAgICAgICAgICBcbiAgICAgICAgICBkYXRhVXBsb2FkLmNvbHVtbnMgPSBoZWFkZXJzO1xuICAgICAgICAgIGRhdGFVcGxvYWQucm93Q291bnQgPSBsaW5lcy5sZW5ndGggLSAxO1xuICAgICAgICAgIGRhdGFVcGxvYWQucHJldmlldyA9IHByZXZpZXc7XG4gICAgICAgIH1cbiAgICAgIH1cbiAgICAgIFxuICAgICAgcmV0dXJuIGRhdGFVcGxvYWQ7XG4gICAgfSBjYXRjaCAoZXJyb3IpIHtcbiAgICAgIGNvbnNvbGUuZXJyb3IoJ0Vycm9yIHVwbG9hZGluZyBkYXRhOicsIGVycm9yKTtcbiAgICAgIHRocm93IGVycm9yO1xuICAgIH1cbiAgfVxuXG4gIGFzeW5jIGdldFVwbG9hZGVkRGF0YXNldHMoKTogUHJvbWlzZTxEYXRhVXBsb2FkW10+IHtcbiAgICB0cnkge1xuICAgICAgY29uc3QgcmVzcG9uc2U6IEF4aW9zUmVzcG9uc2U8QXBpUmVzcG9uc2U8RGF0YVVwbG9hZFtdPj4gPSBhd2FpdCB0aGlzLmFwaS5nZXQoJy9kYXRhL3VwbG9hZHMnKTtcbiAgICAgIHJldHVybiByZXNwb25zZS5kYXRhLmRhdGEgfHwgW107XG4gICAgfSBjYXRjaCAoZXJyb3IpIHtcbiAgICAgIGNvbnNvbGUuZXJyb3IoJ0Vycm9yIGZldGNoaW5nIHVwbG9hZGVkIGRhdGFzZXRzOicsIGVycm9yKTtcbiAgICAgIHJldHVybiBbXTtcbiAgICB9XG4gIH1cblxuICAvLyBEYXNoYm9hcmQgQVBJXG4gIGFzeW5jIGdldERhc2hib2FyZFN0YXRzKCk6IFByb21pc2U8RGFzaGJvYXJkU3RhdHM+IHtcbiAgICB0cnkge1xuICAgICAgLy8gR2V0IHJlYWwgcGlwZWxpbmUgZGF0YSB0byBjYWxjdWxhdGUgc3RhdHNcbiAgICAgIGNvbnN0IHBpcGVsaW5lcyA9IGF3YWl0IHRoaXMuZ2V0UGlwZWxpbmVzKCk7XG4gICAgICBcbiAgICAgIGNvbnN0IHRvdGFsUGlwZWxpbmVzID0gcGlwZWxpbmVzLmxlbmd0aDtcbiAgICAgIGNvbnN0IHJ1bm5pbmdQaXBlbGluZXMgPSBwaXBlbGluZXMuZmlsdGVyKHAgPT4gcC5zdGF0dXMgPT09ICdydW5uaW5nJykubGVuZ3RoO1xuICAgICAgY29uc3QgY29tcGxldGVkUGlwZWxpbmVzID0gcGlwZWxpbmVzLmZpbHRlcihwID0+IHAuc3RhdHVzID09PSAnY29tcGxldGVkJykubGVuZ3RoO1xuICAgICAgY29uc3QgZmFpbGVkUGlwZWxpbmVzID0gcGlwZWxpbmVzLmZpbHRlcihwID0+IHAuc3RhdHVzID09PSAnZmFpbGVkJykubGVuZ3RoO1xuICAgICAgXG4gICAgICBjb25zdCBzdWNjZXNzUmF0ZSA9IHRvdGFsUGlwZWxpbmVzID4gMCA/IChjb21wbGV0ZWRQaXBlbGluZXMgLyB0b3RhbFBpcGVsaW5lcykgKiAxMDAgOiAwO1xuICAgICAgXG4gICAgICAvLyBDYWxjdWxhdGUgYXZlcmFnZSBleGVjdXRpb24gdGltZSBmcm9tIGNvbXBsZXRlZCBwaXBlbGluZXNcbiAgICAgIGNvbnN0IGNvbXBsZXRlZFdpdGhUaW1lcyA9IHBpcGVsaW5lcy5maWx0ZXIocCA9PiBwLnN0YXR1cyA9PT0gJ2NvbXBsZXRlZCcgJiYgcC5jcmVhdGVkQXQgJiYgcC51cGRhdGVkQXQpO1xuICAgICAgY29uc3QgYXZlcmFnZUV4ZWN1dGlvblRpbWUgPSBjb21wbGV0ZWRXaXRoVGltZXMubGVuZ3RoID4gMFxuICAgICAgICA/IGNvbXBsZXRlZFdpdGhUaW1lcy5yZWR1Y2UoKHN1bSwgcCkgPT4ge1xuICAgICAgICAgICAgY29uc3Qgc3RhcnQgPSBuZXcgRGF0ZShwLmNyZWF0ZWRBdCkuZ2V0VGltZSgpO1xuICAgICAgICAgICAgY29uc3QgZW5kID0gbmV3IERhdGUocC51cGRhdGVkQXQpLmdldFRpbWUoKTtcbiAgICAgICAgICAgIHJldHVybiBzdW0gKyAoZW5kIC0gc3RhcnQpIC8gMTAwMDsgLy8gQ29udmVydCB0byBzZWNvbmRzXG4gICAgICAgICAgfSwgMCkgLyBjb21wbGV0ZWRXaXRoVGltZXMubGVuZ3RoXG4gICAgICAgIDogMDtcbiAgICAgIFxuICAgICAgcmV0dXJuIHtcbiAgICAgICAgdG90YWxQaXBlbGluZXMsXG4gICAgICAgIHJ1bm5pbmdQaXBlbGluZXMsXG4gICAgICAgIGNvbXBsZXRlZFBpcGVsaW5lcyxcbiAgICAgICAgZmFpbGVkUGlwZWxpbmVzLFxuICAgICAgICBhdmVyYWdlRXhlY3V0aW9uVGltZSxcbiAgICAgICAgc3VjY2Vzc1JhdGUsXG4gICAgICB9O1xuICAgIH0gY2F0Y2ggKGVycm9yKSB7XG4gICAgICBjb25zb2xlLmVycm9yKCdFcnJvciBmZXRjaGluZyBkYXNoYm9hcmQgc3RhdHM6JywgZXJyb3IpO1xuICAgICAgcmV0dXJuIHtcbiAgICAgICAgdG90YWxQaXBlbGluZXM6IDAsXG4gICAgICAgIHJ1bm5pbmdQaXBlbGluZXM6IDAsXG4gICAgICAgIGNvbXBsZXRlZFBpcGVsaW5lczogMCxcbiAgICAgICAgZmFpbGVkUGlwZWxpbmVzOiAwLFxuICAgICAgICBhdmVyYWdlRXhlY3V0aW9uVGltZTogMCxcbiAgICAgICAgc3VjY2Vzc1JhdGU6IDAsXG4gICAgICB9O1xuICAgIH1cbiAgfVxuXG4gIC8vIEhlYWx0aCBDaGVja1xuICBhc3luYyBoZWFsdGhDaGVjaygpOiBQcm9taXNlPGJvb2xlYW4+IHtcbiAgICB0cnkge1xuICAgICAgY29uc3QgcmVzcG9uc2UgPSBhd2FpdCB0aGlzLmFwaS5nZXQoJy9oZWFsdGgnKTtcbiAgICAgIHJldHVybiByZXNwb25zZS5zdGF0dXMgPT09IDIwMDtcbiAgICB9IGNhdGNoIChlcnJvcikge1xuICAgICAgY29uc29sZS5lcnJvcignSGVhbHRoIGNoZWNrIGZhaWxlZDonLCBlcnJvcik7XG4gICAgICByZXR1cm4gZmFsc2U7XG4gICAgfVxuICB9XG5cbiAgLy8gUmVhbC10aW1lIHBpcGVsaW5lIG1vbml0b3JpbmcgLSByZXR1cm5zIGZ1bGwgcGlwZWxpbmUgZGF0YSB3aXRoIHN0ZXBzIGFuZCBtZXRyaWNzXG4gIGFzeW5jIG1vbml0b3JQaXBlbGluZShwaXBlbGluZUlkOiBzdHJpbmcpOiBQcm9taXNlPGFueT4ge1xuICAgIHRyeSB7XG4gICAgICBjb25zdCByZXNwb25zZSA9IGF3YWl0IHRoaXMuYXBpLmdldChgL3BpcGVsaW5lcy8ke3BpcGVsaW5lSWR9YCk7XG4gICAgICBjb25zdCBkYXRhID0gcmVzcG9uc2UuZGF0YS5kYXRhIHx8IHJlc3BvbnNlLmRhdGEgfHwgbnVsbDtcbiAgICAgIFxuICAgICAgLy8gSWYgdGhlIHBpcGVsaW5lIGhhcyBhIHJlc3VsdCBvYmplY3Qgd2l0aCByZWFsIGV4ZWN1dGlvbiBkYXRhLCBleHRyYWN0IGl0XG4gICAgICBpZiAoZGF0YSAmJiBkYXRhLnJlc3VsdCkge1xuICAgICAgICBjb25zdCByZXN1bHQgPSB0eXBlb2YgZGF0YS5yZXN1bHQgPT09ICdzdHJpbmcnID8gSlNPTi5wYXJzZShkYXRhLnJlc3VsdCkgOiBkYXRhLnJlc3VsdDtcbiAgICAgICAgcmV0dXJuIHtcbiAgICAgICAgICAuLi5kYXRhLFxuICAgICAgICAgIHN0ZXBzOiByZXN1bHQuc3RlcHMgfHwgZGF0YS5zdGVwcyxcbiAgICAgICAgICBsb2dzOiByZXN1bHQubG9ncyB8fCBkYXRhLmxvZ3MsXG4gICAgICAgICAgcGVyZm9ybWFuY2VfbWV0cmljczogcmVzdWx0LnBlcmZvcm1hbmNlX21ldHJpY3MgfHwgZGF0YS5wZXJmb3JtYW5jZV9tZXRyaWNzLFxuICAgICAgICAgIGZlYXR1cmVfaW1wb3J0YW5jZTogcmVzdWx0LmZlYXR1cmVfaW1wb3J0YW5jZSB8fCBkYXRhLmZlYXR1cmVfaW1wb3J0YW5jZSxcbiAgICAgICAgICBleGVjdXRpb25fdGltZTogcmVzdWx0LmV4ZWN1dGlvbl90aW1lIHx8IGRhdGEuZXhlY3V0aW9uX3RpbWUsXG4gICAgICAgICAgdHJhaW5pbmdfdGltZTogcmVzdWx0LnRyYWluaW5nX3RpbWUgfHwgZGF0YS50cmFpbmluZ190aW1lLFxuICAgICAgICAgIG1vZGVsX3R5cGU6IHJlc3VsdC5tb2RlbF90eXBlIHx8IGRhdGEubW9kZWxfdHlwZSxcbiAgICAgICAgfTtcbiAgICAgIH1cbiAgICAgIHJldHVybiBkYXRhO1xuICAgIH0gY2F0Y2ggKGVycm9yKSB7XG4gICAgICBjb25zb2xlLmVycm9yKCdFcnJvciBtb25pdG9yaW5nIHBpcGVsaW5lOicsIGVycm9yKTtcbiAgICAgIHJldHVybiBudWxsO1xuICAgIH1cbiAgfVxuXG4gIC8vIEdldCByZWFsLXRpbWUgZXhlY3V0aW9uIGxvZ3NcbiAgYXN5bmMgZ2V0UGlwZWxpbmVMb2dzKHBpcGVsaW5lSWQ6IHN0cmluZyk6IFByb21pc2U8c3RyaW5nW10+IHtcbiAgICB0cnkge1xuICAgICAgY29uc3QgcmVzcG9uc2UgPSBhd2FpdCB0aGlzLmFwaS5nZXQoYC9waXBlbGluZXMvJHtwaXBlbGluZUlkfS9sb2dzYCk7XG4gICAgICByZXR1cm4gcmVzcG9uc2UuZGF0YS5sb2dzIHx8IHJlc3BvbnNlLmRhdGEuZGF0YSB8fCBbXTtcbiAgICB9IGNhdGNoIChlcnJvcikge1xuICAgICAgY29uc29sZS5lcnJvcignRXJyb3IgZmV0Y2hpbmcgcGlwZWxpbmUgbG9nczonLCBlcnJvcik7XG4gICAgICByZXR1cm4gW107XG4gICAgfVxuICB9XG5cbiAgLy8gR2V0IHBpcGVsaW5lIGV4ZWN1dGlvbiBzdGVwc1xuICBhc3luYyBnZXRQaXBlbGluZVN0ZXBzKHBpcGVsaW5lSWQ6IHN0cmluZyk6IFByb21pc2U8YW55W10+IHtcbiAgICB0cnkge1xuICAgICAgY29uc3QgcGlwZWxpbmVEYXRhID0gYXdhaXQgdGhpcy5tb25pdG9yUGlwZWxpbmUocGlwZWxpbmVJZCk7XG4gICAgICBpZiAocGlwZWxpbmVEYXRhPy5zdGVwcykge1xuICAgICAgICByZXR1cm4gcGlwZWxpbmVEYXRhLnN0ZXBzO1xuICAgICAgfVxuICAgICAgLy8gSWYgc3RlcHMgYXJlIGluIHJlc3VsdCBvYmplY3RcbiAgICAgIGlmIChwaXBlbGluZURhdGE/LnJlc3VsdD8uc3RlcHMpIHtcbiAgICAgICAgcmV0dXJuIHBpcGVsaW5lRGF0YS5yZXN1bHQuc3RlcHM7XG4gICAgICB9XG4gICAgICByZXR1cm4gW107XG4gICAgfSBjYXRjaCAoZXJyb3IpIHtcbiAgICAgIGNvbnNvbGUuZXJyb3IoJ0Vycm9yIGZldGNoaW5nIHBpcGVsaW5lIHN0ZXBzOicsIGVycm9yKTtcbiAgICAgIHJldHVybiBbXTtcbiAgICB9XG4gIH1cblxuICAvLyBFeGVjdXRlIHBpcGVsaW5lXG4gIGFzeW5jIGV4ZWN1dGVQaXBlbGluZUJ5SWQocGlwZWxpbmVJZDogc3RyaW5nLCB1c2VSZWFsQXdzOiBib29sZWFuID0gZmFsc2UpOiBQcm9taXNlPFBpcGVsaW5lRXhlY3V0aW9uIHwgbnVsbD4ge1xuICAgIHRyeSB7XG4gICAgICBjb25zdCByZXNwb25zZTogQXhpb3NSZXNwb25zZTxhbnk+ID0gYXdhaXQgdGhpcy5hcGkucG9zdChgL3BpcGVsaW5lcy8ke3BpcGVsaW5lSWR9L2V4ZWN1dGVgLCB7XG4gICAgICAgIHVzZV9yZWFsX2F3czogdXNlUmVhbEF3c1xuICAgICAgfSk7XG4gICAgICByZXR1cm4gcmVzcG9uc2UuZGF0YS5kYXRhIHx8IHJlc3BvbnNlLmRhdGEgfHwgbnVsbDtcbiAgICB9IGNhdGNoIChlcnJvcikge1xuICAgICAgY29uc29sZS5lcnJvcignRXJyb3IgZXhlY3V0aW5nIHBpcGVsaW5lOicsIGVycm9yKTtcbiAgICAgIHRocm93IGVycm9yO1xuICAgIH1cbiAgfVxuXG4gIC8vIFN0b3AgcnVubmluZyBwaXBlbGluZSAobm90IGltcGxlbWVudGVkIGluIGN1cnJlbnQgTGFtYmRhIGJ1dCBhZGRpbmcgZm9yIGNvbXBsZXRlbmVzcylcbiAgYXN5bmMgc3RvcFBpcGVsaW5lKHBpcGVsaW5lSWQ6IHN0cmluZyk6IFByb21pc2U8Ym9vbGVhbj4ge1xuICAgIHRyeSB7XG4gICAgICBhd2FpdCB0aGlzLmFwaS5wb3N0KGAvcGlwZWxpbmVzLyR7cGlwZWxpbmVJZH0vc3RvcGApO1xuICAgICAgcmV0dXJuIHRydWU7XG4gICAgfSBjYXRjaCAoZXJyb3IpIHtcbiAgICAgIGNvbnNvbGUuZXJyb3IoJ0Vycm9yIHN0b3BwaW5nIHBpcGVsaW5lOicsIGVycm9yKTtcbiAgICAgIHJldHVybiBmYWxzZTtcbiAgICB9XG4gIH1cbn1cblxuZXhwb3J0IGNvbnN0IGFwaVNlcnZpY2UgPSBuZXcgQXBpU2VydmljZSgpO1xuZXhwb3J0IGRlZmF1bHQgYXBpU2VydmljZTsiXX0=