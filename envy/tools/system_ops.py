import subprocess
import os
from typing import Dict, Any

class SystemOps:
    """
    Manages system-level operations for ENVY, such as running shell commands.
    """
    def __init__(self, cwd: str = "."):
        self.cwd = os.path.abspath(cwd)

    def run_command(self, command: str) -> str:
        """
        Executes a shell command and returns the output.
        """
        try:
            # Use shell=True for complex commands, but be careful with sanitization
            # In this context, ENVY is trusted by the user to perform tasks.
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.cwd
            )
            stdout, stderr = process.communicate()
            
            output = []
            if stdout:
                output.append(stdout)
            if stderr:
                output.append(f"Errors:\n{stderr}")
            
            if not output:
                return f"Command executed with exit code {process.returncode} (no output)."
                
            return "\n".join(output)
            
        except Exception as e:
            return f"Error executing command: {str(e)}"

    def set_cwd(self, path: str) -> str:
        """Changes the current working directory for future commands."""
        if os.path.isdir(path):
            self.cwd = os.path.abspath(path)
            return f"Changed working directory to: {self.cwd}"
        else:
            return f"Error: '{path}' is not a valid directory."
