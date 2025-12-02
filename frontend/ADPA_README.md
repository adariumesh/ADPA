# ADPA Frontend Application

A React TypeScript frontend application for the Automated Data Pipeline Architecture (ADPA) system. This application provides a comprehensive web interface for managing ML pipelines, monitoring executions, and viewing results.

## Features

### 🎯 **Dashboard**
- Pipeline overview with real-time status
- Performance metrics and analytics
- Interactive charts showing pipeline distribution
- Quick actions for pipeline management

### 🔧 **Pipeline Builder**
- Step-by-step pipeline creation wizard
- Drag-and-drop file upload interface
- Pipeline configuration and validation
- Data preview functionality

### 📊 **Pipeline Monitor**
- Real-time execution tracking
- Live logs and step progress
- Resource usage monitoring
- Control panel for pipeline operations

### 📈 **Results Viewer**
- Model performance metrics visualization
- Feature importance analysis
- Confusion matrix display
- Model download functionality

## Technology Stack

- **React 18** with TypeScript
- **Material-UI (MUI)** for design system
- **React Router** for navigation
- **Recharts** for data visualization
- **Axios** for API communication
- **React Dropzone** for file uploads

## Getting Started

### Prerequisites
- Node.js 16 or higher
- npm or yarn package manager

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

### Environment Variables

Create a `.env` file in the frontend directory:

```env
REACT_APP_API_URL=https://your-api-gateway-url.amazonaws.com/prod
```

## Application Structure

```
src/
├── components/           # React components
│   ├── Dashboard.tsx    # Main dashboard
│   ├── PipelineBuilder.tsx  # Pipeline creation
│   ├── PipelineMonitor.tsx  # Execution monitoring
│   ├── ResultsViewer.tsx    # Results analysis
│   └── Layout.tsx       # App layout wrapper
├── services/            # API services
│   └── api.ts          # API service layer
├── types/              # TypeScript type definitions
│   └── index.ts        # Application types
├── theme.ts            # Material-UI theme
├── App.tsx             # Main app component
└── index.tsx           # App entry point
```

## Key Components

### Dashboard (`/`)
- **Purpose**: Provides an overview of all pipelines and system status
- **Features**: Status charts, recent pipelines table, quick actions

### Pipeline Builder (`/builder`)
- **Purpose**: Create new ML pipelines through a guided wizard
- **Features**: File upload, configuration forms, validation

### Pipeline Monitor (`/monitor`)
- **Purpose**: Monitor real-time pipeline execution
- **Features**: Live logs, step tracking, resource monitoring

### Results Viewer (`/results`)
- **Purpose**: Analyze and visualize model results
- **Features**: Metrics display, charts, model downloads

## API Integration

The application communicates with the ADPA backend through a REST API:

```typescript
// Main endpoints
GET    /pipelines           # List all pipelines
POST   /pipelines           # Create pipeline
POST   /pipelines/:id/execute  # Execute pipeline
GET    /pipelines/:id/results    # Get model results
POST   /data/upload         # Upload dataset
GET    /dashboard/stats     # Get dashboard statistics
```

## Pipeline Creation Flow

1. **Upload Data**: Drag and drop CSV files or select from computer
2. **Configure Pipeline**: Set name, type, objective, and parameters
3. **Review & Create**: Validate configuration and create pipeline
4. **Monitor Execution**: Track progress in real-time
5. **View Results**: Analyze model performance and download assets

## Development Features

- Mock data for development when backend is unavailable
- Hot reload for rapid development
- TypeScript for type safety
- Material-UI for consistent design
- Responsive layout for all screen sizes

## Chart Visualizations

- **Pie Charts**: Pipeline status distribution
- **Bar Charts**: Pipeline types, feature importance
- **Line Charts**: Resource usage over time
- **Radar Charts**: Model performance metrics
- **Confusion Matrix**: Classification results

This is a complete, production-ready frontend application for the ADPA ML pipeline system.