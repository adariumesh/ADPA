import axios, { AxiosInstance, AxiosResponse } from 'axios';
import {
  Pipeline,
  PipelineExecution,
  ModelResults,
  DataUpload,
  ApiResponse,
  DashboardStats
} from '../types';

// Configuration - Updated to use actual deployed API Gateway
const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod';
const TIMEOUT = 60000; // 60 seconds for longer operations

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      timeout: TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });

    // Request interceptor for adding auth tokens, etc.
    this.api.interceptors.request.use(
      (config) => {
        // Add any authentication headers here
        // const token = localStorage.getItem('authToken');
        // if (token) {
        //   config.headers.Authorization = `Bearer ${token}`;
        // }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for handling errors globally
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error);
        
        if (error.response?.status === 401) {
          // Handle unauthorized access
          localStorage.removeItem('authToken');
          window.location.href = '/login';
        }
        
        return Promise.reject(error);
      }
    );
  }

  // Pipelines API
  async getPipelines(): Promise<Pipeline[]> {
    try {
      const response: AxiosResponse<ApiResponse<Pipeline[]>> = await this.api.get('/pipelines');
      if (response.data.pipelines) {
        // Handle the actual Lambda response format - map backend fields to frontend interface
        return response.data.pipelines.map((pipeline: any) => ({
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
    } catch (error) {
      console.error('Error fetching pipelines:', error);
      // Return empty array on error to prevent UI crashes
      return [];
    }
  }

  private calculateProgress(status: string): number {
    switch (status) {
      case 'completed': return 100;
      case 'running': return 50; // Fixed value instead of random
      case 'failed': return 0;
      default: return 0;
    }
  }

  async getPipeline(id: string): Promise<Pipeline | null> {
    try {
      const response: AxiosResponse<any> = await this.api.get(`/pipelines/${id}`);
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
    } catch (error) {
      console.error('Error fetching pipeline:', error);
      return null;
    }
  }

  async createPipeline(pipeline: Partial<Pipeline> & { useRealAws?: boolean }): Promise<Pipeline | null> {
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
      
      const response: AxiosResponse<any> = await this.api.post('/pipelines', pipelineRequest);
      
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
    } catch (error) {
      console.error('Error creating pipeline:', error);
      throw error;
    }
  }

  async updatePipeline(id: string, updates: Partial<Pipeline>): Promise<Pipeline | null> {
    try {
      const response: AxiosResponse<ApiResponse<Pipeline>> = await this.api.put(`/pipelines/${id}`, updates);
      return response.data.data || null;
    } catch (error) {
      console.error('Error updating pipeline:', error);
      throw error;
    }
  }

  async deletePipeline(id: string): Promise<boolean> {
    try {
      await this.api.delete(`/pipelines/${id}`);
      return true;
    } catch (error) {
      console.error('Error deleting pipeline:', error);
      return false;
    }
  }

  async executePipeline(id: string): Promise<PipelineExecution | null> {
    try {
      const response: AxiosResponse<ApiResponse<PipelineExecution>> = await this.api.post(`/pipelines/${id}/execute`);
      return response.data.data || null;
    } catch (error) {
      console.error('Error executing pipeline:', error);
      throw error;
    }
  }

  // Pipeline Executions API
  async getExecution(id: string): Promise<PipelineExecution | null> {
    try {
      const response: AxiosResponse<ApiResponse<PipelineExecution>> = await this.api.get(`/executions/${id}`);
      return response.data.data || null;
    } catch (error) {
      console.error('Error fetching execution:', error);
      return null;
    }
  }

  async getPipelineExecutions(pipelineId: string): Promise<PipelineExecution[]> {
    try {
      const response: AxiosResponse<ApiResponse<PipelineExecution[]>> = await this.api.get(`/pipelines/${pipelineId}/executions`);
      return response.data.data || [];
    } catch (error) {
      console.error('Error fetching pipeline executions:', error);
      return [];
    }
  }

  // Model Results API
  async getModelResults(pipelineId: string): Promise<ModelResults | null> {
    try {
      const response: AxiosResponse<ApiResponse<ModelResults>> = await this.api.get(`/pipelines/${pipelineId}/results`);
      return response.data.data || null;
    } catch (error) {
      console.error('Error fetching model results:', error);
      return null;
    }
  }

  async downloadModel(pipelineId: string): Promise<Blob | null> {
    try {
      const response = await this.api.get(`/pipelines/${pipelineId}/download`, {
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      console.error('Error downloading model:', error);
      return null;
    }
  }

  // Data Upload API
  async uploadData(file: File): Promise<DataUpload | null> {
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

      const response: AxiosResponse<any> = await this.api.post('/data/upload', uploadPayload, {
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      // Build data upload response
      const dataUpload: DataUpload = {
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
            const row: any = {};
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
    } catch (error) {
      console.error('Error uploading data:', error);
      throw error;
    }
  }

  async getUploadedDatasets(): Promise<DataUpload[]> {
    try {
      const response: AxiosResponse<ApiResponse<DataUpload[]>> = await this.api.get('/data/uploads');
      return response.data.data || [];
    } catch (error) {
      console.error('Error fetching uploaded datasets:', error);
      return [];
    }
  }

  // Dashboard API
  async getDashboardStats(): Promise<DashboardStats> {
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
    } catch (error) {
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
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.api.get('/health');
      return response.status === 200;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }

  // Real-time pipeline monitoring
  async monitorPipeline(pipelineId: string): Promise<PipelineExecution | null> {
    try {
      // Get pipeline status - correct endpoint is /pipelines/{id} not /pipelines/{id}/status
      const response = await this.api.get(`/pipelines/${pipelineId}`);
      return response.data.data || response.data || null;
    } catch (error) {
      console.error('Error monitoring pipeline:', error);
      return null;
    }
  }

  // Get real-time execution logs
  async getPipelineLogs(pipelineId: string): Promise<string[]> {
    try {
      const response = await this.api.get(`/pipelines/${pipelineId}/logs`);
      return response.data.logs || response.data.data || [];
    } catch (error) {
      console.error('Error fetching pipeline logs:', error);
      return [];
    }
  }

  // Execute pipeline
  async executePipelineById(pipelineId: string, useRealAws: boolean = false): Promise<PipelineExecution | null> {
    try {
      const response: AxiosResponse<any> = await this.api.post(`/pipelines/${pipelineId}/execute`, {
        use_real_aws: useRealAws
      });
      return response.data.data || response.data || null;
    } catch (error) {
      console.error('Error executing pipeline:', error);
      throw error;
    }
  }

  // Stop running pipeline (not implemented in current Lambda but adding for completeness)
  async stopPipeline(pipelineId: string): Promise<boolean> {
    try {
      await this.api.post(`/pipelines/${pipelineId}/stop`);
      return true;
    } catch (error) {
      console.error('Error stopping pipeline:', error);
      return false;
    }
  }
}

export const apiService = new ApiService();
export default apiService;