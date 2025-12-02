import React, { useState, useCallback } from 'react';
import {
  Box,
  Stepper,
  Step,
  StepLabel,
  Button,
  Typography,
  Card,
  CardContent,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Alert,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Delete as DeleteIcon,
  Preview as PreviewIcon,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { Pipeline, DataUpload } from '../types';
import { apiService } from '../services/api';

const steps = ['Upload Data', 'Configure Pipeline', 'Review & Create'];

interface PipelineConfig {
  name: string;
  description: string;
  type: 'classification' | 'regression' | 'clustering' | 'anomaly_detection';
  objective: string;
  targetColumn?: string;
  features?: string[];
  algorithm?: string;
}

const PipelineBuilder: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [dataUpload, setDataUpload] = useState<DataUpload | null>(null);
  const [config, setConfig] = useState<PipelineConfig>({
    name: '',
    description: '',
    type: 'classification',
    objective: '',
  });
  const [uploading, setUploading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      setUploadedFile(file);
      setErrors([]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/json': ['.json'],
    },
    maxFiles: 1,
  });

  const handleUpload = async () => {
    if (!uploadedFile) {
      setErrors(['Please select a file to upload']);
      return;
    }

    setUploading(true);
    setErrors([]);

    try {
      const upload = await apiService.uploadData(uploadedFile);
      if (upload) {
        setDataUpload(upload);
        setActiveStep(1);
      } else {
        setErrors(['Failed to upload file']);
      }
    } catch (error) {
      console.error('Upload error:', error);
      setErrors(['Error uploading file. Please try again.']);
    } finally {
      setUploading(false);
    }
  };

  const handleConfigChange = (field: keyof PipelineConfig, value: any) => {
    setConfig(prev => ({ ...prev, [field]: value }));
    setErrors([]);
  };

  const validateConfig = (): boolean => {
    const newErrors: string[] = [];

    if (!config.name.trim()) {
      newErrors.push('Pipeline name is required');
    }
    if (!config.objective.trim()) {
      newErrors.push('Objective description is required');
    }
    if (!dataUpload) {
      newErrors.push('Data upload is required');
    }

    setErrors(newErrors);
    return newErrors.length === 0;
  };

  const handleCreatePipeline = async () => {
    if (!validateConfig()) {
      return;
    }

    setCreating(true);

    try {
      const pipeline: Partial<Pipeline> = {
        name: config.name,
        description: config.description,
        type: config.type,
        objective: config.objective,
        dataset: dataUpload?.filename,
        status: 'pending',
        progress: 0,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      const created = await apiService.createPipeline(pipeline);
      if (created) {
        // Reset form
        setActiveStep(0);
        setUploadedFile(null);
        setDataUpload(null);
        setConfig({
          name: '',
          description: '',
          type: 'classification',
          objective: '',
        });
        alert('Pipeline created successfully!');
      } else {
        setErrors(['Failed to create pipeline']);
      }
    } catch (error) {
      console.error('Create pipeline error:', error);
      setErrors(['Error creating pipeline. Please try again.']);
    } finally {
      setCreating(false);
    }
  };

  const handleNext = () => {
    if (activeStep === 0 && !dataUpload) {
      handleUpload();
      return;
    }
    
    if (activeStep === 1 && !validateConfig()) {
      return;
    }

    setActiveStep(prev => prev + 1);
  };

  const handleBack = () => {
    setActiveStep(prev => prev - 1);
    setErrors([]);
  };

  const handleReset = () => {
    setActiveStep(0);
    setUploadedFile(null);
    setDataUpload(null);
    setConfig({
      name: '',
      description: '',
      type: 'classification',
      objective: '',
    });
    setErrors([]);
  };

  const renderStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Upload Your Dataset
              </Typography>
              <Paper
                {...getRootProps()}
                sx={{
                  border: '2px dashed #ccc',
                  borderRadius: 2,
                  p: 4,
                  textAlign: 'center',
                  cursor: 'pointer',
                  bgcolor: isDragActive ? 'action.hover' : 'transparent',
                  '&:hover': { bgcolor: 'action.hover' },
                }}
              >
                <input {...getInputProps()} />
                <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                {uploadedFile ? (
                  <Box>
                    <Typography variant="h6" color="primary">
                      {uploadedFile.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                    </Typography>
                  </Box>
                ) : (
                  <Box>
                    <Typography variant="h6" gutterBottom>
                      {isDragActive ? 'Drop the file here' : 'Drag & drop a CSV file here'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Or click to select a file
                    </Typography>
                  </Box>
                )}
              </Paper>
              {dataUpload && (
                <Box sx={{ mt: 3 }}>
                  <Alert severity="success">
                    File uploaded successfully! {dataUpload.rowCount} rows, {dataUpload.columns.length} columns
                  </Alert>
                  <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                    <Button
                      startIcon={<PreviewIcon />}
                      onClick={() => setPreviewOpen(true)}
                    >
                      Preview Data
                    </Button>
                    <Button
                      color="error"
                      startIcon={<DeleteIcon />}
                      onClick={() => {
                        setDataUpload(null);
                        setUploadedFile(null);
                      }}
                    >
                      Remove
                    </Button>
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        );

      case 1:
        return (
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Configure Your Pipeline
              </Typography>
              <Grid container spacing={3}>
                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    fullWidth
                    label="Pipeline Name"
                    value={config.name}
                    onChange={(e) => handleConfigChange('name', e.target.value)}
                    required
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <FormControl fullWidth required>
                    <InputLabel>Pipeline Type</InputLabel>
                    <Select
                      value={config.type}
                      label="Pipeline Type"
                      onChange={(e) => handleConfigChange('type', e.target.value)}
                    >
                      <MenuItem value="classification">Classification</MenuItem>
                      <MenuItem value="regression">Regression</MenuItem>
                      <MenuItem value="clustering">Clustering</MenuItem>
                      <MenuItem value="anomaly_detection">Anomaly Detection</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid size={12}>
                  <TextField
                    fullWidth
                    label="Objective"
                    value={config.objective}
                    onChange={(e) => handleConfigChange('objective', e.target.value)}
                    placeholder="Describe what you want to achieve with this pipeline..."
                    required
                    multiline
                    rows={2}
                  />
                </Grid>
                <Grid size={12}>
                  <TextField
                    fullWidth
                    label="Description"
                    value={config.description}
                    onChange={(e) => handleConfigChange('description', e.target.value)}
                    placeholder="Optional description for your pipeline..."
                    multiline
                    rows={3}
                  />
                </Grid>
                {dataUpload && (config.type === 'classification' || config.type === 'regression') && (
                  <Grid size={{ xs: 12, md: 6 }}>
                    <FormControl fullWidth>
                      <InputLabel>Target Column</InputLabel>
                      <Select
                        value={config.targetColumn || ''}
                        label="Target Column"
                        onChange={(e) => handleConfigChange('targetColumn', e.target.value)}
                      >
                        {dataUpload.columns.map((column) => (
                          <MenuItem key={column} value={column}>
                            {column}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                )}
              </Grid>
            </CardContent>
          </Card>
        );

      case 2:
        return (
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Review Your Pipeline
              </Typography>
              <Grid container spacing={3}>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    Pipeline Details
                  </Typography>
                  <Table size="small">
                    <TableBody>
                      <TableRow>
                        <TableCell><strong>Name:</strong></TableCell>
                        <TableCell>{config.name}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell><strong>Type:</strong></TableCell>
                        <TableCell>
                          <Chip label={config.type.replace('_', ' ')} size="small" />
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell><strong>Objective:</strong></TableCell>
                        <TableCell>{config.objective}</TableCell>
                      </TableRow>
                      {config.description && (
                        <TableRow>
                          <TableCell><strong>Description:</strong></TableCell>
                          <TableCell>{config.description}</TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    Dataset Information
                  </Typography>
                  {dataUpload && (
                    <Table size="small">
                      <TableBody>
                        <TableRow>
                          <TableCell><strong>File:</strong></TableCell>
                          <TableCell>{dataUpload.filename}</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell><strong>Rows:</strong></TableCell>
                          <TableCell>{dataUpload.rowCount}</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell><strong>Columns:</strong></TableCell>
                          <TableCell>{dataUpload.columns.length}</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell><strong>Size:</strong></TableCell>
                          <TableCell>{(dataUpload.size / 1024 / 1024).toFixed(2)} MB</TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  )}
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        );

      default:
        return null;
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Pipeline Builder
      </Typography>
      
      {errors.length > 0 && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {errors.map((error, index) => (
            <div key={index}>{error}</div>
          ))}
        </Alert>
      )}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          {activeStep === steps.length ? (
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h6" gutterBottom>
                Pipeline Created Successfully!
              </Typography>
              <Button onClick={handleReset} variant="contained">
                Create Another Pipeline
              </Button>
            </Box>
          ) : (
            <Box>
              {renderStepContent(activeStep)}

              <Box sx={{ display: 'flex', flexDirection: 'row', pt: 3 }}>
                <Button
                  color="inherit"
                  disabled={activeStep === 0}
                  onClick={handleBack}
                  sx={{ mr: 1 }}
                >
                  Back
                </Button>
                <Box sx={{ flex: '1 1 auto' }} />
                {activeStep === steps.length - 1 ? (
                  <Button
                    onClick={handleCreatePipeline}
                    disabled={creating}
                    variant="contained"
                  >
                    {creating ? <CircularProgress size={24} /> : 'Create Pipeline'}
                  </Button>
                ) : (
                  <Button
                    onClick={handleNext}
                    disabled={uploading}
                    variant="contained"
                  >
                    {uploading ? <CircularProgress size={24} /> : 'Next'}
                  </Button>
                )}
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Data Preview Dialog */}
      <Dialog open={previewOpen} onClose={() => setPreviewOpen(false)} maxWidth="lg" fullWidth>
        <DialogTitle>Data Preview</DialogTitle>
        <DialogContent>
          {dataUpload && (
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    {dataUpload.columns.map((column) => (
                      <TableCell key={column}>{column}</TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {dataUpload.preview.slice(0, 5).map((row, index) => (
                    <TableRow key={index}>
                      {dataUpload.columns.map((column) => (
                        <TableCell key={column}>{row[column]}</TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PipelineBuilder;