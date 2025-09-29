#!/usr/bin/env python3
"""
Main entry point for Railway deployment.
Railway Railpack automatically detects and runs main.py files.
"""

import os
import sys
import uvicorn
from app.api.http.app import app

def main():
    """Main function to run the application."""
    # Railway provides PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"Starting AI Maga on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        reload=False  # Disable reload in production
    )

if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print("AI Maga - Voice Assistant API")
        print("Usage: python main.py")
        print("Environment variables:")
        print("  PORT - Port to run on (default: 8000)")
        print("  HOST - Host to bind to (default: 0.0.0.0)")
        sys.exit(0)

    # Run the application
    main()
