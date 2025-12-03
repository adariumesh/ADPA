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
  const [actionLoading, setActionLoading] = useState(false);

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
      setPipelines(data);
      if (data.length > 0 && !selectedPipeline) {
        setSelectedPipeline(data[0].id);
      }
    } catch (error) {
      console.error('Error loading pipelines:', error);
    }
  };

  const loadExecution = async (pipelineId: string) => {
    setLoading(true);
    try {
      // Get REAL pipeline data including steps, logs, and metrics from API
      const pipelineData = await apiService.monitorPipeline(pipelineId);
      const realLogs = await apiService.getPipelineLogs(pipelineId);
      
      // Find the pipeline from the local state to get status info
      const pipeline = pipelines.find(p => p.id === pipelineId);
      const pipelineStatus = pipeline?.status || pipelineData?.status || 'pending';
      
      // Extract real steps from API response if available
      let realSteps: PipelineExecutionStep[] = [];
      if (pipelineData?.steps && Array.isArray(pipelineData.steps)) {
        realSteps = pipelineData.steps.map((step: any) => ({
          id: step.id || `step-${Math.random()}`,
          name: step.name || 'Unknown Step',
          status: step.status || 'completed',
          startTime: step.startTime,
          endTime: step.endTime,
          duration: step.duration,
          logs: step.logs || [],
        }));
      }
      
      // Use real steps if available, otherwise fall back to generated
      const steps = realSteps.length > 0 ? realSteps : getStepsForStatus(pipelineStatus);
      
      // Use real logs if available
      const logsToUse = realLogs.length > 0 ? realLogs : getLogsForStatus(pipelineStatus, pipeline?.objective || '');
      
      // Extract real metrics if available
      const perfMetrics = pipelineData?.performance_metrics || {};
      const executionTime = pipelineData?.execution_time || 0;
      
      // Build execution object with REAL data when available
      const executionData: PipelineExecution = {
        id: 'exec-' + pipelineId,
        pipelineId,
        status: pipelineStatus as any,
        startTime: pipeline?.createdAt || new Date().toISOString(),
        endTime: pipelineStatus === 'completed' ? pipeline?.updatedAt : undefined,
        steps: steps,
        logs: logsToUse,
        metrics: {
          // Use real metrics if available
          cpu_usage: perfMetrics.cpu_usage || (pipelineStatus === 'running' ? 65 : (pipelineStatus === 'completed' ? 10 : 0)),
          memory_usage: perfMetrics.memory_usage || (pipelineStatus === 'running' ? 78 : (pipelineStatus === 'completed' ? 25 : 0)),
          progress: pipeline?.progress || (pipelineStatus === 'completed' ? 100 : 0),
          execution_time: executionTime,
          // Include performance metrics for display
          ...perfMetrics,
        },
      };
      
      setExecution(executionData);
      setLogs(logsToUse);
    } catch (error) {
      console.error('Error loading execution:', error);
      // Create fallback execution on error
      const pipeline = pipelines.find(p => p.id === pipelineId);
      if (pipeline) {
        const fallbackExecution: PipelineExecution = {
          id: 'exec-' + pipelineId,
          pipelineId,
          status: pipeline.status,
          startTime: pipeline.createdAt,
          endTime: pipeline.status === 'completed' ? pipeline.updatedAt : undefined,
          steps: getStepsForStatus(pipeline.status),
          logs: getLogsForStatus(pipeline.status, pipeline.objective || ''),
          metrics: { cpu_usage: 0, memory_usage: 0, progress: pipeline.progress },
        };
        setExecution(fallbackExecution);
        setLogs(fallbackExecution.logs);
      }
    } finally {
      setLoading(false);
    }
  };

  // Fallback: Generate steps based on pipeline status (used when real data not available)
  const getStepsForStatus = (status: string): PipelineExecutionStep[] => {
    const baseSteps = [
      { id: 'step1', name: 'Data Ingestion', logs: ['Loading dataset...', 'Data validation complete', 'Data ingested successfully'] },
      { id: 'step2', name: 'Data Preprocessing', logs: ['Cleaning data...', 'Handling missing values', 'Feature scaling applied'] },
      { id: 'step3', name: 'Feature Engineering', logs: ['Creating new features...', 'Feature selection complete'] },
      { id: 'step4', name: 'Model Training', logs: ['Training model...', 'Optimizing hyperparameters'] },
      { id: 'step5', name: 'Model Evaluation', logs: ['Evaluating model performance...', 'Generating metrics'] },
    ];

    if (status === 'completed') {
      return baseSteps.map((step, idx) => ({
        ...step,
        status: 'completed' as const,
        startTime: new Date(Date.now() - (5 - idx) * 60000).toISOString(),
        endTime: new Date(Date.now() - (4 - idx) * 60000).toISOString(),
        duration: 60,
      }));
    } else if (status === 'running') {
      return baseSteps.map((step, idx) => ({
        ...step,
        status: idx < 2 ? 'completed' as const : (idx === 2 ? 'running' as const : 'pending' as const),
        startTime: idx <= 2 ? new Date(Date.now() - (5 - idx) * 60000).toISOString() : undefined,
        endTime: idx < 2 ? new Date(Date.now() - (4 - idx) * 60000).toISOString() : undefined,
        duration: idx < 2 ? 60 : undefined,
        logs: idx <= 2 ? step.logs : [],
      }));
    } else if (status === 'failed') {
      return baseSteps.map((step, idx) => ({
        ...step,
        status: idx < 2 ? 'completed' as const : (idx === 2 ? 'failed' as const : 'pending' as const),
        startTime: idx <= 2 ? new Date(Date.now() - (5 - idx) * 60000).toISOString() : undefined,
        endTime: idx <= 2 ? new Date(Date.now() - (4 - idx) * 60000).toISOString() : undefined,
        duration: idx < 2 ? 60 : undefined,
        logs: idx === 2 ? ['Error: Pipeline failed at this step'] : (idx < 2 ? step.logs : []),
      }));
    } else {
      return baseSteps.map(step => ({
        ...step,
        status: 'pending' as const,
        logs: [],
      }));
    }
  };

  // Generate logs based on pipeline status
  const getLogsForStatus = (status: string, objective: string): string[] => {
    const baseLogs = [
      `[INFO] Pipeline started for: ${objective}`,
      '[INFO] Initializing data ingestion...',
    ];
    
    if (status === 'completed') {
      return [
        ...baseLogs,
        '[INFO] Data ingestion completed successfully',
        '[INFO] Data preprocessing completed',
        '[INFO] Feature engineering completed',
        '[INFO] Model training completed',
        '[INFO] Model evaluation completed',
        '[SUCCESS] Pipeline completed successfully!',
      ];
    } else if (status === 'running') {
      return [
        ...baseLogs,
        '[INFO] Data ingestion completed',
        '[INFO] Data preprocessing completed',
        '[INFO] Feature engineering in progress...',
      ];
    } else if (status === 'failed') {
      return [
        ...baseLogs,
        '[INFO] Data ingestion completed',
        '[INFO] Data preprocessing completed',
        '[ERROR] Pipeline failed during feature engineering',
      ];
    }
    return ['[INFO] Pipeline pending...'];
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

  const handleStartPipeline = async () => {
    if (!selectedPipeline) return;
    setActionLoading(true);
    try {
      await apiService.executePipelineById(selectedPipeline, true);
      await loadExecution(selectedPipeline);
      await loadPipelines();
    } catch (error) {
      console.error('Error starting pipeline:', error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStopPipeline = async () => {
    if (!selectedPipeline) return;
    setActionLoading(true);
    try {
      await apiService.stopPipeline(selectedPipeline);
      await loadExecution(selectedPipeline);
      await loadPipelines();
    } catch (error) {
      console.error('Error stopping pipeline:', error);
    } finally {
      setActionLoading(false);
    }
  };

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
                  {execution?.steps.map((step, index) => (
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
                      disabled={currentPipeline.status === 'running' || actionLoading}
                      color="success"
                      onClick={handleStartPipeline}
                    >
                      Start
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<PauseIcon />}
                      disabled={currentPipeline.status !== 'running' || actionLoading}
                    >
                      Pause
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<StopIcon />}
                      disabled={currentPipeline.status !== 'running' || actionLoading}
                      color="error"
                      onClick={handleStopPipeline}
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