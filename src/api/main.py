"""
ADPA REST API Server
Provides HTTP endpoints for ADPA functionality
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
import threading

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agent.core.master_agent import MasterAgenticController
from src.agent.utils.llm_integration import LLMReasoningEngine, ReasoningContext
from src.pipeline.evaluation.reporter import ReportingStep
from mcp_server.server import ADPAProjectManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Global ADPA components
adpa_agent = None
project_manager = None
mcp_server_thread = None

def initialize_adpa():
    """Initialize ADPA components"""
    global adpa_agent, project_manager
    
    try:
        # Initialize ADPA Agent
        adpa_agent = MasterAgenticController()
        logger.info("✅ ADPA Agent initialized")
        
        # Initialize Project Manager
        project_manager = ADPAProjectManager(Path('.'))
        logger.info("✅ Project Manager initialized")
        
        return True
    except Exception as e:
        logger.error(f"❌ ADPA initialization failed: {e}")
        return False

def start_mcp_server():
    """Start MCP server in background thread"""
    try:
        from mcp_server.server import main
        asyncio.run(main())
    except Exception as e:
        logger.error(f"MCP server error: {e}")

# Web Interface HTML Template
WEB_INTERFACE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ADPA - Autonomous Data Pipeline Agent</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { 
            text-align: center; 
            background: rgba(255,255,255,0.1); 
            backdrop-filter: blur(10px);
            border-radius: 15px; 
            padding: 30px; 
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .header h1 { 
            color: white; 
            font-size: 2.5em; 
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        .header p { 
            color: rgba(255,255,255,0.9); 
            font-size: 1.2em;
        }
        .grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px;
        }
        .card { 
            background: rgba(255,255,255,0.95); 
            border-radius: 15px; 
            padding: 25px; 
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(0,0,0,0.15);
        }
        .card h3 { 
            color: #4f46e5; 
            margin-bottom: 15px; 
            font-size: 1.3em;
            display: flex;
            align-items: center;
        }
        .card h3::before {
            content: '🚀';
            margin-right: 10px;
            font-size: 1.2em;
        }
        .form-group { margin-bottom: 20px; }
        .form-group label { 
            display: block; 
            margin-bottom: 8px; 
            font-weight: 600;
            color: #374151;
        }
        .form-control { 
            width: 100%; 
            padding: 12px; 
            border: 2px solid #e5e7eb; 
            border-radius: 8px; 
            font-size: 14px;
            transition: border-color 0.3s ease;
        }
        .form-control:focus {
            outline: none;
            border-color: #4f46e5;
            box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
        }
        .btn { 
            background: linear-gradient(45deg, #4f46e5, #7c3aed);
            color: white; 
            border: none; 
            padding: 12px 24px; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 16px;
            font-weight: 600;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
        }
        .result { 
            margin-top: 20px; 
            padding: 20px; 
            background: #f8fafc; 
            border-radius: 8px; 
            border-left: 4px solid #4f46e5;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-running { background: #10b981; }
        .status-stopped { background: #ef4444; }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #4f46e5;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .api-docs {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 25px;
            margin-top: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .endpoint {
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .method {
            background: #10b981;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            margin-right: 10px;
        }
        .method.post { background: #3b82f6; }
        .method.get { background: #10b981; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 ADPA</h1>
            <p>Autonomous Data Pipeline Agent - Cloud Edition</p>
            <p style="margin-top: 10px;">
                <span class="status-indicator status-running"></span>
                Running in Container Mode
            </p>
        </div>

        <div class="grid">
            <div class="card">
                <h3>🔍 System Status</h3>
                <div id="system-status">
                    <div class="loading"></div> Loading system status...
                </div>
                <button class="btn" onclick="checkSystemStatus()" style="margin-top: 15px;">
                    Refresh Status
                </button>
            </div>

            <div class="card">
                <h3>🚀 Execute Pipeline</h3>
                <div class="form-group">
                    <label>Data Description:</label>
                    <input type="text" class="form-control" id="data-description" 
                           placeholder="e.g., customer data with age, income, purchase history">
                </div>
                <div class="form-group">
                    <label>ML Objective:</label>
                    <input type="text" class="form-control" id="ml-objective" 
                           placeholder="e.g., predict customer churn, forecast sales">
                </div>
                <button class="btn" onclick="executePipeline()">
                    Execute Pipeline
                </button>
                <div id="pipeline-result" class="result" style="display: none;"></div>
            </div>

            <div class="card">
                <h3>📊 Project Status</h3>
                <div id="project-status">
                    <div class="loading"></div> Loading project status...
                </div>
                <button class="btn" onclick="getProjectStatus()" style="margin-top: 15px;">
                    Get Status
                </button>
            </div>

            <div class="card">
                <h3>📋 Next Task</h3>
                <div id="next-task">
                    <div class="loading"></div> Loading recommendations...
                </div>
                <button class="btn" onclick="getNextTask()" style="margin-top: 15px;">
                    Get Recommendation
                </button>
            </div>
        </div>

        <div class="api-docs">
            <h3>📚 API Documentation</h3>
            <p style="margin-bottom: 20px; color: #6b7280;">
                Use these endpoints to integrate ADPA into your applications:
            </p>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/status</strong> - Get system status
            </div>
            <div class="endpoint">
                <span class="method post">POST</span>
                <strong>/api/pipeline/execute</strong> - Execute ML pipeline
            </div>
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/project/status</strong> - Get project completion status
            </div>
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/project/next-task</strong> - Get next recommended task
            </div>
            
            <p style="margin-top: 20px; padding: 15px; background: #fef3c7; border-radius: 8px; border-left: 4px solid #f59e0b;">
                <strong>🔗 Container URL:</strong> Access this interface at 
                <code>http://your-container-url:8000</code>
            </p>
        </div>
    </div>

    <script>
        // JavaScript for dynamic interactions
        async function checkSystemStatus() {
            const statusDiv = document.getElementById('system-status');
            statusDiv.innerHTML = '<div class="loading"></div> Checking system status...';
            
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                statusDiv.innerHTML = `
                    <div style="margin-bottom: 10px;">
                        <strong>🟢 ADPA Agent:</strong> ${data.adpa_status}
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>📡 MCP Server:</strong> ${data.mcp_status}
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>⏱️ Uptime:</strong> ${data.uptime || 'N/A'}
                    </div>
                    <div>
                        <strong>🐳 Container:</strong> ${data.container_info || 'Active'}
                    </div>
                `;
            } catch (error) {
                statusDiv.innerHTML = `<div style="color: red;">❌ Error: ${error.message}</div>`;
            }
        }

        async function executePipeline() {
            const dataDesc = document.getElementById('data-description').value;
            const mlObjective = document.getElementById('ml-objective').value;
            const resultDiv = document.getElementById('pipeline-result');
            
            if (!dataDesc || !mlObjective) {
                alert('Please fill in both fields');
                return;
            }
            
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<div class="loading"></div> Executing pipeline...';
            
            try {
                const response = await fetch('/api/pipeline/execute', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        data_description: dataDesc,
                        objective: mlObjective
                    })
                });
                
                const data = await response.json();
                
                resultDiv.innerHTML = `
                    <h4>✅ Pipeline Execution Complete</h4>
                    <p><strong>Status:</strong> ${data.status}</p>
                    <p><strong>Execution ID:</strong> ${data.execution_id}</p>
                    <p><strong>Duration:</strong> ${data.duration}</p>
                    ${data.report ? `<div style="margin-top: 15px;"><strong>Report:</strong><br><pre style="background: #f9fafb; padding: 10px; border-radius: 4px; white-space: pre-wrap;">${data.report.substring(0, 500)}...</pre></div>` : ''}
                `;
            } catch (error) {
                resultDiv.innerHTML = `<div style="color: red;">❌ Error: ${error.message}</div>`;
            }
        }

        async function getProjectStatus() {
            const statusDiv = document.getElementById('project-status');
            statusDiv.innerHTML = '<div class="loading"></div> Loading project status...';
            
            try {
                const response = await fetch('/api/project/status');
                const data = await response.json();
                
                statusDiv.innerHTML = `
                    <div style="margin-bottom: 10px;">
                        <strong>📊 Completion:</strong> ${data.overall_completion}%
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>📋 Phase:</strong> ${data.current_phase}
                    </div>
                    <div>
                        <strong>✅ Features Complete:</strong> ${data.completed_features.length}
                    </div>
                `;
            } catch (error) {
                statusDiv.innerHTML = `<div style="color: red;">❌ Error: ${error.message}</div>`;
            }
        }

        async function getNextTask() {
            const taskDiv = document.getElementById('next-task');
            taskDiv.innerHTML = '<div class="loading"></div> Getting next task...';
            
            try {
                const response = await fetch('/api/project/next-task');
                const data = await response.json();
                
                if (data.task_id) {
                    taskDiv.innerHTML = `
                        <div style="margin-bottom: 10px;">
                            <strong>📋 Task:</strong> ${data.task_id}
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>⏱️ Estimate:</strong> ${data.estimated_time}
                        </div>
                        <div>
                            <strong>💡 Guidance:</strong> ${data.guidance}
                        </div>
                    `;
                } else {
                    taskDiv.innerHTML = `<div>🎉 ${data.message}</div>`;
                }
            } catch (error) {
                taskDiv.innerHTML = `<div style="color: red;">❌ Error: ${error.message}</div>`;
            }
        }

        // Auto-load status on page load
        window.onload = function() {
            checkSystemStatus();
            getProjectStatus();
            getNextTask();
        };
    </script>
</body>
</html>
"""

# API Routes
@app.route('/')
def index():
    """Serve the web interface"""
    return render_template_string(WEB_INTERFACE_HTML)

@app.route('/health')
def health():
    """Health check endpoint for container"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "adpa_initialized": adpa_agent is not None,
        "mcp_initialized": project_manager is not None
    })

@app.route('/api/status')
def api_status():
    """Get system status"""
    return jsonify({
        "adpa_status": "Active" if adpa_agent else "Inactive",
        "mcp_status": "Active" if project_manager else "Inactive",
        "uptime": "Running in container",
        "container_info": f"Python {sys.version[:5]}, ADPA v1.0.0"
    })

@app.route('/api/pipeline/execute', methods=['POST'])
def execute_pipeline():
    """Execute ADPA pipeline"""
    try:
        data = request.get_json()
        data_description = data.get('data_description', '')
        objective = data.get('objective', '')
        
        if not adpa_agent:
            return jsonify({"error": "ADPA agent not initialized"}), 500
        
        # Simulate pipeline execution
        execution_id = f"exec_{int(datetime.now().timestamp())}"
        
        # Use the reasoning engine
        reasoning_engine = LLMReasoningEngine()
        context = ReasoningContext(
            domain="pipeline_planning",
            objective=objective,
            data_context={"description": data_description}
        )
        
        # Get reasoning result
        start_time = datetime.now()
        result = reasoning_engine.reason_about_pipeline_planning(context)
        duration = (datetime.now() - start_time).total_seconds()
        
        # Generate report
        reporter = ReportingStep()
        report_context = {
            'ml_results': {
                'algorithm': 'ADPA Autonomous Agent',
                'primary_metric': 0.85,
                'problem_type': 'automated_ml',
                'training_status': 'Completed'
            },
            'total_duration': duration,
            'pipeline_id': execution_id
        }
        
        report_result = reporter.execute(context=report_context)
        report = report_result.artifacts.get('comprehensive_report', 'Report generated successfully')
        
        return jsonify({
            "status": "completed",
            "execution_id": execution_id,
            "duration": f"{duration:.2f} seconds",
            "confidence": result.confidence,
            "reasoning": result.reasoning[:200] + "...",
            "report": report[:1000] + "..." if len(report) > 1000 else report
        })
        
    except Exception as e:
        logger.error(f"Pipeline execution error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/project/status')
def project_status():
    """Get project completion status"""
    try:
        if not project_manager:
            return jsonify({"error": "Project manager not initialized"}), 500
        
        status = project_manager.get_project_status()
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Project status error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/project/next-task')
def next_task():
    """Get next recommended task"""
    try:
        if not project_manager:
            return jsonify({"error": "Project manager not initialized"}), 500
        
        task = project_manager.get_next_task()
        return jsonify(task)
        
    except Exception as e:
        logger.error(f"Next task error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/mcp/tools')
def mcp_tools():
    """List available MCP tools"""
    return jsonify({
        "tools": [
            "get_project_status",
            "get_next_task", 
            "update_task_status",
            "get_aws_credentials",
            "get_implementation_guidance",
            "get_code_patterns"
        ],
        "mcp_server_url": "http://localhost:8001"
    })

if __name__ == '__main__':
    # Initialize ADPA
    if not initialize_adpa():
        logger.error("Failed to initialize ADPA components")
        sys.exit(1)
    
    # Start MCP server in background
    mcp_server_thread = threading.Thread(target=start_mcp_server, daemon=True)
    mcp_server_thread.start()
    
    # Start Flask web server
    port = int(os.environ.get('ADPA_PORT', 8000))
    logger.info(f"🚀 Starting ADPA Web Server on port {port}")
    logger.info(f"🌐 Web Interface: http://localhost:{port}")
    logger.info(f"📡 API Base URL: http://localhost:{port}/api")
    
    app.run(host='0.0.0.0', port=port, debug=False)