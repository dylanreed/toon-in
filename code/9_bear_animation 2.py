from tqdm import tqdm
import pygame
import json
import os
import subprocess
import random
import shutil
import cv2
import numpy as np
import cairosvg
from PIL import Image
from io import BytesIO
import re
import whisper

# Function to load subtitles
def load_subtitles(subtitle_file):
    with open(subtitle_file, "r", encoding="utf-8") as f:
        return json.load(f)

# Function to load viseme data
def load_viseme_data(viseme_file):
    with open(viseme_file, "r", encoding="utf-8") as f:
        return json.load(f)
    
# Function to generate random blink timings
def generate_blink_timings(total_duration):
    current_time = 0.0
    blinks = []
    while current_time < total_duration:
        blink_start = current_time + random.uniform(2, 7)
        blinks.append((blink_start, blink_start + 0.1, blink_start + 0.2, blink_start + 0.3))
        current_time = blink_start
    return blinks

# Function to load viseme images
def load_viseme_images(viseme_directory):
    viseme_images = {}
    for filename in os.listdir(viseme_directory):
        if filename.endswith(".png"):
            viseme_images[filename] = pygame.image.load(os.path.join(viseme_directory, filename))
    return viseme_images

# Function to generate animated background
def generate_animated_background(output_path, frame_size=(1920, 1080), fps=24, duration=None):
    svg_template = """
    <svg width="100%" height="100%" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <rect width="100%" height="100%" fill="#f1f1f1" />
        <path fill="#bf0a30" fill-opacity="0.7" d="M-100 -100L200 -100L200 {y1}L-100 {y1}Z" transform="rotate({r1}, 50, 0)"/>
        <path fill="#ffffff" fill-opacity="0.7" d="M-100 -100L200 -100L200 {y2}L-100 {y2}Z" transform="rotate({r2}, 50, 0)"/>
        <path fill="#002868" fill-opacity="0.2" d="M-100 -100L200 -100L200 {y3}L-100 {y3}Z" transform="rotate({r3}, 50, 0)"/>
    </svg>
    """
    if duration is None:
        duration = viseme_data[-1]["end_time"]  # Use total duration of animation
    num_frames = int(fps * duration)

    temp_frames_dir = os.path.join(os.path.dirname(output_path), "background_frames")
    os.makedirs(temp_frames_dir, exist_ok=True)
    for frame in range(num_frames):
        r1 = -10 + 20 * np.sin(frame * 2 * np.pi / (fps * 5))
        r2 = -30 + 60 * np.sin(frame * 2 * np.pi / (fps * 12.5))
        r3 = 40 - 80 * np.sin(frame * 2 * np.pi / (fps * 30))
        y1, y2, y3 = 50 + 10 * np.sin(frame * 0.1), 50 + 15 * np.sin(frame * 0.08), 20 + 20 * np.sin(frame * 0.05)
        svg_content = svg_template.format(y1=y1, y2=y2, y3=y3, r1=r1, r2=r2, r3=r3)
        png_bytes = cairosvg.svg2png(bytestring=svg_content, output_width=frame_size[0], output_height=frame_size[1])
        img = Image.open(BytesIO(png_bytes))
        frame_path = os.path.join(temp_frames_dir, f"frame_{frame:04d}.png")
        img.save(frame_path)
    return temp_frames_dir

# Function to render animation
def render_animation_to_video(viseme_data, subtitle_data, background_frames_dir, output_video, fps, resolution, temp_dir, head_image_path, blink_half_path, blink_closed_path, viseme_directory, emotions_directory, audio_file):
    pygame.init()
    screen = pygame.Surface(resolution)
    font = pygame.font.Font(None, 144)

    head_image = pygame.image.load(head_image_path)
    blink_half = pygame.image.load(blink_half_path)
    blink_closed = pygame.image.load(blink_closed_path)
    viseme_images = load_viseme_images(viseme_directory)
    os.makedirs(temp_dir, exist_ok=True)
    total_frames = int(viseme_data[-1]["end_time"] * fps)
    blinks = generate_blink_timings(viseme_data[-1]["end_time"])
    frame_time = 1 / fps
    current_time = 0.0
    temp_video = output_video.replace(".mp4", "_no_audio.mp4")


    for frame_number in tqdm(range(total_frames), desc="Rendering Frames"):
        bg_frame_path = os.path.join(background_frames_dir, f"frame_{frame_number % len(os.listdir(background_frames_dir)):04d}.png")
        bg_image = pygame.image.load(bg_frame_path)
        screen.blit(bg_image, (0, 0))
        head_x = resolution[0] // 2 - head_image.get_width() // 2
        head_y = resolution[1] // 2 - head_image.get_height() // 2 + resolution[1] // 4
        screen.blit(head_image, (head_x, head_y))
        viseme_to_render = "sad.png"
        for entry in viseme_data:
            if entry["start_time"] <= current_time < entry["end_time"]:
                viseme_to_render = entry["mouth_shape"]
                break
        if viseme_to_render in viseme_images:
            screen.blit(viseme_images[viseme_to_render], (head_x, head_y))
        subtitle_text = ""
        for subtitle in subtitle_data:
            if subtitle["start_time"] <= current_time < subtitle["end_time"]:
                subtitle_text = subtitle["word"]
                break
        if subtitle_text:
            text_surface = font.render(subtitle_text, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(resolution[0] // 2, resolution[1] -1000))
            screen.blit(text_surface, text_rect)      
        for blink_start, half, closed, half_back in blinks:
            if blink_start <= current_time < half:
                screen.blit(blink_half, (head_x, head_y))
            elif half <= current_time < closed:
                screen.blit(blink_closed, (head_x, head_y))
            elif closed <= current_time < half_back:
                screen.blit(blink_half, (head_x, head_y))      
        frame_path = os.path.join(temp_dir, f"frame_{frame_number:04d}.png")
        pygame.image.save(screen, frame_path)
        current_time += frame_time

    subprocess.run(["ffmpeg", "-y", "-framerate", str(fps), "-i", os.path.join(temp_dir, "frame_%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", temp_video], check=True)
    subprocess.run(["ffmpeg", "-y", "-i", temp_video, "-i", audio_file, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", output_video.replace(".mp4", "_final.mp4")], check=True)

if __name__ == "__main__":
    viseme_file = "/Users/nervous/Documents/GitHub/toon-in/data/viseme_data.json"
    subtitle_file = "/Users/nervous/Documents/GitHub/toon-in/data/word_data.json"
    background_path = "/Users/nervous/Documents/GitHub/toon-in/assets/background/generated_background.png"
    output_video = "/Users/nervous/Documents/GitHub/toon-in/output/clip.mp4"
    audio_file = "/Users/nervous/Documents/GitHub/toon-in/data/audio/audio.wav"
    head_image_path = "/Users/nervous/Documents/GitHub/toon-in/assets/bear/body.png"
    blink_half_path = "/Users/nervous/Documents/GitHub/toon-in/assets/bear/blink/half.png"
    blink_closed_path = "/Users/nervous/Documents/GitHub/toon-in/assets/bear/blink/closed.png"
    viseme_directory = "/Users/nervous/Documents/GitHub/toon-in/assets/bear/visemes/"
    emotions_directory = "/Users/nervous/Documents/GitHub/toon-in/assets/bear/emotions/"
    fps = 24
    resolution = (1920, 1080)
    temp_dir = "/Users/nervous/Documents/GitHub/toon-in/data/tmp_frames/"
    
    subtitle_data = load_subtitles(subtitle_file)
    viseme_data = load_viseme_data(viseme_file)
    background_frames_dir = generate_animated_background(background_path, duration=viseme_data[-1]["end_time"])
    render_animation_to_video(viseme_data, subtitle_data, background_frames_dir, output_video, fps, resolution, temp_dir, head_image_path, blink_half_path, blink_closed_path, viseme_directory, emotions_directory, audio_file)

