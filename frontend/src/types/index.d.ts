export interface Pipeline {
    id: string;
    name: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    createdAt: string;
    updatedAt: string;
    objective: string;
    dataset?: string;
    model?: string;
    accuracy?: number;
    progress: number;
    description?: string;
    type: 'classification' | 'regression' | 'clustering' | 'anomaly_detection';
    result?: any;
    modelPath?: string;
    steps?: any[];
    error?: string;
    aiInsights?: any;
}
export interface PipelineExecutionStep {
    id: string;
    name: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    startTime?: string;
    endTime?: string;
    logs: string[];
    duration?: number;
}
export interface PipelineExecution {
    id: string;
    pipelineId: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    startTime: string;
    endTime?: string;
    steps: PipelineExecutionStep[];
    logs: string[];
    metrics?: Record<string, any>;
}
export interface ModelMetrics {
    accuracy?: number;
    precision?: number;
    recall?: number;
    f1Score?: number;
    rmse?: number;
    mae?: number;
    r2Score?: number;
    mape?: number;
    confusionMatrix?: number[][];
    featureImportance?: {
        feature: string;
        importance: number;
    }[];
}
export interface ModelResults {
    id: string;
    pipelineId: string;
    modelType: string;
    metrics: ModelMetrics;
    trainingTime: number;
    predictions?: any[];
    modelPath?: string;
    createdAt: string;
}
export interface DataUpload {
    id: string;
    filename: string;
    size: number;
    uploadedAt: string;
    columns: string[];
    rowCount: number;
    preview: any[];
}
export interface ApiResponse<T> {
    success?: boolean;
    data?: T;
    error?: string;
    message?: string;
    pipelines?: any[];
    count?: number;
    timestamp?: string;
}
export interface DashboardStats {
    totalPipelines: number;
    runningPipelines: number;
    completedPipelines: number;
    failedPipelines: number;
    averageExecutionTime: number;
    successRate: number;
}
export interface ChartData {
    name: string;
    value: number;
    color?: string;
}
export interface TimeSeriesData {
    timestamp: string;
    value: number;
    metric: string;
}
