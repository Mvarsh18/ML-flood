from flask import Flask, render_template, request
import os
import speech_recognition as sr
import requests
from pydub import AudioSegment
from pydub.utils import mediainfo

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max upload size: 16MB

# Function to detect human voice in the audio file
def detect_human_voice(audio_file_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file_path) as source:
        audio = recognizer.record(source)

        try:
            # Recognize speech using Google Web API
            speech_text = recognizer.recognize_google(audio)
            if speech_text:
                return True, speech_text
        except sr.UnknownValueError:
            return False, "No recognizable human voice detected"
        except sr.RequestError as e:
            return False, f"API Error: {e}"

    return False, "No human voice detected"

# Fetch location from IP using ipinfo.io
def get_location_by_ip(ip):
    response = requests.get(f'https://ipinfo.io/{ip}/json')
    data = response.json()
    return data.get("city", "Unknown location"), data.get("country", "Unknown country")

# Home route for file upload and processing
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "audio_file" not in request.files:
            return "No file part"

        file = request.files["audio_file"]

        if file.filename == "":
            return "No selected file"

        if file:
            # Save the uploaded MP3 file
            mp3_filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(mp3_filepath)

            # Check if the uploaded file is a valid MP3
            audio_info = mediainfo(mp3_filepath)
            if audio_info.get('codec_name') != 'mp3':
                return "Invalid file format. Please upload an MP3 file."

            # Detect human voice in the MP3 file
            is_human, message = detect_human_voice(mp3_filepath)

            if is_human:
                # Get user location by IP
                user_ip = request.remote_addr
                city, country = get_location_by_ip(user_ip)

                return f"Human voice detected: {message}. Location: {city}, {country}"
            else:
                return f"Error: {message}"

    return render_template("index.html")

if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
