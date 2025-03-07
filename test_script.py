#!/usr/bin/env python3

print("This is a test script")
print("If you can see this, Python is working correctly")

import sys
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

import os
print(f"Current working directory: {os.getcwd()}")
print(f"Directory contents: {os.listdir('.')}") 