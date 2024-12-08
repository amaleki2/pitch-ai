import subprocess
import json
import sys
import httpx
import asyncio
import argparse
import os

class ModelAPIModifier:
    def __init__(self, model_type='llama', model_path=None, api_key=None, port=8080, host='127.0.0.1'):
        """
        Initialize the model modifier with support for Llama.cpp and OpenAI
        
        :param model_type: 'llama' or 'openai'
        :param model_path: Path to the GGUF model (for Llama)
        :param api_key: OpenAI API key
        :param port: Port to run the server on (for Llama)
        :param host: Host address for the server (for Llama)
        """
        self.model_type = model_type
        self.model_path = model_path
        self.port = port
        self.host = host
        self.server_process = None
        self.client = None
        
        # OpenAI specific setup
        if model_type == 'openai':
            if not api_key:
                api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
            self.api_key = api_key
            self.client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
    
    async def start_server(self):
        """
        Start the server (Llama.cpp) or prepare API client (OpenAI)
        """
        if self.model_type == 'llama':
            # Construct the server launch command
            server_command = [
                'llama-server',  # Assumes llama-server is in PATH
                '-m', self.model_path,
                '--host', str(self.host),
                '--port', str(self.port)
            ]
            
            # Launch the server as a subprocess
            self.server_process = subprocess.Popen(
                server_command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Create async HTTP client for Llama
            self.client = httpx.AsyncClient(timeout=30.0)
            
            # Wait for server to be ready with exponential backoff
            max_attempts = 10
            for attempt in range(max_attempts):
                try:
                    response = await self._test_server_connection()
                    if response:
                        print(f"Llama.cpp server started successfully on {self.host}:{self.port}")
                        return
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                except Exception as e:
                    print(f"Connection attempt {attempt + 1} failed: {e}")
            
            raise RuntimeError("Could not connect to the server after multiple attempts")
        
        # For OpenAI, just confirm API key is set
        elif self.model_type == 'openai':
            print("OpenAI API client initialized.")
    
    async def _test_server_connection(self):
        """
        Test connection to the Llama.cpp server
        
        :return: True if server is responsive, False otherwise
        """
        if self.model_type == 'llama':
            try:
                response = await self.client.get(f'http://{self.host}:{self.port}/health')
                return response.status_code == 200
            except (httpx.RequestError, httpx.HTTPStatusError):
                return False
        return True
    
    async def modify_text(self, 
                    original_text, 
                    instruction="Rewrite the text to be more concise",
                    max_tokens=150,
                    temperature=0.7):
        """
        Modify text using either Llama.cpp server or OpenAI API
        
        :param original_text: Text to be modified
        :param instruction: Specific instruction for text modification
        :param max_tokens: Maximum number of tokens to generate
        :param temperature: Sampling temperature for text generation
        :return: Modified text
        """
        if self.model_type == 'llama':
            # Construct the full prompt for Llama
            full_prompt = f"{instruction}\n\nOriginal Text: {original_text}\n\nModified Text:"
            
            # Prepare request payload
            payload = {
                "prompt": full_prompt,
                "n_predict": max_tokens,
                "temperature": temperature,
                "stop": ["\n"]
            }
            
            try:
                # Send async request to the server
                response = await self.client.post(
                    f'http://{self.host}:{self.port}/completion', 
                    json=payload
                )

                # Check if request was successful
                if response.status_code == 200:
                    # Extract the generated text
                    result = response.json()
                    modified_text = result.get('content', '').strip()
                    return modified_text
                else:
                    print(f"Server error: {response.status_code}")
                    return None
            
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                print(f"Request error: {e}")
                return None
        
        elif self.model_type == 'openai':
            # Construct the full prompt for OpenAI
            full_prompt = f"{instruction}\n\nOriginal Text: {original_text}\n\nModified Text:"
            
            # Prepare OpenAI API payload
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that modifies text."},
                    {"role": "user", "content": full_prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            try:
                # Send async request to OpenAI
                response = await self.client.post(
                    "https://api.openai.com/v1/chat/completions", 
                    json=payload
                )

                # Check if request was successful
                if response.status_code == 200:
                    # Extract the generated text
                    result = response.json()
                    modified_text = result['choices'][0]['message']['content'].strip()
                    return modified_text
                else:
                    print(f"OpenAI API error: {response.status_code}")
                    return None
            
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                print(f"OpenAI request error: {e}")
                return None
    
    async def _stop_server(self):
        """
        Stop the server or close the client
        """
        if self.model_type == 'llama':
            if self.client:
                await self.client.aclose()
            
            if self.server_process:
                print("Stopping llama.cpp server...")
                self.server_process.terminate()
                try:
                    # Wait for the process to end
                    self.server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate
                    self.server_process.kill()
                
                print("Server stopped.")
        elif self.model_type == 'openai':
            if self.client:
                await self.client.aclose()
    
    async def __aenter__(self):
        """
        Async context manager entry - start the server or prepare API client
        """
        await self.start_server()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit - stop the server or close the client
        """
        await self._stop_server()

def extract_transcript_from_json(json_path):
    """
    Extract transcript from a JSON file containing speech transcription results.
    
    :param json_path: Path to the JSON file
    :return: Extracted transcript text
    """
    try:
        with open(json_path, 'r') as file:
            data = json.load(file)
        
        # Navigate to the transcript in the nested structure
        transcript = data['results']['channels'][0]['alternatives'][0]['transcript']
        return transcript
    
    except (KeyError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error extracting transcript: {e}")
        return None

# [Rest of the previous script remains the same]
async def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Multi-Model Text Modifier")
    parser.add_argument('json_path', help='Path to the input JSON file')
    
    # Add mutually exclusive group for model selection
    model_group = parser.add_mutually_exclusive_group(required=True)
    model_group.add_argument('--llama', dest='model_type', action='store_const', 
                              const='llama', help='Use Llama.cpp local server')
    model_group.add_argument('--openai', dest='model_type', action='store_const', 
                              const='openai', help='Use OpenAI API')
    
    # Conditional arguments
    parser.add_argument('--model-path', help='Path to the GGUF model (for Llama)')
    parser.add_argument('--api-key', help='OpenAI API key (optional, can use OPENAI_API_KEY env)')
    parser.add_argument('--port', type=int, default=8080, help='Port for the server (default: 8080)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Extract transcript
    transcript = extract_transcript_from_json(args.json_path)
    if not transcript:
        print("No transcript found in the JSON file.")
        sys.exit(1)
    else:
        print("Original Transcript:")
        print(transcript)
    
    # Modification instructions
    instructions = [
        "Make this pitch more engaging, concise, and impactful",
        "Use confident and persuasive language that clearly communicates the value proposition, connects with the audience emotionally, and inspires them to take action",
        "Simplify any jargon, emphasize key benefits, and include a strong call-to-action"
    ]
    
    # Prepare model modifier arguments
    modifier_args = {
        'model_type': args.model_type,
        'model_path': args.model_path if args.model_type == 'llama' else None,
        'api_key': args.api_key if args.model_type == 'openai' else None,
        'port': args.port
    }
    
    # Use async context manager to handle server lifecycle
    try:
        async with ModelAPIModifier(**modifier_args) as modifier:
            # Interactive modification loop
            while True:
                print("\n--- Available Instructions ---")
                for i, inst in enumerate(instructions, 1):
                    print(f"{i}. {inst}")
                print("0. Exit")
                print("-1. Comprehensive Context Gathering")
                
                # Get user choice
                try:
                    choice = int(input("\nEnter the number of the instruction (0 to exit, -1 for context): "))
                    
                    if choice == 0:
                        break
                    elif choice == -1:
                        # Start comprehensive context gathering
                        context_gatherer = PitchContextGatherer()
                        context = await context_gatherer.gather_context()
                        
                        # Generate refinement strategy dynamically
                        comprehensive_instruction = await generate_refinement_strategy(modifier, context)
                        
                        # Modify text with the AI-generated instruction
                        modified_text = await modifier.modify_text(
                            transcript, 
                            instruction=comprehensive_instruction+". keep the speech length same."
                        )
                        
                        # Display result
                        print("\n--- Context-Refined Pitch ---")
                        print("\n--- Refinement Strategy ---")
                        print(comprehensive_instruction)
                        print("\n--- Modified Pitch ---")
                        print(modified_text)
                    
                    elif 1 <= choice <= len(instructions):
                        # Modify text with selected instruction
                        instruction = instructions[choice - 1]
                        modified_text = await modifier.modify_text(
                            transcript, 
                            instruction=instruction+". keep the speech length same."
                        )
                        
                        # Display result
                        print("\n--- Modified Text ---")
                        print(modified_text)
                    else:
                        instruction = input("Enter your own prompt: ")
                        modified_text = await modifier.modify_text(
                            transcript, 
                            instruction=instruction+". keep the speech length same."
                        )
                        
                        # Display result
                        print("\n--- Modified Text ---")
                        print(modified_text)
                
                except ValueError:
                    print("Please enter a valid number.")
    
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())