import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { theme } from './theme';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import PipelineBuilder from './components/PipelineBuilder';
import PipelineMonitor from './components/PipelineMonitor';
import ResultsViewer from './components/ResultsViewer';

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/builder" element={<PipelineBuilder />} />
            <Route path="/monitor" element={<PipelineMonitor />} />
            <Route path="/results" element={<ResultsViewer />} />
          </Routes>
        </Layout>
      </Router>
    </ThemeProvider>
  );
}

export default App;
