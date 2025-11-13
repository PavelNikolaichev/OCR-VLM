import subprocess
import sys


def start_api_server():
    return subprocess.Popen([sys.executable, "api.py"])

def start_streamlit_app():
    return subprocess.Popen(["streamlit", "run", "main.py"])

if __name__ == "__main__":
    api_process = start_api_server()
    streamlit_process = start_streamlit_app()

    try:
        api_process.wait()
        streamlit_process.wait()
    except KeyboardInterrupt:
        print("Shutting down...")
        api_process.terminate()
        streamlit_process.terminate()
        api_process.wait()
        streamlit_process.wait()
        print("Shutdown complete.")