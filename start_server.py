import uvicorn
import os
import sys

def main():
    print("Starting FastAPI Server...")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python path: {sys.executable}")
    
    try:
        uvicorn.run("run:app", host="127.0.0.1", port=8000, reload=True, log_level="info")
    except Exception as e:
        print(f"Server startup error: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
