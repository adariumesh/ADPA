import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  IconButton,
  LinearProgress,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Tooltip,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  Delete as DeleteIcon,
  Psychology as AIIcon,
  CheckCircle as CheckIcon,
  Cancel as ErrorIcon,
  AutoAwesome as SparkleIcon,
} from '@mui/icons-material';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend } from 'recharts';
import { Pipeline, DashboardStats } from '../types';
import { apiService } from '../services/api';

const Dashboard: React.FC = () => {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [aiStatus, setAiStatus] = useState<any>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // Use real API to get pipelines and stats
      const pipelinesData = await apiService.getPipelines();
      const statsData = await apiService.getDashboardStats();
      
      // Get AI/health status
      try {
        const response = await fetch('https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/health');
        const healthData = await response.json();
        setAiStatus(healthData);
      } catch (e) {
        console.error('Could not fetch AI status:', e);
      }
      
      setPipelines(pipelinesData);
      setStats(statsData);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExecutePipeline = async (pipelineId: string) => {
    try {
      await apiService.executePipeline(pipelineId);
      loadData(); // Refresh data
    } catch (error) {
      console.error('Error executing pipeline:', error);
    }
  };

  const getStatusColor = (status: Pipeline['status']) => {
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

  const getStatusChartData = () => {
    const statusCounts = pipelines.reduce((acc, pipeline) => {
      acc[pipeline.status] = (acc[pipeline.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return [
      { name: 'Completed', value: statusCounts.completed || 0, color: '#4caf50' },
      { name: 'Running', value: statusCounts.running || 0, color: '#2196f3' },
      { name: 'Failed', value: statusCounts.failed || 0, color: '#f44336' },
      { name: 'Pending', value: statusCounts.pending || 0, color: '#ff9800' },
    ];
  };

  const getTypeChartData = () => {
    const typeCounts = pipelines.reduce((acc, pipeline) => {
      acc[pipeline.type] = (acc[pipeline.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(typeCounts).map(([name, value]) => ({ name, value }));
  };

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" gutterBottom>
          Dashboard
        </Typography>
        <LinearProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Dashboard
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={loadData}
        >
          Refresh
        </Button>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Pipelines
              </Typography>
              <Typography variant="h5" component="h2">
                {pipelines.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Running Pipelines
              </Typography>
              <Typography variant="h5" component="h2" color="primary">
                {pipelines.filter(p => p.status === 'running').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Success Rate
              </Typography>
              <Typography variant="h5" component="h2" color="success.main">
                {pipelines.length > 0 
                  ? Math.round((pipelines.filter(p => p.status === 'completed').length / pipelines.length) * 100)
                  : 0}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Avg. Accuracy
              </Typography>
              <Typography variant="h5" component="h2">
                {pipelines.filter(p => p.accuracy).length > 0
                  ? Math.round((pipelines.filter(p => p.accuracy).reduce((sum, p) => sum + (p.accuracy || 0), 0) / pipelines.filter(p => p.accuracy).length) * 100)
                  : 0}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* AI Capabilities Status Card */}
      {aiStatus && (
        <Card sx={{ mb: 4, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <AIIcon sx={{ fontSize: 40, color: 'white', mr: 2 }} />
              <Box>
                <Typography variant="h5" sx={{ color: 'white', fontWeight: 'bold' }}>
                  🤖 ADPA Agentic AI System
                </Typography>
                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                  Version {aiStatus.version || '4.0.0-agentic'} | Powered by Amazon Bedrock
                </Typography>
              </Box>
              <Chip 
                label={aiStatus.status === 'healthy' ? '● Online' : '○ Degraded'} 
                sx={{ 
                  ml: 'auto', 
                  bgcolor: aiStatus.status === 'healthy' ? '#4caf50' : '#ff9800',
                  color: 'white',
                  fontWeight: 'bold'
                }} 
              />
            </Box>
            
            <Grid container spacing={2}>
              {/* Components Status */}
              <Grid size={{ xs: 12, md: 4 }}>
                <Paper sx={{ p: 2, bgcolor: 'rgba(255,255,255,0.1)' }}>
                  <Typography variant="subtitle2" sx={{ color: 'white', mb: 1 }}>
                    System Components
                  </Typography>
                  <List dense>
                    {aiStatus.components && Object.entries(aiStatus.components).map(([key, value]) => (
                      <ListItem key={key} sx={{ py: 0 }}>
                        <ListItemIcon sx={{ minWidth: 32 }}>
                          {value ? <CheckIcon sx={{ color: '#4caf50', fontSize: 18 }} /> : <ErrorIcon sx={{ color: '#f44336', fontSize: 18 }} />}
                        </ListItemIcon>
                        <ListItemText 
                          primary={key.replace('_', ' ').toUpperCase()} 
                          primaryTypographyProps={{ sx: { color: 'white', fontSize: '0.85rem' } }}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Paper>
              </Grid>
              
              {/* AI Capabilities */}
              <Grid size={{ xs: 12, md: 8 }}>
                <Paper sx={{ p: 2, bgcolor: 'rgba(255,255,255,0.1)' }}>
                  <Typography variant="subtitle2" sx={{ color: 'white', mb: 1 }}>
                    <SparkleIcon sx={{ fontSize: 16, mr: 0.5, verticalAlign: 'middle' }} />
                    AI Capabilities (Amazon Bedrock Claude 3.5)
                  </Typography>
                  <Grid container spacing={1}>
                    {aiStatus.ai_capabilities?.agentic_features?.map((feature: string, index: number) => (
                      <Grid key={index} size={{ xs: 6 }}>
                        <Chip
                          icon={<CheckIcon sx={{ color: 'white !important' }} />}
                          label={feature.replace(/_/g, ' ')}
                          size="small"
                          sx={{ 
                            bgcolor: 'rgba(255,255,255,0.2)', 
                            color: 'white',
                            fontSize: '0.75rem',
                            '& .MuiChip-icon': { color: 'white' }
                          }}
                        />
                      </Grid>
                    ))}
                  </Grid>
                  {aiStatus.ai_capabilities?.bedrock_enabled && (
                    <Alert severity="success" sx={{ mt: 2, bgcolor: 'rgba(76, 175, 80, 0.2)', color: 'white' }}>
                      <strong>Bedrock AI Enabled:</strong> Pipelines use intelligent NL understanding, dataset analysis, and AI-powered planning
                    </Alert>
                  )}
                </Paper>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Charts */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Pipeline Status Distribution
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={getStatusChartData()}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name}: ${value}`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {getStatusChartData().map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Pipeline Types
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={getTypeChartData()}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Legend />
                  <Bar dataKey="value" fill="#1976d2" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Recent Pipelines Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Recent Pipelines
          </Typography>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Progress</TableCell>
                  <TableCell>Accuracy</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {pipelines.map((pipeline) => (
                  <TableRow key={pipeline.id}>
                    <TableCell>
                      <Typography variant="subtitle2">{pipeline.name}</Typography>
                      <Typography variant="body2" color="textSecondary">
                        {pipeline.description}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={pipeline.type.replace('_', ' ')}
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={pipeline.status}
                        color={getStatusColor(pipeline.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ width: '100px' }}>
                        <LinearProgress 
                          variant="determinate" 
                          value={pipeline.progress} 
                          color={pipeline.status === 'failed' ? 'error' : 'primary'}
                        />
                        <Typography variant="caption">{pipeline.progress}%</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      {pipeline.accuracy ? `${Math.round(pipeline.accuracy * 100)}%` : 'N/A'}
                    </TableCell>
                    <TableCell>
                      {new Date(pipeline.createdAt).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Tooltip title="Run Pipeline">
                        <IconButton
                          size="small"
                          onClick={() => handleExecutePipeline(pipeline.id)}
                          disabled={pipeline.status === 'running'}
                          color="primary"
                        >
                          <PlayIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="View Details">
                        <IconButton size="small" color="info">
                          <ViewIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete Pipeline">
                        <IconButton size="small" color="error">
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Dashboard;