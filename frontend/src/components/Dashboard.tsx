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
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend } from 'recharts';
import { Pipeline, DashboardStats } from '../types';
import { apiService } from '../services/api';

const Dashboard: React.FC = () => {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // Use mock data for development, switch to real API when available
      const pipelinesData = await apiService.getMockPipelines();
      const statsData = await apiService.getDashboardStats();
      
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