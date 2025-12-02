#!/usr/bin/env python3
print("Python execution test successful!")
print("Current directory:", __import__('os').getcwd())
print("AWS boto3 available:", bool(__import__('boto3', None)))