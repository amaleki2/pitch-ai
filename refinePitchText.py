import subprocess
import requests
import json
import sys
import httpx
import asyncio
import time
import argparse

class LlamaCppServerModifier:
    def __init__(self, model_path, port=8080, host='127.0.0.1'):
        """
        Initialize the Llama.cpp server modifier.
        
        :param model_path: Path to the GGUF model file
        :param port: Port to run the server on
        :param host: Host address for the server
        """
        self.model_path = model_path
        self.port = port
        self.host = host
        self.server_process = None
        
    def start_server(self):
        """
        Start the llama.cpp server.
        """
        # Construct the server launch command
        server_command = [
            'llama-server',  # Assumes llama-server is in PATH
            '-m', self.model_path,
            '--host', str(self.host),
            '--port', str(self.port)
        ]
        
        #try:
        # Launch the server as a subprocess
        self.server_process = subprocess.Popen(
            server_command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a moment for the server to start
        time.sleep(20)
        #a = input()
        # Verify server is running
        response = self._test_server_connection()
        if response:
            print(f"Llama.cpp server started successfully on {self.host}:{self.port}")
        else:
            raise RuntimeError("Could not connect to the server")
            
        # except Exception as e:
        #     print(f"Error starting server: {e}")
        #     self._stop_server()
        #     raise
    
    def _test_server_connection(self):
        """
        Test connection to the server.
        
        :return: True if server is responsive, False otherwise
        """
        try:
            response = requests.get(f'http://{self.host}:{self.port}/health')
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def modify_text(self, 
                    original_text, 
                    instruction="Rewrite the text to be more concise",
                    max_tokens=150,
                    temperature=0.7):
        """
        Modify text using the running llama.cpp server.
        
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
        
        #try:
        # Send request to the server
        response = requests.post(
            f'http://{self.host}:{self.port}/completion', 
            json=payload
        )

        #time.sleep(20)
        
        # Check if request was successful
        if response.status_code == 200:
            # Extract the generated text
            result = response.json()
            modified_text = result.get('content', '').strip()
            return modified_text
        else:
            print(f"Server error: {response.status_code}")
            return None
        
        # except requests.RequestException as e:
        #     print(f"Request error: {e}")
        #     return None
    
    def _stop_server(self):
        """
        Stop the llama.cpp server.
        """
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
    
    def __enter__(self):
        """
        Context manager entry - start the server.
        """
        self.start_server()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit - stop the server.
        """
        self._stop_server()

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

def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Llama.cpp Server Text Modifier")
    parser.add_argument('json_path', help='Path to the input JSON file')
    parser.add_argument('model_path', help='Path to the GGUF model')
    parser.add_argument('--port', type=int, default=8080, help='Port for the server (default: 8080)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Extract transcript
    transcript = extract_transcript_from_json(args.json_path)
    if not transcript:
        print("No transcript found in the JSON file.")
        sys.exit(1)
    else:
        print(transcript)
    
    # Modification instructions
    instructions = [
        "Make this pitch more engaging, concise, and impactful",
        "Use confident and persuasive language that clearly communicates the value proposition, connects with the audience emotionally, and inspires them to take action",
        "Simplify any jargon, emphasize key benefits, and include a strong call-to-action"
    ]
    
    # Use context manager to handle server lifecycle
    try:
        with LlamaCppServerModifier(args.model_path, port=args.port) as modifier:
            # Interactive modification loop
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
                        modified_text = modifier.modify_text(
                            transcript, 
                            instruction=instruction+". keep the speech length same."
                        )
                        
                        # Display result
                        print("\n--- Modified Text ---")
                        print(modified_text)
                    else:
                        instruction = input("Enter your own prompt: ")
                        modified_text = modifier.modify_text(
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
    main()