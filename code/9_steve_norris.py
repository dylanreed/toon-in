import sys
import os
import json
import time
import random
import numpy as np
import cv2
import argparse
from enum import Enum
from typing import Dict, Tuple, List, Optional 
from pathlib import Path  
import pygame
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import argparse

# Constants
FPS = 60
DEFAULT_WINDOW_SIZE = (1020,1080)
BLINK_DURATION = 0.15
BLINK_INTERVAL = (2, 6)

class BlinkState:
    def __init__(self):
        self.is_blinking = False
        self.blink_start = 0
        self.blink_duration = BLINK_DURATION
        self.next_blink = random.uniform(*BLINK_INTERVAL)
        self.current_frame = "open"
        
        # Pre-calculate blink thresholds for 4-stage blink
        self._blink_thresholds = [
            (0.15, "half"),     # First stage - eyes start to close
            (0.30, "third"),    # Second stage - eyes more closed
            (0.45, "closed"),   # Third stage - eyes fully closed
            (0.60, "closed"),   # Hold closed position
            (0.75, "third"),    # Start opening - third open
            (0.90, "half"),     # Half open
            (1.0, "open")       # Fully open
        ]

    def update(self, current_time: float) -> str:
        if not self.is_blinking and current_time >= self.next_blink:
            self.is_blinking = True
            self.blink_start = current_time
            
        if self.is_blinking:
            blink_time = current_time - self.blink_start
            relative_time = blink_time / self.blink_duration
            
            for threshold, frame in self._blink_thresholds:
                if relative_time < threshold:
                    self.current_frame = frame
                    break
            else:
                self.is_blinking = False
                self.current_frame = "open"
                self.next_blink = current_time + random.uniform(*BLINK_INTERVAL)
                
        return f"{self.current_frame}.png"

class Movement:
    def __init__(self):
        self.bob_amplitude = 0.5
        self.sway_amplitude = 0.5
        self.bob_frequency = 1
        self.sway_frequency = 0.75
        self.micro_movement_scale = 0.5
        self.zoom_duration = 10.0
        self.zoom_start_scale = 1.0
        self.zoom_end_scale = 1.0
        
        # Pre-calculate constants
        self.random_offset = random.uniform(0, 2 * np.pi)
        self.noise_offset_x = random.uniform(0, 1000)
        self.noise_offset_y = random.uniform(0, 1000)
        self.noise_speed = 0.5
        self._2pi = 2 * np.pi

    def get_offset(self, current_time: float) -> Tuple[float, float, float]:
        # Optimize calculations by reducing repetitive operations
        time_bob = current_time * self.bob_frequency * self._2pi + self.random_offset
        time_sway = current_time * self.sway_frequency * self._2pi + self.random_offset
        time_noise = current_time * self.noise_speed
        
        bob = np.sin(time_bob) * self.bob_amplitude
        sway = np.sin(time_sway) * self.sway_amplitude
        
        noise_x = np.sin(time_noise + self.noise_offset_x) * self.micro_movement_scale
        noise_y = np.sin(time_noise + self.noise_offset_y) * self.micro_movement_scale
        
        zoom_progress = min(current_time / self.zoom_duration, 1.0)
        current_scale = self.zoom_start_scale + (self.zoom_end_scale - self.zoom_start_scale) * zoom_progress
        
        return sway + noise_x, bob + noise_y, current_scale

class MouthAnimation:
    def __init__(self, 
                 window_size: Tuple[int, int] = DEFAULT_WINDOW_SIZE,
                 character_scale: float = 1.0,
                 character_position: Optional[Tuple[int, int]] = None,
                 flip_vertical: bool = False,
                 audio_path: Optional[str] = None,
                 background_path: Optional[str] = None,
                 morph_duration: float = 0.1): 
        
        pygame.init()
        pygame.mixer.init()
        
        # Get base directory for relative paths
        self.base_dir = Path(__file__).parent.parent
        
        self.window_size = window_size
        self.character_scale = character_scale
        self.character_position = character_position or (window_size[0] // 2, window_size[1] // 2)
        self.flip_vertical = flip_vertical
        self.morph_duration = morph_duration
        self.previous_viseme = "neutral.png"
        self.previous_viseme_time = 0
        
        # Initialize display with hardware acceleration
        self.screen = pygame.display.set_mode(window_size, pygame.SRCALPHA | pygame.HWSURFACE | pygame.DOUBLEBUF)
        pygame.display.set_caption("Character Animation")
        
        self.clock = pygame.time.Clock()
        self.start_time = None
        self.audio_path = audio_path
        
        self.blink_state = BlinkState()
        self.movement = Movement()
        
        # Load assets using relative paths
        self._load_assets()
        self._load_background(background_path)
        self._load_audio(audio_path)
        
        self.animation_data = self._load_animation_data()
        self.current_viseme = "neutral.png"

    def _load_assets(self):
        """Load all image assets with proper error handling"""
        # Load body image
        self.body_image = self.load_image(self.base_dir / "assets/steve/body.png")
        
        # Load visemes - updated with specific viseme set
        self.viseme_images = {}
        viseme_path = self.base_dir / "assets/steve/visemes"
        viseme_files = [
            "ee.png",
            "bmp.png",
            "o.png",
            "qw.png",
            "shch.png",
            "r.png",
            "aei.png",
            "th.png",
            "fv.png",
            "l.png",
            "cdgknstxyz.png",
            "neutral.png"
        ]
        # Actually load each viseme image
        for filename in viseme_files:
            full_path = viseme_path / filename
            self.viseme_images[filename] = self.load_image(full_path)
        
        # Load blink images - updated for four-stage blink
        self.blink_images = {}
        blink_path = self.base_dir / "assets/steve/blink"
        for filename in ["open.png", "half.png", "third.png", "closed.png"]:
            self.blink_images[filename] = self.load_image(blink_path / filename)

    def _load_background(self, background_path: Optional[str]):
        """Load background image if provided"""
        self.background_image = None
        if background_path:
            bg_path = Path(background_path)
            if not bg_path.is_absolute():
                bg_path = self.base_dir / bg_path
            if bg_path.exists():
                self.background_image = pygame.image.load(str(bg_path)).convert()
                self.background_image = pygame.transform.scale(self.background_image, self.window_size)

    def _load_audio(self, audio_path: Optional[str]):
        """Load audio file if provided"""
        self.audio = None
        self.audio_length = 0
        
        if audio_path:
            audio_path = Path(audio_path)
            if not audio_path.is_absolute():
                audio_path = self.base_dir / audio_path
            if audio_path.exists():
                self.audio = pygame.mixer.Sound(str(audio_path))
                self.audio_length = self.audio.get_length()

    def _load_animation_data(self) -> List[dict]:
        """Load animation data from JSON file"""
        try:
            animation_path = self.base_dir / "data/viseme_data.json"
            with open(animation_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading animation data: {e}")
            return []

    def load_image(self, path: Path) -> pygame.Surface:
        """Load image with error handling and placeholder generation"""
        try:
            return pygame.image.load(str(path)).convert_alpha()
        except pygame.error as e:
            print(f"Error loading image {path}: {e}")
            return self._create_placeholder_image(path.name)

    @staticmethod
    def _create_placeholder_image(filename: str) -> pygame.Surface:
        """Create a placeholder image for missing assets"""
        placeholder = pygame.Surface((200, 200), pygame.SRCALPHA)
        pygame.draw.rect(placeholder, (255, 0, 0, 128), placeholder.get_rect(), 2)
        font = pygame.font.Font(None, 36)
        text = font.render(filename, True, (255, 0, 0))
        text_rect = text.get_rect(center=placeholder.get_rect().center)
        placeholder.blit(text, text_rect)
        return placeholder

    # ... [other methods remain the same] ...

    def export_video_threaded(self, output_path: str = "output.mp4", fps: int = FPS, num_threads: int = 4):
        """Export animation to video file using multiple threads for faster processing"""
        print(f"Starting multi-threaded video export with {num_threads} threads...")
        
        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create temp directory for frame storage
        temp_dir = Path(tempfile.mkdtemp())
        print(f"Created temporary directory: {temp_dir}")
        
        try:
            duration = self.audio_length if self.audio_length > 0 else max(
                frame["end_time"] for frame in self.animation_data
            )
            
            frame_count = int(duration * fps)
            
            # Split into chunks
            chunk_size = (frame_count + num_threads - 1) // num_threads
            chunks = [(i * chunk_size, min((i + 1) * chunk_size, frame_count)) 
                    for i in range(num_threads)]
            
            # Thread-local storage for viseme morphing
            thread_local = threading.local()
            
            # Function to process a chunk and save frames to disk
            def process_chunk(start_idx, end_idx, thread_id):
                # ... [processing code remains the same] ...
                pass
            
            # Process chunks in parallel
            print(f"Starting parallel processing with {num_threads} threads...")
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                # ... [rest of the method remains the same] ...
                pass
                
        except Exception as e:
            print(f"Error during video export: {e}")
            raise
        
        finally:
            # Clean up temp files
            try:
                print(f"Cleaning up temporary files in {temp_dir}")
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Failed to clean up temp directory: {e}")


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate animation for Dylan')
    parser.add_argument('--audio_path', type=str, default="data/audio/dylan/dylan.wav",
                      help='Path to the audio file')
    parser.add_argument('--background_path', type=str, default="assets/background/blank_background.png",
                      help='Path to the background image')
    parser.add_argument('--output_path', type=str, default="output/dylan/dylan.mp4",
                      help='Path to save the output video')
    parser.add_argument('--threaded', action='store_true', help='Use threaded rendering for faster export')
    parser.add_argument('--num_threads', type=int, default=4, help='Number of threads to use for export')
    args = parser.parse_args()
    
    # Set your window size and paths
    window_size = (1920, 1080)
    
    # Create animation instance with custom character scale and position
    animation = MouthAnimation(
        window_size=window_size,
        character_scale=0.2,
        character_position=(1300, 625),
        flip_vertical=True,
        audio_path=args.audio_path,
        background_path=args.background_path,
    )
    
    # Use export_video directly instead of preview_animation
    animation.export_video(args.output_path, fps=60)

if __name__ == "__main__":
    main()