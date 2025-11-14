"""Launch script to run both API server and Streamlit app."""
import subprocess
import sys
import time

from config import config
from logger import setup_logger

logger = setup_logger(__name__)


def start_api_server():
    """Start the FastAPI server."""
    logger.info("Starting API server...")
    return subprocess.Popen(
        [sys.executable, "api.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )


def start_streamlit_app():
    """Start the Streamlit app."""
    logger.info("Starting Streamlit app...")
    return subprocess.Popen(
        ["streamlit", "run", "main.py", "--server.port", "8501"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )


def shutdown_processes(api_process, streamlit_process):
    """Gracefully shutdown both processes."""
    logger.info("Shutting down services...")

    # Send terminate signal
    api_process.terminate()
    streamlit_process.terminate()

    # Wait for graceful shutdown
    try:
        api_process.wait(timeout=5)
        streamlit_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        logger.warning("Processes did not terminate gracefully, forcing shutdown...")
        api_process.kill()
        streamlit_process.kill()
        api_process.wait()
        streamlit_process.wait()

    logger.info("Shutdown complete.")


if __name__ == "__main__":
    api_process = None
    streamlit_process = None

    try:
        # Start API server
        api_process = start_api_server()

        # Wait a moment for API to start
        logger.info("Waiting for API server to initialize...")
        time.sleep(3)

        # Check if API process is still running
        if api_process.poll() is not None:
            logger.error("API server failed to start")
            sys.exit(1)

        # Start Streamlit app
        streamlit_process = start_streamlit_app()

        logger.info("Services started successfully!")
        logger.info(f"API: http://{config.API_HOST}:{config.API_PORT}")
        logger.info("Streamlit: http://localhost:8501")
        logger.info("Press Ctrl+C to stop all services")

        # Wait for processes
        api_process.wait()
        streamlit_process.wait()

    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
        if api_process and streamlit_process:
            shutdown_processes(api_process, streamlit_process)

    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
        if api_process and streamlit_process:
            shutdown_processes(api_process, streamlit_process)
        sys.exit(1)
