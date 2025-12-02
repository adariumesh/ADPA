#!/usr/bin/env python3
"""
Simple runner for ADPA deployment
"""

def main():
    import sys
    import os
    from pathlib import Path
    
    # Set working directory
    project_dir = Path("/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa")
    os.chdir(project_dir)
    
    # Import and run the deployment
    sys.path.insert(0, str(project_dir))
    
    try:
        import direct_deploy
        return direct_deploy.main()
    except ImportError as e:
        print(f"Failed to import direct_deploy: {e}")
        
        # Try to run the boto3_deploy directly
        try:
            import boto3_deploy
            return boto3_deploy.main()
        except ImportError as e2:
            print(f"Failed to import boto3_deploy: {e2}")
            
            # Manual execution
            exec(open('direct_deploy.py').read())
            
    except Exception as e:
        print(f"Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    print(f"\\nDeployment finished with exit code: {exit_code}")