#!/usr/bin/env python3
"""
Check for latest git changes and identify what needs to be pulled
"""

import subprocess
import sys
import json
from datetime import datetime

def run_command(cmd):
    """Run command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd='.')
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def check_git_status():
    """Check current git status and remote updates"""
    print("🔍 Checking Git Status and Remote Updates")
    print("=" * 50)
    
    # Check current branch
    current_branch, _, _ = run_command("git rev-parse --abbrev-ref HEAD")
    print(f"Current branch: {current_branch}")
    
    # Check local commit
    local_commit, _, _ = run_command("git rev-parse HEAD")
    print(f"Local commit: {local_commit[:8]}")
    
    # Fetch latest from remote
    print("\n🌐 Fetching from remote...")
    fetch_out, fetch_err, fetch_code = run_command("git fetch origin")
    
    if fetch_code != 0:
        print(f"⚠️  Fetch warning: {fetch_err}")
    
    # Check remote commit  
    remote_commit, _, _ = run_command("git rev-parse origin/main")
    print(f"Remote commit: {remote_commit[:8]}")
    
    # Check if we're behind
    behind_count, _, _ = run_command("git rev-list --count HEAD..origin/main")
    ahead_count, _, _ = run_command("git rev-list --count origin/main..HEAD")
    
    print(f"\n📊 Sync Status:")
    print(f"  Behind remote: {behind_count} commits")
    print(f"  Ahead of remote: {ahead_count} commits")
    
    # Check for uncommitted changes
    status_out, _, _ = run_command("git status --porcelain")
    if status_out:
        print(f"\n⚠️  Uncommitted changes:")
        for line in status_out.split('\n'):
            if line.strip():
                print(f"    {line}")
    
    # Get recent commits on remote
    print(f"\n📝 Recent commits on origin/main:")
    recent_commits, _, _ = run_command("git log origin/main --oneline -5")
    for line in recent_commits.split('\n'):
        if line.strip():
            print(f"    {line}")
    
    # Check if pull is needed
    if int(behind_count) > 0:
        print(f"\n🔄 PULL NEEDED: {behind_count} new commits available")
        
        # Show what would be pulled
        print("\n📥 New commits that would be pulled:")
        new_commits, _, _ = run_command("git log HEAD..origin/main --oneline")
        for line in new_commits.split('\n'):
            if line.strip():
                print(f"    + {line}")
                
        return True, int(behind_count)
    else:
        print("\n✅ UP TO DATE: No new commits to pull")
        return False, 0

def check_for_conflicts():
    """Check if there would be merge conflicts"""
    print(f"\n🔍 Checking for potential conflicts...")
    
    # Check which files changed in both local and remote
    local_changes, _, _ = run_command("git diff HEAD..origin/main --name-only")
    uncommitted_changes, _, _ = run_command("git diff HEAD --name-only") 
    
    local_files = set(local_changes.split('\n')) if local_changes else set()
    uncommitted_files = set(uncommitted_changes.split('\n')) if uncommitted_changes else set()
    
    potential_conflicts = local_files.intersection(uncommitted_files)
    
    if potential_conflicts:
        print(f"⚠️  Potential conflict files:")
        for file in potential_conflicts:
            if file.strip():
                print(f"    - {file}")
        return True
    else:
        print("✅ No potential conflicts detected")
        return False

def main():
    print("ADPA Git Status and Update Checker")
    print("=" * 50)
    
    # Check if we're in a git repo
    _, _, code = run_command("git status")
    if code != 0:
        print("❌ Not in a git repository!")
        sys.exit(1)
    
    # Check git status and updates
    needs_pull, commit_count = check_git_status()
    
    # Check for potential conflicts
    has_conflicts = check_for_conflicts()
    
    # Summary and recommendations
    print("\n" + "=" * 50)
    print("📋 SUMMARY & RECOMMENDATIONS")
    print("=" * 50)
    
    if not needs_pull:
        print("✅ Repository is up to date")
        print("👍 Safe to proceed with integration")
        
    elif needs_pull and not has_conflicts:
        print(f"🔄 Pull recommended: {commit_count} new commits available")
        print("✅ No conflicts expected")
        print("\n🚀 Recommended actions:")
        print("  1. git stash (save current work)")  
        print("  2. git pull origin main")
        print("  3. git stash pop (restore work)")
        print("  4. Test integration after pull")
        
    elif needs_pull and has_conflicts:
        print(f"⚠️  Pull needed but conflicts likely: {commit_count} new commits")
        print("❌ Manual merge required")
        print("\n🚨 Recommended actions:")
        print("  1. Commit current changes first")
        print("  2. git pull origin main") 
        print("  3. Resolve merge conflicts manually")
        print("  4. Test thoroughly after merge")
        
    else:
        print("🤔 Unusual git state detected")
        print("💡 Recommend manual git inspection")

if __name__ == "__main__":
    main()