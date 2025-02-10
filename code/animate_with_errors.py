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
import logging
from pathlib import Path
from contextlib import contextmanager
import tempfile

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('animation.log'),
        logging.StreamHandler()
    ]
)

class AnimationError(Exception):
    """Custom exception for animation-related errors"""
    pass

@contextmanager
def temporary_directory():
    """Context manager for creating and cleaning up temporary directories"""
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logging.error(f"Error cleaning up temporary directory {temp_dir}: {e}")

@contextmanager
def pygame_surface(resolution):
    """Context manager for pygame surface initialization and cleanup"""
    if not pygame.get_init():
        pygame.init()
    surface = pygame.Surface(resolution)
    try:
        yield surface
    finally:
        surface = None  # Help garbage collection

class ResourceManager:
    """Manages loading and caching of resources"""
    def __init__(self):
        self._cache = {}
        
    def get_image(self, path):
        """Load and cache an image"""
        if path not in self._cache:
            try:
                self._cache[path] = pygame.image.load(path)
            except pygame.error as e:
                raise AnimationError(f"Failed to load image {path}: {e}")
        return self._cache[path]
    
    def clear_cache(self):
        """Clear the resource cache"""
        self._cache.clear()

def check_file_exists(filepath, description):
    """Verify if a required file exists"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Required {description} file not found: {filepath}")

def load_subtitles(subtitle_file):
    """Load subtitles with error handling"""
    try:
        check_file_exists(subtitle_file, "subtitles")
        with open(subtitle_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise AnimationError("Subtitle file must contain a list of subtitle entries")
        return data
    except json.JSONDecodeError as e:
        raise AnimationError(f"Invalid JSON in subtitles file: {e}")
    except Exception as e:
        raise AnimationError(f"Error loading subtitles: {e}")

def load_viseme_data(viseme_file):
    """Load viseme data with error handling"""
    try:
        check_file_exists(viseme_file, "viseme")
        with open(viseme_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise AnimationError("Viseme file must contain a list of viseme entries")
        return data
    except json.JSONDecodeError as e:
        raise AnimationError(f"Invalid JSON in viseme file: {e}")
    except Exception as e:
        raise AnimationError(f"Error loading viseme data: {e}")

def generate_blink_timings(total_duration):
    """Generate random blink timings with validation"""
    if total_duration <= 0:
        raise ValueError("Total duration must be positive")
    try:
        current_time = 0.0
        blinks = []
        while current_time < total_duration:
            blink_start = current_time + random.uniform(2, 7)
            blinks.append((blink_start, blink_start + 0.1, blink_start + 0.2, blink_start + 0.3))
            current_time = blink_start
        return blinks
    except Exception as e:
        raise AnimationError(f"Error generating blink timings: {e}")

def generate_animated_background(output_path, frame_size=(1920, 1080), fps=24, duration=None):
    """Generate animated background with error handling and resource management"""
    try:
        if duration is None or duration <= 0:
            raise ValueError("Invalid duration specified")

        svg_template = """
        <svg width="100%" height="100%" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <rect width="100%" height="100%" fill="#f1f1f1" />
            <path fill="#bf0a30" fill-opacity="0.7" d="M-100 -100L200 -100L200 {y1}L-100 {y1}Z" transform="rotate({r1}, 50, 0)"/>
            <path fill="#ffffff" fill-opacity="0.7" d="M-100 -100L200 -100L200 {y2}L-100 {y2}Z" transform="rotate({r2}, 50, 0)"/>
            <path fill="#002868" fill-opacity="0.2" d="M-100 -100L200 -100L200 {y3}L-100 {y3}Z" transform="rotate({r3}, 50, 0)"/>
        </svg>
        """
        
        num_frames = int(fps * duration)
        
        with temporary_directory() as temp_frames_dir:
            for frame in range(num_frames):
                try:
                    r1 = -10 + 20 * np.sin(frame * 2 * np.pi / (fps * 5))
                    r2 = -30 + 60 * np.sin(frame * 2 * np.pi / (fps * 12.5))
                    r3 = 40 - 80 * np.sin(frame * 2 * np.pi / (fps * 30))
                    y1, y2, y3 = 50 + 10 * np.sin(frame * 0.1), 50 + 15 * np.sin(frame * 0.08), 20 + 20 * np.sin(frame * 0.05)
                    svg_content = svg_template.format(y1=y1, y2=y2, y3=y3, r1=r1, r2=r2, r3=r3)
                    
                    png_bytes = cairosvg.svg2png(bytestring=svg_content, output_width=frame_size[0], output_height=frame_size[1])
                    
                    with Image.open(BytesIO(png_bytes)) as img:
                        frame_path = os.path.join(temp_frames_dir, f"frame_{frame:04d}.png")
                        img.save(frame_path)
                        
                except Exception as e:
                    logging.error(f"Error generating frame {frame}: {e}")
                    continue
                    
            return temp_frames_dir
    except Exception as e:
        raise AnimationError(f"Error generating animated background: {e}")

def render_animation_to_video(viseme_data, subtitle_data, background_frames_dir, output_video, fps, resolution, 
                            temp_dir, head_image_path, blink_half_path, blink_closed_path, viseme_directory, 
                            emotions_directory, audio_file):
    """Render animation with resource management and error handling"""
    resource_manager = ResourceManager()
    
    try:
        # Validate inputs
        for filepath in [head_image_path, blink_half_path, blink_closed_path, audio_file]:
            check_file_exists(filepath, os.path.basename(filepath))
        
        check_file_exists(background_frames_dir, "background frames directory")
        check_file_exists(viseme_directory, "viseme directory")
        check_file_exists(emotions_directory, "emotions directory")
        
        if not viseme_data or not subtitle_data:
            raise AnimationError("Empty viseme or subtitle data")
        
        with temporary_directory() as render_temp_dir:
            with pygame_surface(resolution) as screen:
                font = pygame.font.Font(None, 144)
                
                # Load images using resource manager
                head_image = resource_manager.get_image(head_image_path)
                blink_half = resource_manager.get_image(blink_half_path)
                blink_closed = resource_manager.get_image(blink_closed_path)
                
                # Load viseme images
                viseme_images = {}
                for filename in os.listdir(viseme_directory):
                    if filename.endswith(".png"):
                        viseme_images[filename] = resource_manager.get_image(os.path.join(viseme_directory, filename))
                
                total_frames = int(viseme_data[-1]["end_time"] * fps)
                blinks = generate_blink_timings(viseme_data[-1]["end_time"])
                frame_time = 1 / fps
                current_time = 0.0
                
                # Create temporary video file
                temp_video = os.path.join(render_temp_dir, "temp_video.mp4")
                
                # Render frames with progress bar
                for frame_number in tqdm(range(total_frames), desc="Rendering Frames"):
                    try:
                        bg_frame_path = os.path.join(background_frames_dir, 
                                                   f"frame_{frame_number % len(os.listdir(background_frames_dir)):04d}.png")
                        bg_image = resource_manager.get_image(bg_frame_path)
                        screen.blit(bg_image, (0, 0))
                        
                        head_x = resolution[0] // 2 - head_image.get_width() // 2
                        head_y = resolution[1] // 2 - head_image.get_height() // 2 + resolution[1] // 4
                        screen.blit(head_image, (head_x, head_y))
                        
                        # Handle visemes
                        viseme_to_render = "sad.png"
                        for entry in viseme_data:
                            if entry["start_time"] <= current_time < entry["end_time"]:
                                viseme_to_render = entry["mouth_shape"]
                                break
                                
                        if viseme_to_render in viseme_images:
                            screen.blit(viseme_images[viseme_to_render], (head_x, head_y))
                        
                        # Handle subtitles
                        subtitle_text = ""
                        for subtitle in subtitle_data:
                            if subtitle["start_time"] <= current_time < subtitle["end_time"]:
                                subtitle_text = subtitle["word"]
                                break
                                
                        if subtitle_text:
                            text_surface = font.render(subtitle_text, True, (255, 255, 255))
                            text_rect = text_surface.get_rect(center=(resolution[0] // 2, resolution[1] - 1000))
                            screen.blit(text_surface, text_rect)
                        
                        # Handle blinks
                        for blink_start, half, closed, half_back in blinks:
                            if blink_start <= current_time < half:
                                screen.blit(blink_half, (head_x, head_y))
                            elif half <= current_time < closed:
                                screen.blit(blink_closed, (head_x, head_y))
                            elif closed <= current_time < half_back:
                                screen.blit(blink_half, (head_x, head_y))
                        
                        frame_path = os.path.join(render_temp_dir, f"frame_{frame_number:04d}.png")
                        pygame.image.save(screen, frame_path)
                        current_time += frame_time
                        
                    except Exception as e:
                        logging.error(f"Error rendering frame {frame_number}: {e}")
                        continue
                
                # Compile video with FFmpeg
                try:
                    subprocess.run(
                        ["ffmpeg", "-y", "-framerate", str(fps), "-i", 
                         os.path.join(render_temp_dir, "frame_%04d.png"), 
                         "-c:v", "libx264", "-pix_fmt", "yuv420p", temp_video],
                        check=True, capture_output=True, text=True
                    )
                    
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", temp_video, "-i", audio_file,
                         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                         "-shortest", output_video.replace(".mp4", "_final.mp4")],
                        check=True, capture_output=True, text=True
                    )
                    
                except subprocess.CalledProcessError as e:
                    raise AnimationError(f"FFmpeg error: {e.stderr}")
                
    except Exception as e:
        raise AnimationError(f"Error in animation rendering: {e}")
    finally:
        # Clear resource manager cache
        resource_manager.clear_cache()

if __name__ == "__main__":
    try:
        # Define paths
        base_dir = Path("/Users/nervous/Documents/GitHub/toon-in")
        viseme_file = base_dir / "data/viseme_data.json"
        subtitle_file = base_dir / "data/word_data.json"
        background_path = base_dir / "assets/background/generated_background.png"
        output_video = base_dir / "output/clip.mp4"
        audio_file = base_dir / "data/audio/audio.wav"
        head_image_path = base_dir / "assets/bear/body.png"
        blink_half_path = base_dir / "assets/bear/blink/half.png"
        blink_closed_path = base_dir / "assets/bear/blink/closed.png"
        viseme_directory = base_dir / "assets/bear/visemes/"
        emotions_directory = base_dir / "assets/bear/emotions/"
        
        # Animation parameters
        fps = 24
        resolution = (1920, 1080)
        
        # Load data and generate animation
        logging.info("Starting animation generation")
        subtitle_data = load_subtitles(subtitle_file)
        viseme_data = load_viseme_data(viseme_file)
        
        with temporary_directory() as temp_dir:
            background_frames_dir = generate_animated_background(
                background_path, 
                duration=viseme_data[-1]["end_time"]
            )
            
            render_animation_to_video(
                viseme_data, subtitle_data, background_frames_dir, 
                output_video, fps, resolution, temp_dir, 
                head_image_path, blink_half_path, blink_closed_path, 
                viseme_directory, emotions_directory, audio_file
            )
        
        logging.info("Animation completed successfully")
        
    except Exception as e:
        logging.error(f"Animation generation failed: {e}")
        raise