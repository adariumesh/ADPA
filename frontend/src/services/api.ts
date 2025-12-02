import axios, { AxiosInstance, AxiosResponse } from 'axios';
import {
  Pipeline,
  PipelineExecution,
  ModelResults,
  DataUpload,
  ApiResponse,
  DashboardStats
} from '../types';

// Configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://lvojiw3qc9.execute-api.us-east-2.amazonaws.com/prod';
const TIMEOUT = 30000; // 30 seconds

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
      return response.data.data || [];
    } catch (error) {
      console.error('Error fetching pipelines:', error);
      return [];
    }
  }

  async getPipeline(id: string): Promise<Pipeline | null> {
    try {
      const response: AxiosResponse<ApiResponse<Pipeline>> = await this.api.get(`/pipelines/${id}`);
      return response.data.data || null;
    } catch (error) {
      console.error('Error fetching pipeline:', error);
      return null;
    }
  }

  async createPipeline(pipeline: Partial<Pipeline>): Promise<Pipeline | null> {
    try {
      const response: AxiosResponse<ApiResponse<Pipeline>> = await this.api.post('/pipelines', pipeline);
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
      const formData = new FormData();
      formData.append('file', file);

      const response: AxiosResponse<ApiResponse<DataUpload>> = await this.api.post('/data/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data.data || null;
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
      const response: AxiosResponse<ApiResponse<DashboardStats>> = await this.api.get('/dashboard/stats');
      return response.data.data || {
        totalPipelines: 0,
        runningPipelines: 0,
        completedPipelines: 0,
        failedPipelines: 0,
        averageExecutionTime: 0,
        successRate: 0,
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

  // Mock data methods for development
  async getMockPipelines(): Promise<Pipeline[]> {
    return [
      {
        id: '1',
        name: 'Customer Segmentation',
        status: 'completed',
        createdAt: '2024-01-15T10:00:00Z',
        updatedAt: '2024-01-15T11:30:00Z',
        objective: 'Classify customers into segments',
        dataset: 'customer_data.csv',
        model: 'Random Forest',
        accuracy: 0.85,
        progress: 100,
        description: 'ML pipeline for customer segmentation using demographic data',
        type: 'classification',
      },
      {
        id: '2',
        name: 'Sales Forecasting',
        status: 'running',
        createdAt: '2024-01-16T09:00:00Z',
        updatedAt: '2024-01-16T09:45:00Z',
        objective: 'Predict future sales',
        dataset: 'sales_data.csv',
        model: 'LSTM',
        progress: 65,
        description: 'Time series forecasting for sales prediction',
        type: 'regression',
      },
      {
        id: '3',
        name: 'Fraud Detection',
        status: 'failed',
        createdAt: '2024-01-14T14:00:00Z',
        updatedAt: '2024-01-14T15:30:00Z',
        objective: 'Detect fraudulent transactions',
        dataset: 'transaction_data.csv',
        progress: 30,
        description: 'Anomaly detection for fraud prevention',
        type: 'anomaly_detection',
      },
    ];
  }
}

export const apiService = new ApiService();
export default apiService;