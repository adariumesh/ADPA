import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tabs,
  Tab,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import {
  Download as DownloadIcon,
  Assessment as AssessmentIcon,
  ShowChart as ChartIcon,
  DataObject as DataIcon,
  CloudDownload as CloudDownloadIcon,
} from '@mui/icons-material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  Cell,
  PieChart,
  Pie,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';
import { Pipeline, ModelResults, ModelMetrics } from '../types';
import { apiService } from '../services/api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`results-tabpanel-${index}`}
      aria-labelledby={`results-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const ResultsViewer: React.FC = () => {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selectedPipeline, setSelectedPipeline] = useState<string>('');
  const [results, setResults] = useState<ModelResults | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [downloadDialogOpen, setDownloadDialogOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadPipelines();
  }, []);

  useEffect(() => {
    if (selectedPipeline) {
      loadResults(selectedPipeline);
    }
  }, [selectedPipeline]);

  const loadPipelines = async () => {
    try {
      const data = await apiService.getMockPipelines();
      const completedPipelines = data.filter(p => p.status === 'completed');
      setPipelines(completedPipelines);
      if (completedPipelines.length > 0 && !selectedPipeline) {
        setSelectedPipeline(completedPipelines[0].id);
      }
    } catch (error) {
      console.error('Error loading pipelines:', error);
    }
  };

  const loadResults = async (pipelineId: string) => {
    setLoading(true);
    try {
      // Mock results data
      const mockResults: ModelResults = {
        id: 'result-' + pipelineId,
        pipelineId,
        modelType: 'Random Forest',
        metrics: {
          accuracy: 0.85,
          precision: 0.82,
          recall: 0.88,
          f1Score: 0.85,
          confusionMatrix: [
            [145, 8, 2],
            [12, 132, 6],
            [3, 7, 142]
          ],
          featureImportance: [
            { feature: 'age', importance: 0.25 },
            { feature: 'income', importance: 0.22 },
            { feature: 'education', importance: 0.18 },
            { feature: 'location', importance: 0.15 },
            { feature: 'experience', importance: 0.12 },
            { feature: 'gender', importance: 0.08 },
          ]
        },
        trainingTime: 245,
        modelPath: '/models/customer_segmentation_rf.pkl',
        createdAt: new Date().toISOString(),
        predictions: [
          { actual: 'A', predicted: 'A', confidence: 0.92 },
          { actual: 'B', predicted: 'B', confidence: 0.88 },
          { actual: 'C', predicted: 'A', confidence: 0.76 },
          { actual: 'A', predicted: 'A', confidence: 0.95 },
          { actual: 'B', predicted: 'C', confidence: 0.72 },
        ]
      };

      setResults(mockResults);
    } catch (error) {
      console.error('Error loading results:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadModel = async () => {
    if (!selectedPipeline) return;
    
    try {
      const blob = await apiService.downloadModel(selectedPipeline);
      if (blob) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `model_${selectedPipeline}.pkl`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error('Error downloading model:', error);
    }
  };

  const getConfusionMatrixData = () => {
    if (!results?.metrics.confusionMatrix) return [];
    
    const matrix = results.metrics.confusionMatrix;
    const data = [];
    
    for (let i = 0; i < matrix.length; i++) {
      for (let j = 0; j < matrix[i].length; j++) {
        data.push({
          x: j,
          y: i,
          value: matrix[i][j],
          label: `Predicted: ${j}, Actual: ${i}, Count: ${matrix[i][j]}`
        });
      }
    }
    
    return data;
  };

  const getFeatureImportanceData = () => {
    return results?.metrics.featureImportance || [];
  };

  const getMetricsRadarData = () => {
    if (!results?.metrics) return [];
    
    return [
      {
        subject: 'Accuracy',
        value: (results.metrics.accuracy || 0) * 100,
        fullMark: 100,
      },
      {
        subject: 'Precision',
        value: (results.metrics.precision || 0) * 100,
        fullMark: 100,
      },
      {
        subject: 'Recall',
        value: (results.metrics.recall || 0) * 100,
        fullMark: 100,
      },
      {
        subject: 'F1 Score',
        value: (results.metrics.f1Score || 0) * 100,
        fullMark: 100,
      },
    ];
  };

  const currentPipeline = pipelines.find(p => p.id === selectedPipeline);

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Results Viewer</Typography>
        <Button
          variant="contained"
          startIcon={<DownloadIcon />}
          onClick={() => setDownloadDialogOpen(true)}
          disabled={!selectedPipeline || !results}
        >
          Download Results
        </Button>
      </Box>

      {/* Pipeline Selection */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={3} alignItems="center">
            <Grid size={{ xs: 12, md: 6 }}>
              <FormControl fullWidth>
                <InputLabel>Select Pipeline</InputLabel>
                <Select
                  value={selectedPipeline}
                  label="Select Pipeline"
                  onChange={(e) => setSelectedPipeline(e.target.value)}
                >
                  {pipelines.map((pipeline) => (
                    <MenuItem key={pipeline.id} value={pipeline.id}>
                      {pipeline.name} - {pipeline.type}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            {currentPipeline && (
              <Grid size={{ xs: 12, md: 6 }}>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Chip label={currentPipeline.type.replace('_', ' ')} variant="outlined" />
                  <Chip label={`${currentPipeline.accuracy ? Math.round(currentPipeline.accuracy * 100) : 0}% Accuracy`} color="primary" />
                  <Chip label={`${currentPipeline.progress}% Complete`} color="success" />
                </Box>
              </Grid>
            )}
          </Grid>
        </CardContent>
      </Card>

      {!selectedPipeline && (
        <Alert severity="info">
          Please select a completed pipeline to view its results.
        </Alert>
      )}

      {pipelines.length === 0 && (
        <Alert severity="warning">
          No completed pipelines found. Complete a pipeline to view results here.
        </Alert>
      )}

      {selectedPipeline && results && (
        <>
          {/* Results Tabs */}
          <Card>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs
                value={tabValue}
                onChange={(e, newValue) => setTabValue(newValue)}
                aria-label="results tabs"
              >
                <Tab label="Overview" icon={<AssessmentIcon />} />
                <Tab label="Metrics" icon={<ChartIcon />} />
                <Tab label="Feature Importance" icon={<DataIcon />} />
                <Tab label="Predictions" icon={<DataIcon />} />
              </Tabs>
            </Box>

            {/* Overview Tab */}
            <TabPanel value={tabValue} index={0}>
              <Grid container spacing={3}>
                {/* Model Info */}
                <Grid size={{ xs: 12, md: 6 }}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Model Information
                      </Typography>
                      <Table size="small">
                        <TableBody>
                          <TableRow>
                            <TableCell><strong>Model Type:</strong></TableCell>
                            <TableCell>{results.modelType}</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell><strong>Training Time:</strong></TableCell>
                            <TableCell>{results.trainingTime}s</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell><strong>Created:</strong></TableCell>
                            <TableCell>{new Date(results.createdAt).toLocaleString()}</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell><strong>Model Path:</strong></TableCell>
                            <TableCell>{results.modelPath}</TableCell>
                          </TableRow>
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Key Metrics */}
                <Grid size={{ xs: 12, md: 6 }}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Key Metrics
                      </Typography>
                      <Grid container spacing={2}>
                        <Grid size={6}>
                          <Box textAlign="center">
                            <Typography variant="h4" color="primary">
                              {Math.round((results.metrics.accuracy || 0) * 100)}%
                            </Typography>
                            <Typography variant="body2">Accuracy</Typography>
                          </Box>
                        </Grid>
                        <Grid size={6}>
                          <Box textAlign="center">
                            <Typography variant="h4" color="secondary">
                              {Math.round((results.metrics.f1Score || 0) * 100)}%
                            </Typography>
                            <Typography variant="body2">F1 Score</Typography>
                          </Box>
                        </Grid>
                        <Grid size={6}>
                          <Box textAlign="center">
                            <Typography variant="h4" color="success.main">
                              {Math.round((results.metrics.precision || 0) * 100)}%
                            </Typography>
                            <Typography variant="body2">Precision</Typography>
                          </Box>
                        </Grid>
                        <Grid size={6}>
                          <Box textAlign="center">
                            <Typography variant="h4" color="warning.main">
                              {Math.round((results.metrics.recall || 0) * 100)}%
                            </Typography>
                            <Typography variant="body2">Recall</Typography>
                          </Box>
                        </Grid>
                      </Grid>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Performance Radar Chart */}
                <Grid size={12}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Performance Overview
                      </Typography>
                      <ResponsiveContainer width="100%" height={400}>
                        <BarChart data={getMetricsRadarData()}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="subject" />
                          <YAxis />
                          <Tooltip />
                          <Bar dataKey="value" fill="#1976d2" />
                        </BarChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </TabPanel>

            {/* Metrics Tab */}
            <TabPanel value={tabValue} index={1}>
              <Grid container spacing={3}>
                {/* Confusion Matrix */}
                {results.metrics.confusionMatrix && (
                  <Grid size={{ xs: 12, md: 6 }}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          Confusion Matrix
                        </Typography>
                        <TableContainer component={Paper}>
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell></TableCell>
                                <TableCell align="center" colSpan={results.metrics.confusionMatrix[0].length}>
                                  <strong>Predicted</strong>
                                </TableCell>
                              </TableRow>
                              <TableRow>
                                <TableCell><strong>Actual</strong></TableCell>
                                {results.metrics.confusionMatrix[0].map((_, index) => (
                                  <TableCell key={index} align="center">
                                    {String.fromCharCode(65 + index)}
                                  </TableCell>
                                ))}
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {results.metrics.confusionMatrix.map((row, rowIndex) => (
                                <TableRow key={rowIndex}>
                                  <TableCell component="th" scope="row">
                                    <strong>{String.fromCharCode(65 + rowIndex)}</strong>
                                  </TableCell>
                                  {row.map((value, colIndex) => (
                                    <TableCell
                                      key={colIndex}
                                      align="center"
                                      sx={{
                                        bgcolor: rowIndex === colIndex ? 'success.light' : 'error.light',
                                        color: 'white',
                                        fontWeight: 'bold',
                                      }}
                                    >
                                      {value}
                                    </TableCell>
                                  ))}
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      </CardContent>
                    </Card>
                  </Grid>
                )}

                {/* Metrics Breakdown */}
                <Grid size={{ xs: 12, md: 6 }}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Detailed Metrics
                      </Typography>
                      <List>
                        <ListItem>
                          <ListItemText
                            primary="Accuracy"
                            secondary={`${Math.round((results.metrics.accuracy || 0) * 10000) / 100}%`}
                          />
                        </ListItem>
                        <ListItem>
                          <ListItemText
                            primary="Precision"
                            secondary={`${Math.round((results.metrics.precision || 0) * 10000) / 100}%`}
                          />
                        </ListItem>
                        <ListItem>
                          <ListItemText
                            primary="Recall"
                            secondary={`${Math.round((results.metrics.recall || 0) * 10000) / 100}%`}
                          />
                        </ListItem>
                        <ListItem>
                          <ListItemText
                            primary="F1 Score"
                            secondary={`${Math.round((results.metrics.f1Score || 0) * 10000) / 100}%`}
                          />
                        </ListItem>
                      </List>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </TabPanel>

            {/* Feature Importance Tab */}
            <TabPanel value={tabValue} index={2}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Feature Importance
                  </Typography>
                  <ResponsiveContainer width="100%" height={400}>
                    <BarChart data={getFeatureImportanceData()} layout="horizontal">
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" domain={[0, 'dataMax']} />
                      <YAxis dataKey="feature" type="category" width={80} />
                      <Tooltip />
                      <Bar dataKey="importance" fill="#1976d2" />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </TabPanel>

            {/* Predictions Tab */}
            <TabPanel value={tabValue} index={3}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Sample Predictions
                  </Typography>
                  <TableContainer component={Paper}>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Actual</TableCell>
                          <TableCell>Predicted</TableCell>
                          <TableCell>Confidence</TableCell>
                          <TableCell>Status</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {results.predictions?.slice(0, 10).map((prediction, index) => (
                          <TableRow key={index}>
                            <TableCell>{prediction.actual}</TableCell>
                            <TableCell>{prediction.predicted}</TableCell>
                            <TableCell>{Math.round(prediction.confidence * 100)}%</TableCell>
                            <TableCell>
                              <Chip
                                label={prediction.actual === prediction.predicted ? 'Correct' : 'Incorrect'}
                                color={prediction.actual === prediction.predicted ? 'success' : 'error'}
                                size="small"
                              />
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>
            </TabPanel>
          </Card>
        </>
      )}

      {/* Download Dialog */}
      <Dialog open={downloadDialogOpen} onClose={() => setDownloadDialogOpen(false)}>
        <DialogTitle>Download Options</DialogTitle>
        <DialogContent>
          <Typography gutterBottom>
            Choose what you'd like to download:
          </Typography>
          <List>
            <ListItem>
              <Button startIcon={<CloudDownloadIcon />} fullWidth onClick={handleDownloadModel}>
                Download Trained Model (.pkl)
              </Button>
            </ListItem>
            <ListItem>
              <Button startIcon={<AssessmentIcon />} fullWidth>
                Download Results Report (.pdf)
              </Button>
            </ListItem>
            <ListItem>
              <Button startIcon={<DataIcon />} fullWidth>
                Download Predictions (.csv)
              </Button>
            </ListItem>
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDownloadDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ResultsViewer;