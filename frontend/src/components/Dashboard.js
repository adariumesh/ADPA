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
const react_router_dom_1 = require("react-router-dom");
const material_1 = require("@mui/material");
const icons_material_1 = require("@mui/icons-material");
const recharts_1 = require("recharts");
const api_1 = require("../services/api");
const Dashboard = () => {
    const navigate = (0, react_router_dom_1.useNavigate)();
    const [pipelines, setPipelines] = (0, react_1.useState)([]);
    const [stats, setStats] = (0, react_1.useState)(null);
    const [loading, setLoading] = (0, react_1.useState)(true);
    const [aiStatus, setAiStatus] = (0, react_1.useState)(null);
    const [deleteDialogOpen, setDeleteDialogOpen] = (0, react_1.useState)(false);
    const [pipelineToDelete, setPipelineToDelete] = (0, react_1.useState)(null);
    (0, react_1.useEffect)(() => {
        loadData();
    }, []);
    const loadData = async () => {
        setLoading(true);
        try {
            // Use real API to get pipelines and stats
            const pipelinesData = await api_1.apiService.getPipelines();
            const statsData = await api_1.apiService.getDashboardStats();
            // Get AI/health status
            try {
                const response = await fetch('https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/health');
                const healthData = await response.json();
                setAiStatus(healthData);
            }
            catch (e) {
                console.error('Could not fetch AI status:', e);
            }
            setPipelines(pipelinesData);
            setStats(statsData);
        }
        catch (error) {
            console.error('Error loading dashboard data:', error);
        }
        finally {
            setLoading(false);
        }
    };
    const handleExecutePipeline = async (pipelineId) => {
        try {
            await api_1.apiService.executePipeline(pipelineId);
            loadData(); // Refresh data
        }
        catch (error) {
            console.error('Error executing pipeline:', error);
        }
    };
    const handleViewPipeline = (pipelineId) => {
        // Navigate to monitor page with this pipeline selected
        navigate('/monitor');
    };
    const handleDeleteClick = (pipelineId) => {
        setPipelineToDelete(pipelineId);
        setDeleteDialogOpen(true);
    };
    const handleDeleteConfirm = async () => {
        if (pipelineToDelete) {
            try {
                await api_1.apiService.deletePipeline(pipelineToDelete);
                loadData(); // Refresh data
            }
            catch (error) {
                console.error('Error deleting pipeline:', error);
            }
        }
        setDeleteDialogOpen(false);
        setPipelineToDelete(null);
    };
    const handleDeleteCancel = () => {
        setDeleteDialogOpen(false);
        setPipelineToDelete(null);
    };
    const getStatusColor = (status) => {
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
        }, {});
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
        }, {});
        return Object.entries(typeCounts).map(([name, value]) => ({ name, value }));
    };
    if (loading) {
        return (<material_1.Box sx={{ p: 3 }}>
        <material_1.Typography variant="h4" gutterBottom>
          Dashboard
        </material_1.Typography>
        <material_1.LinearProgress />
      </material_1.Box>);
    }
    return (<material_1.Box sx={{ p: 3 }}>
      <material_1.Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <material_1.Typography variant="h4" gutterBottom>
          Dashboard
        </material_1.Typography>
        <material_1.Button variant="outlined" startIcon={<icons_material_1.Refresh />} onClick={loadData}>
          Refresh
        </material_1.Button>
      </material_1.Box>

      {/* Stats Cards */}
      <material_1.Grid container spacing={3} sx={{ mb: 4 }}>
        <material_1.Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <material_1.Card>
            <material_1.CardContent>
              <material_1.Typography color="textSecondary" gutterBottom>
                Total Pipelines
              </material_1.Typography>
              <material_1.Typography variant="h5" component="h2">
                {pipelines.length}
              </material_1.Typography>
            </material_1.CardContent>
          </material_1.Card>
        </material_1.Grid>
        <material_1.Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <material_1.Card>
            <material_1.CardContent>
              <material_1.Typography color="textSecondary" gutterBottom>
                Running Pipelines
              </material_1.Typography>
              <material_1.Typography variant="h5" component="h2" color="primary">
                {pipelines.filter(p => p.status === 'running').length}
              </material_1.Typography>
            </material_1.CardContent>
          </material_1.Card>
        </material_1.Grid>
        <material_1.Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <material_1.Card>
            <material_1.CardContent>
              <material_1.Typography color="textSecondary" gutterBottom>
                Success Rate
              </material_1.Typography>
              <material_1.Typography variant="h5" component="h2" color="success.main">
                {pipelines.length > 0
            ? Math.round((pipelines.filter(p => p.status === 'completed').length / pipelines.length) * 100)
            : 0}%
              </material_1.Typography>
            </material_1.CardContent>
          </material_1.Card>
        </material_1.Grid>
        <material_1.Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <material_1.Card>
            <material_1.CardContent>
              <material_1.Typography color="textSecondary" gutterBottom>
                Avg. Accuracy
              </material_1.Typography>
              <material_1.Typography variant="h5" component="h2">
                {pipelines.filter(p => p.accuracy).length > 0
            ? Math.round((pipelines.filter(p => p.accuracy).reduce((sum, p) => sum + (p.accuracy || 0), 0) / pipelines.filter(p => p.accuracy).length) * 100)
            : 0}%
              </material_1.Typography>
            </material_1.CardContent>
          </material_1.Card>
        </material_1.Grid>
      </material_1.Grid>

      {/* AI Capabilities Status Card */}
      {aiStatus && (<material_1.Card sx={{ mb: 4, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
          <material_1.CardContent>
            <material_1.Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <icons_material_1.Psychology sx={{ fontSize: 40, color: 'white', mr: 2 }}/>
              <material_1.Box>
                <material_1.Typography variant="h5" sx={{ color: 'white', fontWeight: 'bold' }}>
                  🤖 ADPA Agentic AI System
                </material_1.Typography>
                <material_1.Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                  Version {aiStatus.version || '4.0.0-agentic'} | Powered by Amazon Bedrock
                </material_1.Typography>
              </material_1.Box>
              <material_1.Chip label={aiStatus.status === 'healthy' ? '● Online' : '○ Degraded'} sx={{
                ml: 'auto',
                bgcolor: aiStatus.status === 'healthy' ? '#4caf50' : '#ff9800',
                color: 'white',
                fontWeight: 'bold'
            }}/>
            </material_1.Box>
            
            <material_1.Grid container spacing={2}>
              {/* Components Status */}
              <material_1.Grid size={{ xs: 12, md: 4 }}>
                <material_1.Paper sx={{ p: 2, bgcolor: 'rgba(255,255,255,0.1)' }}>
                  <material_1.Typography variant="subtitle2" sx={{ color: 'white', mb: 1 }}>
                    System Components
                  </material_1.Typography>
                  <material_1.List dense>
                    {aiStatus.components && Object.entries(aiStatus.components).map(([key, value]) => (<material_1.ListItem key={key} sx={{ py: 0 }}>
                        <material_1.ListItemIcon sx={{ minWidth: 32 }}>
                          {value ? <icons_material_1.CheckCircle sx={{ color: '#4caf50', fontSize: 18 }}/> : <icons_material_1.Cancel sx={{ color: '#f44336', fontSize: 18 }}/>}
                        </material_1.ListItemIcon>
                        <material_1.ListItemText primary={key.replace('_', ' ').toUpperCase()} primaryTypographyProps={{ sx: { color: 'white', fontSize: '0.85rem' } }}/>
                      </material_1.ListItem>))}
                  </material_1.List>
                </material_1.Paper>
              </material_1.Grid>
              
              {/* AI Capabilities */}
              <material_1.Grid size={{ xs: 12, md: 8 }}>
                <material_1.Paper sx={{ p: 2, bgcolor: 'rgba(255,255,255,0.1)' }}>
                  <material_1.Typography variant="subtitle2" sx={{ color: 'white', mb: 1 }}>
                    <icons_material_1.AutoAwesome sx={{ fontSize: 16, mr: 0.5, verticalAlign: 'middle' }}/>
                    AI Capabilities (Amazon Bedrock Claude 3.5)
                  </material_1.Typography>
                  <material_1.Grid container spacing={1}>
                    {aiStatus.ai_capabilities?.agentic_features?.map((feature, index) => (<material_1.Grid key={index} size={{ xs: 6 }}>
                        <material_1.Chip icon={<icons_material_1.CheckCircle sx={{ color: 'white !important' }}/>} label={feature.replace(/_/g, ' ')} size="small" sx={{
                    bgcolor: 'rgba(255,255,255,0.2)',
                    color: 'white',
                    fontSize: '0.75rem',
                    '& .MuiChip-icon': { color: 'white' }
                }}/>
                      </material_1.Grid>))}
                  </material_1.Grid>
                  {aiStatus.ai_capabilities?.bedrock_enabled && (<material_1.Alert severity="success" sx={{ mt: 2, bgcolor: 'rgba(76, 175, 80, 0.2)', color: 'white' }}>
                      <strong>Bedrock AI Enabled:</strong> Pipelines use intelligent NL understanding, dataset analysis, and AI-powered planning
                    </material_1.Alert>)}
                </material_1.Paper>
              </material_1.Grid>
            </material_1.Grid>
          </material_1.CardContent>
        </material_1.Card>)}

      {/* Charts */}
      <material_1.Grid container spacing={3} sx={{ mb: 4 }}>
        <material_1.Grid size={{ xs: 12, md: 6 }}>
          <material_1.Card>
            <material_1.CardContent>
              <material_1.Typography variant="h6" gutterBottom>
                Pipeline Status Distribution
              </material_1.Typography>
              <recharts_1.ResponsiveContainer width="100%" height={300}>
                <recharts_1.PieChart>
                  <recharts_1.Pie data={getStatusChartData()} cx="50%" cy="50%" labelLine={false} label={({ name, value }) => `${name}: ${value}`} outerRadius={80} fill="#8884d8" dataKey="value">
                    {getStatusChartData().map((entry, index) => (<recharts_1.Cell key={`cell-${index}`} fill={entry.color}/>))}
                  </recharts_1.Pie>
                </recharts_1.PieChart>
              </recharts_1.ResponsiveContainer>
            </material_1.CardContent>
          </material_1.Card>
        </material_1.Grid>
        <material_1.Grid size={{ xs: 12, md: 6 }}>
          <material_1.Card>
            <material_1.CardContent>
              <material_1.Typography variant="h6" gutterBottom>
                Pipeline Types
              </material_1.Typography>
              <recharts_1.ResponsiveContainer width="100%" height={300}>
                <recharts_1.BarChart data={getTypeChartData()}>
                  <recharts_1.CartesianGrid strokeDasharray="3 3"/>
                  <recharts_1.XAxis dataKey="name"/>
                  <recharts_1.YAxis />
                  <recharts_1.Legend />
                  <recharts_1.Bar dataKey="value" fill="#1976d2"/>
                </recharts_1.BarChart>
              </recharts_1.ResponsiveContainer>
            </material_1.CardContent>
          </material_1.Card>
        </material_1.Grid>
      </material_1.Grid>

      {/* Recent Pipelines Table */}
      <material_1.Card>
        <material_1.CardContent>
          <material_1.Typography variant="h6" gutterBottom>
            Recent Pipelines
          </material_1.Typography>
          <material_1.TableContainer component={material_1.Paper}>
            <material_1.Table>
              <material_1.TableHead>
                <material_1.TableRow>
                  <material_1.TableCell>Name</material_1.TableCell>
                  <material_1.TableCell>Type</material_1.TableCell>
                  <material_1.TableCell>Status</material_1.TableCell>
                  <material_1.TableCell>Progress</material_1.TableCell>
                  <material_1.TableCell>Accuracy</material_1.TableCell>
                  <material_1.TableCell>Created</material_1.TableCell>
                  <material_1.TableCell>Actions</material_1.TableCell>
                </material_1.TableRow>
              </material_1.TableHead>
              <material_1.TableBody>
                {pipelines.map((pipeline) => (<material_1.TableRow key={pipeline.id}>
                    <material_1.TableCell>
                      <material_1.Typography variant="subtitle2">{pipeline.name}</material_1.Typography>
                      <material_1.Typography variant="body2" color="textSecondary">
                        {pipeline.description}
                      </material_1.Typography>
                    </material_1.TableCell>
                    <material_1.TableCell>
                      <material_1.Chip label={pipeline.type.replace('_', ' ')} size="small" variant="outlined"/>
                    </material_1.TableCell>
                    <material_1.TableCell>
                      <material_1.Chip label={pipeline.status} color={getStatusColor(pipeline.status)} size="small"/>
                    </material_1.TableCell>
                    <material_1.TableCell>
                      <material_1.Box sx={{ width: '100px' }}>
                        <material_1.LinearProgress variant="determinate" value={pipeline.progress} color={pipeline.status === 'failed' ? 'error' : 'primary'}/>
                        <material_1.Typography variant="caption">{pipeline.progress}%</material_1.Typography>
                      </material_1.Box>
                    </material_1.TableCell>
                    <material_1.TableCell>
                      {pipeline.accuracy ? `${Math.round(pipeline.accuracy * 100)}%` : 'N/A'}
                    </material_1.TableCell>
                    <material_1.TableCell>
                      {new Date(pipeline.createdAt).toLocaleDateString()}
                    </material_1.TableCell>
                    <material_1.TableCell>
                      <material_1.Tooltip title="Run Pipeline">
                        <material_1.IconButton size="small" onClick={() => handleExecutePipeline(pipeline.id)} disabled={pipeline.status === 'running'} color="primary">
                          <icons_material_1.PlayArrow />
                        </material_1.IconButton>
                      </material_1.Tooltip>
                      <material_1.Tooltip title="View Details">
                        <material_1.IconButton size="small" color="info" onClick={() => handleViewPipeline(pipeline.id)}>
                          <icons_material_1.Visibility />
                        </material_1.IconButton>
                      </material_1.Tooltip>
                      <material_1.Tooltip title="Delete Pipeline">
                        <material_1.IconButton size="small" color="error" onClick={() => handleDeleteClick(pipeline.id)}>
                          <icons_material_1.Delete />
                        </material_1.IconButton>
                      </material_1.Tooltip>
                    </material_1.TableCell>
                  </material_1.TableRow>))}
              </material_1.TableBody>
            </material_1.Table>
          </material_1.TableContainer>
        </material_1.CardContent>
      </material_1.Card>

      {/* Delete Confirmation Dialog */}
      <material_1.Dialog open={deleteDialogOpen} onClose={handleDeleteCancel}>
        <material_1.DialogTitle>Delete Pipeline</material_1.DialogTitle>
        <material_1.DialogContent>
          <material_1.DialogContentText>
            Are you sure you want to delete this pipeline? This action cannot be undone.
          </material_1.DialogContentText>
        </material_1.DialogContent>
        <material_1.DialogActions>
          <material_1.Button onClick={handleDeleteCancel}>Cancel</material_1.Button>
          <material_1.Button onClick={handleDeleteConfirm} color="error" variant="contained">
            Delete
          </material_1.Button>
        </material_1.DialogActions>
      </material_1.Dialog>
    </material_1.Box>);
};
exports.default = Dashboard;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiRGFzaGJvYXJkLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiRGFzaGJvYXJkLnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiOzs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7O0FBQUEsK0NBQW1EO0FBQ25ELHVEQUErQztBQUMvQyw0Q0E0QnVCO0FBQ3ZCLHdEQVM2QjtBQUM3Qix1Q0FBd0g7QUFFeEgseUNBQTZDO0FBRTdDLE1BQU0sU0FBUyxHQUFhLEdBQUcsRUFBRTtJQUMvQixNQUFNLFFBQVEsR0FBRyxJQUFBLDhCQUFXLEdBQUUsQ0FBQztJQUMvQixNQUFNLENBQUMsU0FBUyxFQUFFLFlBQVksQ0FBQyxHQUFHLElBQUEsZ0JBQVEsRUFBYSxFQUFFLENBQUMsQ0FBQztJQUMzRCxNQUFNLENBQUMsS0FBSyxFQUFFLFFBQVEsQ0FBQyxHQUFHLElBQUEsZ0JBQVEsRUFBd0IsSUFBSSxDQUFDLENBQUM7SUFDaEUsTUFBTSxDQUFDLE9BQU8sRUFBRSxVQUFVLENBQUMsR0FBRyxJQUFBLGdCQUFRLEVBQUMsSUFBSSxDQUFDLENBQUM7SUFDN0MsTUFBTSxDQUFDLFFBQVEsRUFBRSxXQUFXLENBQUMsR0FBRyxJQUFBLGdCQUFRLEVBQU0sSUFBSSxDQUFDLENBQUM7SUFDcEQsTUFBTSxDQUFDLGdCQUFnQixFQUFFLG1CQUFtQixDQUFDLEdBQUcsSUFBQSxnQkFBUSxFQUFDLEtBQUssQ0FBQyxDQUFDO0lBQ2hFLE1BQU0sQ0FBQyxnQkFBZ0IsRUFBRSxtQkFBbUIsQ0FBQyxHQUFHLElBQUEsZ0JBQVEsRUFBZ0IsSUFBSSxDQUFDLENBQUM7SUFFOUUsSUFBQSxpQkFBUyxFQUFDLEdBQUcsRUFBRTtRQUNiLFFBQVEsRUFBRSxDQUFDO0lBQ2IsQ0FBQyxFQUFFLEVBQUUsQ0FBQyxDQUFDO0lBRVAsTUFBTSxRQUFRLEdBQUcsS0FBSyxJQUFJLEVBQUU7UUFDMUIsVUFBVSxDQUFDLElBQUksQ0FBQyxDQUFDO1FBQ2pCLElBQUksQ0FBQztZQUNILDBDQUEwQztZQUMx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QUksQ0FBQyxTQUFTLENBQUMsT0FBTyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsRUFBRSxDQUFDLENBQUMsRUFBRSxFQUFFLEVBQUUsQ0FBQyxFQUFFLENBQUMsQ0FDeEM7UUFBQSxDQUFDLGVBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxFQUFFLEVBQUUsRUFBRSxFQUFFLEVBQUUsRUFBRSxFQUFFLENBQUMsRUFBRSxFQUFFLEVBQUUsQ0FBQyxFQUFFLENBQUMsQ0FDbkM7VUFBQSxDQUFDLGVBQUksQ0FDSDtZQUFBLENBQUMsc0JBQVcsQ0FDVjtjQUFBLENBQUMscUJBQVUsQ0FBQyxLQUFLLENBQUMsZUFBZSxDQUFDLFlBQVksQ0FDNUM7O2NBQ0YsRUFBRSxxQkFBVSxDQUNaO2NBQUEsQ0FBQyxxQkFBVSxDQUFDLE9BQU8sQ0FBQyxJQUFJLENBQUMsU0FBUyxDQUFDLElBQUksQ0FDckM7Z0JBQUEsQ0FBQyxTQUFTLENBQUMsTUFBTSxDQUNuQjtjQUFBLEVBQUUscUJBQVUsQ0FDZDtZQUFBLEVBQUUsc0JBQVcsQ0FDZjtVQUFBLEVBQUUsZUFBSSxDQUNSO1FBQUEsRUFBRSxlQUFJLENBQ047UUFBQSxDQUFDLGVBQUksQ0FBQyxJQUFJLENBQUMsQ0FBQyxFQUFFLEVBQUUsRUFBRSxFQUFFLEVBQUUsRUFBRSxFQUFFLENBQUMsRUFBRSxFQUFFLEVBQUUsQ0FBQyxFQUFFLENBQUMsQ0FDbkM7VUFBQSxDQUFDLGVBQUksQ0FDSDtZQUFBLENBQUMsc0JBQVcsQ0FDVjtjQUFBLENBQUMscUJBQVUsQ0FBQyxLQUFLLENBQUMsZUFBZSxDQUFDLFlBQVksQ0FDNUM7O2NBQ0YsRUFBRSxxQkFBVSxDQUNaO2NBQUEsQ0FBQyxxQkFBVSxDQUFDLE9BQU8sQ0FBQyxJQUFJLENBQUMsU0FBUyxDQUFDLElBQUksQ0FBQyxLQUFLLENBQUMsU0FBUyxDQUNyRDtnQkFBQSxDQUFDLFNBQVMsQ0FBQyxNQUFNLENBQUMsQ0FBQyxDQUFDLEVBQUUsQ0FBQyxDQUFDLENBQUMsTUFBTSxLQUFLLFNBQVMsQ0FBQyxDQUFDLE1BQU0s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Q1g7b0JBQUEsRUFBRSxvQkFBUyxDQUNiO2tCQUFBLEVBQUUsbUJBQVEsQ0FBQyxDQUNaLENBQUMsQ0FDSjtjQUFBLEVBQUUsb0JBQVMsQ0FDYjtZQUFBLEVBQUUsZ0JBQUssQ0FDVDtVQUFBLEVBQUUseUJBQWMsQ0FDbEI7UUFBQSxFQUFFLHNCQUFXLENBQ2Y7TUFBQSxFQUFFLGVBQUksQ0FFTjs7TUFBQSxDQUFDLGdDQUFnQyxDQUNqQztNQUFBLENBQUMsaUJBQU0sQ0FBQyxJQUFJLENBQUMsQ0FBQyxnQkFBZ0IsQ0FBQyxDQUFDLE9BQU8sQ0FBQyxDQUFDLGtCQUFrQixDQUFDLENBQzFEO1FBQUEsQ0FBQyxzQkFBVyxDQUFDLGVBQWUsRUFBRSxzQkFBVyxDQUN6QztRQUFBLENBQUMsd0JBQWEsQ0FDWjtVQUFBLENBQUMsNEJBQWlCLENBQ2hCOztVQUNGLEVBQUUsNEJBQWlCLENBQ3JCO1FBQUEsRUFBRSx3QkFBYSxDQUNmO1FBQUEsQ0FBQyx3QkFBYSxDQUNaO1VBQUEsQ0FBQyxpQkFBTSxDQUFDLE9BQU8sQ0FBQyxDQUFDLGtCQUFrQixDQUFDLENBQUMsTUFBTSxFQUFFLGlCQUFNLENBQ25EO1VBQUEsQ0FBQyxpQkFBTSxDQUFDLE9BQU8sQ0FBQyxDQUFDLG1CQUFtQixDQUFDLENBQUMsS0FBSyxDQUFDLE9BQU8sQ0FBQyxPQUFPLENBQUMsV0FBVyxDQUNyRTs7VUFDRixFQUFFLGlCQUFNLENBQ1Y7UUFBQSxFQUFFLHdCQUFhLENBQ2pCO01BQUEsRUFBRSxpQkFBTSxDQUNWO0lBQUEsRUFBRSxjQUFHLENBQUMsQ0FDUCxDQUFDO0FBQ0osQ0FBQyxDQUFDO0FBRUYsa0JBQWUsU0FBUyxDQUFDIiwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0IFJlYWN0LCB7IHVzZVN0YXRlLCB1c2VFZmZlY3QgfSBmcm9tICdyZWFjdCc7XG5pbXBvcnQgeyB1c2VOYXZpZ2F0ZSB9IGZyb20gJ3JlYWN0LXJvdXRlci1kb20nO1xuaW1wb3J0IHtcbiAgR3JpZCxcbiAgQ2FyZCxcbiAgQ2FyZENvbnRlbnQsXG4gIFR5cG9ncmFwaHksXG4gIEJveCxcbiAgQ2hpcCxcbiAgSWNvbkJ1dHRvbixcbiAgTGluZWFyUHJvZ3Jlc3MsXG4gIEJ1dHRvbixcbiAgVGFibGUsXG4gIFRhYmxlQm9keSxcbiAgVGFibGVDZWxsLFxuICBUYWJsZUNvbnRhaW5lcixcbiAgVGFibGVIZWFkLFxuICBUYWJsZVJvdyxcbiAgUGFwZXIsXG4gIFRvb2x0aXAsXG4gIEFsZXJ0LFxuICBMaXN0LFxuICBMaXN0SXRlbSxcbiAgTGlzdEl0ZW1JY29uLFxuICBMaXN0SXRlbVRleHQsXG4gIERpYWxvZyxcbiAgRGlhbG9nVGl0bGUsXG4gIERpYWxvZ0NvbnRlbnQsXG4gIERpYWxvZ0NvbnRlbnRUZXh0LFxuICBEaWFsb2dBY3Rpb25zLFxufSBmcm9tICdAbXVpL21hdGVyaWFsJztcbmltcG9ydCB7XG4gIFBsYXlBcnJvdyBhcyBQbGF5SWNvbixcbiAgUmVmcmVzaCBhcyBSZWZyZXNoSWNvbixcbiAgVmlzaWJpbGl0eSBhcyBWaWV3SWNvbixcbiAgRGVsZXRlIGFzIERlbGV0ZUljb24sXG4gIFBzeWNob2xvZ3kgYXMgQUlJY29uLFxuICBDaGVja0NpcmNsZSBhcyBDaGVja0ljb24sXG4gIENhbmNlbCBhcyBFcnJvckljb24sXG4gIEF1dG9Bd2Vzb21lIGFzIFNwYXJrbGVJY29uLFxufSBmcm9tICdAbXVpL2ljb25zLW1hdGVyaWFsJztcbmltcG9ydCB7IFBpZUNoYXJ0LCBQaWUsIENlbGwsIFJlc3BvbnNpdmVDb250YWluZXIsIEJhckNoYXJ0LCBCYXIsIFhBeGlzLCBZQXhpcywgQ2FydGVzaWFuR3JpZCwgTGVnZW5kIH0gZnJvbSAncmVjaGFydHMnO1xuaW1wb3J0IHsgUGlwZWxpbmUsIERhc2hib2FyZFN0YXRzIH0gZnJvbSAnLi4vdHlwZXMnO1xuaW1wb3J0IHsgYXBpU2VydmljZSB9IGZyb20gJy4uL3NlcnZpY2VzL2FwaSc7XG5cbmNvbnN0IERhc2hib2FyZDogUmVhY3QuRkMgPSAoKSA9PiB7XG4gIGNvbnN0IG5hdmlnYXRlID0gdXNlTmF2aWdhdGUoKTtcbiAgY29uc3QgW3BpcGVsaW5lcywgc2V0UGlwZWxpbmVzXSA9IHVzZVN0YXRlPFBpcGVsaW5lW10+KFtdKTtcbiAgY29uc3QgW3N0YXRzLCBzZXRTdGF0c10gPSB1c2VTdGF0ZTxEYXNoYm9hcmRTdGF0cyB8IG51bGw+KG51bGwpO1xuICBjb25zdCBbbG9hZGluZywgc2V0TG9hZGluZ10gPSB1c2VTdGF0ZSh0cnVlKTtcbiAgY29uc3QgW2FpU3RhdHVzLCBzZXRBaVN0YXR1c10gPSB1c2VTdGF0ZTxhbnk+KG51bGwpO1xuICBjb25zdCBbZGVsZXRlRGlhbG9nT3Blbiwgc2V0RGVsZXRlRGlhbG9nT3Blbl0gPSB1c2VTdGF0ZShmYWxzZSk7XG4gIGNvbnN0IFtwaXBlbGluZVRvRGVsZXRlLCBzZXRQaXBlbGluZVRvRGVsZXRlXSA9IHVzZVN0YXRlPHN0cmluZyB8IG51bGw+KG51bGwpO1xuXG4gIHVzZUVmZmVjdCgoKSA9PiB7XG4gICAgbG9hZERhdGEoKTtcbiAgfSwgW10pO1xuXG4gIGNvbnN0IGxvYWREYXRhID0gYXN5bmMgKCkgPT4ge1xuICAgIHNldExvYWRpbmcodHJ1ZSk7XG4gICAgdHJ5IHtcbiAgICAgIC8vIFVzZSByZWFsIEFQSSB0byBnZXQgcGlwZWxpbmVzIGFuZCBzdGF0c1xuICAgICAgY29uc3QgcGlwZWxpbmVzRGF0YSA9IGF3YWl0IGFwaVNlcnZpY2UuZ2V0UGlwZWxpbmVzKCk7XG4gICAgICBjb25zdCBzdGF0c0RhdGEgPSBhd2FpdCBhcGlTZXJ2aWNlLmdldERhc2hib2FyZFN0YXRzKCk7XG4gICAgICBcbiAgICAgIC8vIEdldCBBSS9oZWFsdGggc3RhdHVzXG4gICAgICB0cnkge1xuICAgICAgICBjb25zdCByZXNwb25zZSA9IGF3YWl0IGZldGNoKCdodHRwczovL2NyMWtrajcyMTMuZXhlY3V0ZS1hcGkudXMtZWFzdC0yLmFtYXpvbmF3cy5jb20vcHJvZC9oZWFsdGgnKTtcbiAgICAgICAgY29uc3QgaGVhbHRoRGF0YSA9IGF3YWl0IHJlc3BvbnNlLmpzb24oKTtcbiAgICAgICAgc2V0QWlTdGF0dXMoaGVhbHRoRGF0YSk7XG4gICAgICB9IGNhdGNoIChlKSB7XG4gICAgICAgIGNvbnNvbGUuZXJyb3IoJ0NvdWxkIG5vdCBmZXRjaCBBSSBzdGF0dXM6JywgZSk7XG4gICAgICB9XG4gICAgICBcbiAgICAgIHNldFBpcGVsaW5lcyhwaXBlbGluZXNEYXRhKTtcbiAgICAgIHNldFN0YXRzKHN0YXRzRGF0YSk7XG4gICAgfSBjYXRjaCAoZXJyb3IpIHtcbiAgICAgIGNvbnNvbGUuZXJyb3IoJ0Vycm9yIGxvYWRpbmcgZGFzaGJvYXJkIGRhdGE6JywgZXJyb3IpO1xuICAgIH0gZmluYWxseSB7XG4gICAgICBzZXRMb2FkaW5nKGZhbHNlKTtcbiAgICB9XG4gIH07XG5cbiAgY29uc3QgaGFuZGxlRXhlY3V0ZVBpcGVsaW5lID0gYXN5bmMgKHBpcGVsaW5lSWQ6IHN0cmluZykgPT4ge1xuICAgIHRyeSB7XG4gICAgICBhd2FpdCBhcGlTZXJ2aWNlLmV4ZWN1dGVQaXBlbGluZShwaXBlbGluZUlkKTtcbiAgICAgIGxvYWREYXRhKCk7IC8vIFJlZnJlc2ggZGF0YVxuICAgIH0gY2F0Y2ggKGVycm9yKSB7XG4gICAgICBjb25zb2xlLmVycm9yKCdFcnJvciBleGVjdXRpbmcgcGlwZWxpbmU6JywgZXJyb3IpO1xuICAgIH1cbiAgfTtcblxuICBjb25zdCBoYW5kbGVWaWV3UGlwZWxpbmUgPSAocGlwZWxpbmVJZDogc3RyaW5nKSA9PiB7XG4gICAgLy8gTmF2aWdhdGUgdG8gbW9uaXRvciBwYWdlIHdpdGggdGhpcyBwaXBlbGluZSBzZWxlY3RlZFxuICAgIG5hdmlnYXRlKCcvbW9uaXRvcicpO1xuICB9O1xuXG4gIGNvbnN0IGhhbmRsZURlbGV0ZUNsaWNrID0gKHBpcGVsaW5lSWQ6IHN0cmluZykgPT4ge1xuICAgIHNldFBpcGVsaW5lVG9EZWxldGUocGlwZWxpbmVJZCk7XG4gICAgc2V0RGVsZXRlRGlhbG9nT3Blbih0cnVlKTtcbiAgfTtcblxuICBjb25zdCBoYW5kbGVEZWxldGVDb25maXJtID0gYXN5bmMgKCkgPT4ge1xuICAgIGlmIChwaXBlbGluZVRvRGVsZXRlKSB7XG4gICAgICB0cnkge1xuICAgICAgICBhd2FpdCBhcGlTZXJ2aWNlLmRlbGV0ZVBpcGVsaW5lKHBpcGVsaW5lVG9EZWxldGUpO1xuICAgICAgICBsb2FkRGF0YSgpOyAvLyBSZWZyZXNoIGRhdGFcbiAgICAgIH0gY2F0Y2ggKGVycm9yKSB7XG4gICAgICAgIGNvbnNvbGUuZXJyb3IoJ0Vycm9yIGRlbGV0aW5nIHBpcGVsaW5lOicsIGVycm9yKTtcbiAgICAgIH1cbiAgICB9XG4gICAgc2V0RGVsZXRlRGlhbG9nT3BlbihmYWxzZSk7XG4gICAgc2V0UGlwZWxpbmVUb0RlbGV0ZShudWxsKTtcbiAgfTtcblxuICBjb25zdCBoYW5kbGVEZWxldGVDYW5jZWwgPSAoKSA9PiB7XG4gICAgc2V0RGVsZXRlRGlhbG9nT3BlbihmYWxzZSk7XG4gICAgc2V0UGlwZWxpbmVUb0RlbGV0ZShudWxsKTtcbiAgfTtcblxuICBjb25zdCBnZXRTdGF0dXNDb2xvciA9IChzdGF0dXM6IFBpcGVsaW5lWydzdGF0dXMnXSkgPT4ge1xuICAgIHN3aXRjaCAoc3RhdHVzKSB7XG4gICAgICBjYXNlICdjb21wbGV0ZWQnOlxuICAgICAgICByZXR1cm4gJ3N1Y2Nlc3MnO1xuICAgICAgY2FzZSAncnVubmluZyc6XG4gICAgICAgIHJldHVybiAncHJpbWFyeSc7XG4gICAgICBjYXNlICdmYWlsZWQnOlxuICAgICAgICByZXR1cm4gJ2Vycm9yJztcbiAgICAgIGRlZmF1bHQ6XG4gICAgICAgIHJldHVybiAnZGVmYXVsdCc7XG4gICAgfVxuICB9O1xuXG4gIGNvbnN0IGdldFN0YXR1c0NoYXJ0RGF0YSA9ICgpID0+IHtcbiAgICBjb25zdCBzdGF0dXNDb3VudHMgPSBwaXBlbGluZXMucmVkdWNlKChhY2MsIHBpcGVsaW5lKSA9PiB7XG4gICAgICBhY2NbcGlwZWxpbmUuc3RhdHVzXSA9IChhY2NbcGlwZWxpbmUuc3RhdHVzXSB8fCAwKSArIDE7XG4gICAgICByZXR1cm4gYWNjO1xuICAgIH0sIHt9IGFzIFJlY29yZDxzdHJpbmcsIG51bWJlcj4pO1xuXG4gICAgcmV0dXJuIFtcbiAgICAgIHsgbmFtZTogJ0NvbXBsZXRlZCcsIHZhbHVlOiBzdGF0dXNDb3VudHMuY29tcGxldGVkIHx8IDAsIGNvbG9yOiAnIzRjYWY1MCcgfSxcbiAgICAgIHsgbmFtZTogJ1J1bm5pbmcnLCB2YWx1ZTogc3RhdHVzQ291bnRzLnJ1bm5pbmcgfHwgMCwgY29sb3I6ICcjMjE5NmYzJyB9LFxuICAgICAgeyBuYW1lOiAnRmFpbGVkJywgdmFsdWU6IHN0YXR1c0NvdW50cy5mYWlsZWQgfHwgMCwgY29sb3I6ICcjZjQ0MzM2JyB9LFxuICAgICAgeyBuYW1lOiAnUGVuZGluZycsIHZhbHVlOiBzdGF0dXNDb3VudHMucGVuZGluZyB8fCAwLCBjb2xvcjogJyNmZjk4MDAnIH0sXG4gICAgXTtcbiAgfTtcblxuICBjb25zdCBnZXRUeXBlQ2hhcnREYXRhID0gKCkgPT4ge1xuICAgIGNvbnN0IHR5cGVDb3VudHMgPSBwaXBlbGluZXMucmVkdWNlKChhY2MsIHBpcGVsaW5lKSA9PiB7XG4gICAgICBhY2NbcGlwZWxpbmUudHlwZV0gPSAoYWNjW3BpcGVsaW5lLnR5cGVdIHx8IDApICsgMTtcbiAgICAgIHJldHVybiBhY2M7XG4gICAgfSwge30gYXMgUmVjb3JkPHN0cmluZywgbnVtYmVyPik7XG5cbiAgICByZXR1cm4gT2JqZWN0LmVudHJpZXModHlwZUNvdW50cykubWFwKChbbmFtZSwgdmFsdWVdKSA9PiAoeyBuYW1lLCB2YWx1ZSB9KSk7XG4gIH07XG5cbiAgaWYgKGxvYWRpbmcpIHtcbiAgICByZXR1cm4gKFxuICAgICAgPEJveCBzeD17eyBwOiAzIH19PlxuICAgICAgICA8VHlwb2dyYXBoeSB2YXJpYW50PVwiaDRcIiBndXR0ZXJCb3R0b20+XG4gICAgICAgICAgRGFzaGJvYXJkXG4gICAgICAgIDwvVHlwb2dyYXBoeT5cbiAgICAgICAgPExpbmVhclByb2dyZXNzIC8+XG4gICAgICA8L0JveD5cbiAgICApO1xuICB9XG5cbiAgcmV0dXJuIChcbiAgICA8Qm94IHN4PXt7IHA6IDMgfX0+XG4gICAgICA8Qm94IHN4PXt7IGRpc3BsYXk6ICdmbGV4JywganVzdGlmeUNvbnRlbnQ6ICdzcGFjZS1iZXR3ZWVuJywgYWxpZ25JdGVtczogJ2NlbnRlcicsIG1iOiAzIH19PlxuICAgICAgICA8VHlwb2dyYXBoeSB2YXJpYW50PVwiaDRcIiBndXR0ZXJCb3R0b20+XG4gICAgICAgICAgRGFzaGJvYXJkXG4gICAgICAgIDwvVHlwb2dyYXBoeT5cbiAgICAgICAgPEJ1dHRvblxuICAgICAgICAgIHZhcmlhbnQ9XCJvdXRsaW5lZFwiXG4gICAgICAgICAgc3RhcnRJY29uPXs8UmVmcmVzaEljb24gLz59XG4gICAgICAgICAgb25DbGljaz17bG9hZERhdGF9XG4gICAgICAgID5cbiAgICAgICAgICBSZWZyZXNoXG4gICAgICAgIDwvQnV0dG9uPlxuICAgICAgPC9Cb3g+XG5cbiAgICAgIHsvKiBTdGF0cyBDYXJkcyAqL31cbiAgICAgIDxHcmlkIGNvbnRhaW5lciBzcGFjaW5nPXszfSBzeD17eyBtYjogNCB9fT5cbiAgICAgICAgPEdyaWQgc2l6ZT17eyB4czogMTIsIHNtOiA2LCBtZDogMyB9fT5cbiAgICAgICAgICA8Q2FyZD5cbiAgICAgICAgICAgIDxDYXJkQ29udGVudD5cbiAgICAgICAgICAgICAgPFR5cG9ncmFwaHkgY29sb3I9XCJ0ZXh0U2Vjb25kYXJ5XCIgZ3V0dGVyQm90dG9tPlxuICAgICAgICAgICAgICAgIFRvdGFsIFBpcGVsaW5lc1xuICAgICAgICAgICAgICA8L1R5cG9ncmFwaHk+XG4gICAgICAgICAgICAgIDxUeXBvZ3JhcGh5IHZhcmlhbnQ9XCJoNVwiIGNvbXBvbmVudD1cImgyXCI+XG4gICAgICAgICAgICAgICAge3BpcGVsaW5lcy5sZW5ndGh9XG4gICAgICAgICAgICAgIDwvVHlwb2dyYXBoeT5cbiAgICAgICAgICAgIDwvQ2FyZENvbnRlbnQ+XG4gICAgICAgICAgPC9DYXJkPlxuICAgICAgICA8L0dyaWQ+XG4gICAgICAgIDxHcmlkIHNpemU9e3sgeHM6IDEyLCBzbTogNiwgbWQ6IDMgfX0+XG4gICAgICAgICAgPENhcmQ+XG4gICAgICAgICAgICA8Q2FyZENvbnRlbnQ+XG4gICAgICAgICAgICAgIDxUeXBvZ3JhcGh5IGNvbG9yPVwidGV4dFNlY29uZGFyeVwiIGd1dHRlckJvdHRvbT5cbiAgICAgICAgICAgICAgICBSdW5uaW5nIFBpcGVsaW5lc1xuICAgICAgICAgICAgICA8L1R5cG9ncmFwaHk+XG4gICAgICAgICAgICAgIDxUeXBvZ3JhcGh5IHZhcmlhbnQ9XCJoNVwiIGNvbXBvbmVudD1cImgyXCIgY29sb3I9XCJwcmltYXJ5XCI+XG4gICAgICAgICAgICAgICAge3BpcGVsaW5lcy5maWx0ZXIocCA9PiBwLnN0YXR1cyA9PT0gJ3J1bm5pbmcnKS5sZW5ndGh9XG4gICAgICAgICAgICAgIDwvVHlwb2dyYXBoeT5cbiAgICAgICAgICAgIDwvQ2FyZENvbnRlbnQ+XG4gICAgICAgICAgPC9DYXJkPlxuICAgICAgICA8L0dyaWQ+XG4gICAgICAgIDxHcmlkIHNpemU9e3sgeHM6IDEyLCBzbTogNiwgbWQ6IDMgfX0+XG4gICAgICAgICAgPENhcmQ+XG4gICAgICAgICAgICA8Q2FyZENvbnRlbnQ+XG4gICAgICAgICAgICAgIDxUeXBvZ3JhcGh5IGNvbG9yPVwidGV4dFNlY29uZGFyeVwiIGd1dHRlckJvdHRvbT5cbiAgICAgICAgICAgICAgICBTdWNjZXNzIFJhdGVcbiAgICAgICAgICAgICAgPC9UeXBvZ3JhcGh5PlxuICAgICAgICAgICAgICA8VHlwb2dyYXBoeSB2YXJpYW50PVwiaDVcIiBjb21wb25lbnQ9XCJoMlwiIGNvbG9yPVwic3VjY2Vzcy5tYWluXCI+XG4gICAgICAgICAgICAgICAge3BpcGVsaW5lcy5sZW5ndGggPiAwIFxuICAgICAgICAgICAgICAgICAgPyBNYXRoLnJvdW5kKChwaXBlbGluZXMuZmlsdGVyKHAgPT4gcC5zdGF0dXMgPT09ICdjb21wbGV0ZWQnKS5sZW5ndGggLyBwaXBlbGluZXMubGVuZ3RoKSAqIDEwMClcbiAgICAgICAgICAgICAgICAgIDogMH0lXG4gICAgICAgICAgICAgIDwvVHlwb2dyYXBoeT5cbiAgICAgICAgICAgIDwvQ2FyZENvbnRlbnQ+XG4gICAgICAgICAgPC9DYXJkPlxuICAgICAgICA8L0dyaWQ+XG4gICAgICAgIDxHcmlkIHNpemU9e3sgeHM6IDEyLCBzbTogNiwgbWQ6IDMgfX0+XG4gICAgICAgICAgPENhcmQ+XG4gICAgICAgICAgICA8Q2FyZENvbnRlbnQ+XG4gICAgICAgICAgICAgIDxUeXBvZ3JhcGh5IGNvbG9yPVwidGV4dFNlY29uZGFyeVwiIGd1dHRlckJvdHRvbT5cbiAgICAgICAgICAgICAgICBBdmcuIEFjY3VyYWN5XG4gICAgICAgICAgICAgIDwvVHlwb2dyYXBoeT5cbiAgICAgICAgICAgICAgPFR5cG9ncmFwaHkgdmFyaWFudD1cImg1XCIgY29tcG9uZW50PVwiaDJcIj5cbiAgICAgICAgICAgICAgICB7cGlwZWxpbmVzLmZpbHRlcihwID0+IHAuYWNjdXJhY3kpLmxlbmd0aCA+IDBcbiAgICAgICAgICAgICAgICAgID8gTWF0aC5yb3VuZCgocGlwZWxpbmVzLmZpbHRlcihwID0+IHAuYWNjdXJhY3kpLnJlZHVjZSgoc3VtLCBwKSA9PiBzdW0gKyAocC5hY2N1cmFjeSB8fCAwKSwgMCkgLyBwaXBlbGluZXMuZmlsdGVyKHAgPT4gcC5hY2N1cmFjeSkubGVuZ3RoKSAqIDEwMClcbiAgICAgICAgICAgICAgICAgIDogMH0lXG4gICAgICAgICAgICAgIDwvVHlwb2dyYXBoeT5cbiAgICAgICAgICAgIDwvQ2FyZENvbnRlbnQ+XG4gICAgICAgICAgPC9DYXJkPlxuICAgICAgICA8L0dyaWQ+XG4gICAgICA8L0dyaWQ+XG5cbiAgICAgIHsvKiBBSSBDYXBhYmlsaXRpZXMgU3RhdHVzIENhcmQgKi99XG4gICAgICB7YWlTdGF0dXMgJiYgKFxuICAgICAgICA8Q2FyZCBzeD17eyBtYjogNCwgYmFja2dyb3VuZDogJ2xpbmVhci1ncmFkaWVudCgxMzVkZWcsICM2NjdlZWEgMCUsICM3NjRiYTIgMTAwJSknIH19PlxuICAgICAgICAgIDxDYXJkQ29udGVudD5cbiAgICAgICAgICAgIDxCb3ggc3g9e3sgZGlzcGxheTogJ2ZsZXgnLCBhbGlnbkl0ZW1zOiAnY2VudGVyJywgbWI6IDIgfX0+XG4gICAgICAgICAgICAgIDxBSUljb24gc3g9e3sgZm9udFNpemU6IDQwLCBjb2xvcjogJ3doaXRlJywgbXI6IDIgfX0gLz5cbiAgICAgICAgICAgICAgPEJveD5cbiAgICAgICAgICAgICAgICA8VHlwb2dyYXBoeSB2YXJpYW50PVwiaDVcIiBzeD17eyBjb2xvcjogJ3doaXRlJywgZm9udFdlaWdodDogJ2JvbGQnIH19PlxuICAgICAgICAgICAgICAgICAg8J+kliBBRFBBIEFnZW50aWMgQUkgU3lzdGVtXG4gICAgICAgICAgICAgICAgPC9UeXBvZ3JhcGh5PlxuICAgICAgICAgICAgICAgIDxUeXBvZ3JhcGh5IHZhcmlhbnQ9XCJib2R5MlwiIHN4PXt7IGNvbG9yOiAncmdiYSgyNTUsMjU1LDI1NSwwLjgpJyB9fT5cbiAgICAgICAgICAgICAgICAgIFZlcnNpb24ge2FpU3RhdHVzLnZlcnNpb24gfHwgJzQuMC4wLWFnZW50aWMnfSB8IFBvd2VyZWQgYnkgQW1hem9uIEJlZHJvY2tcbiAgICAgICAgICAgICAgICA8L1R5cG9ncmFwaHk+XG4gICAgICAgICAgICAgIDwvQm94PlxuICAgICAgICAgICAgICA8Q2hpcCBcbiAgICAgICAgICAgICAgICBsYWJlbD17YWlTdGF0dXMuc3RhdHVzID09PSAnaGVhbHRoeScgPyAn4pePIE9ubGluZScgOiAn4peLIERlZ3JhZGVkJ30gXG4gICAgICAgICAgICAgICAgc3g9e3sgXG4gICAgICAgICAgICAgICAgICBtbDogJ2F1dG8nLCBcbiAgICAgICAgICAgICAgICAgIGJnY29sb3I6IGFpU3RhdHVzLnN0YXR1cyA9PT0gJ2hlYWx0aHknID8gJyM0Y2FmNTAnIDogJyNmZjk4MDAnLFxuICAgICAgICAgICAgICAgICAgY29sb3I6ICd3aGl0ZScsXG4gICAgICAgICAgICAgICAgICBmb250V2VpZ2h0OiAnYm9sZCdcbiAgICAgICAgICAgICAgICB9fSBcbiAgICAgICAgICAgICAgLz5cbiAgICAgICAgICAgIDwvQm94PlxuICAgICAgICAgICAgXG4gICAgICAgICAgICA8R3JpZCBjb250YWluZXIgc3BhY2luZz17Mn0+XG4gICAgICAgICAgICAgIHsvKiBDb21wb25lbnRzIFN0YXR1cyAqL31cbiAgICAgICAgICAgICAgPEdyaWQgc2l6ZT17eyB4czogMTIsIG1kOiA0IH19PlxuICAgICAgICAgICAgICAgIDxQYXBlciBzeD17eyBwOiAyLCBiZ2NvbG9yOiAncmdiYSgyNTUsMjU1LDI1NSwwLjEpJyB9fT5cbiAgICAgICAgICAgICAgICAgIDxUeXBvZ3JhcGh5IHZhcmlhbnQ9XCJzdWJ0aXRsZTJcIiBzeD17eyBjb2xvcjogJ3doaXRlJywgbWI6IDEgfX0+XG4gICAgICAgICAgICAgICAgICAgIFN5c3RlbSBDb21wb25lbnRzXG4gICAgICAgICAgICAgICAgICA8L1R5cG9ncmFwaHk+XG4gICAgICAgICAgICAgICAgICA8TGlzdCBkZW5zZT5cbiAgICAgICAgICAgICAgICAgICAge2FpU3RhdHVzLmNvbXBvbmVudHMgJiYgT2JqZWN0LmVudHJpZXMoYWlTdGF0dXMuY29tcG9uZW50cykubWFwKChba2V5LCB2YWx1ZV0pID0+IChcbiAgICAgICAgICAgICAgICAgICAgICA8TGlzdEl0ZW0ga2V5PXtrZXl9IHN4PXt7IHB5OiAwIH19PlxuICAgICAgICAgICAgICAgICAgICAgICAgPExpc3RJdGVtSWNvbiBzeD17eyBtaW5XaWR0aDogMzIgfX0+XG4gICAgICAgICAgICAgICAgICAgICAgICAgIHt2YWx1ZSA/IDxDaGVja0ljb24gc3g9e3sgY29sb3I6ICcjNGNhZjUwJywgZm9udFNpemU6IDE4IH19IC8+IDogPEVycm9ySWNvbiBzeD17eyBjb2xvcjogJyNmNDQzMzYnLCBmb250U2l6ZTogMTggfX0gLz59XG4gICAgICAgICAgICAgICAgICAgICAgICA8L0xpc3RJdGVtSWNvbj5cbiAgICAgICAgICAgICAgICAgICAgICAgIDxMaXN0SXRlbVRleHQgXG4gICAgICAgICAgICAgICAgICAgICAgICAgIHByaW1hcnk9e2tleS5yZXBsYWNlKCdfJywgJyAnKS50b1VwcGVyQ2FzZSgpfSBcbiAgICAgICAgICAgICAgICAgICAgICAgICAgcHJpbWFyeVR5cG9ncmFwaHlQcm9wcz17eyBzeDogeyBjb2xvcjogJ3doaXRlJywgZm9udFNpemU6ICcwLjg1cmVtJyB9IH19XG4gICAgICAgICAgICAgICAgICAgICAgICAvPlxuICAgICAgICAgICAgICAgICAgICAgIDwvTGlzdEl0ZW0+XG4gICAgICAgICAgICAgICAgICAgICkpfVxuICAgICAgICAgICAgICAgICAgPC9MaXN0PlxuICAgICAgICAgICAgICAgIDwvUGFwZXI+XG4gICAgICAgICAgICAgIDwvR3JpZD5cbiAgICAgICAgICAgICAgXG4gICAgICAgICAgICAgIHsvKiBBSSBDYXBhYmlsaXRpZXMgKi99XG4gICAgICAgICAgICAgIDxHcmlkIHNpemU9e3sgeHM6IDEyLCBtZDogOCB9fT5cbiAgICAgICAgICAgICAgICA8UGFwZXIgc3g9e3sgcDogMiwgYmdjb2xvcjogJ3JnYmEoMjU1LDI1NSwyNTUsMC4xKScgfX0+XG4gICAgICAgICAgICAgICAgICA8VHlwb2dyYXBoeSB2YXJpYW50PVwic3VidGl0bGUyXCIgc3g9e3sgY29sb3I6ICd3aGl0ZScsIG1iOiAxIH19PlxuICAgICAgICAgICAgICAgICAgICA8U3BhcmtsZUljb24gc3g9e3sgZm9udFNpemU6IDE2LCBtcjogMC41LCB2ZXJ0aWNhbEFsaWduOiAnbWlkZGxlJyB9fSAvPlxuICAgICAgICAgICAgICAgICAgICBBSSBDYXBhYmlsaXRpZXMgKEFtYXpvbiBCZWRyb2NrIENsYXVkZSAzLjUpXG4gICAgICAgICAgICAgICAgICA8L1R5cG9ncmFwaHk+XG4gICAgICAgICAgICAgICAgICA8R3JpZCBjb250YWluZXIgc3BhY2luZz17MX0+XG4gICAgICAgICAgICAgICAgICAgIHthaVN0YXR1cy5haV9jYXBhYmlsaXRpZXM/LmFnZW50aWNfZmVhdHVyZXM/Lm1hcCgoZmVhdHVyZTogc3RyaW5nLCBpbmRleDogbnVtYmVyKSA9PiAoXG4gICAgICAgICAgICAgICAgICAgICAgPEdyaWQga2V5PXtpbmRleH0gc2l6ZT17eyB4czogNiB9fT5cbiAgICAgICAgICAgICAgICAgICAgICAgIDxDaGlwXG4gICAgICAgICAgICAgICAgICAgICAgICAgIGljb249ezxDaGVja0ljb24gc3g9e3sgY29sb3I6ICd3aGl0ZSAhaW1wb3J0YW50JyB9fSAvPn1cbiAgICAgICAgICAgICAgICAgICAgICAgICAgbGFiZWw9e2ZlYXR1cmUucmVwbGFjZSgvXy9nLCAnICcpfVxuICAgICAgICAgICAgICAgICAgICAgICAgICBzaXplPVwic21hbGxcIlxuICAgICAgICAgICAgICAgICAgICAgICAgICBzeD17eyBcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICBiZ2NvbG9yOiAncmdiYSgyNTUsMjU1LDI1NSwwLjIpJywgXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgY29sb3I6ICd3aGl0ZScsXG4gICAgICAgICAgICAgICAgICAgICAgICAgICAgZm9udFNpemU6ICcwLjc1cmVtJyxcbiAgICAgICAgICAgICAgICAgICAgICAgICAgICAnJiAuTXVpQ2hpcC1pY29uJzogeyBjb2xvcjogJ3doaXRlJyB9XG4gICAgICAgICAgICAgICAgICAgICAgICAgIH19XG4gICAgICAgICAgICAgICAgICAgICAgICAvPlxuICAgICAgICAgICAgICAgICAgICAgIDwvR3JpZD5cbiAgICAgICAgICAgICAgICAgICAgKSl9XG4gICAgICAgICAgICAgICAgICA8L0dyaWQ+XG4gICAgICAgICAgICAgICAgICB7YWlTdGF0dXMuYWlfY2FwYWJpbGl0aWVzPy5iZWRyb2NrX2VuYWJsZWQgJiYgKFxuICAgICAgICAgICAgICAgICAgICA8QWxlcnQgc2V2ZXJpdHk9XCJzdWNjZXNzXCIgc3g9e3sgbXQ6IDIsIGJnY29sb3I6ICdyZ2JhKDc2LCAxNzUsIDgwLCAwLjIpJywgY29sb3I6ICd3aGl0ZScgfX0+XG4gICAgICAgICAgICAgICAgICAgICAgPHN0cm9uZz5CZWRyb2NrIEFJIEVuYWJsZWQ6PC9zdHJvbmc+IFBpcGVsaW5lcyB1c2UgaW50ZWxsaWdlbnQgTkwgdW5kZXJzdGFuZGluZywgZGF0YXNldCBhbmFseXNpcywgYW5kIEFJLXBvd2VyZWQgcGxhbm5pbmdcbiAgICAgICAgICAgICAgICAgICAgPC9BbGVydD5cbiAgICAgICAgICAgICAgICAgICl9XG4gICAgICAgICAgICAgICAgPC9QYXBlcj5cbiAgICAgICAgICAgICAgPC9HcmlkPlxuICAgICAgICAgICAgPC9HcmlkPlxuICAgICAgICAgIDwvQ2FyZENvbnRlbnQ+XG4gICAgICAgIDwvQ2FyZD5cbiAgICAgICl9XG5cbiAgICAgIHsvKiBDaGFydHMgKi99XG4gICAgICA8R3JpZCBjb250YWluZXIgc3BhY2luZz17M30gc3g9e3sgbWI6IDQgfX0+XG4gICAgICAgIDxHcmlkIHNpemU9e3sgeHM6IDEyLCBtZDogNiB9fT5cbiAgICAgICAgICA8Q2FyZD5cbiAgICAgICAgICAgIDxDYXJkQ29udGVudD5cbiAgICAgICAgICAgICAgPFR5cG9ncmFwaHkgdmFyaWFudD1cImg2XCIgZ3V0dGVyQm90dG9tPlxuICAgICAgICAgICAgICAgIFBpcGVsaW5lIFN0YXR1cyBEaXN0cmlidXRpb25cbiAgICAgICAgICAgICAgPC9UeXBvZ3JhcGh5PlxuICAgICAgICAgICAgICA8UmVzcG9uc2l2ZUNvbnRhaW5lciB3aWR0aD1cIjEwMCVcIiBoZWlnaHQ9ezMwMH0+XG4gICAgICAgICAgICAgICAgPFBpZUNoYXJ0PlxuICAgICAgICAgICAgICAgICAgPFBpZVxuICAgICAgICAgICAgICAgICAgICBkYXRhPXtnZXRTdGF0dXNDaGFydERhdGEoKX1cbiAgICAgICAgICAgICAgICAgICAgY3g9XCI1MCVcIlxuICAgICAgICAgICAgICAgICAgICBjeT1cIjUwJVwiXG4gICAgICAgICAgICAgICAgICAgIGxhYmVsTGluZT17ZmFsc2V9XG4gICAgICAgICAgICAgICAgICAgIGxhYmVsPXsoeyBuYW1lLCB2YWx1ZSB9KSA9PiBgJHtuYW1lfTogJHt2YWx1ZX1gfVxuICAgICAgICAgICAgICAgICAgICBvdXRlclJhZGl1cz17ODB9XG4gICAgICAgICAgICAgICAgICAgIGZpbGw9XCIjODg4NGQ4XCJcbiAgICAgICAgICAgICAgICAgICAgZGF0YUtleT1cInZhbHVlXCJcbiAgICAgICAgICAgICAgICAgID5cbiAgICAgICAgICAgICAgICAgICAge2dldFN0YXR1c0NoYXJ0RGF0YSgpLm1hcCgoZW50cnksIGluZGV4KSA9PiAoXG4gICAgICAgICAgICAgICAgICAgICAgPENlbGwga2V5PXtgY2VsbC0ke2luZGV4fWB9IGZpbGw9e2VudHJ5LmNvbG9yfSAvPlxuICAgICAgICAgICAgICAgICAgICApKX1cbiAgICAgICAgICAgICAgICAgIDwvUGllPlxuICAgICAgICAgICAgICAgIDwvUGllQ2hhcnQ+XG4gICAgICAgICAgICAgIDwvUmVzcG9uc2l2ZUNvbnRhaW5lcj5cbiAgICAgICAgICAgIDwvQ2FyZENvbnRlbnQ+XG4gICAgICAgICAgPC9DYXJkPlxuICAgICAgICA8L0dyaWQ+XG4gICAgICAgIDxHcmlkIHNpemU9e3sgeHM6IDEyLCBtZDogNiB9fT5cbiAgICAgICAgICA8Q2FyZD5cbiAgICAgICAgICAgIDxDYXJkQ29udGVudD5cbiAgICAgICAgICAgICAgPFR5cG9ncmFwaHkgdmFyaWFudD1cImg2XCIgZ3V0dGVyQm90dG9tPlxuICAgICAgICAgICAgICAgIFBpcGVsaW5lIFR5cGVzXG4gICAgICAgICAgICAgIDwvVHlwb2dyYXBoeT5cbiAgICAgICAgICAgICAgPFJlc3BvbnNpdmVDb250YWluZXIgd2lkdGg9XCIxMDAlXCIgaGVpZ2h0PXszMDB9PlxuICAgICAgICAgICAgICAgIDxCYXJDaGFydCBkYXRhPXtnZXRUeXBlQ2hhcnREYXRhKCl9PlxuICAgICAgICAgICAgICAgICAgPENhcnRlc2lhbkdyaWQgc3Ryb2tlRGFzaGFycmF5PVwiMyAzXCIgLz5cbiAgICAgICAgICAgICAgICAgIDxYQXhpcyBkYXRhS2V5PVwibmFtZVwiIC8+XG4gICAgICAgICAgICAgICAgICA8WUF4aXMgLz5cbiAgICAgICAgICAgICAgICAgIDxMZWdlbmQgLz5cbiAgICAgICAgICAgICAgICAgIDxCYXIgZGF0YUtleT1cInZhbHVlXCIgZmlsbD1cIiMxOTc2ZDJcIiAvPlxuICAgICAgICAgICAgICAgIDwvQmFyQ2hhcnQ+XG4gICAgICAgICAgICAgIDwvUmVzcG9uc2l2ZUNvbnRhaW5lcj5cbiAgICAgICAgICAgIDwvQ2FyZENvbnRlbnQ+XG4gICAgICAgICAgPC9DYXJkPlxuICAgICAgICA8L0dyaWQ+XG4gICAgICA8L0dyaWQ+XG5cbiAgICAgIHsvKiBSZWNlbnQgUGlwZWxpbmVzIFRhYmxlICovfVxuICAgICAgPENhcmQ+XG4gICAgICAgIDxDYXJkQ29udGVudD5cbiAgICAgICAgICA8VHlwb2dyYXBoeSB2YXJpYW50PVwiaDZcIiBndXR0ZXJCb3R0b20+XG4gICAgICAgICAgICBSZWNlbnQgUGlwZWxpbmVzXG4gICAgICAgICAgPC9UeXBvZ3JhcGh5PlxuICAgICAgICAgIDxUYWJsZUNvbnRhaW5lciBjb21wb25lbnQ9e1BhcGVyfT5cbiAgICAgICAgICAgIDxUYWJsZT5cbiAgICAgICAgICAgICAgPFRhYmxlSGVhZD5cbiAgICAgICAgICAgICAgICA8VGFibGVSb3c+XG4gICAgICAgICAgICAgICAgICA8VGFibGVDZWxsPk5hbWU8L1RhYmxlQ2VsbD5cbiAgICAgICAgICAgICAgICAgIDxUYWJsZUNlbGw+VHlwZTwvVGFibGVDZWxsPlxuICAgICAgICAgICAgICAgICAgPFRhYmxlQ2VsbD5TdGF0dXM8L1RhYmxlQ2VsbD5cbiAgICAgICAgICAgICAgICAgIDxUYWJsZUNlbGw+UHJvZ3Jlc3M8L1RhYmxlQ2VsbD5cbiAgICAgICAgICAgICAgICAgIDxUYWJsZUNlbGw+QWNjdXJhY3k8L1RhYmxlQ2VsbD5cbiAgICAgICAgICAgICAgICAgIDxUYWJsZUNlbGw+Q3JlYXRlZDwvVGFibGVDZWxsPlxuICAgICAgICAgICAgICAgICAgPFRhYmxlQ2VsbD5BY3Rpb25zPC9UYWJsZUNlbGw+XG4gICAgICAgICAgICAgICAgPC9UYWJsZVJvdz5cbiAgICAgICAgICAgICAgPC9UYWJsZUhlYWQ+XG4gICAgICAgICAgICAgIDxUYWJsZUJvZHk+XG4gICAgICAgICAgICAgICAge3BpcGVsaW5lcy5tYXAoKHBpcGVsaW5lKSA9PiAoXG4gICAgICAgICAgICAgICAgICA8VGFibGVSb3cga2V5PXtwaXBlbGluZS5pZH0+XG4gICAgICAgICAgICAgICAgICAgIDxUYWJsZUNlbGw+XG4gICAgICAgICAgICAgICAgICAgICAgPFR5cG9ncmFwaHkgdmFyaWFudD1cInN1YnRpdGxlMlwiPntwaXBlbGluZS5uYW1lfTwvVHlwb2dyYXBoeT5cbiAgICAgICAgICAgICAgICAgICAgICA8VHlwb2dyYXBoeSB2YXJpYW50PVwiYm9keTJcIiBjb2xvcj1cInRleHRTZWNvbmRhcnlcIj5cbiAgICAgICAgICAgICAgICAgICAgICAgIHtwaXBlbGluZS5kZXNjcmlwdGlvbn1cbiAgICAgICAgICAgICAgICAgICAgICA8L1R5cG9ncmFwaHk+XG4gICAgICAgICAgICAgICAgICAgIDwvVGFibGVDZWxsPlxuICAgICAgICAgICAgICAgICAgICA8VGFibGVDZWxsPlxuICAgICAgICAgICAgICAgICAgICAgIDxDaGlwXG4gICAgICAgICAgICAgICAgICAgICAgICBsYWJlbD17cGlwZWxpbmUudHlwZS5yZXBsYWNlKCdfJywgJyAnKX1cbiAgICAgICAgICAgICAgICAgICAgICAgIHNpemU9XCJzbWFsbFwiXG4gICAgICAgICAgICAgICAgICAgICAgICB2YXJpYW50PVwib3V0bGluZWRcIlxuICAgICAgICAgICAgICAgICAgICAgIC8+XG4gICAgICAgICAgICAgICAgICAgIDwvVGFibGVDZWxsPlxuICAgICAgICAgICAgICAgICAgICA8VGFibGVDZWxsPlxuICAgICAgICAgICAgICAgICAgICAgIDxDaGlwXG4gICAgICAgICAgICAgICAgICAgICAgICBsYWJlbD17cGlwZWxpbmUuc3RhdHVzfVxuICAgICAgICAgICAgICAgICAgICAgICAgY29sb3I9e2dldFN0YXR1c0NvbG9yKHBpcGVsaW5lLnN0YXR1cyl9XG4gICAgICAgICAgICAgICAgICAgICAgICBzaXplPVwic21hbGxcIlxuICAgICAgICAgICAgICAgICAgICAgIC8+XG4gICAgICAgICAgICAgICAgICAgIDwvVGFibGVDZWxsPlxuICAgICAgICAgICAgICAgICAgICA8VGFibGVDZWxsPlxuICAgICAgICAgICAgICAgICAgICAgIDxCb3ggc3g9e3sgd2lkdGg6ICcxMDBweCcgfX0+XG4gICAgICAgICAgICAgICAgICAgICAgICA8TGluZWFyUHJvZ3Jlc3MgXG4gICAgICAgICAgICAgICAgICAgICAgICAgIHZhcmlhbnQ9XCJkZXRlcm1pbmF0ZVwiIFxuICAgICAgICAgICAgICAgICAgICAgICAgICB2YWx1ZT17cGlwZWxpbmUucHJvZ3Jlc3N9IFxuICAgICAgICAgICAgICAgICAgICAgICAgICBjb2xvcj17cGlwZWxpbmUuc3RhdHVzID09PSAnZmFpbGVkJyA/ICdlcnJvcicgOiAncHJpbWFyeSd9XG4gICAgICAgICAgICAgICAgICAgICAgICAvPlxuICAgICAgICAgICAgICAgICAgICAgICAgPFR5cG9ncmFwaHkgdmFyaWFudD1cImNhcHRpb25cIj57cGlwZWxpbmUucHJvZ3Jlc3N9JTwvVHlwb2dyYXBoeT5cbiAgICAgICAgICAgICAgICAgICAgICA8L0JveD5cbiAgICAgICAgICAgICAgICAgICAgPC9UYWJsZUNlbGw+XG4gICAgICAgICAgICAgICAgICAgIDxUYWJsZUNlbGw+XG4gICAgICAgICAgICAgICAgICAgICAge3BpcGVsaW5lLmFjY3VyYWN5ID8gYCR7TWF0aC5yb3VuZChwaXBlbGluZS5hY2N1cmFjeSAqIDEwMCl9JWAgOiAnTi9BJ31cbiAgICAgICAgICAgICAgICAgICAgPC9UYWJsZUNlbGw+XG4gICAgICAgICAgICAgICAgICAgIDxUYWJsZUNlbGw+XG4gICAgICAgICAgICAgICAgICAgICAge25ldyBEYXRlKHBpcGVsaW5lLmNyZWF0ZWRBdCkudG9Mb2NhbGVEYXRlU3RyaW5nKCl9XG4gICAgICAgICAgICAgICAgICAgIDwvVGFibGVDZWxsPlxuICAgICAgICAgICAgICAgICAgICA8VGFibGVDZWxsPlxuICAgICAgICAgICAgICAgICAgICAgIDxUb29sdGlwIHRpdGxlPVwiUnVuIFBpcGVsaW5lXCI+XG4gICAgICAgICAgICAgICAgICAgICAgICA8SWNvbkJ1dHRvblxuICAgICAgICAgICAgICAgICAgICAgICAgICBzaXplPVwic21hbGxcIlxuICAgICAgICAgICAgICAgICAgICAgICAgICBvbkNsaWNrPXsoKSA9PiBoYW5kbGVFeGVjdXRlUGlwZWxpbmUocGlwZWxpbmUuaWQpfVxuICAgICAgICAgICAgICAgICAgICAgICAgICBkaXNhYmxlZD17cGlwZWxpbmUuc3RhdHVzID09PSAncnVubmluZyd9XG4gICAgICAgICAgICAgICAgICAgICAgICAgIGNvbG9yPVwicHJpbWFyeVwiXG4gICAgICAgICAgICAgICAgICAgICAgICA+XG4gICAgICAgICAgICAgICAgICAgICAgICAgIDxQbGF5SWNvbiAvPlxuICAgICAgICAgICAgICAgICAgICAgICAgPC9JY29uQnV0dG9uPlxuICAgICAgICAgICAgICAgICAgICAgIDwvVG9vbHRpcD5cbiAgICAgICAgICAgICAgICAgICAgICA8VG9vbHRpcCB0aXRsZT1cIlZpZXcgRGV0YWlsc1wiPlxuICAgICAgICAgICAgICAgICAgICAgICAgPEljb25CdXR0b24gXG4gICAgICAgICAgICAgICAgICAgICAgICAgIHNpemU9XCJzbWFsbFwiIFxuICAgICAgICAgICAgICAgICAgICAgICAgICBjb2xvcj1cImluZm9cIlxuICAgICAgICAgICAgICAgICAgICAgICAgICBvbkNsaWNrPXsoKSA9PiBoYW5kbGVWaWV3UGlwZWxpbmUocGlwZWxpbmUuaWQpfVxuICAgICAgICAgICAgICAgICAgICAgICAgPlxuICAgICAgICAgICAgICAgICAgICAgICAgICA8Vmlld0ljb24gLz5cbiAgICAgICAgICAgICAgICAgICAgICAgIDwvSWNvbkJ1dHRvbj5cbiAgICAgICAgICAgICAgICAgICAgICA8L1Rvb2x0aXA+XG4gICAgICAgICAgICAgICAgICAgICAgPFRvb2x0aXAgdGl0bGU9XCJEZWxldGUgUGlwZWxpbmVcIj5cbiAgICAgICAgICAgICAgICAgICAgICAgIDxJY29uQnV0dG9uIFxuICAgICAgICAgICAgICAgICAgICAgICAgICBzaXplPVwic21hbGxcIiBcbiAgICAgICAgICAgICAgICAgICAgICAgICAgY29sb3I9XCJlcnJvclwiXG4gICAgICAgICAgICAgICAgICAgICAgICAgIG9uQ2xpY2s9eygpID0+IGhhbmRsZURlbGV0ZUNsaWNrKHBpcGVsaW5lLmlkKX1cbiAgICAgICAgICAgICAgICAgICAgICAgID5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgPERlbGV0ZUljb24gLz5cbiAgICAgICAgICAgICAgICAgICAgICAgIDwvSWNvbkJ1dHRvbj5cbiAgICAgICAgICAgICAgICAgICAgICA8L1Rvb2x0aXA+XG4gICAgICAgICAgICAgICAgICAgIDwvVGFibGVDZWxsPlxuICAgICAgICAgICAgICAgICAgPC9UYWJsZVJvdz5cbiAgICAgICAgICAgICAgICApKX1cbiAgICAgICAgICAgICAgPC9UYWJsZUJvZHk+XG4gICAgICAgICAgICA8L1RhYmxlPlxuICAgICAgICAgIDwvVGFibGVDb250YWluZXI+XG4gICAgICAgIDwvQ2FyZENvbnRlbnQ+XG4gICAgICA8L0NhcmQ+XG5cbiAgICAgIHsvKiBEZWxldGUgQ29uZmlybWF0aW9uIERpYWxvZyAqL31cbiAgICAgIDxEaWFsb2cgb3Blbj17ZGVsZXRlRGlhbG9nT3Blbn0gb25DbG9zZT17aGFuZGxlRGVsZXRlQ2FuY2VsfT5cbiAgICAgICAgPERpYWxvZ1RpdGxlPkRlbGV0ZSBQaXBlbGluZTwvRGlhbG9nVGl0bGU+XG4gICAgICAgIDxEaWFsb2dDb250ZW50PlxuICAgICAgICAgIDxEaWFsb2dDb250ZW50VGV4dD5cbiAgICAgICAgICAgIEFyZSB5b3Ugc3VyZSB5b3Ugd2FudCB0byBkZWxldGUgdGhpcyBwaXBlbGluZT8gVGhpcyBhY3Rpb24gY2Fubm90IGJlIHVuZG9uZS5cbiAgICAgICAgICA8L0RpYWxvZ0NvbnRlbnRUZXh0PlxuICAgICAgICA8L0RpYWxvZ0NvbnRlbnQ+XG4gICAgICAgIDxEaWFsb2dBY3Rpb25zPlxuICAgICAgICAgIDxCdXR0b24gb25DbGljaz17aGFuZGxlRGVsZXRlQ2FuY2VsfT5DYW5jZWw8L0J1dHRvbj5cbiAgICAgICAgICA8QnV0dG9uIG9uQ2xpY2s9e2hhbmRsZURlbGV0ZUNvbmZpcm19IGNvbG9yPVwiZXJyb3JcIiB2YXJpYW50PVwiY29udGFpbmVkXCI+XG4gICAgICAgICAgICBEZWxldGVcbiAgICAgICAgICA8L0J1dHRvbj5cbiAgICAgICAgPC9EaWFsb2dBY3Rpb25zPlxuICAgICAgPC9EaWFsb2c+XG4gICAgPC9Cb3g+XG4gICk7XG59O1xuXG5leHBvcnQgZGVmYXVsdCBEYXNoYm9hcmQ7Il19