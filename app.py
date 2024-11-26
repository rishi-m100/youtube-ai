from flask import Flask, render_template, request
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv('GENAI_API_KEY'))

app = Flask(__name__)
def extract_video_id(url):
    youtube_regex = (
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    match = re.match(youtube_regex, url)
    return match.group(6) if match else None

def format_summary(text):

    parts = text.split("**Key Points:**")
    if len(parts) != 2:
        return {"summary": text, "key_points": []}
    
    summary = parts[0].replace("**Summary**", "").strip()
    
    key_points = []
    for point in parts[1].split("*")[1:]:

        point = point.strip()
        if point:

            point = point.replace("**", "").strip()
            key_points.append(point)
    
    return {
        "summary": summary,
        "key_points": key_points
    }

def get_summary(video_id):
    try:
        # Get transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = "\n".join([entry['text'] for entry in transcript])
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = transcript_text + "\n" + "Summarize this text in 7-10 detailed sentences. Then create a 10-bullet point list of the key points."
        response = model.generate_content(prompt)
        formatted = format_summary(response.candidates[0].content.parts[0].text)
        return formatted
    except Exception as e:
        return {"summary": str(e), "key_points": []}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        video_id = extract_video_id(url)
        if video_id:
            summary_data = get_summary(video_id)
            return render_template('index.html', 
                                summary=summary_data['summary'], 
                                key_points=summary_data['key_points'], 
                                video_id=video_id)
        return render_template('index.html', error="Invalid YouTube URL")
    return render_template('index.html')


with open('templates/index.html', 'w') as f:
    f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Transcript Summarizer</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100 min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <div class="max-w-3xl mx-auto">
            <h1 class="text-4xl font-bold text-center mb-8 text-gray-800">
                YouTube Transcript Summarizer
            </h1>
            
            <form method="POST" class="mb-8">
                <div class="flex gap-4">
                    <input 
                        type="text" 
                        name="url" 
                        placeholder="Enter YouTube URL" 
                        class="flex-1 p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                    >
                    <button 
                        type="submit" 
                        class="bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600 transition-colors"
                    >
                        Summarize
                    </button>
                </div>
            </form>

            {% if error %}
            <div class="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-8" role="alert">
                <p>{{ error }}</p>
            </div>
            {% endif %}

            {% if video_id %}
            <div class="mb-8">
                <div class="aspect-w-16 aspect-h-9">
                    <iframe 
                        class="w-full h-96 rounded-lg shadow-lg"
                        src="https://www.youtube.com/embed/{{ video_id }}"
                        frameborder="0"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowfullscreen
                    ></iframe>
                </div>
            </div>
            {% endif %}

            {% if summary %}
            <div class="bg-white rounded-lg shadow-lg p-6 space-y-6">
                <div>
                    <h2 class="text-2xl font-semibold mb-4 text-gray-800">Summary</h2>
                    <div class="prose max-w-none text-gray-700">
                        {{ summary }}
                    </div>
                </div>
                
                {% if key_points %}
                <div>
                    <h2 class="text-2xl font-semibold mb-4 text-gray-800">Key Points</h2>
                    <ul class="list-disc pl-6 space-y-2 text-gray-700">
                        {% for point in key_points %}
                        <li>{{ point }}</li>
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}
            </div>
            {% endif %}
        </div>
    </div>
</body>
</html>
    """)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)