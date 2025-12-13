"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
const react_1 = __importStar(require("react"));
const material_1 = require("@mui/material");
const icons_material_1 = require("@mui/icons-material");
const react_dropzone_1 = require("react-dropzone");
const api_1 = require("../services/api");
const steps = ['Upload Data', 'Configure Pipeline', 'Review & Create'];
const PipelineBuilder = () => {
    const [activeStep, setActiveStep] = (0, react_1.useState)(0);
    const [uploadedFile, setUploadedFile] = (0, react_1.useState)(null);
    const [dataUpload, setDataUpload] = (0, react_1.useState)(null);
    const [config, setConfig] = (0, react_1.useState)({
        name: '',
        description: '',
        type: 'classification',
        objective: '',
        useRealAws: true, // ✅ Default to true (real AWS infrastructure)
    });
    const [uploading, setUploading] = (0, react_1.useState)(false);
    const [creating, setCreating] = (0, react_1.useState)(false);
    const [previewOpen, setPreviewOpen] = (0, react_1.useState)(false);
    const [errors, setErrors] = (0, react_1.useState)([]);
    const onDrop = (0, react_1.useCallback)((acceptedFiles) => {
        const file = acceptedFiles[0];
        if (file) {
            setUploadedFile(file);
            setErrors([]);
        }
    }, []);
    const { getRootProps, getInputProps, isDragActive } = (0, react_dropzone_1.useDropzone)({
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
            const upload = await api_1.apiService.uploadData(uploadedFile);
            if (upload) {
                setDataUpload(upload);
                setActiveStep(1);
            }
            else {
                setErrors(['Failed to upload file']);
            }
        }
        catch (error) {
            console.error('Upload error:', error);
            setErrors(['Error uploading file. Please try again.']);
        }
        finally {
            setUploading(false);
        }
    };
    const handleConfigChange = (field, value) => {
        setConfig(prev => ({ ...prev, [field]: value }));
        setErrors([]);
    };
    const validateConfig = () => {
        const newErrors = [];
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
            const pipeline = {
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
            const created = await api_1.apiService.createPipeline({
                ...pipeline,
                useRealAws: config.useRealAws !== undefined ? config.useRealAws : true, // ✅ Pass as config
            });
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
            }
            else {
                setErrors(['Failed to create pipeline']);
            }
        }
        catch (error) {
            console.error('Create pipeline error:', error);
            setErrors(['Error creating pipeline. Please try again.']);
        }
        finally {
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
    const renderStepContent = (step) => {
        switch (step) {
            case 0:
                return (<material_1.Card>
            <material_1.CardContent>
              <material_1.Typography variant="h6" gutterBottom>
                Upload Your Dataset
              </material_1.Typography>
              <material_1.Paper {...getRootProps()} sx={{
                        border: '2px dashed #ccc',
                        borderRadius: 2,
                        p: 4,
                        textAlign: 'center',
                        cursor: 'pointer',
                        bgcolor: isDragActive ? 'action.hover' : 'transparent',
                        '&:hover': { bgcolor: 'action.hover' },
                    }}>
                <input {...getInputProps()}/>
                <icons_material_1.CloudUpload sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }}/>
                {uploadedFile ? (<material_1.Box>
                    <material_1.Typography variant="h6" color="primary">
                      {uploadedFile.name}
                    </material_1.Typography>
                    <material_1.Typography variant="body2" color="text.secondary">
                      {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                    </material_1.Typography>
                  </material_1.Box>) : (<material_1.Box>
                    <material_1.Typography variant="h6" gutterBottom>
                      {isDragActive ? 'Drop the file here' : 'Drag & drop a CSV file here'}
                    </material_1.Typography>
                    <material_1.Typography variant="body2" color="text.secondary">
                      Or click to select a file
                    </material_1.Typography>
                  </material_1.Box>)}
              </material_1.Paper>
              {dataUpload && (<material_1.Box sx={{ mt: 3 }}>
                  <material_1.Alert severity="success">
                    File uploaded successfully! {dataUpload.rowCount} rows, {dataUpload.columns.length} columns
                  </material_1.Alert>
                  <material_1.Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                    <material_1.Button startIcon={<icons_material_1.Preview />} onClick={() => setPreviewOpen(true)}>
                      Preview Data
                    </material_1.Button>
                    <material_1.Button color="error" startIcon={<icons_material_1.Delete />} onClick={() => {
                            setDataUpload(null);
                            setUploadedFile(null);
                        }}>
                      Remove
                    </material_1.Button>
                  </material_1.Box>
                </material_1.Box>)}
            </material_1.CardContent>
          </material_1.Card>);
            case 1:
                return (<material_1.Card>
            <material_1.CardContent>
              <material_1.Typography variant="h6" gutterBottom>
                Configure Your Pipeline
              </material_1.Typography>
              <material_1.Grid container spacing={3}>
                <material_1.Grid size={{ xs: 12, md: 6 }}>
                  <material_1.TextField fullWidth label="Pipeline Name" value={config.name} onChange={(e) => handleConfigChange('name', e.target.value)} required/>
                </material_1.Grid>
                <material_1.Grid size={{ xs: 12, md: 6 }}>
                  <material_1.FormControl fullWidth required>
                    <material_1.InputLabel>Pipeline Type</material_1.InputLabel>
                    <material_1.Select value={config.type} label="Pipeline Type" onChange={(e) => handleConfigChange('type', e.target.value)}>
                      <material_1.MenuItem value="classification">Classification</material_1.MenuItem>
                      <material_1.MenuItem value="regression">Regression</material_1.MenuItem>
                      <material_1.MenuItem value="clustering">Clustering</material_1.MenuItem>
                      <material_1.MenuItem value="anomaly_detection">Anomaly Detection</material_1.MenuItem>
                    </material_1.Select>
                  </material_1.FormControl>
                </material_1.Grid>
                <material_1.Grid size={12}>
                  <material_1.TextField fullWidth label="Objective" value={config.objective} onChange={(e) => handleConfigChange('objective', e.target.value)} placeholder="Describe what you want to achieve with this pipeline..." required multiline rows={2}/>
                </material_1.Grid>
                <material_1.Grid size={12}>
                  <material_1.TextField fullWidth label="Description" value={config.description} onChange={(e) => handleConfigChange('description', e.target.value)} placeholder="Optional description for your pipeline..." multiline rows={3}/>
                </material_1.Grid>
                <material_1.Grid size={12}>
                  <material_1.FormControlLabel control={<material_1.Checkbox checked={config.useRealAws || false} onChange={(e) => handleConfigChange('useRealAws', e.target.checked)} color="primary"/>} label={<material_1.Box>
                        <material_1.Typography component="span">
                          Use Real AWS Infrastructure
                        </material_1.Typography>
                        <material_1.Typography variant="caption" display="block" color="text.secondary">
                          Execute pipeline on actual AWS services (Step Functions + SageMaker). 
                          Uncheck for simulation mode.
                        </material_1.Typography>
                      </material_1.Box>}/>
                </material_1.Grid>
                {dataUpload && (config.type === 'classification' || config.type === 'regression') && (<material_1.Grid size={{ xs: 12, md: 6 }}>
                    <material_1.FormControl fullWidth>
                      <material_1.InputLabel>Target Column</material_1.InputLabel>
                      <material_1.Select value={config.targetColumn || ''} label="Target Column" onChange={(e) => handleConfigChange('targetColumn', e.target.value)}>
                        {dataUpload.columns.map((column) => (<material_1.MenuItem key={column} value={column}>
                            {column}
                          </material_1.MenuItem>))}
                      </material_1.Select>
                    </material_1.FormControl>
                  </material_1.Grid>)}
              </material_1.Grid>
            </material_1.CardContent>
          </material_1.Card>);
            case 2:
                return (<material_1.Card>
            <material_1.CardContent>
              <material_1.Typography variant="h6" gutterBottom>
                Review Your Pipeline
              </material_1.Typography>
              <material_1.Grid container spacing={3}>
                <material_1.Grid size={{ xs: 12, md: 6 }}>
                  <material_1.Typography variant="subtitle1" gutterBottom>
                    Pipeline Details
                  </material_1.Typography>
                  <material_1.Table size="small">
                    <material_1.TableBody>
                      <material_1.TableRow>
                        <material_1.TableCell><strong>Name:</strong></material_1.TableCell>
                        <material_1.TableCell>{config.name}</material_1.TableCell>
                      </material_1.TableRow>
                      <material_1.TableRow>
                        <material_1.TableCell><strong>Type:</strong></material_1.TableCell>
                        <material_1.TableCell>
                          <material_1.Chip label={config.type.replace('_', ' ')} size="small"/>
                        </material_1.TableCell>
                      </material_1.TableRow>
                      <material_1.TableRow>
                        <material_1.TableCell><strong>Objective:</strong></material_1.TableCell>
                        <material_1.TableCell>{config.objective}</material_1.TableCell>
                      </material_1.TableRow>
                      {config.description && (<material_1.TableRow>
                          <material_1.TableCell><strong>Description:</strong></material_1.TableCell>
                          <material_1.TableCell>{config.description}</material_1.TableCell>
                        </material_1.TableRow>)}
                    </material_1.TableBody>
                  </material_1.Table>
                </material_1.Grid>
                <material_1.Grid size={{ xs: 12, md: 6 }}>
                  <material_1.Typography variant="subtitle1" gutterBottom>
                    Dataset Information
                  </material_1.Typography>
                  {dataUpload && (<material_1.Table size="small">
                      <material_1.TableBody>
                        <material_1.TableRow>
                          <material_1.TableCell><strong>File:</strong></material_1.TableCell>
                          <material_1.TableCell>{dataUpload.filename}</material_1.TableCell>
                        </material_1.TableRow>
                        <material_1.TableRow>
                          <material_1.TableCell><strong>Rows:</strong></material_1.TableCell>
                          <material_1.TableCell>{dataUpload.rowCount}</material_1.TableCell>
                        </material_1.TableRow>
                        <material_1.TableRow>
                          <material_1.TableCell><strong>Columns:</strong></material_1.TableCell>
                          <material_1.TableCell>{dataUpload.columns.length}</material_1.TableCell>
                        </material_1.TableRow>
                        <material_1.TableRow>
                          <material_1.TableCell><strong>Size:</strong></material_1.TableCell>
                          <material_1.TableCell>{(dataUpload.size / 1024 / 1024).toFixed(2)} MB</material_1.TableCell>
                        </material_1.TableRow>
                      </material_1.TableBody>
                    </material_1.Table>)}
                </material_1.Grid>
              </material_1.Grid>
            </material_1.CardContent>
          </material_1.Card>);
            default:
                return null;
        }
    };
    return (<material_1.Box sx={{ p: 3 }}>
      <material_1.Typography variant="h4" gutterBottom>
        Pipeline Builder
      </material_1.Typography>
      
      {errors.length > 0 && (<material_1.Alert severity="error" sx={{ mb: 3 }}>
          {errors.map((error, index) => (<div key={index}>{error}</div>))}
        </material_1.Alert>)}

      <material_1.Card sx={{ mb: 3 }}>
        <material_1.CardContent>
          <material_1.Stepper activeStep={activeStep} sx={{ mb: 3 }}>
            {steps.map((label) => (<material_1.Step key={label}>
                <material_1.StepLabel>{label}</material_1.StepLabel>
              </material_1.Step>))}
          </material_1.Stepper>

          {activeStep === steps.length ? (<material_1.Box sx={{ textAlign: 'center' }}>
              <material_1.Typography variant="h6" gutterBottom>
                Pipeline Created Successfully!
              </material_1.Typography>
              <material_1.Button onClick={handleReset} variant="contained">
                Create Another Pipeline
              </material_1.Button>
            </material_1.Box>) : (<material_1.Box>
              {renderStepContent(activeStep)}

              <material_1.Box sx={{ display: 'flex', flexDirection: 'row', pt: 3 }}>
                <material_1.Button color="inherit" disabled={activeStep === 0} onClick={handleBack} sx={{ mr: 1 }}>
                  Back
                </material_1.Button>
                <material_1.Box sx={{ flex: '1 1 auto' }}/>
                {activeStep === steps.length - 1 ? (<material_1.Button onClick={handleCreatePipeline} disabled={creating} variant="contained">
                    {creating ? <material_1.CircularProgress size={24}/> : 'Create Pipeline'}
                  </material_1.Button>) : (<material_1.Button onClick={handleNext} disabled={uploading} variant="contained">
                    {uploading ? <material_1.CircularProgress size={24}/> : 'Next'}
                  </material_1.Button>)}
              </material_1.Box>
            </material_1.Box>)}
        </material_1.CardContent>
      </material_1.Card>

      {/* Data Preview Dialog */}
      <material_1.Dialog open={previewOpen} onClose={() => setPreviewOpen(false)} maxWidth="lg" fullWidth>
        <material_1.DialogTitle>Data Preview</material_1.DialogTitle>
        <material_1.DialogContent>
          {dataUpload && (<material_1.TableContainer component={material_1.Paper}>
              <material_1.Table size="small">
                <material_1.TableHead>
                  <material_1.TableRow>
                    {dataUpload.columns.map((column) => (<material_1.TableCell key={column}>{column}</material_1.TableCell>))}
                  </material_1.TableRow>
                </material_1.TableHead>
                <material_1.TableBody>
                  {dataUpload.preview.slice(0, 5).map((row, index) => (<material_1.TableRow key={index}>
                      {dataUpload.columns.map((column) => (<material_1.TableCell key={column}>{row[column]}</material_1.TableCell>))}
                    </material_1.TableRow>))}
                </material_1.TableBody>
              </material_1.Table>
            </material_1.TableContainer>)}
        </material_1.DialogContent>
        <material_1.DialogActions>
          <material_1.Button onClick={() => setPreviewOpen(false)}>Close</material_1.Button>
        </material_1.DialogActions>
      </material_1.Dialog>
    </material_1.Box>);
};
exports.default = PipelineBuilder;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiUGlwZWxpbmVCdWlsZGVyLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiUGlwZWxpbmVCdWlsZGVyLnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiOzs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7O0FBQUEsK0NBQXFEO0FBQ3JELDRDQWdDdUI7QUFDdkIsd0RBSTZCO0FBQzdCLG1EQUE2QztBQUU3Qyx5Q0FBNkM7QUFFN0MsTUFBTSxLQUFLLEdBQUcsQ0FBQyxhQUFhLEVBQUUsb0JBQW9CLEVBQUUsaUJBQWlCLENBQUMsQ0FBQztBQWF2RSxNQUFNLGVBQWUsR0FBYSxHQUFHLEVBQUU7SUFDckMsTUFBTSxDQUFDLFVBQVUsRUFBRSxhQUFhLENBQUMsR0FBRyxJQUFBLGdCQUFRLEVBQUMsQ0FBQyxDQUFDLENBQUM7SUFDaEQsTUFBTSxDQUFDLFlBQVksRUFBRSxlQUFlLENBQUMsR0FBRyxJQUFBLGdCQUFRLEVBQWMsSUFBSSxDQUFDLENBQUM7SUFDcEUsTUFBTSxDQUFDLFVBQVUsRUFBRSxhQUFhLENBQUMsR0FBRyxJQUFBLGdCQUFRLEVBQW9CLElBQUksQ0FBQyxDQUFDO0lBQ3RFLE1BQU0sQ0FBQyxNQUFNLEVBQUUsU0FBUyxDQUFDLEdBQUcsSUFBQSxnQkFBUSxFQUFpQjtRQUNuRCxJQUFJLEVBQUUsRUFBRTtRQUNSLFdBQVcsRUFBRSxFQUFFO1FBQ2YsSUFBSSxFQUFFLGdCQUFnQjtRQUN0QixTQUFTLEVBQUUsRUFBRTtRQUNiLFVBQVUsRUFBRSxJQUFJLEVBQUUsOENBQThDO0tBQ2pFLENBQUMsQ0FBQztJQUNILE1BQU0sQ0FBQyxTQUFTLEVBQUUsWUFBWSxDQUFDLEdBQUcsSUFBQSxnQkFBUSxFQUFDLEtBQUssQ0FBQyxDQUFDO0lBQ2xELE1BQU0sQ0FBQyxRQUFRLEVBQUUsV0FBVyxDQUFDLEdBQUcsSUFBQSxnQkFBUSxFQUFDLEtBQUssQ0FBQyxDQUFDO0lBQ2hELE1BQU0sQ0FBQyxXQUFXLEVBQUUsY0FBYyxDQUFDLEdBQUcsSUFBQSxnQkFB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LHdCQUFhLENBQ2pCO01BQUEsRUFBRSxpQkFBTSxDQUNWO0lBQUEsRUFBRSxjQUFHLENBQUMsQ0FDUCxDQUFDO0FBQ0osQ0FBQyxDQUFDO0FBRUYsa0JBQWUsZUFBZSxDQUFDIiwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0IFJlYWN0LCB7IHVzZVN0YXRlLCB1c2VDYWxsYmFjayB9IGZyb20gJ3JlYWN0JztcbmltcG9ydCB7XG4gIEJveCxcbiAgU3RlcHBlcixcbiAgU3RlcCxcbiAgU3RlcExhYmVsLFxuICBCdXR0b24sXG4gIFR5cG9ncmFwaHksXG4gIENhcmQsXG4gIENhcmRDb250ZW50LFxuICBUZXh0RmllbGQsXG4gIEZvcm1Db250cm9sLFxuICBJbnB1dExhYmVsLFxuICBTZWxlY3QsXG4gIE1lbnVJdGVtLFxuICBHcmlkLFxuICBBbGVydCxcbiAgUGFwZXIsXG4gIFRhYmxlLFxuICBUYWJsZUJvZHksXG4gIFRhYmxlQ2VsbCxcbiAgVGFibGVDb250YWluZXIsXG4gIFRhYmxlSGVhZCxcbiAgVGFibGVSb3csXG4gIENoaXAsXG4gIEljb25CdXR0b24sXG4gIERpYWxvZyxcbiAgRGlhbG9nVGl0bGUsXG4gIERpYWxvZ0NvbnRlbnQsXG4gIERpYWxvZ0FjdGlvbnMsXG4gIENpcmN1bGFyUHJvZ3Jlc3MsXG4gIEZvcm1Db250cm9sTGFiZWwsXG4gIENoZWNrYm94LFxufSBmcm9tICdAbXVpL21hdGVyaWFsJztcbmltcG9ydCB7XG4gIENsb3VkVXBsb2FkIGFzIFVwbG9hZEljb24sXG4gIERlbGV0ZSBhcyBEZWxldGVJY29uLFxuICBQcmV2aWV3IGFzIFByZXZpZXdJY29uLFxufSBmcm9tICdAbXVpL2ljb25zLW1hdGVyaWFsJztcbmltcG9ydCB7IHVzZURyb3B6b25lIH0gZnJvbSAncmVhY3QtZHJvcHpvbmUnO1xuaW1wb3J0IHsgUGlwZWxpbmUsIERhdGFVcGxvYWQgfSBmcm9tICcuLi90eXBlcyc7XG5pbXBvcnQgeyBhcGlTZXJ2aWNlIH0gZnJvbSAnLi4vc2VydmljZXMvYXBpJztcblxuY29uc3Qgc3RlcHMgPSBbJ1VwbG9hZCBEYXRhJywgJ0NvbmZpZ3VyZSBQaXBlbGluZScsICdSZXZpZXcgJiBDcmVhdGUnXTtcblxuaW50ZXJmYWNlIFBpcGVsaW5lQ29uZmlnIHtcbiAgbmFtZTogc3RyaW5nO1xuICBkZXNjcmlwdGlvbjogc3RyaW5nO1xuICB0eXBlOiAnY2xhc3NpZmljYXRpb24nIHwgJ3JlZ3Jlc3Npb24nIHwgJ2NsdXN0ZXJpbmcnIHwgJ2Fub21hbHlfZGV0ZWN0aW9uJztcbiAgb2JqZWN0aXZlOiBzdHJpbmc7XG4gIHVzZVJlYWxBd3M/OiBib29sZWFuOyAvLyDinIUgUmVhbCBBV1MgdG9nZ2xlIChkZWZhdWx0IHRydWUpXG4gIHRhcmdldENvbHVtbj86IHN0cmluZztcbiAgZmVhdHVyZXM/OiBzdHJpbmdbXTtcbiAgYWxnb3JpdGhtPzogc3RyaW5nO1xufVxuXG5jb25zdCBQaXBlbGluZUJ1aWxkZXI6IFJlYWN0LkZDID0gKCkgPT4ge1xuICBjb25zdCBbYWN0aXZlU3RlcCwgc2V0QWN0aXZlU3RlcF0gPSB1c2VTdGF0ZSgwKTtcbiAgY29uc3QgW3VwbG9hZGVkRmlsZSwgc2V0VXBsb2FkZWRGaWxlXSA9IHVzZVN0YXRlPEZpbGUgfCBudWxsPihudWxsKTtcbiAgY29uc3QgW2RhdGFVcGxvYWQsIHNldERhdGFVcGxvYWRdID0gdXNlU3RhdGU8RGF0YVVwbG9hZCB8IG51bGw+KG51bGwpO1xuICBjb25zdCBbY29uZmlnLCBzZXRDb25maWddID0gdXNlU3RhdGU8UGlwZWxpbmVDb25maWc+KHtcbiAgICBuYW1lOiAnJyxcbiAgICBkZXNjcmlwdGlvbjogJycsXG4gICAgdHlwZTogJ2NsYXNzaWZpY2F0aW9uJyxcbiAgICBvYmplY3RpdmU6ICcnLFxuICAgIHVzZVJlYWxBd3M6IHRydWUsIC8vIOKchSBEZWZhdWx0IHRvIHRydWUgKHJlYWwgQVdTIGluZnJhc3RydWN0dXJlKVxuICB9KTtcbiAgY29uc3QgW3VwbG9hZGluZywgc2V0VXBsb2FkaW5nXSA9IHVzZVN0YXRlKGZhbHNlKTtcbiAgY29uc3QgW2NyZWF0aW5nLCBzZXRDcmVhdGluZ10gPSB1c2VTdGF0ZShmYWxzZSk7XG4gIGNvbnN0IFtwcmV2aWV3T3Blbiwgc2V0UHJldmlld09wZW5dID0gdXNlU3RhdGUoZmFsc2UpO1xuICBjb25zdCBbZXJyb3JzLCBzZXRFcnJvcnNdID0gdXNlU3RhdGU8c3RyaW5nW10+KFtdKTtcblxuICBjb25zdCBvbkRyb3AgPSB1c2VDYWxsYmFjaygoYWNjZXB0ZWRGaWxlczogRmlsZVtdKSA9PiB7XG4gICAgY29uc3QgZmlsZSA9IGFjY2VwdGVkRmlsZXNbMF07XG4gICAgaWYgKGZpbGUpIHtcbiAgICAgIHNldFVwbG9hZGVkRmlsZShmaWxlKTtcbiAgICAgIHNldEVycm9ycyhbXSk7XG4gICAgfVxuICB9LCBbXSk7XG5cbiAgY29uc3QgeyBnZXRSb290UHJvcHMsIGdldElucHV0UHJvcHMsIGlzRHJhZ0FjdGl2ZSB9ID0gdXNlRHJvcHpvbmUoe1xuICAgIG9uRHJvcCxcbiAgICBhY2NlcHQ6IHtcbiAgICAgICd0ZXh0L2Nzdic6IFsnLmNzdiddLFxuICAgICAgJ2FwcGxpY2F0aW9uL2pzb24nOiBbJy5qc29uJ10sXG4gICAgfSxcbiAgICBtYXhGaWxlczogMSxcbiAgfSk7XG5cbiAgY29uc3QgaGFuZGxlVXBsb2FkID0gYXN5bmMgKCkgPT4ge1xuICAgIGlmICghdXBsb2FkZWRGaWxlKSB7XG4gICAgICBzZXRFcnJvcnMoWydQbGVhc2Ugc2VsZWN0IGEgZmlsZSB0byB1cGxvYWQnXSk7XG4gICAgICByZXR1cm47XG4gICAgfVxuXG4gICAgc2V0VXBsb2FkaW5nKHRydWUpO1xuICAgIHNldEVycm9ycyhbXSk7XG5cbiAgICB0cnkge1xuICAgICAgY29uc3QgdXBsb2FkID0gYXdhaXQgYXBpU2VydmljZS51cGxvYWREYXRhKHVwbG9hZGVkRmlsZSk7XG4gICAgICBpZiAodXBsb2FkKSB7XG4gICAgICAgIHNldERhdGFVcGxvYWQodXBsb2FkKTtcbiAgICAgICAgc2V0QWN0aXZlU3RlcCgxKTtcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIHNldEVycm9ycyhbJ0ZhaWxlZCB0byB1cGxvYWQgZmlsZSddKTtcbiAgICAgIH1cbiAgICB9IGNhdGNoIChlcnJvcikge1xuICAgICAgY29uc29sZS5lcnJvcignVXBsb2FkIGVycm9yOicsIGVycm9yKTtcbiAgICAgIHNldEVycm9ycyhbJ0Vycm9yIHVwbG9hZGluZyBmaWxlLiBQbGVhc2UgdHJ5IGFnYWluLiddKTtcbiAgICB9IGZpbmFsbHkge1xuICAgICAgc2V0VXBsb2FkaW5nKGZhbHNlKTtcbiAgICB9XG4gIH07XG5cbiAgY29uc3QgaGFuZGxlQ29uZmlnQ2hhbmdlID0gKGZpZWxkOiBrZXlvZiBQaXBlbGluZUNvbmZpZywgdmFsdWU6IGFueSkgPT4ge1xuICAgIHNldENvbmZpZyhwcmV2ID0+ICh7IC4uLnByZXYsIFtmaWVsZF06IHZhbHVlIH0pKTtcbiAgICBzZXRFcnJvcnMoW10pO1xuICB9O1xuXG4gIGNvbnN0IHZhbGlkYXRlQ29uZmlnID0gKCk6IGJvb2xlYW4gPT4ge1xuICAgIGNvbnN0IG5ld0Vycm9yczogc3RyaW5nW10gPSBbXTtcblxuICAgIGlmICghY29uZmlnLm5hbWUudHJpbSgpKSB7XG4gICAgICBuZXdFcnJvcnMucHVzaCgnUGlwZWxpbmUgbmFtZSBpcyByZXF1aXJlZCcpO1xuICAgIH1cbiAgICBpZiAoIWNvbmZpZy5vYmplY3RpdmUudHJpbSgpKSB7XG4gICAgICBuZXdFcnJvcnMucHVzaCgnT2JqZWN0aXZlIGRlc2NyaXB0aW9uIGlzIHJlcXVpcmVkJyk7XG4gICAgfVxuICAgIGlmICghZGF0YVVwbG9hZCkge1xuICAgICAgbmV3RXJyb3JzLnB1c2goJ0RhdGEgdXBsb2FkIGlzIHJlcXVpcmVkJyk7XG4gICAgfVxuXG4gICAgc2V0RXJyb3JzKG5ld0Vycm9ycyk7XG4gICAgcmV0dXJuIG5ld0Vycm9ycy5sZW5ndGggPT09IDA7XG4gIH07XG5cbiAgY29uc3QgaGFuZGxlQ3JlYXRlUGlwZWxpbmUgPSBhc3luYyAoKSA9PiB7XG4gICAgaWYgKCF2YWxpZGF0ZUNvbmZpZygpKSB7XG4gICAgICByZXR1cm47XG4gICAgfVxuXG4gICAgc2V0Q3JlYXRpbmcodHJ1ZSk7XG5cbiAgICB0cnkge1xuICAgICAgY29uc3QgcGlwZWxpbmU6IFBhcnRpYWw8UGlwZWxpbmU+ID0ge1xuICAgICAgICBuYW1lOiBjb25maWcubmFtZSxcbiAgICAgICAgZGVzY3JpcHRpb246IGNvbmZpZy5kZXNjcmlwdGlvbixcbiAgICAgICAgdHlwZTogY29uZmlnLnR5cGUsXG4gICAgICAgIG9iamVjdGl2ZTogY29uZmlnLm9iamVjdGl2ZSxcbiAgICAgICAgZGF0YXNldDogZGF0YVVwbG9hZD8uZmlsZW5hbWUsXG4gICAgICAgIHN0YXR1czogJ3BlbmRpbmcnLFxuICAgICAgICBwcm9ncmVzczogMCxcbiAgICAgICAgY3JlYXRlZEF0OiBuZXcgRGF0ZSgpLnRvSVNPU3RyaW5nKCksXG4gICAgICAgIHVwZGF0ZWRBdDogbmV3IERhdGUoKS50b0lTT1N0cmluZygpLFxuICAgICAgfTtcblxuICAgICAgY29uc3QgY3JlYXRlZCA9IGF3YWl0IGFwaVNlcnZpY2UuY3JlYXRlUGlwZWxpbmUoe1xuICAgICAgICAuLi5waXBlbGluZSxcbiAgICAgICAgdXNlUmVhbEF3czogY29uZmlnLnVzZVJlYWxBd3MgIT09IHVuZGVmaW5lZCA/IGNvbmZpZy51c2VSZWFsQXdzIDogdHJ1ZSwgLy8g4pyFIFBhc3MgYXMgY29uZmlnXG4gICAgICB9KTtcbiAgICAgIGlmIChjcmVhdGVkKSB7XG4gICAgICAgIC8vIFJlc2V0IGZvcm1cbiAgICAgICAgc2V0QWN0aXZlU3RlcCgwKTtcbiAgICAgICAgc2V0VXBsb2FkZWRGaWxlKG51bGwpO1xuICAgICAgICBzZXREYXRhVXBsb2FkKG51bGwpO1xuICAgICAgICBzZXRDb25maWcoe1xuICAgICAgICAgIG5hbWU6ICcnLFxuICAgICAgICAgIGRlc2NyaXB0aW9uOiAnJyxcbiAgICAgICAgICB0eXBlOiAnY2xhc3NpZmljYXRpb24nLFxuICAgICAgICAgIG9iamVjdGl2ZTogJycsXG4gICAgICAgIH0pO1xuICAgICAgICBhbGVydCgnUGlwZWxpbmUgY3JlYXRlZCBzdWNjZXNzZnVsbHkhJyk7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBzZXRFcnJvcnMoWydGYWlsZWQgdG8gY3JlYXRlIHBpcGVsaW5lJ10pO1xuICAgICAgfVxuICAgIH0gY2F0Y2ggKGVycm9yKSB7XG4gICAgICBjb25zb2xlLmVycm9yKCdDcmVhdGUgcGlwZWxpbmUgZXJyb3I6JywgZXJyb3IpO1xuICAgICAgc2V0RXJyb3JzKFsnRXJyb3IgY3JlYXRpbmcgcGlwZWxpbmUuIFBsZWFzZSB0cnkgYWdhaW4uJ10pO1xuICAgIH0gZmluYWxseSB7XG4gICAgICBzZXRDcmVhdGluZyhmYWxzZSk7XG4gICAgfVxuICB9O1xuXG4gIGNvbnN0IGhhbmRsZU5leHQgPSAoKSA9PiB7XG4gICAgaWYgKGFjdGl2ZVN0ZXAgPT09IDAgJiYgIWRhdGFVcGxvYWQpIHtcbiAgICAgIGhhbmRsZVVwbG9hZCgpO1xuICAgICAgcmV0dXJuO1xuICAgIH1cbiAgICBcbiAgICBpZiAoYWN0aXZlU3RlcCA9PT0gMSAmJiAhdmFsaWRhdGVDb25maWcoKSkge1xuICAgICAgcmV0dXJuO1xuICAgIH1cblxuICAgIHNldEFjdGl2ZVN0ZXAocHJldiA9PiBwcmV2ICsgMSk7XG4gIH07XG5cbiAgY29uc3QgaGFuZGxlQmFjayA9ICgpID0+IHtcbiAgICBzZXRBY3RpdmVTdGVwKHByZXYgPT4gcHJldiAtIDEpO1xuICAgIHNldEVycm9ycyhbXSk7XG4gIH07XG5cbiAgY29uc3QgaGFuZGxlUmVzZXQgPSAoKSA9PiB7XG4gICAgc2V0QWN0aXZlU3RlcCgwKTtcbiAgICBzZXRVcGxvYWRlZEZpbGUobnVsbCk7XG4gICAgc2V0RGF0YVVwbG9hZChudWxsKTtcbiAgICBzZXRDb25maWcoe1xuICAgICAgbmFtZTogJycsXG4gICAgICBkZXNjcmlwdGlvbjogJycsXG4gICAgICB0eXBlOiAnY2xhc3NpZmljYXRpb24nLFxuICAgICAgb2JqZWN0aXZlOiAnJyxcbiAgICB9KTtcbiAgICBzZXRFcnJvcnMoW10pO1xuICB9O1xuXG4gIGNvbnN0IHJlbmRlclN0ZXBDb250ZW50ID0gKHN0ZXA6IG51bWJlcikgPT4ge1xuICAgIHN3aXRjaCAoc3RlcCkge1xuICAgICAgY2FzZSAwOlxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgIDxDYXJkPlxuICAgICAgICAgICAgPENhcmRDb250ZW50PlxuICAgICAgICAgICAgICA8VHlwb2dyYXBoeSB2YXJpYW50PVwiaDZcIiBndXR0ZXJCb3R0b20+XG4gICAgICAgICAgICAgICAgVXBsb2FkIFlvdXIgRGF0YXNldFxuICAgICAgICAgICAgICA8L1R5cG9ncmFwaHk+XG4gICAgICAgICAgICAgIDxQYXBlclxuICAgICAgICAgICAgICAgIHsuLi5nZXRSb290UHJvcHMoKX1cbiAgICAgICAgICAgICAgICBzeD17e1xuICAgICAgICAgICAgICAgICAgYm9yZGVyOiAnMnB4IGRhc2hlZCAjY2NjJyxcbiAgICAgICAgICAgICAgICAgIGJvcmRlclJhZGl1czogMixcbiAgICAgICAgICAgICAgICAgIHA6IDQsXG4gICAgICAgICAgICAgICAgICB0ZXh0QWxpZ246ICdjZW50ZXInLFxuICAgICAgICAgICAgICAgICAgY3Vyc29yOiAncG9pbnRlcicsXG4gICAgICAgICAgICAgICAgICBiZ2NvbG9yOiBpc0RyYWdBY3RpdmUgPyAnYWN0aW9uLmhvdmVyJyA6ICd0cmFuc3BhcmVudCcsXG4gICAgICAgICAgICAgICAgICAnJjpob3Zlcic6IHsgYmdjb2xvcjogJ2FjdGlvbi5ob3ZlcicgfSxcbiAgICAgICAgICAgICAgICB9fVxuICAgICAgICAgICAgICA+XG4gICAgICAgICAgICAgICAgPGlucHV0IHsuLi5nZXRJbnB1dFByb3BzKCl9IC8+XG4gICAgICAgICAgICAgICAgPFVwbG9hZEljb24gc3g9e3sgZm9udFNpemU6IDQ4LCBjb2xvcjogJ3RleHQuc2Vjb25kYXJ5JywgbWI6IDIgfX0gLz5cbiAgICAgICAgICAgICAgICB7dXBsb2FkZWRGaWxlID8gKFxuICAgICAgICAgICAgICAgICAgPEJveD5cbiAgICAgICAgICAgICAgICAgICAgPFR5cG9ncmFwaHkgdmFyaWFudD1cImg2XCIgY29sb3I9XCJwcmltYXJ5XCI+XG4gICAgICAgICAgICAgICAgICAgICAge3VwbG9hZGVkRmlsZS5uYW1lfVxuICAgICAgICAgICAgICAgICAgICA8L1R5cG9ncmFwaHk+XG4gICAgICAgICAgICAgICAgICAgIDxUeXBvZ3JhcGh5IHZhcmlhbnQ9XCJib2R5MlwiIGNvbG9yPVwidGV4dC5zZWNvbmRhcnlcIj5cbiAgICAgICAgICAgICAgICAgICAgICB7KHVwbG9hZGVkRmlsZS5zaXplIC8gMTAyNCAvIDEwMjQpLnRvRml4ZWQoMil9IE1CXG4gICAgICAgICAgICAgICAgICAgIDwvVHlwb2dyYXBoeT5cbiAgICAgICAgICAgICAgICAgIDwvQm94PlxuICAgICAgICAgICAgICAgICkgOiAoXG4gICAgICAgICAgICAgICAgICA8Qm94PlxuICAgICAgICAgICAgICAgICAgICA8VHlwb2dyYXBoeSB2YXJpYW50PVwiaDZcIiBndXR0ZXJCb3R0b20+XG4gICAgICAgICAgICAgICAgICAgICAge2lzRHJhZ0FjdGl2ZSA/ICdEcm9wIHRoZSBmaWxlIGhlcmUnIDogJ0RyYWcgJiBkcm9wIGEgQ1NWIGZpbGUgaGVyZSd9XG4gICAgICAgICAgICAgICAgICAgIDwvVHlwb2dyYXBoeT5cbiAgICAgICAgICAgICAgICAgICAgPFR5cG9ncmFwaHkgdmFyaWFudD1cImJvZHkyXCIgY29sb3I9XCJ0ZXh0LnNlY29uZGFyeVwiPlxuICAgICAgICAgICAgICAgICAgICAgIE9yIGNsaWNrIHRvIHNlbGVjdCBhIGZpbGVcbiAgICAgICAgICAgICAgICAgICAgPC9UeXBvZ3JhcGh5PlxuICAgICAgICAgICAgICAgICAgPC9Cb3g+XG4gICAgICAgICAgICAgICAgKX1cbiAgICAgICAgICAgICAgPC9QYXBlcj5cbiAgICAgICAgICAgICAge2RhdGFVcGxvYWQgJiYgKFxuICAgICAgICAgICAgICAgIDxCb3ggc3g9e3sgbXQ6IDMgfX0+XG4gICAgICAgICAgICAgICAgICA8QWxlcnQgc2V2ZXJpdHk9XCJzdWNjZXNzXCI+XG4gICAgICAgICAgICAgICAgICAgIEZpbGUgdXBsb2FkZWQgc3VjY2Vzc2Z1bGx5ISB7ZGF0YVVwbG9hZC5yb3dDb3VudH0gcm93cywge2RhdGFVcGxvYWQuY29sdW1ucy5sZW5ndGh9IGNvbHVtbnNcbiAgICAgICAgICAgICAgICAgIDwvQWxlcnQ+XG4gICAgICAgICAgICAgICAgICA8Qm94IHN4PXt7IG10OiAyLCBkaXNwbGF5OiAnZmxleCcsIGdhcDogMSB9fT5cbiAgICAgICAgICAgICAgICAgICAgPEJ1dHRvblxuICAgICAgICAgICAgICAgICAgICAgIHN0YXJ0SWNvbj17PFByZXZpZXdJY29uIC8+fVxuICAgICAgICAgICAgICAgICAgICAgIG9uQ2xpY2s9eygpID0+IHNldFByZXZpZXdPcGVuKHRydWUpfVxuICAgICAgICAgICAgICAgICAgICA+XG4gICAgICAgICAgICAgICAgICAgICAgUHJldmlldyBEYXRhXG4gICAgICAgICAgICAgICAgICAgIDwvQnV0dG9uPlxuICAgICAgICAgICAgICAgICAgICA8QnV0dG9uXG4gICAgICAgICAgICAgICAgICAgICAgY29sb3I9XCJlcnJvclwiXG4gICAgICAgICAgICAgICAgICAgICAgc3RhcnRJY29uPXs8RGVsZXRlSWNvbiAvPn1cbiAgICAgICAgICAgICAgICAgICAgICBvbkNsaWNrPXsoKSA9PiB7XG4gICAgICAgICAgICAgICAgICAgICAgICBzZXREYXRhVXBsb2FkKG51bGwpO1xuICAgICAgICAgICAgICAgICAgICAgICAgc2V0VXBsb2FkZWRGaWxlKG51bGwpO1xuICAgICAgICAgICAgICAgICAgICAgIH19XG4gICAgICAgICAgICAgICAgICAgID5cbiAgICAgICAgICAgICAgICAgICAgICBSZW1vdmVcbiAgICAgICAgICAgICAgICAgICAgPC9CdXR0b24+XG4gICAgICAgICAgICAgICAgICA8L0JveD5cbiAgICAgICAgICAgICAgICA8L0JveD5cbiAgICAgICAgICAgICAgKX1cbiAgICAgICAgICAgIDwvQ2FyZENvbnRlbnQ+XG4gICAgICAgICAgPC9DYXJkPlxuICAgICAgICApO1xuXG4gICAgICBjYXNlIDE6XG4gICAgICAgIHJldHVybiAoXG4gICAgICAgICAgPENhcmQ+XG4gICAgICAgICAgICA8Q2FyZENvbnRlbnQ+XG4gICAgICAgICAgICAgIDxUeXBvZ3JhcGh5IHZhcmlhbnQ9XCJoNlwiIGd1dHRlckJvdHRvbT5cbiAgICAgICAgICAgICAgICBDb25maWd1cmUgWW91ciBQaXBlbGluZVxuICAgICAgICAgICAgICA8L1R5cG9ncmFwaHk+XG4gICAgICAgICAgICAgIDxHcmlkIGNvbnRhaW5lciBzcGFjaW5nPXszfT5cbiAgICAgICAgICAgICAgICA8R3JpZCBzaXplPXt7IHhzOiAxMiwgbWQ6IDYgfX0+XG4gICAgICAgICAgICAgICAgICA8VGV4dEZpZWxkXG4gICAgICAgICAgICAgICAgICAgIGZ1bGxXaWR0aFxuICAgICAgICAgICAgICAgICAgICBsYWJlbD1cIlBpcGVsaW5lIE5hbWVcIlxuICAgICAgICAgICAgICAgICAgICB2YWx1ZT17Y29uZmlnLm5hbWV9XG4gICAgICAgICAgICAgICAgICAgIG9uQ2hhbmdlPXsoZSkgPT4gaGFuZGxlQ29uZmlnQ2hhbmdlKCduYW1lJywgZS50YXJnZXQudmFsdWUpfVxuICAgICAgICAgICAgICAgICAgICByZXF1aXJlZFxuICAgICAgICAgICAgICAgICAgLz5cbiAgICAgICAgICAgICAgICA8L0dyaWQ+XG4gICAgICAgICAgICAgICAgPEdyaWQgc2l6ZT17eyB4czogMTIsIG1kOiA2IH19PlxuICAgICAgICAgICAgICAgICAgPEZvcm1Db250cm9sIGZ1bGxXaWR0aCByZXF1aXJlZD5cbiAgICAgICAgICAgICAgICAgICAgPElucHV0TGFiZWw+UGlwZWxpbmUgVHlwZTwvSW5wdXRMYWJlbD5cbiAgICAgICAgICAgICAgICAgICAgPFNlbGVjdFxuICAgICAgICAgICAgICAgICAgICAgIHZhbHVlPXtjb25maWcudHlwZX1cbiAgICAgICAgICAgICAgICAgICAgICBsYWJlbD1cIlBpcGVsaW5lIFR5cGVcIlxuICAgICAgICAgICAgICAgICAgICAgIG9uQ2hhbmdlPXsoZSkgPT4gaGFuZGxlQ29uZmlnQ2hhbmdlKCd0eXBlJywgZS50YXJnZXQudmFsdWUpfVxuICAgICAgICAgICAgICAgICAgICA+XG4gICAgICAgICAgICAgICAgICAgICAgPE1lbnVJdGVtIHZhbHVlPVwiY2xhc3NpZmljYXRpb25cIj5DbGFzc2lmaWNhdGlvbjwvTWVudUl0ZW0+XG4gICAgICAgICAgICAgICAgICAgICAgPE1lbnVJdGVtIHZhbHVlPVwicmVncmVzc2lvblwiPlJlZ3Jlc3Npb248L01lbnVJdGVtPlxuICAgICAgICAgICAgICAgICAgICAgIDxNZW51SXRlbSB2YWx1ZT1cImNsdXN0ZXJpbmdcIj5DbHVzdGVyaW5nPC9NZW51SXRlbT5cbiAgICAgICAgICAgICAgICAgICAgICA8TWVudUl0ZW0gdmFsdWU9XCJhbm9tYWx5X2RldGVjdGlvblwiPkFub21hbHkgRGV0ZWN0aW9uPC9NZW51SXRlbT5cbiAgICAgICAgICAgICAgICAgICAgPC9TZWxlY3Q+XG4gICAgICAgICAgICAgICAgICA8L0Zvcm1Db250cm9sPlxuICAgICAgICAgICAgICAgIDwvR3JpZD5cbiAgICAgICAgICAgICAgICA8R3JpZCBzaXplPXsxMn0+XG4gICAgICAgICAgICAgICAgICA8VGV4dEZpZWxkXG4gICAgICAgICAgICAgICAgICAgIGZ1bGxXaWR0aFxuICAgICAgICAgICAgICAgICAgICBsYWJlbD1cIk9iamVjdGl2ZVwiXG4gICAgICAgICAgICAgICAgICAgIHZhbHVlPXtjb25maWcub2JqZWN0aXZlfVxuICAgICAgICAgICAgICAgICAgICBvbkNoYW5nZT17KGUpID0+IGhhbmRsZUNvbmZpZ0NoYW5nZSgnb2JqZWN0aXZlJywgZS50YXJnZXQudmFsdWUpfVxuICAgICAgICAgICAgICAgICAgICBwbGFjZWhvbGRlcj1cIkRlc2NyaWJlIHdoYXQgeW91IHdhbnQgdG8gYWNoaWV2ZSB3aXRoIHRoaXMgcGlwZWxpbmUuLi5cIlxuICAgICAgICAgICAgICAgICAgICByZXF1aXJlZFxuICAgICAgICAgICAgICAgICAgICBtdWx0aWxpbmVcbiAgICAgICAgICAgICAgICAgICAgcm93cz17Mn1cbiAgICAgICAgICAgICAgICAgIC8+XG4gICAgICAgICAgICAgICAgPC9HcmlkPlxuICAgICAgICAgICAgICAgIDxHcmlkIHNpemU9ezEyfT5cbiAgICAgICAgICAgICAgICAgIDxUZXh0RmllbGRcbiAgICAgICAgICAgICAgICAgICAgZnVsbFdpZHRoXG4gICAgICAgICAgICAgICAgICAgIGxhYmVsPVwiRGVzY3JpcHRpb25cIlxuICAgICAgICAgICAgICAgICAgICB2YWx1ZT17Y29uZmlnLmRlc2NyaXB0aW9ufVxuICAgICAgICAgICAgICAgICAgICBvbkNoYW5nZT17KGUpID0+IGhhbmRsZUNvbmZpZ0NoYW5nZSgnZGVzY3JpcHRpb24nLCBlLnRhcmdldC52YWx1ZSl9XG4gICAgICAgICAgICAgICAgICAgIHBsYWNlaG9sZGVyPVwiT3B0aW9uYWwgZGVzY3JpcHRpb24gZm9yIHlvdXIgcGlwZWxpbmUuLi5cIlxuICAgICAgICAgICAgICAgICAgICBtdWx0aWxpbmVcbiAgICAgICAgICAgICAgICAgICAgcm93cz17M31cbiAgICAgICAgICAgICAgICAgIC8+XG4gICAgICAgICAgICAgICAgPC9HcmlkPlxuICAgICAgICAgICAgICAgIDxHcmlkIHNpemU9ezEyfT5cbiAgICAgICAgICAgICAgICAgIDxGb3JtQ29udHJvbExhYmVsXG4gICAgICAgICAgICAgICAgICAgIGNvbnRyb2w9e1xuICAgICAgICAgICAgICAgICAgICAgIDxDaGVja2JveFxuICAgICAgICAgICAgICAgICAgICAgICAgY2hlY2tlZD17Y29uZmlnLnVzZVJlYWxBd3MgfHwgZmFsc2V9XG4gICAgICAgICAgICAgICAgICAgICAgICBvbkNoYW5nZT17KGUpID0+IGhhbmRsZUNvbmZpZ0NoYW5nZSgndXNlUmVhbEF3cycsIGUudGFyZ2V0LmNoZWNrZWQpfVxuICAgICAgICAgICAgICAgICAgICAgICAgY29sb3I9XCJwcmltYXJ5XCJcbiAgICAgICAgICAgICAgICAgICAgICAvPlxuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIGxhYmVsPXtcbiAgICAgICAgICAgICAgICAgICAgICA8Qm94PlxuICAgICAgICAgICAgICAgICAgICAgICAgPFR5cG9ncmFwaHkgY29tcG9uZW50PVwic3BhblwiPlxuICAgICAgICAgICAgICAgICAgICAgICAgICBVc2UgUmVhbCBBV1MgSW5mcmFzdHJ1Y3R1cmVcbiAgICAgICAgICAgICAgICAgICAgICAgIDwvVHlwb2dyYXBoeT5cbiAgICAgICAgICAgICAgICAgICAgICAgIDxUeXBvZ3JhcGh5IHZhcmlhbnQ9XCJjYXB0aW9uXCIgZGlzcGxheT1cImJsb2NrXCIgY29sb3I9XCJ0ZXh0LnNlY29uZGFyeVwiPlxuICAgICAgICAgICAgICAgICAgICAgICAgICBFeGVjdXRlIHBpcGVsaW5lIG9uIGFjdHVhbCBBV1Mgc2VydmljZXMgKFN0ZXAgRnVuY3Rpb25zICsgU2FnZU1ha2VyKS4gXG4gICAgICAgICAgICAgICAgICAgICAgICAgIFVuY2hlY2sgZm9yIHNpbXVsYXRpb24gbW9kZS5cbiAgICAgICAgICAgICAgICAgICAgICAgIDwvVHlwb2dyYXBoeT5cbiAgICAgICAgICAgICAgICAgICAgICA8L0JveD5cbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgLz5cbiAgICAgICAgICAgICAgICA8L0dyaWQ+XG4gICAgICAgICAgICAgICAge2RhdGFVcGxvYWQgJiYgKGNvbmZpZy50eXBlID09PSAnY2xhc3NpZmljYXRpb24nIHx8IGNvbmZpZy50eXBlID09PSAncmVncmVzc2lvbicpICYmIChcbiAgICAgICAgICAgICAgICAgIDxHcmlkIHNpemU9e3sgeHM6IDEyLCBtZDogNiB9fT5cbiAgICAgICAgICAgICAgICAgICAgPEZvcm1Db250cm9sIGZ1bGxXaWR0aD5cbiAgICAgICAgICAgICAgICAgICAgICA8SW5wdXRMYWJlbD5UYXJnZXQgQ29sdW1uPC9JbnB1dExhYmVsPlxuICAgICAgICAgICAgICAgICAgICAgIDxTZWxlY3RcbiAgICAgICAgICAgICAgICAgICAgICAgIHZhbHVlPXtjb25maWcudGFyZ2V0Q29sdW1uIHx8ICcnfVxuICAgICAgICAgICAgICAgICAgICAgICAgbGFiZWw9XCJUYXJnZXQgQ29sdW1uXCJcbiAgICAgICAgICAgICAgICAgICAgICAgIG9uQ2hhbmdlPXsoZSkgPT4gaGFuZGxlQ29uZmlnQ2hhbmdlKCd0YXJnZXRDb2x1bW4nLCBlLnRhcmdldC52YWx1ZSl9XG4gICAgICAgICAgICAgICAgICAgICAgPlxuICAgICAgICAgICAgICAgICAgICAgICAge2RhdGFVcGxvYWQuY29sdW1ucy5tYXAoKGNvbHVtbikgPT4gKFxuICAgICAgICAgICAgICAgICAgICAgICAgICA8TWVudUl0ZW0ga2V5PXtjb2x1bW59IHZhbHVlPXtjb2x1bW59PlxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIHtjb2x1bW59XG4gICAgICAgICAgICAgICAgICAgICAgICAgIDwvTWVudUl0ZW0+XG4gICAgICAgICAgICAgICAgICAgICAgICApKX1cbiAgICAgICAgICAgICAgICAgICAgICA8L1NlbGVjdD5cbiAgICAgICAgICAgICAgICAgICAgPC9Gb3JtQ29udHJvbD5cbiAgICAgICAgICAgICAgICAgIDwvR3JpZD5cbiAgICAgICAgICAgICAgICApfVxuICAgICAgICAgICAgICA8L0dyaWQ+XG4gICAgICAgICAgICA8L0NhcmRDb250ZW50PlxuICAgICAgICAgIDwvQ2FyZD5cbiAgICAgICAgKTtcblxuICAgICAgY2FzZSAyOlxuICAgICAgICByZXR1cm4gKFxuICAgICAgICAgIDxDYXJkPlxuICAgICAgICAgICAgPENhcmRDb250ZW50PlxuICAgICAgICAgICAgICA8VHlwb2dyYXBoeSB2YXJpYW50PVwiaDZcIiBndXR0ZXJCb3R0b20+XG4gICAgICAgICAgICAgICAgUmV2aWV3IFlvdXIgUGlwZWxpbmVcbiAgICAgICAgICAgICAgPC9UeXBvZ3JhcGh5PlxuICAgICAgICAgICAgICA8R3JpZCBjb250YWluZXIgc3BhY2luZz17M30+XG4gICAgICAgICAgICAgICAgPEdyaWQgc2l6ZT17eyB4czogMTIsIG1kOiA2IH19PlxuICAgICAgICAgICAgICAgICAgPFR5cG9ncmFwaHkgdmFyaWFudD1cInN1YnRpdGxlMVwiIGd1dHRlckJvdHRvbT5cbiAgICAgICAgICAgICAgICAgICAgUGlwZWxpbmUgRGV0YWlsc1xuICAgICAgICAgICAgICAgICAgPC9UeXBvZ3JhcGh5PlxuICAgICAgICAgICAgICAgICAgPFRhYmxlIHNpemU9XCJzbWFsbFwiPlxuICAgICAgICAgICAgICAgICAgICA8VGFibGVCb2R5PlxuICAgICAgICAgICAgICAgICAgICAgIDxUYWJsZVJvdz5cbiAgICAgICAgICAgICAgICAgICAgICAgIDxUYWJsZUNlbGw+PHN0cm9uZz5OYW1lOjwvc3Ryb25nPjwvVGFibGVDZWxsPlxuICAgICAgICAgICAgICAgICAgICAgICAgPFRhYmxlQ2VsbD57Y29uZmlnLm5hbWV9PC9UYWJsZUNlbGw+XG4gICAgICAgICAgICAgICAgICAgICAgPC9UYWJsZVJvdz5cbiAgICAgICAgICAgICAgICAgICAgICA8VGFibGVSb3c+XG4gICAgICAgICAgICAgICAgICAgICAgICA8VGFibGVDZWxsPjxzdHJvbmc+VHlwZTo8L3N0cm9uZz48L1RhYmxlQ2VsbD5cbiAgICAgICAgICAgICAgICAgICAgICAgIDxUYWJsZUNlbGw+XG4gICAgICAgICAgICAgICAgICAgICAgICAgIDxDaGlwIGxhYmVsPXtjb25maWcudHlwZS5yZXBsYWNlKCdfJywgJyAnKX0gc2l6ZT1cInNtYWxsXCIgLz5cbiAgICAgICAgICAgICAgICAgICAgICAgIDwvVGFibGVDZWxsPlxuICAgICAgICAgICAgICAgICAgICAgIDwvVGFibGVSb3c+XG4gICAgICAgICAgICAgICAgICAgICAgPFRhYmxlUm93PlxuICAgICAgICAgICAgICAgICAgICAgICAgPFRhYmxlQ2VsbD48c3Ryb25nPk9iamVjdGl2ZTo8L3N0cm9uZz48L1RhYmxlQ2VsbD5cbiAgICAgICAgICAgICAgICAgICAgICAgIDxUYWJsZUNlbGw+e2NvbmZpZy5vYmplY3RpdmV9PC9UYWJsZUNlbGw+XG4gICAgICAgICAgICAgICAgICAgICAgPC9UYWJsZVJvdz5cbiAgICAgICAgICAgICAgICAgICAgICB7Y29uZmlnLmRlc2NyaXB0aW9uICYmIChcbiAgICAgICAgICAgICAgICAgICAgICAgIDxUYWJsZVJvdz5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgPFRhYmxlQ2VsbD48c3Ryb25nPkRlc2NyaXB0aW9uOjwvc3Ryb25nPjwvVGFibGVDZWxsPlxuICAgICAgICAgICAgICAgICAgICAgICAgICA8VGFibGVDZWxsPntjb25maWcuZGVzY3JpcHRpb259PC9UYWJsZUNlbGw+XG4gICAgICAgICAgICAgICAgICAgICAgICA8L1RhYmxlUm93PlxuICAgICAgICAgICAgICAgICAgICAgICl9XG4gICAgICAgICAgICAgICAgICAgIDwvVGFibGVCb2R5PlxuICAgICAgICAgICAgICAgICAgPC9UYWJsZT5cbiAgICAgICAgICAgICAgICA8L0dyaWQ+XG4gICAgICAgICAgICAgICAgPEdyaWQgc2l6ZT17eyB4czogMTIsIG1kOiA2IH19PlxuICAgICAgICAgICAgICAgICAgPFR5cG9ncmFwaHkgdmFyaWFudD1cInN1YnRpdGxlMVwiIGd1dHRlckJvdHRvbT5cbiAgICAgICAgICAgICAgICAgICAgRGF0YXNldCBJbmZvcm1hdGlvblxuICAgICAgICAgICAgICAgICAgPC9UeXBvZ3JhcGh5PlxuICAgICAgICAgICAgICAgICAge2RhdGFVcGxvYWQgJiYgKFxuICAgICAgICAgICAgICAgICAgICA8VGFibGUgc2l6ZT1cInNtYWxsXCI+XG4gICAgICAgICAgICAgICAgICAgICAgPFRhYmxlQm9keT5cbiAgICAgICAgICAgICAgICAgICAgICAgIDxUYWJsZVJvdz5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgPFRhYmxlQ2VsbD48c3Ryb25nPkZpbGU6PC9zdHJvbmc+PC9UYWJsZUNlbGw+XG4gICAgICAgICAgICAgICAgICAgICAgICAgIDxUYWJsZUNlbGw+e2RhdGFVcGxvYWQuZmlsZW5hbWV9PC9UYWJsZUNlbGw+XG4gICAgICAgICAgICAgICAgICAgICAgICA8L1RhYmxlUm93PlxuICAgICAgICAgICAgICAgICAgICAgICAgPFRhYmxlUm93PlxuICAgICAgICAgICAgICAgICAgICAgICAgICA8VGFibGVDZWxsPjxzdHJvbmc+Um93czo8L3N0cm9uZz48L1RhYmxlQ2VsbD5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgPFRhYmxlQ2VsbD57ZGF0YVVwbG9hZC5yb3dDb3VudH08L1RhYmxlQ2VsbD5cbiAgICAgICAgICAgICAgICAgICAgICAgIDwvVGFibGVSb3c+XG4gICAgICAgICAgICAgICAgICAgICAgICA8VGFibGVSb3c+XG4gICAgICAgICAgICAgICAgICAgICAgICAgIDxUYWJsZUNlbGw+PHN0cm9uZz5Db2x1bW5zOjwvc3Ryb25nPjwvVGFibGVDZWxsPlxuICAgICAgICAgICAgICAgICAgICAgICAgICA8VGFibGVDZWxsPntkYXRhVXBsb2FkLmNvbHVtbnMubGVuZ3RofTwvVGFibGVDZWxsPlxuICAgICAgICAgICAgICAgICAgICAgICAgPC9UYWJsZVJvdz5cbiAgICAgICAgICAgICAgICAgICAgICAgIDxUYWJsZVJvdz5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgPFRhYmxlQ2VsbD48c3Ryb25nPlNpemU6PC9zdHJvbmc+PC9UYWJsZUNlbGw+XG4gICAgICAgICAgICAgICAgICAgICAgICAgIDxUYWJsZUNlbGw+eyhkYXRhVXBsb2FkLnNpemUgLyAxMDI0IC8gMTAyNCkudG9GaXhlZCgyKX0gTUI8L1RhYmxlQ2VsbD5cbiAgICAgICAgICAgICAgICAgICAgICAgIDwvVGFibGVSb3c+XG4gICAgICAgICAgICAgICAgICAgICAgPC9UYWJsZUJvZHk+XG4gICAgICAgICAgICAgICAgICAgIDwvVGFibGU+XG4gICAgICAgICAgICAgICAgICApfVxuICAgICAgICAgICAgICAgIDwvR3JpZD5cbiAgICAgICAgICAgICAgPC9HcmlkPlxuICAgICAgICAgICAgPC9DYXJkQ29udGVudD5cbiAgICAgICAgICA8L0NhcmQ+XG4gICAgICAgICk7XG5cbiAgICAgIGRlZmF1bHQ6XG4gICAgICAgIHJldHVybiBudWxsO1xuICAgIH1cbiAgfTtcblxuICByZXR1cm4gKFxuICAgIDxCb3ggc3g9e3sgcDogMyB9fT5cbiAgICAgIDxUeXBvZ3JhcGh5IHZhcmlhbnQ9XCJoNFwiIGd1dHRlckJvdHRvbT5cbiAgICAgICAgUGlwZWxpbmUgQnVpbGRlclxuICAgICAgPC9UeXBvZ3JhcGh5PlxuICAgICAgXG4gICAgICB7ZXJyb3JzLmxlbmd0aCA+IDAgJiYgKFxuICAgICAgICA8QWxlcnQgc2V2ZXJpdHk9XCJlcnJvclwiIHN4PXt7IG1iOiAzIH19PlxuICAgICAgICAgIHtlcnJvcnMubWFwKChlcnJvciwgaW5kZXgpID0+IChcbiAgICAgICAgICAgIDxkaXYga2V5PXtpbmRleH0+e2Vycm9yfTwvZGl2PlxuICAgICAgICAgICkpfVxuICAgICAgICA8L0FsZXJ0PlxuICAgICAgKX1cblxuICAgICAgPENhcmQgc3g9e3sgbWI6IDMgfX0+XG4gICAgICAgIDxDYXJkQ29udGVudD5cbiAgICAgICAgICA8U3RlcHBlciBhY3RpdmVTdGVwPXthY3RpdmVTdGVwfSBzeD17eyBtYjogMyB9fT5cbiAgICAgICAgICAgIHtzdGVwcy5tYXAoKGxhYmVsKSA9PiAoXG4gICAgICAgICAgICAgIDxTdGVwIGtleT17bGFiZWx9PlxuICAgICAgICAgICAgICAgIDxTdGVwTGFiZWw+e2xhYmVsfTwvU3RlcExhYmVsPlxuICAgICAgICAgICAgICA8L1N0ZXA+XG4gICAgICAgICAgICApKX1cbiAgICAgICAgICA8L1N0ZXBwZXI+XG5cbiAgICAgICAgICB7YWN0aXZlU3RlcCA9PT0gc3RlcHMubGVuZ3RoID8gKFxuICAgICAgICAgICAgPEJveCBzeD17eyB0ZXh0QWxpZ246ICdjZW50ZXInIH19PlxuICAgICAgICAgICAgICA8VHlwb2dyYXBoeSB2YXJpYW50PVwiaDZcIiBndXR0ZXJCb3R0b20+XG4gICAgICAgICAgICAgICAgUGlwZWxpbmUgQ3JlYXRlZCBTdWNjZXNzZnVsbHkhXG4gICAgICAgICAgICAgIDwvVHlwb2dyYXBoeT5cbiAgICAgICAgICAgICAgPEJ1dHRvbiBvbkNsaWNrPXtoYW5kbGVSZXNldH0gdmFyaWFudD1cImNvbnRhaW5lZFwiPlxuICAgICAgICAgICAgICAgIENyZWF0ZSBBbm90aGVyIFBpcGVsaW5lXG4gICAgICAgICAgICAgIDwvQnV0dG9uPlxuICAgICAgICAgICAgPC9Cb3g+XG4gICAgICAgICAgKSA6IChcbiAgICAgICAgICAgIDxCb3g+XG4gICAgICAgICAgICAgIHtyZW5kZXJTdGVwQ29udGVudChhY3RpdmVTdGVwKX1cblxuICAgICAgICAgICAgICA8Qm94IHN4PXt7IGRpc3BsYXk6ICdmbGV4JywgZmxleERpcmVjdGlvbjogJ3JvdycsIHB0OiAzIH19PlxuICAgICAgICAgICAgICAgIDxCdXR0b25cbiAgICAgICAgICAgICAgICAgIGNvbG9yPVwiaW5oZXJpdFwiXG4gICAgICAgICAgICAgICAgICBkaXNhYmxlZD17YWN0aXZlU3RlcCA9PT0gMH1cbiAgICAgICAgICAgICAgICAgIG9uQ2xpY2s9e2hhbmRsZUJhY2t9XG4gICAgICAgICAgICAgICAgICBzeD17eyBtcjogMSB9fVxuICAgICAgICAgICAgICAgID5cbiAgICAgICAgICAgICAgICAgIEJhY2tcbiAgICAgICAgICAgICAgICA8L0J1dHRvbj5cbiAgICAgICAgICAgICAgICA8Qm94IHN4PXt7IGZsZXg6ICcxIDEgYXV0bycgfX0gLz5cbiAgICAgICAgICAgICAgICB7YWN0aXZlU3RlcCA9PT0gc3RlcHMubGVuZ3RoIC0gMSA/IChcbiAgICAgICAgICAgICAgICAgIDxCdXR0b25cbiAgICAgICAgICAgICAgICAgICAgb25DbGljaz17aGFuZGxlQ3JlYXRlUGlwZWxpbmV9XG4gICAgICAgICAgICAgICAgICAgIGRpc2FibGVkPXtjcmVhdGluZ31cbiAgICAgICAgICAgICAgICAgICAgdmFyaWFudD1cImNvbnRhaW5lZFwiXG4gICAgICAgICAgICAgICAgICA+XG4gICAgICAgICAgICAgICAgICAgIHtjcmVhdGluZyA/IDxDaXJjdWxhclByb2dyZXNzIHNpemU9ezI0fSAvPiA6ICdDcmVhdGUgUGlwZWxpbmUnfVxuICAgICAgICAgICAgICAgICAgPC9CdXR0b24+XG4gICAgICAgICAgICAgICAgKSA6IChcbiAgICAgICAgICAgICAgICAgIDxCdXR0b25cbiAgICAgICAgICAgICAgICAgICAgb25DbGljaz17aGFuZGxlTmV4dH1cbiAgICAgICAgICAgICAgICAgICAgZGlzYWJsZWQ9e3VwbG9hZGluZ31cbiAgICAgICAgICAgICAgICAgICAgdmFyaWFudD1cImNvbnRhaW5lZFwiXG4gICAgICAgICAgICAgICAgICA+XG4gICAgICAgICAgICAgICAgICAgIHt1cGxvYWRpbmcgPyA8Q2lyY3VsYXJQcm9ncmVzcyBzaXplPXsyNH0gLz4gOiAnTmV4dCd9XG4gICAgICAgICAgICAgICAgICA8L0J1dHRvbj5cbiAgICAgICAgICAgICAgICApfVxuICAgICAgICAgICAgICA8L0JveD5cbiAgICAgICAgICAgIDwvQm94PlxuICAgICAgICAgICl9XG4gICAgICAgIDwvQ2FyZENvbnRlbnQ+XG4gICAgICA8L0NhcmQ+XG5cbiAgICAgIHsvKiBEYXRhIFByZXZpZXcgRGlhbG9nICovfVxuICAgICAgPERpYWxvZyBvcGVuPXtwcmV2aWV3T3Blbn0gb25DbG9zZT17KCkgPT4gc2V0UHJldmlld09wZW4oZmFsc2UpfSBtYXhXaWR0aD1cImxnXCIgZnVsbFdpZHRoPlxuICAgICAgICA8RGlhbG9nVGl0bGU+RGF0YSBQcmV2aWV3PC9EaWFsb2dUaXRsZT5cbiAgICAgICAgPERpYWxvZ0NvbnRlbnQ+XG4gICAgICAgICAge2RhdGFVcGxvYWQgJiYgKFxuICAgICAgICAgICAgPFRhYmxlQ29udGFpbmVyIGNvbXBvbmVudD17UGFwZXJ9PlxuICAgICAgICAgICAgICA8VGFibGUgc2l6ZT1cInNtYWxsXCI+XG4gICAgICAgICAgICAgICAgPFRhYmxlSGVhZD5cbiAgICAgICAgICAgICAgICAgIDxUYWJsZVJvdz5cbiAgICAgICAgICAgICAgICAgICAge2RhdGFVcGxvYWQuY29sdW1ucy5tYXAoKGNvbHVtbikgPT4gKFxuICAgICAgICAgICAgICAgICAgICAgIDxUYWJsZUNlbGwga2V5PXtjb2x1bW59Pntjb2x1bW59PC9UYWJsZUNlbGw+XG4gICAgICAgICAgICAgICAgICAgICkpfVxuICAgICAgICAgICAgICAgICAgPC9UYWJsZVJvdz5cbiAgICAgICAgICAgICAgICA8L1RhYmxlSGVhZD5cbiAgICAgICAgICAgICAgICA8VGFibGVCb2R5PlxuICAgICAgICAgICAgICAgICAge2RhdGFVcGxvYWQucHJldmlldy5zbGljZSgwLCA1KS5tYXAoKHJvdywgaW5kZXgpID0+IChcbiAgICAgICAgICAgICAgICAgICAgPFRhYmxlUm93IGtleT17aW5kZXh9PlxuICAgICAgICAgICAgICAgICAgICAgIHtkYXRhVXBsb2FkLmNvbHVtbnMubWFwKChjb2x1bW4pID0+IChcbiAgICAgICAgICAgICAgICAgICAgICAgIDxUYWJsZUNlbGwga2V5PXtjb2x1bW59Pntyb3dbY29sdW1uXX08L1RhYmxlQ2VsbD5cbiAgICAgICAgICAgICAgICAgICAgICApKX1cbiAgICAgICAgICAgICAgICAgICAgPC9UYWJsZVJvdz5cbiAgICAgICAgICAgICAgICAgICkpfVxuICAgICAgICAgICAgICAgIDwvVGFibGVCb2R5PlxuICAgICAgICAgICAgICA8L1RhYmxlPlxuICAgICAgICAgICAgPC9UYWJsZUNvbnRhaW5lcj5cbiAgICAgICAgICApfVxuICAgICAgICA8L0RpYWxvZ0NvbnRlbnQ+XG4gICAgICAgIDxEaWFsb2dBY3Rpb25zPlxuICAgICAgICAgIDxCdXR0b24gb25DbGljaz17KCkgPT4gc2V0UHJldmlld09wZW4oZmFsc2UpfT5DbG9zZTwvQnV0dG9uPlxuICAgICAgICA8L0RpYWxvZ0FjdGlvbnM+XG4gICAgICA8L0RpYWxvZz5cbiAgICA8L0JveD5cbiAgKTtcbn07XG5cbmV4cG9ydCBkZWZhdWx0IFBpcGVsaW5lQnVpbGRlcjsiXX0=