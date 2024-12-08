import subprocess
import json
import sys
import httpx
import asyncio
import argparse

class LlamaCppServerModifier:
    def __init__(self, model_path, port=8080, host='127.0.0.1'):
        """
        Initialize the Llama.cpp server modifier with async support.
        
        :param model_path: Path to the GGUF model file
        :param port: Port to run the server on
        :param host: Host address for the server
        """
        self.model_path = model_path
        self.port = port
        self.host = host
        self.server_process = None
        self.client = None
    
    async def start_server(self):
        """
        Asynchronously start the llama.cpp server.
        """
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
        
        # Create async HTTP client
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
    
    async def _test_server_connection(self):
        """
        Async test connection to the server.
        
        :return: True if server is responsive, False otherwise
        """
        try:
            response = await self.client.get(f'http://{self.host}:{self.port}/health')
            return response.status_code == 200
        except (httpx.RequestError, httpx.HTTPStatusError):
            return False
    
    async def modify_text(self, 
                    original_text, 
                    instruction="Rewrite the text to be more concise",
                    max_tokens=150,
                    temperature=0.7):
        """
        Modify text using the running llama.cpp server asynchronously.
        
        :param original_text: Text to be modified
        :param instruction: Specific instruction for text modification
        :param max_tokens: Maximum number of tokens to generate
        :param temperature: Sampling temperature for text generation
        :return: Modified text
        """
        # Construct the full prompt
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
    
    async def _stop_server(self):
        """
        Async method to stop the llama.cpp server.
        """
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
    
    async def __aenter__(self):
        """
        Async context manager entry - start the server.
        """
        await self.start_server()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit - stop the server.
        """
        await self._stop_server()

def extract_transcript_from_json(data):
    """
    Extract transcript from a JSON file containing speech transcription results.
    
    :param json_path: Path to the JSON file
    :return: Extracted transcript text
    """
    try:
        # with open(json_path, 'r') as file:
        #     data = json.load(file)
        
        # Navigate to the transcript in the nested structure
        transcript = data['results']['channels'][0]['alternatives'][0]['transcript']
        return transcript
    
    except (KeyError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error extracting transcript: {e}")
        return None

async def refinePitch(json_path, model_path, port, prompt=None):
    # Set up argument parsing
    # parser = argparse.ArgumentParser(description="Llama.cpp Server Text Modifier")
    # parser.add_argument('json_path', help='Path to the input JSON file')
    # parser.add_argument('model_path', help='Path to the GGUF model')
    # parser.add_argument('--port', type=int, default=8080, help='Port for the server (default: 8080)')
    
    # Parse arguments
    #args = parser.parse_args()
    
    # Extract transcript
    transcript = extract_transcript_from_json(json_path)
    if not transcript:
        print("No transcript found in the JSON file.")
        sys.exit(1)
    else:
        print("----Here is the transcript! ---\n")
        print(transcript)
    
    # Modification instructions
    instructions = [
        "Make this pitch more engaging, concise, and impactful",
        "Use confident and persuasive language that clearly communicates the value proposition, connects with the audience emotionally, and inspires them to take action",
        "Simplify any jargon, emphasize key benefits, and include a strong call-to-action"
    ]
    print("\n--- Starting the server ---")
    # Use async context manager to handle server lifecycle
    try:
        async with LlamaCppServerModifier(model_path=model_path, port=port) as modifier:
            # Interactive modification loop
            if prompt is not None:
                instruction = prompt
                modified_text = await modifier.modify_text(
                    transcript, 
                    instruction=instruction+". keep the speech length same."
                )
                
                # Display result
                print("\n--- Modified Text ---")
                if modified_text is None:
                    return transcript
                return modified_text
            while True:
                print("\n--- Available Instructions ---")
                for i, inst in enumerate(instructions, 1):
                    print(f"{i}. {inst}")
                print("0. Exit")
                
                # Get user choice
                try:
                    choice = int(input("\nEnter the number of the instruction (0 to exit): "))
                    
                    if choice == 0:
                        break
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
                    if modified_text is not None:
                        return modified_text                
                except ValueError:
                    print("Please enter a valid number.")
    
    except Exception as e:
        print(f"An error occurred: {e}")

# if __name__ == "__main__":
#     asyncio.run(refinePitch())