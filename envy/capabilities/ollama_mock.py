class OllamaMock:
    """Mock Ollama client for cloud environments where Ollama is not available."""
    
    def chat(self, model, messages):
        return {
            'message': {
                'content': "Ollama is not available in this cloud environment. Please run ENVY locally for vision capabilities."
            }
        }

# Global instance
ollama = OllamaMock()
