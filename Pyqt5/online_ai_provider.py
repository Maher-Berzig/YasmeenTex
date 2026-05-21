"""
online_ai_provider.py: Online AI provider implementations for LaTeX Exercise Viewer.
"""
import requests
import json


class OnlineAIProvider:
    """Handles communication with various AI providers."""
    
    def __init__(self):
        self.provider = None
        self.api_key = None
        self.model = None
        self.base_urls = {
            'groq': 'https://api.groq.com/openai/v1',
            'openai': 'https://api.openai.com/v1',
            'anthropic': 'https://api.anthropic.com/v1',
            'huggingface': 'https://api-inference.huggingface.co',
            'deepseek': 'https://api.deepseek.com/v1',
            'qwen': 'https://dashscope.aliyuncs.com/api/v1',
            'gemini': 'https://generativelanguage.googleapis.com/v1'
        }
    
    def set_provider(self, provider, api_key, model):
        """Set the provider configuration and validate."""
        if provider not in self.base_urls:
            return False
        
        # Modèles par défaut pour chaque provider
        default_models = {
            'groq': 'llama3-8b-8192',
            'openai': 'gpt-3.5-turbo',
            'anthropic': 'claude-3-haiku-20240307',
            'huggingface': 'mistralai/Mistral-7B-Instruct-v0.1',
            'deepseek': 'deepseek-chat',
            'qwen': 'qwen-turbo',
            'gemini': 'gemini-pro'
        }
        
        self.provider = provider
        self.api_key = api_key
        self.model = model or default_models.get(provider, 'default')
        return True
    
    def query(self, prompt, max_tokens=1000, temperature=0.7):
        """Send query to the selected AI provider."""
        # Validation des paramètres
        if not self.provider or not self.api_key:
            return None, "Provider not configured"
        
        if not prompt or not prompt.strip():
            return None, "Empty prompt"
        
        try:
            if self.provider == 'groq':
                return self._query_groq(prompt, max_tokens, temperature)
            elif self.provider == 'openai':
                return self._query_openai(prompt, max_tokens, temperature)
            elif self.provider == 'anthropic':
                return self._query_anthropic(prompt, max_tokens, temperature)
            elif self.provider == 'huggingface':
                return self._query_huggingface(prompt, max_tokens, temperature)
            elif self.provider == 'deepseek':
                return self._query_deepseek(prompt, max_tokens, temperature)
            elif self.provider == 'qwen':
                return self._query_qwen(prompt, max_tokens, temperature)
            elif self.provider == 'gemini':
                return self._query_gemini(prompt, max_tokens, temperature)
            else:
                return None, f"Unsupported provider: {self.provider}"
        except requests.exceptions.Timeout:
            return None, "Request timeout - try again"
        except requests.exceptions.ConnectionError:
            return None, "Connection error - check your internet"
        except Exception as e:
            return None, f"Unexpected error: {str(e)}"
    
    def _query_groq(self, prompt, max_tokens, temperature):
        """Query Groq API."""
        url = f"{self.base_urls['groq']}/chat/completions"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': self.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': temperature
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'], None
        else:
            return None, f"Groq API error: {response.status_code} - {response.text}"
    
    def _query_openai(self, prompt, max_tokens, temperature):
        """Query OpenAI API."""
        url = f"{self.base_urls['openai']}/chat/completions"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': self.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': temperature
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'], None
        else:
            return None, f"OpenAI API error: {response.status_code} - {response.text}"
    
    def _query_anthropic(self, prompt, max_tokens, temperature):
        """Query Anthropic Claude API."""
        url = f"{self.base_urls['anthropic']}/messages"
        headers = {
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json'
        }
        data = {
            'model': self.model,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'messages': [{'role': 'user', 'content': prompt}]
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result['content'][0]['text'], None
        else:
            return None, f"Anthropic API error: {response.status_code} - {response.text}"
    
    def _query_huggingface(self, prompt, max_tokens, temperature):
        """Query Hugging Face API."""
        url = f"{self.base_urls['huggingface']}/models/{self.model}"
        headers = {
            'Authorization': f'Bearer {self.api_key}' if self.api_key else None,
            'Content-Type': 'application/json'
        }
        data = {
            'inputs': prompt,
            'parameters': {
                'max_new_tokens': max_tokens,
                'temperature': temperature,
                'return_full_text': False
            }
        }
        
        # Remove None headers
        headers = {k: v for k, v in headers.items() if v is not None}
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            if response.status_code == 200:
                result = response.json()
                # Gestion de différents formats de réponse Hugging Face
                if isinstance(result, list) and len(result) > 0:
                    if 'generated_text' in result[0]:
                        return result[0]['generated_text'], None
                    else:
                        return str(result[0]), None
                elif isinstance(result, dict) and 'generated_text' in result:
                    return result['generated_text'], None
                else:
                    return str(result), None
            else:
                return None, f"Hugging Face API error: {response.status_code} - {response.text}"
        except Exception as e:
            return None, f"Hugging Face connection error: {str(e)}"
    
    def _query_deepseek(self, prompt, max_tokens, temperature):
        """Query DeepSeek API."""
        url = f"{self.base_urls['deepseek']}/chat/completions"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': self.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': temperature
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'], None
        else:
            return None, f"DeepSeek API error: {response.status_code} - {response.text}"
    
    def _query_qwen(self, prompt, max_tokens, temperature):
        """Query Qwen API."""
        url = f"{self.base_urls['qwen']}/services/aigc/text-generation/generation"
        headers = {
            'Authorization': f'Bearer {self.api_key}',  # ✅ This IS correct for DashScope
            'Content-Type': 'application/json'
        }
        data = {
            'model': self.model,
            'input': {
                'messages': [{'role': 'user', 'content': prompt}]
            },
            'parameters': {
                'max_tokens': max_tokens,
                'temperature': temperature
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if 'output' in result and 'text' in result['output']:
                return result['output']['text'], None
            else:
                return None, "Unexpected response format from Qwen API"
        else:
            return None, f"Qwen API error: {response.status_code} - {response.text}"
        
    def _query_gemini(self, prompt, max_tokens, temperature):
        """Query Google Gemini API."""
        url = f"{self.base_urls['gemini']}/models/{self.model}:generateContent?key={self.api_key}"
        data = {
            'contents': [{
                'parts': [{'text': prompt}]
            }],
            'generationConfig': {
                'maxOutputTokens': max_tokens,
                'temperature': temperature
            }
        }
        
        response = requests.post(url, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    return candidate['content']['parts'][0]['text'], None
                else:
                    return None, "Unexpected response format from Gemini API"
            else:
                return None, "No candidates in Gemini response"
        else:
            error_msg = response.text
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', error_msg)
            except:
                pass
            return None, f"Gemini API error: {response.status_code} - {error_msg}"