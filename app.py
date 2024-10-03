import threading
import ollama
import json
import speech_recognition as sr
from gtts import gTTS
import pygame
from flask import Flask, render_template, jsonify, request, send_file
import os

app = Flask(__name__)

recognizer = sr.Recognizer()
mic = sr.Microphone()

history_file = 'conversation_history.json'
audio_file = 'static/speech.mp3'  # Path for the audio file

# Load conversation history from file
def load_history(filename):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_history(filename, history):
    with open(filename, 'w') as file:
        json.dump(history, file, indent=4)

history = load_history(history_file)

def create_prompt(history):
    prompt = ""
    for entry in history:
        if 'user' in entry:
            prompt += "User: " + entry['user'] + "\n"
        if 'ai' in entry:
            prompt += "AI: " + entry['ai'] + "\n"
    prompt += "User: "
    return prompt

is_recording = False  # Flag to control recording

# Function to start recording
def start_recording():
    global is_recording
    is_recording = True

# Function to stop recording and process the audio
def stop_recording():
    global is_recording
    is_recording = False
    print("Stopped Recording... Processing audio...")

    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Listening for speech...")
        audio = recognizer.listen(source)

    try:
        user_input = recognizer.recognize_google(audio, language="th-TH").lower()
        print(f"You said: {user_input}")
        return user_input
    except sr.UnknownValueError:
        return "Sorry, I could not understand the audio."
    except sr.RequestError as e:
        return f"Could not request results from the recognition service; {e}"

# Function to handle AI generation and TTS
def ai_response(user_input):
    history.append({"user": user_input})
    prompt = create_prompt(history)

    # AI generation using ollama
    response = ollama.generate(model='llama3.2:3b', prompt=prompt + user_input)
    response_text = response['response']

    history.append({"ai": response_text})
    save_history(history_file, history)

    # TTS response (Thai language)
    tts = gTTS(response_text, lang='th', slow=False)
    tts.save(audio_file)

    return response_text

# Flask route to render HTML with buttons
@app.route('/')
def index():
    return render_template('index.html')

# Flask route to start the recording
@app.route('/start-recording', methods=['POST'])
def start_record():
    start_recording()
    return jsonify({'status': 'recording'})

# Flask route to stop the recording and process the audio
@app.route('/stop-recording', methods=['POST'])
def stop_record():
    user_input = stop_recording()
    
    response_text = ai_response(user_input)
    return jsonify({'status': 'success', 'response': response_text, 'audio': audio_file})

# Flask route to process user text input
@app.route('/process-text', methods=['POST'])
def process_text():
    user_input = request.json.get('text')

    response_text = ai_response(user_input)
    return jsonify({'status': 'success', 'response': response_text, 'audio': audio_file})

# Flask route to serve the audio file
@app.route('/get-audio')
def get_audio():
    return send_file(audio_file, as_attachment=False)

if __name__ == "__main__":
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(host='0.0.0.0', port=5000, debug=True)
