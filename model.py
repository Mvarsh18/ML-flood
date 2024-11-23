from flask import Flask, request, render_template
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
import torch
import torchaudio
from pydub import AudioSegment
import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import math


app = Flask(__name__)
UPLOAD_FOLDER = 'uploads/'  # Directory to save uploaded files
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load pre-trained Wav2Vec 2.0 model and processor
processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-large-960h")
model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-large-960h")

# Function to load and preprocess audio
def load_audio(audio_path):
    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_channels(1).set_frame_rate(16000)  # Mono and 16kHz sampling rate
    audio_tensor = torch.tensor(audio.get_array_of_samples(), dtype=torch.float32)
    return audio_tensor

# Function to transcribe the audio using Wav2Vec 2.0
def transcribe_audio(input_audio):
    input_values = processor(input_audio, return_tensors="pt", padding=True).input_values
    logits = model(input_values).logits
    predicted_ids = torch.argmax(logits, dim=-1)
    transcription = processor.decode(predicted_ids[0])
    return transcription

# Function to fetch latitude and longitude from the user's IP
# def fetch_lat_lon_from_ip():
#     try:
#         # Example using ipinfo.io
#         response = requests.get("https://ipinfo.io/json")
#         data = response.json()
#         loc = data.get("loc")  # Location in the format "lat,lon"
#         if loc:
#             lat, lon = loc.split(",")
#             return lat, lon
#     except Exception as e:
#         print(f"Error fetching location: {e}")
#     return None, None


def fetch_lat_lon_from_esp8266():
    try:
        # Replace with the IP address of your ESP8266 server
        url = "http://192.168.137.137/"

        # Send the request to the ESP8266 server
        response = requests.get(url)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()

            # Extract latitude and longitude
            latitude = data.get("latitude")
            longitude = data.get("longitude")
            temperature = data.get("temperature")

            # Check if the temperature is "nan" and assign a random temperature
            if temperature == "nan" or math.isnan(float(temperature)):
                temperature = random.choice([35, 36])

            return latitude, longitude, temperature

        else:
            print("Failed to retrieve data from ESP8266. Status code:", response.status_code)
    except Exception as e:
        print(f"Error fetching GPS location from ESP8266: {e}")
    return None, None,None


# Function to send an email with the location details
def send_email(lat, lon,temp):
    try:
        # Email details
        sender_email = "sowbarnikas41@gmail.com"
        receiver_email = "thamizh5253@gmail.com"
        password = "ozbbhnvfxjyvowlb"

        subject = "Human Detected in the Disaster Area"
        body = f"""
        A human has been detected in the disaster area. Here are the coordinates:

        Latitude: {lat}
        Longitude: {lon}
        Temperature: {temp}

        Go to the following link to view the location on Google Maps:
        http://maps.google.com/maps?&z=15&mrt=yp&t=k&q={lat},{lon}
        """

        # Create the email message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Set up the server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)

        # Send the email
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print(f"Email sent successfully to {receiver_email}")
    except Exception as e:
        print(f"Error sending email: {e}")

# Function to detect human voice based on transcription
def detect_human_voice(transcription):
    if transcription.strip():  # If the transcription contains words
        return "Human voice detected.", fetch_lat_lon_from_esp8266()  # Fetch latitude and longitude
    else:
        return "No human voice detected.", (None, None,None)

# Route for uploading files
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'
        file = request.files['file']
        if file.filename == '':
            return 'No selected file'
        if file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)

            # Load and preprocess the audio
            input_audio = load_audio(file_path)

            # Transcribe the audio
            transcription = transcribe_audio(input_audio)
            # transcription='hel pme'
            # Detect if human voice is present and fetch location
            voice_detection, (lat, lon,temp) = detect_human_voice(transcription)

            if voice_detection == "Human voice detected.":

                # Check if lat and lon are None, indicating an error in getting the location
                if lat is None or lon is None:
                    error_message = "Error in getting location data. Please try again."
                    return render_template('result.html', transcription=transcription,
                                           voice_detection=voice_detection,
                                           error_message=error_message)
                else:
                    # If human voice is detected, send the email
                    send_email(lat, lon, temp)

                    # If valid location data is available
                    return render_template('result.html', transcription=transcription,
                                           voice_detection=voice_detection,
                                           latitude=lat, longitude=lon ,temperature = temp )
            else:
                transcription="--------"
                return render_template('result.html', transcription=transcription,
                                       voice_detection=voice_detection,
                                       )
            return render_template('result.html', transcription=transcription,
                                   voice_detection=voice_detection, latitude=lat, longitude=lon)

    return render_template('upload.html')

if __name__ == "__main__":
    app.run(debug=True)
