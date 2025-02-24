import sys
import os
import json
import time
import random
import numpy as np
import cv2
from enum import Enum
from typing import Dict, Tuple, List, Optional 
from pathlib import Path  
import pygame

# Constants
FPS = 60
DEFAULT_WINDOW_SIZE = (1000, 1000)
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
                 background_path: Optional[str] = None):
        
        pygame.init()
        pygame.mixer.init()
        
        # Get base directory for relative paths
        self.base_dir = Path(__file__).parent.parent
        
        self.window_size = window_size
        self.character_scale = character_scale
        self.character_position = character_position or (window_size[0] // 2, window_size[1] // 2)
        self.flip_vertical = flip_vertical
        
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
        self.body_image = self.load_image(self.base_dir / "assets/norris/body.png")
        
        # Load visemes
        self.viseme_images = {}
        viseme_path = self.base_dir / "assets/norris/visemes"
        for filename in ["aei.png", "bmp.png", "cdgknstxyz.png", "ee.png", 
                        "fv.png", "l.png", "o.png", "qw.png", "r.png", 
                        "s.png", "shch.png", "th.png", "uw.png", "neutral.png"]:
            self.viseme_images[filename] = self.load_image(viseme_path / filename)
        
        # Load blink images - updated for four-stage blink
        self.blink_images = {}
        blink_path = self.base_dir / "assets/norris/blink"
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

    def draw_frame(self, viseme_filename: str, blink_filename: str, current_time: float, surface=None):
        """Draw a single frame of animation"""
        surface = surface or self.screen
        surface.fill((0, 0, 0, 0))
        
        if self.background_image:
            surface.blit(self.background_image, (0, 0))
        
        offset_x, offset_y, movement_scale = self.movement.get_offset(current_time)
        total_scale = self.character_scale * movement_scale
        
        # Draw all components in order: body, viseme, blink
        components = [
            (self.body_image, None),
            (self.viseme_images.get(viseme_filename), viseme_filename),
            (self.blink_images.get(blink_filename), blink_filename)
        ]
        
        for image, _ in components:
            if image:
                scaled_size = (
                    int(image.get_width() * total_scale),
                    int(image.get_height() * total_scale)
                )
                scaled_image = pygame.transform.smoothscale(image, scaled_size)
                
                if self.flip_vertical:
                    scaled_image = pygame.transform.flip(scaled_image, True, False)
                
                image_rect = scaled_image.get_rect(center=(
                    self.character_position[0] + offset_x,
                    self.character_position[1] + offset_y
                ))
                surface.blit(scaled_image, image_rect)
        
        if surface == self.screen:
            pygame.display.flip()

    def get_current_viseme(self, current_time: float) -> str:
        """Get the current viseme based on time"""
        for frame in self.animation_data:
            if frame["start_time"] <= current_time <= frame["end_time"]:
                return frame["viseme"]
        return "neutral.png"

    def preview_animation(self):
        """Preview the animation in real-time"""
        running = True
        self.start_time = time.time()
        paused = False
        pause_time = 0
        
        if self.audio:
            self.audio.play()
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                ):
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        paused = not paused
                        if paused:
                            pause_time = time.time()
                            if self.audio:
                                pygame.mixer.pause()
                        else:
                            self.start_time += time.time() - pause_time
                            if self.audio:
                                pygame.mixer.unpause()
                    elif event.key == pygame.K_r:
                        self.start_time = time.time()
                        self.blink_state = BlinkState()
                        if self.audio:
                            self.audio.stop()
                            self.audio.play()

            if not paused:
                current_time = time.time() - self.start_time
                if self.audio and current_time > self.audio_length:
                    running = False
                    break
                
                viseme = self.get_current_viseme(current_time)
                blink = self.blink_state.update(current_time)
                self.draw_frame(viseme, blink, current_time)

            self.clock.tick(FPS)

        if self.audio:
            self.audio.stop()
        pygame.quit()

    def export_video(self, output_path: str = "output.mp4", fps: int = FPS):
        """Export animation to video file"""
        print("Starting video export...")
        
        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        duration = self.audio_length if self.audio_length > 0 else max(
            frame["end_time"] for frame in self.animation_data
        )
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, self.window_size)
        temp_screen = pygame.Surface(self.window_size, pygame.SRCALPHA)
        
        frame_count = int(duration * fps)
        for i in range(frame_count):
            current_time = i / fps
            
            viseme = self.get_current_viseme(current_time)
            blink = self.blink_state.update(current_time)
            self.draw_frame(viseme, blink, current_time, temp_screen)
            
            frame_data = pygame.surfarray.array3d(temp_screen)
            frame_data = cv2.cvtColor(frame_data, cv2.COLOR_RGB2BGR)
            frame_data = np.transpose(frame_data, (1, 0, 2))
            
            out.write(frame_data)
            
            if i % fps == 0:
                print(f"Processed {i/fps:.1f}s of {duration:.1f}s")
        
        out.release()
        print(f"Video exported to {output_path}")
        
        if self.audio_path:
            audio_path = Path(self.audio_path)
            if not audio_path.is_absolute():
                audio_path = self.base_dir / audio_path
            if audio_path.exists():
                print("Adding audio...")
                temp_video = output_path.with_name(output_path.stem + "_temp" + output_path.suffix)
                output_path.rename(temp_video)
                os.system(f'ffmpeg -i {temp_video} -i {audio_path} -c:v copy -c:a aac {output_path}')
                temp_video.unlink()
                print("Audio added successfully")

def main():
    # Set your window size and paths
    window_size = (1000, 1000)
    audio_path = "/Users/nervous/Documents/GitHub/toon-in/data/audio/audio.wav"
    background_path = "/Users/nervous/Documents/GitHub/toon-in/assets/background/norris_background.png"
    
    # Create animation instance with custom character scale and position
    animation = MouthAnimation(
        window_size=window_size,
        character_scale=0.2,  # Adjust this to change character size
        character_position=(700, 625),  # Adjust x,y coordinates
        flip_vertical=False,  # Set to True to flip the animation vertically
        audio_path=audio_path,
        background_path=background_path,
    )
    
    # Choose whether to preview or export
    animation.preview_animation()
    #animation.export_video("/Users/nervous/Documents/GitHub/toon-in/output/norris/output.mp4", fps=60)

if __name__ == "__main__":
    main()