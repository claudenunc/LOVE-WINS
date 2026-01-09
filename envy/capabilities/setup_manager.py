import shutil
import subprocess
import logging
import sys
import os

logger = logging.getLogger(__name__)

class SetupManager:
    """
    Manages self-setup and dependency verification for ENVY.
    Allows the agent to 'build itself' by installing required tools.
    """
    
    def __init__(self):
        self.is_windows = sys.platform == 'win32'

    def check_ollama(self) -> bool:
        """Checks if Ollama is installed and accessible."""
        return shutil.which("ollama") is not None

    def install_ollama(self) -> str:
        """Attempts to install Ollama."""
        if self.check_ollama():
            return "Ollama is already installed."

        logger.info("Ollama not found. Attempting installation...")
        
        if self.is_windows:
            # Try using winget
            try:
                # Check if winget is available
                if shutil.which("winget"):
                    cmd = ["winget", "install", "Ollama.Ollama", "-e", "--silent", "--accept-source-agreements", "--accept-package-agreements"]
                    subprocess.run(cmd, check=True)
                    return "Ollama installed via Winget. Please restart your terminal/script to update PATH."
                else:
                    return "Winget not found. Please install Ollama manually from ollama.com."
            except subprocess.CalledProcessError as e:
                return f"Failed to install Ollama via Winget: {e}"
        else:
            # Linux/Mac curl script
            try:
                cmd = "curl -fsSL https://ollama.com/install.sh | sh"
                subprocess.run(cmd, shell=True, check=True)
                return "Ollama installed successfully."
            except subprocess.CalledProcessError as e:
                return f"Failed to install Ollama via script: {e}"

    def pull_model(self, model_name: str) -> str:
        """Pulls a specific model using Ollama."""
        if not self.check_ollama():
            return "Ollama is not installed. Cannot pull model."
            
        logger.info(f"Pulling model: {model_name}...")
        try:
            # We use stream=True to avoid buffering everything
            process = subprocess.Popen(
                ["ollama", "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # Wait for completion
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                return f"Successfully pulled {model_name}."
            else:
                return f"Failed to pull {model_name}: {stderr}"
        except Exception as e:
            return f"Error executing ollama pull: {e}"

    def run_full_setup(self):
        """Runs the complete setup sequence for open-source capabilities."""
        report = []
        
        # 1. Ollama
        report.append(self.install_ollama())
        
        # 2. Pull Vision Model
        if self.check_ollama():
            report.append(self.pull_model("llama3.2-vision"))
        else:
            report.append("Skipping model pull (Ollama missing).")
            
        return "\n".join(report)
