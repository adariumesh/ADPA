import { Pipeline, PipelineExecution, ModelResults, DataUpload, DashboardStats } from '../types';
declare class ApiService {
    private api;
    constructor();
    getPipelines(): Promise<Pipeline[]>;
    private calculateProgress;
    getPipeline(id: string): Promise<Pipeline | null>;
    createPipeline(pipeline: Partial<Pipeline> & {
        useRealAws?: boolean;
    }): Promise<Pipeline | null>;
    updatePipeline(id: string, updates: Partial<Pipeline>): Promise<Pipeline | null>;
    deletePipeline(id: string): Promise<boolean>;
    executePipeline(id: string): Promise<PipelineExecution | null>;
    getExecution(id: string): Promise<PipelineExecution | null>;
    getPipelineExecutions(pipelineId: string): Promise<PipelineExecution[]>;
    getModelResults(pipelineId: string): Promise<ModelResults | null>;
    downloadModel(pipelineId: string): Promise<Blob | null>;
    uploadData(file: File): Promise<DataUpload | null>;
    getUploadedDatasets(): Promise<DataUpload[]>;
    getDashboardStats(): Promise<DashboardStats>;
    healthCheck(): Promise<boolean>;
    monitorPipeline(pipelineId: string): Promise<any>;
    getPipelineLogs(pipelineId: string): Promise<string[]>;
    getPipelineSteps(pipelineId: string): Promise<any[]>;
    executePipelineById(pipelineId: string, useRealAws?: boolean): Promise<PipelineExecution | null>;
    stopPipeline(pipelineId: string): Promise<boolean>;
}
export declare const apiService: ApiService;
export default apiService;
