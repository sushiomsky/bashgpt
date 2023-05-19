# -------------------------------------------------------------------------------
# Name:        GPT Conversation Application
# Purpose:     An application to have conversations with OpenAI's GPT model
#              with support for saving conversations, handling shell scripts,
#              setting custom prompts and more.
#
# Author:      Dennis Kelly Suchomsky
#
# Created:     15/05/2023
# Copyright:   (c) Dennis Kelly Suchomsky 2023
# Licence:     Your License Here
# -------------------------------------------------------------------------------

import os
import json
import re
import openai
import subprocess
import uuid
from datetime import datetime
from getpass import getpass

# Get the OpenAI API key from the user and store it
if not os.path.exists('api_key.txt'):
    api_key = getpass('Please enter your OpenAI API key: ')
    with open('api_key.txt', 'w') as f:
        f.write(api_key)
else:
    with open('api_key.txt', 'r') as f:
        api_key = f.read()

# Set OpenAI API key
openai.api_key = api_key

# Function to chat with GPT
def chat_with_gpt(messages, temperature):
    response = openai.ChatCompletion.create(
        model="gpt-4.0-turbo",  # Please replace with your model version
        messages=messages,
        temperature=temperature
    )
    return response['choices'][0]['message']['content']

# Function to handle shell script
def handle_shell_script(response):
    script_match = re.search('```shell\s*(.*?)\s*```', response, re.DOTALL)
    filename_match = re.search('filename: (.*?)\n', response, re.DOTALL)
    if script_match and filename_match:
        script_content = script_match.group(1).strip()
        filename = filename_match.group(1).strip()
        script_path = f"working/{filename}.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        print(f"Found a shell script. Saved to {script_path}")
        if input("Do you want to execute the script? (y/n) ").lower() == 'y':
            result = subprocess.run(script_path, capture_output=True, text=True, shell=True)
            if result.returncode != 0:
                print(f"Script exited with error: {result.stderr}")
                if input("Do you want to send the error to the AI? (y/n) ").lower() == 'y':
                    return result.stderr
    return None

# Function to save conversation
def save_conversation(foldername, messages):
    if not os.path.exists(foldername):
        os.makedirs(foldername)
    for i, message in enumerate(messages):
        with open(f"{foldername}/{i+1}.txt", 'w') as f:
            f.write(message['role'] + ': ' + message['content'])

# Function to load conversation
def load_conversation(foldername):
    messages = []
    i = 1
    while True:
        filename = f"{foldername}/{i}.txt"
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                role, content = f.read().split(': ', 1)
                messages.append({"role": role, "content": content})
            i += 1
        else:
            break
    return messages

# Function to generate a unique foldername
def generate_foldername():
    return datetime.now().strftime("%Y%m%d%H%M%S") + '-' + str(uuid.uuid4())

# Function to select a conversation to continue
def select_conversation():
    folders = [folder for folder in os.listdir() if os.path.isdir(folder)]
    folders.sort()
    print("Select a conversation to continue:")
    print("0: Start a new conversation")
    for i, folder in enumerate(folders):
        print(f"{i+1}: {folder}")
    selection = int(input("Enter the number of your selection: "))
    if selection == 0:
        return generate_foldername()
    else:
        return folders[selection - 1]

# Function to ask for temperature
def ask_for_temperature():
    temp = input("Enter the desired temperature for the conversation (0.0-1.0): ")
    return float(temp)

# Function to show help
def show_help():
    print("""
Commands:
quit: Exit the application.
new: Start a new conversation.
settemperature <value>: Set the temperature for the next conversation.
setprompt <alias> <prompt>: Set a custom prompt with an alias.
<alias>: Use a custom prompt.
If a shell script is detected in the AI's response, you will be asked if you want to execute it.
    """)

# Initial temperature
temperature = 0.5

# Load custom prompts
if os.path.exists('custom_prompts.json'):
    with open('custom_prompts.json', 'r') as f:
        custom_prompts = json.load(f)
else:
    custom_prompts = {}

# Main loop
foldername = select_conversation()
if os.path.exists(foldername):
    messages = load_conversation(foldername)
else:
    temperature = ask_for_temperature()
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
    ]

while True:
    user_input = input("You: ")
    if user_input.lower() == 'quit':
        save_conversation(foldername, messages)
        print(f"Conversation saved to {foldername}")
        break
    elif user_input.lower() == 'new':
        save_conversation(foldername, messages)
        print(f"Conversation saved to {foldername}")
        temperature = ask_for_temperature()
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
        ]
        foldername = generate_foldername()
        continue
    elif user_input.lower() == 'help':
        show_help()
        continue
    elif user_input.lower().startswith('settemperature '):
        temperature = float(user_input.split(' ')[1])
        print(f"Set temperature to {temperature}")
        continue
    elif user_input.lower().startswith('setprompt '):
        alias, prompt = user_input.split(' ', 2)[1:]
        custom_prompts[alias] = prompt
        with open('custom_prompts.json', 'w') as f:
            json.dump(custom_prompts, f)
        print(f"Set custom prompt '{alias}' to '{prompt}'")
        continue
    elif user_input.lower() in custom_prompts:
        user_input = custom_prompts[user_input.lower()]
    messages.append({"role": "user", "content": user_input})
    save_conversation(foldername, messages)  # Save after user message
    response = chat_with_gpt(messages, temperature)
    messages.append({"role": "assistant", "content": response})
    save_conversation(foldername, messages)  # Save after assistant response
    print("GPT: ", response)
    error = handle_shell_script(response)
    if error:
        messages.append({"role": "user", "content": error})
        save_conversation(foldername, messages)  # Save after user error message
        response = chat_with_gpt(messages, temperature)
        messages.append({"role": "assistant", "content": response})
        save_conversation(foldername, messages)  # Save after assistant error response
        print("GPT: ", response)
