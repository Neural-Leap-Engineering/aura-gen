from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
import subprocess
import gradio as gr
import requests
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
import os
from PIL import Image
from io import BytesIO
import requests
from PIL import Image
from io import BytesIO
import openai
import json
import requests
import boto3
from io import BytesIO
from PIL import Image
import json
import gradio as gr
import imgkit
import base64
import uuid
import os


AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")

AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

api_key = os.environ.get("api_key")

openai.api_key = os.environ.get("Openai_API")

openai_api_key = os.environ.get("Openai_API")

model_name = "gpt-3.5-turbo"

rapid_api_key = os.environ.get("rapid_api_key")

def generate_title_and_subtitles(prompt, model_name, keyword):
    chat_model = ChatOpenAI(temperature=0, openai_api_key=openai_api_key, model_name=model_name)
    
    # Generate content with keyword
    messages = [HumanMessage(content=prompt+keyword)]
    content = chat_model.predict_messages(messages).content
    
    # Try to split the content into title and subtitle based on the keyword
    try:
        title, subtitle = content.split(keyword, 1)
    except ValueError:
        # Handle the case when the keyword is not found
        title = content
        subtitle = content
    
    # Remove leading and trailing spaces from title and subtitle
    title = title.strip()
    subtitle = subtitle.strip()

    struture=[{'title': title, 'subtitles': [subtitle]}]
    print(struture)
    # Return title and subtitle as a tuple
    return struture

def generate_images(structure):
    # Create a dictionary to store S3 file paths grouped by title
    image_dict = {}

    # Iterate through each article
    for i, art in enumerate(structure):
        title = art['title']

        # Make a request to generate the image for the title
        r_title = requests.post('https://clipdrop-api.co/text-to-image/v1',
            files={
                'prompt': (None, title, 'text/plain')
            },
            headers={'x-api-key': api_key}
        )

        if r_title.ok:
            image_bytes_title = BytesIO(r_title.content)
            image_title = Image.open(image_bytes_title)

            # Reset the position of the BytesIO object to the beginning
            image_bytes_title.seek(0)

            # Specify the file path and format for the title
            title_file_path = f'generated_title_image_{i}.png'
            image_title.save(title_file_path)

            s3 = boto3.client('s3')
            bucket_name = 'auragenv1'
            content_type = 'image/png'

            # Save the image to S3
            s3.upload_file(title_file_path, bucket_name, title_file_path, ExtraArgs={'ContentType': content_type})

            # Add the S3 file path to the image_dict
            if title in image_dict:
                image_dict[title].append(f'https://auragenv1.s3.amazonaws.com/{title_file_path}')
            else:
                image_dict[title] = [f'https://auragenv1.s3.amazonaws.com/{title_file_path}']

        else:
            r_title.raise_for_status()

        # Iterate through the subtitles for each article
        for j, subtitle in enumerate(art['subtitles']):
            # Make a request to generate the image for the subtitle
            r_subtitle = requests.post('https://clipdrop-api.co/text-to-image/v1',
                files={
                    'prompt': (None, subtitle, 'text/plain')
                },
                headers={'x-api-key': api_key}
            )

            if r_subtitle.ok:
                image_bytes_subtitle = BytesIO(r_subtitle.content)
                image_subtitle = Image.open(image_bytes_subtitle)

                # Reset the position of the BytesIO object to the beginning
                image_bytes_subtitle.seek(0)

                # Specify the file path and format for the subtitle
                subtitle_file_path = f'generated_subtitle_image_{i}_{j}.png'
                image_subtitle.save(subtitle_file_path)

                # Save the image to S3
                s3.upload_file(subtitle_file_path, bucket_name, subtitle_file_path, ExtraArgs={'ContentType': content_type})

                # Add the S3 file path to the image_dict
                if title in image_dict:
                    image_dict[title].append(f'https://auragenv1.s3.amazonaws.com/{subtitle_file_path}')
                else:
                    image_dict[title] = [f'https://auragenv1.s3.amazonaws.com/{subtitle_file_path}']

            else:
                r_subtitle.raise_for_status()

    dict_as_string = json.dumps(image_dict)
    return dict_as_string

def generate_html(dict_as_string):
    
    response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": dict_as_string+", using this multiple dictionary data create html article structure including title subtitle and also the paragraph with image component. use image size width 300px height 300px and images margin must be auto. use all components center align and responsive"}
    ],
    temperature=0.8,
    max_tokens=1500
    )

    # Extracting assistant's response
    assistant_response = response['choices'][0]['message']['content']

    #print(assistant_response)
    print(assistant_response)
    return assistant_response


def final(key_word, num_terms):
    key_word_list = rapid_api(key_word) if key_word else []
    
    combined_data = []
    # Loop through each keyword to generate titles and subtitles
    for keyword in key_word_list[:int(num_terms)]:
        article_data = generate_title_and_subtitles(keyword, model_name, keyword)
        combined_data.extend(article_data)

    # Generate images for the combined data
    combined_script = generate_images(combined_data)

    # Generate the HTML structure based on the data and images
    final_html = generate_html(combined_script)

    with open("output.html", "w") as html_file:
        html_file.write(final_html)

    return gr.HTML(final_html)
    

def rapid_api(key_word):
    url = "https://seo-keyword-research.p.rapidapi.com/keynew.php"
    querystring = {"keyword": key_word, "country": "in"}
    headers = {
        "X-RapidAPI-Key": rapid_api_key,
        "X-RapidAPI-Host": "seo-keyword-research.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        data = response.json()
        text_values = [item['text'] for item in data]
        return text_values
    else:
        return []
    

interface = gr.Interface(
    fn=final, 
    inputs=[
        gr.Textbox(label="Key Word", placeholder="Enter keyword..."),
        gr.Number(label="Number of Terms")
    ],
    outputs=gr.HTML(label="Generated articles will appear here...")
)

if __name__ == "__main__":
    interface.launch()