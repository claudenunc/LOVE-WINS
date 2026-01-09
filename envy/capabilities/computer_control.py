import os
import base64
import logging
from typing import List, Dict, Any, Optional
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

try:
    import ollama
except ImportError:
    ollama = None

try:
    from interpreter import interpreter
except ImportError:
    interpreter = None

logger = logging.getLogger(__name__)

class VisionController:
    """
    Implements 'The Body' using Vision-Based Control.
    Supports:
    - Anthropic Computer Use (Cloud, High Precision)
    - Ollama Llama 3.2 Vision (Local, Open Source, Experimental)
    """
    def __init__(self, provider: str = "ollama", model: Optional[str] = None):
        self.provider = provider
        self.model_name = model
        
        if self.provider == "anthropic":
            if not Anthropic:
                logger.error("Anthropic library not installed.")
                return
            api_key = os.getenv("ANTHROPIC_API_KEY")
            self.client = Anthropic(api_key=api_key) if api_key else None
            self.model_name = model or "claude-3-5-sonnet-20241022"
            
        elif self.provider == "ollama":
            if not ollama:
                logger.error("Ollama library not installed.")
                return
            self.model_name = model or "llama3.2-vision"
            # Verify model exists or pull it? 
            # For speed, we assume user has pulled it: `ollama pull llama3.2-vision`

    def take_screenshot(self) -> str:
        """
        Captures the screen and returns a base64 encoded string.
        (Placeholder: Real implementation requires a library like pyautogui or mss)
        """
        # import pyautogui
        # ... capture logic ...
        # For prototype, we'll just log
        logger.info("Taking screenshot (placeholder)...")
        return "base64_encoded_image_placeholder"

    def analyze(self, instruction: str) -> str:
        """
        Analyzes the screen based on an instruction.
        """
        screenshot_b64 = self.take_screenshot()
        
        if self.provider == "anthropic":
            if not self.client:
                return "Error: Anthropic client not initialized (missing API key?)."
            # Simplified call - real Computer Use is more complex
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": screenshot_b64}},
                        {"type": "text", "text": instruction}
                    ]
                }]
            )
            return message.content[0].text

        elif self.provider == "ollama":
            try:
                # Ollama expects path or bytes, but python lib handles b64 if passed correctly or bytes
                # The python lib 'images' kwarg takes file paths or base64 strings
                response = ollama.chat(
                    model=self.model_name,
                    messages=[{
                        'role': 'user',
                        'content': instruction,
                        'images': [screenshot_b64]
                    }]
                )
                return response['message']['content']
            except Exception as e:
                return f"Error querying local vision model: {e}"
        
        return "Error: Unknown provider."

    def execute_action(self, action: Dict[str, Any]):
        """
        Executes the low-level HID command returned by the model.
        """
        # ... (same as before)
        pass

    async def run_loop(self, instruction: str):
        # ... (same as before)
        pass

class CodeController:
    """
    Implements 'The Body' using Code-Based Control (Open Interpreter).
    Act as a 'Super-User' writing scripts to execute tasks.
    """
    def __init__(self, local_mode: bool = False):
        if interpreter is None:
            logger.warning("Open Interpreter not installed.")
            return
            
        self.interpreter = interpreter
        self.interpreter.auto_run = True
        self.interpreter.offline = local_mode # Use local models if true
        
        # Configure safety
        # self.interpreter.safe_mode = "ask" # As per "Human-in-the-Loop" requirement

    def chat(self, message: str) -> str:
        """
        Sends a message to Open Interpreter to execute system tasks.
        """
        if not self.interpreter:
            return "Interpreter unavailable."
            
        logger.info(f"Delegating to Open Interpreter: {message}")
        # Interpreter returns a generator or list of messages
        response = self.interpreter.chat(message)
        return str(response)

    def set_sandbox(self, sandbox_type: str = "subprocess"):
        """
        Configures the execution environment (e.g., E2B, Docker).
        """
        # interpreter.computer.backend = ... (if supported) or custom configuration
        pass
