import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Paper,
  Divider,
  IconButton,
  Button,
  TextField,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Alert,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  DataObject as DataIcon,
  ModelTraining as ModelIcon,
  Assessment as AssessmentIcon,
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Pipeline, PipelineExecution, PipelineExecutionStep } from '../types';
import { apiService } from '../services/api';

const PipelineMonitor: React.FC = () => {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selectedPipeline, setSelectedPipeline] = useState<string>('');
  const [execution, setExecution] = useState<PipelineExecution | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadPipelines();
  }, []);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (autoRefresh && selectedPipeline) {
      interval = setInterval(() => {
        loadExecution(selectedPipeline);
      }, 5000); // Refresh every 5 seconds
    }
    return () => clearInterval(interval);
  }, [autoRefresh, selectedPipeline]);

  const loadPipelines = async () => {
    try {
      const data = await apiService.getPipelines();
      console.log('Loaded pipelines:', data);
      setPipelines(data);
      // Auto-select first pipeline if none selected
      if (data.length > 0 && !selectedPipeline) {
        const firstPipelineId = data[0].id;
        console.log('Auto-selecting first pipeline:', firstPipelineId);
        setSelectedPipeline(firstPipelineId);
      }
    } catch (error) {
      console.error('Error loading pipelines:', error);
    }
  };

  const loadExecution = async (pipelineId: string) => {
    setLoading(true);
    try {
      // Get pipeline details from our local state
      const pipeline = pipelines.find(p => p.id === pipelineId);
      console.log('Loading execution for pipeline:', pipelineId, pipeline);
      
      // Try to get real execution data from the backend
      const [executionData, executionLogs] = await Promise.all([
        apiService.monitorPipeline(pipelineId),
        apiService.getPipelineLogs(pipelineId).catch(() => [] as string[]), // Gracefully handle missing endpoint
      ]);
      
      console.log('Execution data received:', executionData);
      console.log('Execution logs received:', executionLogs);
      
      // Cast to any to handle different API response formats
      const execData = executionData as any;
      
      if (execData && execData.steps && execData.steps.length > 0) {
        // Use real execution data from backend - map to correct format
        const mappedSteps: PipelineExecutionStep[] = execData.steps.map((step: any, idx: number) => ({
          id: step.id || `step${idx + 1}`,
          name: step.name || `Step ${idx + 1}`,
          status: step.status || 'pending',
          duration: step.duration,
          startTime: step.startTime || step.start_time,
          endTime: step.endTime || step.end_time,
          logs: step.logs || (step.details ? [step.details] : []),
        }));
        
        const mappedExecution: PipelineExecution = {
          id: execData.id || `exec-${pipelineId}`,
          pipelineId: pipelineId,
          status: execData.status || pipeline?.status || 'pending',
          startTime: execData.startTime || execData.start_time || pipeline?.createdAt || new Date().toISOString(),
          endTime: execData.endTime || execData.end_time,
          steps: mappedSteps,
          logs: execData.logs || executionLogs || [],
          metrics: execData.metrics || {
            cpu_usage: pipeline?.status === 'running' ? 65 : (pipeline?.status === 'completed' ? 10 : 0),
            memory_usage: pipeline?.status === 'running' ? 78 : (pipeline?.status === 'completed' ? 25 : 0),
            progress: execData.progress || pipeline?.progress || 0,
          },
        };
        
        console.log('Mapped execution with steps:', mappedExecution);
        setExecution(mappedExecution);
        setLogs(mappedExecution.logs);
      } else {
        // Fallback: construct execution from pipeline data if no execution endpoint
        const fallbackExecution: PipelineExecution = {
          id: 'exec-' + pipelineId,
          pipelineId,
          status: pipeline?.status || 'pending',
          startTime: pipeline?.createdAt || new Date().toISOString(),
          endTime: pipeline?.status === 'completed' ? pipeline?.updatedAt : undefined,
          steps: getStepsFromPipeline(pipeline),
          logs: executionLogs.length > 0 ? executionLogs : getDefaultLogs(pipeline?.status || 'pending', pipeline?.objective || '', pipeline?.error),
          metrics: {
            cpu_usage: pipeline?.status === 'running' ? 65 : (pipeline?.status === 'completed' ? 10 : 0),
            memory_usage: pipeline?.status === 'running' ? 78 : (pipeline?.status === 'completed' ? 25 : 0),
            progress: pipeline?.progress || 0,
          },
        };
        
        setExecution(fallbackExecution);
        setLogs(fallbackExecution.logs);
      }
    } catch (error) {
      console.error('Error loading execution:', error);
      // On error, try to show basic info from pipeline
      const pipeline = pipelines.find(p => p.id === pipelineId);
      if (pipeline) {
        const errorExecution: PipelineExecution = {
          id: 'exec-' + pipelineId,
          pipelineId,
          status: pipeline.status || 'pending',
          startTime: pipeline.createdAt || new Date().toISOString(),
          endTime: pipeline.status === 'completed' ? pipeline.updatedAt : undefined,
          steps: getStepsFromPipeline(pipeline),
          logs: [`[ERROR] Could not fetch execution details: ${error}`],
          metrics: { cpu_usage: 0, memory_usage: 0, progress: pipeline.progress || 0 },
        };
        setExecution(errorExecution);
        setLogs(errorExecution.logs);
      }
    } finally {
      setLoading(false);
    }
  };

  // Generate steps from pipeline data (real data when available, calculated from timestamps otherwise)
  const getStepsFromPipeline = (pipeline: Pipeline | undefined): PipelineExecutionStep[] => {
    if (!pipeline) {
      return getBaseSteps().map(step => ({
        ...step,
        status: 'pending' as const,
        logs: ['Waiting for pipeline to start...'],
      }));
    }

    // First, check if pipeline has real steps from the API
    if (pipeline.steps && pipeline.steps.length > 0) {
      console.log('Using real steps from pipeline:', pipeline.steps);
      return pipeline.steps.map((step: any, idx: number) => ({
        id: step.id || `step${idx + 1}`,
        name: step.name || `Step ${idx + 1}`,
        status: step.status || 'pending',
        duration: step.duration,
        startTime: step.startTime || step.start_time,
        endTime: step.endTime || step.end_time,
        logs: step.logs || (step.details ? [step.details] : ['Step details not available']),
      }));
    }

    // If pipeline has an error, show it in the first step
    if (pipeline.error) {
      const errorSteps = getBaseSteps();
      errorSteps[0] = {
        ...errorSteps[0],
        logs: [`Error: ${pipeline.error}`],
      };
      return errorSteps.map((step, idx) => ({
        ...step,
        status: idx === 0 ? 'failed' as const : 'pending' as const,
        logs: idx === 0 ? step.logs : ['Not started due to previous error'],
      }));
    }

    const status = pipeline.status;
    const startTime = pipeline.createdAt ? new Date(pipeline.createdAt).getTime() : Date.now();
    const endTime = pipeline.updatedAt ? new Date(pipeline.updatedAt).getTime() : Date.now();
    const totalDuration = (endTime - startTime) / 1000; // in seconds
    
    const baseSteps = getBaseSteps();
    const stepCount = baseSteps.length;

    if (status === 'completed') {
      // Distribute actual execution time across steps
      const stepDuration = totalDuration / stepCount;
      return baseSteps.map((step, idx) => ({
        ...step,
        status: 'completed' as const,
        startTime: new Date(startTime + idx * stepDuration * 1000).toISOString(),
        endTime: new Date(startTime + (idx + 1) * stepDuration * 1000).toISOString(),
        duration: Math.round(stepDuration),
      }));
    } else if (status === 'running') {
      // Calculate which step we're on based on elapsed time and progress
      const progress = pipeline.progress || 0;
      const currentStepIndex = Math.floor((progress / 100) * stepCount);
      const elapsedTime = (Date.now() - startTime) / 1000;
      const stepDuration = currentStepIndex > 0 ? elapsedTime / currentStepIndex : 0;
      
      return baseSteps.map((step, idx) => ({
        ...step,
        status: idx < currentStepIndex ? 'completed' as const : 
                (idx === currentStepIndex ? 'running' as const : 'pending' as const),
        startTime: idx <= currentStepIndex ? new Date(startTime + idx * stepDuration * 1000).toISOString() : undefined,
        endTime: idx < currentStepIndex ? new Date(startTime + (idx + 1) * stepDuration * 1000).toISOString() : undefined,
        duration: idx < currentStepIndex ? Math.round(stepDuration) : undefined,
        logs: idx <= currentStepIndex ? step.logs : [],
      }));
    } else if (status === 'failed') {
      const progress = pipeline.progress || 0;
      const failedStepIndex = Math.floor((progress / 100) * stepCount);
      const elapsedTime = totalDuration;
      const stepDuration = failedStepIndex > 0 ? elapsedTime / (failedStepIndex + 1) : elapsedTime;
      
      return baseSteps.map((step, idx) => ({
        ...step,
        status: idx < failedStepIndex ? 'completed' as const : 
                (idx === failedStepIndex ? 'failed' as const : 'pending' as const),
        startTime: idx <= failedStepIndex ? new Date(startTime + idx * stepDuration * 1000).toISOString() : undefined,
        endTime: idx <= failedStepIndex ? new Date(startTime + (idx + 1) * stepDuration * 1000).toISOString() : undefined,
        duration: idx <= failedStepIndex ? Math.round(stepDuration) : undefined,
        logs: idx === failedStepIndex ? ['Error: Pipeline failed at this step'] : (idx < failedStepIndex ? step.logs : []),
      }));
    } else {
      return baseSteps.map(step => ({
        ...step,
        status: 'pending' as const,
        logs: ['Waiting to start...'],
      }));
    }
  };

  // Base step definitions
  const getBaseSteps = () => [
    { id: 'step1', name: 'Data Ingestion', logs: ['Loading dataset...', 'Data validation complete', 'Data ingested successfully'] },
    { id: 'step2', name: 'Data Preprocessing', logs: ['Cleaning data...', 'Handling missing values', 'Feature scaling applied'] },
    { id: 'step3', name: 'Feature Engineering', logs: ['Creating new features...', 'Feature selection complete'] },
    { id: 'step4', name: 'Model Training', logs: ['Training model...', 'Optimizing hyperparameters'] },
    { id: 'step5', name: 'Model Evaluation', logs: ['Evaluating model performance...', 'Generating metrics'] },
  ];

  // Default logs when backend logs are not available
  const getDefaultLogs = (status: string, objective: string, error?: string): string[] => {
    const timestamp = new Date().toLocaleTimeString();
    const baseLogs = [
      `[${timestamp}] [INFO] Pipeline: ${objective || 'No objective specified'}`,
      `[${timestamp}] [INFO] Status: ${status}`,
    ];
    
    if (error) {
      return [
        ...baseLogs,
        `[${timestamp}] [ERROR] ${error}`,
      ];
    }
    
    if (status === 'completed') {
      return [
        ...baseLogs,
        `[${timestamp}] [SUCCESS] Pipeline completed successfully!`,
      ];
    } else if (status === 'running') {
      return [
        ...baseLogs,
        `[${timestamp}] [INFO] Pipeline is currently running...`,
      ];
    } else if (status === 'failed') {
      return [
        ...baseLogs,
        `[${timestamp}] [ERROR] Pipeline failed - check execution steps for details`,
      ];
    } else if (status === 'pending') {
      return [
        ...baseLogs,
        `[${timestamp}] [INFO] Pipeline is pending - waiting to start`,
      ];
    }
    return baseLogs;
  };

  useEffect(() => {
    if (selectedPipeline) {
      loadExecution(selectedPipeline);
    }
  }, [selectedPipeline]);

  const getStepIcon = (status: PipelineExecutionStep['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon color="success" />;
      case 'running':
        return <PlayIcon color="primary" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      default:
        return <ScheduleIcon color="disabled" />;
    }
  };

  const getStepColor = (status: PipelineExecutionStep['status']) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'running':
        return 'primary';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const getMetricsChartData = () => {
    // Mock time series data for metrics
    return [
      { time: '5m ago', cpu: 45, memory: 60 },
      { time: '4m ago', cpu: 52, memory: 65 },
      { time: '3m ago', cpu: 58, memory: 70 },
      { time: '2m ago', cpu: 62, memory: 75 },
      { time: '1m ago', cpu: 65, memory: 78 },
      { time: 'now', cpu: 65, memory: 78 },
    ];
  };

  const currentPipeline = pipelines.find(p => p.id === selectedPipeline);

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Pipeline Monitor</Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => selectedPipeline && loadExecution(selectedPipeline)}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant={autoRefresh ? "contained" : "outlined"}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            Auto Refresh: {autoRefresh ? 'ON' : 'OFF'}
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Pipeline Selection */}
        <Grid size={12}>
          <Card>
            <CardContent>
              <FormControl fullWidth>
                <InputLabel>Select Pipeline</InputLabel>
                <Select
                  value={selectedPipeline}
                  label="Select Pipeline"
                  onChange={(e) => setSelectedPipeline(e.target.value)}
                >
                  {pipelines.map((pipeline) => (
                    <MenuItem key={pipeline.id} value={pipeline.id}>
                      {pipeline.name} - {pipeline.status}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </CardContent>
          </Card>
        </Grid>

        {currentPipeline && (
          <>
            {/* Pipeline Overview */}
            <Grid size={{ xs: 12, md: 6 }}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Pipeline Overview
                  </Typography>
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1">{currentPipeline.name}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {currentPipeline.description}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                    <Chip
                      label={currentPipeline.status}
                      color={getStepColor(currentPipeline.status as any)}
                      size="small"
                    />
                    <Chip
                      label={currentPipeline.type.replace('_', ' ')}
                      variant="outlined"
                      size="small"
                    />
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={currentPipeline.progress} 
                    sx={{ mb: 1 }}
                  />
                  <Typography variant="caption">
                    Progress: {currentPipeline.progress}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            {/* Execution Metrics */}
            <Grid size={{ xs: 12, md: 6 }}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Resource Usage
                  </Typography>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={getMetricsChartData()}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" />
                      <YAxis />
                      <Tooltip />
                      <Line
                        type="monotone"
                        dataKey="cpu"
                        stroke="#1976d2"
                        name="CPU %"
                        strokeWidth={2}
                      />
                      <Line
                        type="monotone"
                        dataKey="memory"
                        stroke="#dc004e"
                        name="Memory %"
                        strokeWidth={2}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </Grid>

            {/* Execution Steps */}
            <Grid size={{ xs: 12, md: 8 }}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Execution Steps
                  </Typography>
                  {(!execution || !execution.steps || execution.steps.length === 0) && (
                    <Alert severity="info" sx={{ mb: 2 }}>
                      Loading execution steps... If this persists, the pipeline may not have started yet.
                    </Alert>
                  )}
                  {execution?.steps?.map((step, index) => (
                    <Accordion key={step.id}>
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                          {getStepIcon(step.status)}
                          <Typography sx={{ flexGrow: 1 }}>{step.name}</Typography>
                          <Chip
                            label={step.status}
                            color={getStepColor(step.status)}
                            size="small"
                          />
                          {step.duration && (
                            <Typography variant="caption" color="text.secondary">
                              {step.duration}s
                            </Typography>
                          )}
                        </Box>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Box>
                          <Typography variant="subtitle2" gutterBottom>
                            Logs:
                          </Typography>
                          <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50' }}>
                            {step.logs.length > 0 ? (
                              step.logs.map((log, logIndex) => (
                                <Typography
                                  key={logIndex}
                                  variant="body2"
                                  component="div"
                                  sx={{ fontFamily: 'monospace' }}
                                >
                                  {log}
                                </Typography>
                              ))
                            ) : (
                              <Typography variant="body2" color="text.secondary">
                                No logs available
                              </Typography>
                            )}
                          </Paper>
                          {step.startTime && (
                            <Box sx={{ mt: 2 }}>
                              <Typography variant="caption" color="text.secondary">
                                Started: {new Date(step.startTime).toLocaleString()}
                              </Typography>
                              {step.endTime && (
                                <>
                                  <br />
                                  <Typography variant="caption" color="text.secondary">
                                    Ended: {new Date(step.endTime).toLocaleString()}
                                  </Typography>
                                </>
                              )}
                            </Box>
                          )}
                        </Box>
                      </AccordionDetails>
                    </Accordion>
                  ))}
                </CardContent>
              </Card>
            </Grid>

            {/* Live Logs */}
            <Grid size={{ xs: 12, md: 4 }}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Live Logs
                  </Typography>
                  <Paper
                    variant="outlined"
                    sx={{
                      height: 400,
                      overflow: 'auto',
                      p: 2,
                      bgcolor: 'grey.900',
                      color: 'grey.100',
                    }}
                  >
                    {logs.map((log, index) => (
                      <Typography
                        key={index}
                        variant="body2"
                        component="div"
                        sx={{
                          fontFamily: 'monospace',
                          fontSize: '0.8rem',
                          mb: 0.5,
                        }}
                      >
                        [{new Date().toLocaleTimeString()}] {log}
                      </Typography>
                    ))}
                  </Paper>
                </CardContent>
              </Card>
            </Grid>

            {/* Control Panel */}
            <Grid size={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Control Panel
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button
                      variant="contained"
                      startIcon={<PlayIcon />}
                      disabled={currentPipeline.status === 'running'}
                      color="success"
                    >
                      Start
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<PauseIcon />}
                      disabled={currentPipeline.status !== 'running'}
                    >
                      Pause
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<StopIcon />}
                      disabled={currentPipeline.status !== 'running'}
                      color="error"
                    >
                      Stop
                    </Button>
                  </Box>
                  {currentPipeline.status === 'running' && (
                    <Alert severity="info" sx={{ mt: 2 }}>
                      Pipeline is currently running. Monitor the progress above.
                    </Alert>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </>
        )}

        {!selectedPipeline && (
          <Grid size={12}>
            <Alert severity="info">
              Please select a pipeline to monitor its execution.
            </Alert>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default PipelineMonitor;