import pygame
import sys
import os
import json
import time
import random
import numpy as np
import cv2
from enum import Enum
from typing import Dict, Tuple, List

class BlinkState:
    def __init__(self):
        self.is_blinking = False
        self.blink_start = 0
        self.blink_duration = 0.15
        self.next_blink = random.uniform(2, 6)
        self.current_frame = "open"

    def update(self, current_time: float) -> str:
        if not self.is_blinking and current_time >= self.next_blink:
            self.is_blinking = True
            self.blink_start = current_time
            
        if self.is_blinking:
            blink_time = current_time - self.blink_start
            if blink_time < self.blink_duration * 0.2:
                self.current_frame = "half"
            elif blink_time < self.blink_duration * 0.4:
                self.current_frame = "closed"
            elif blink_time < self.blink_duration * 0.6:
                self.current_frame = "closed"
            elif blink_time < self.blink_duration * 0.8:
                self.current_frame = "half"
            elif blink_time < self.blink_duration:
                self.current_frame = "open"
            else:
                self.is_blinking = False
                self.current_frame = "open"
                self.next_blink = current_time + random.uniform(2, 6)
                
        return f"{self.current_frame}.png"

class MouthAnimation:
    def __init__(self, window_size: Tuple[int, int] = (400, 400), audio_path: str = None):
        pygame.init()
        pygame.mixer.init()
        self.window_size = window_size
        self.screen = pygame.display.set_mode(window_size, pygame.SRCALPHA)
        pygame.display.set_caption("Character Animation")
        
        self.clock = pygame.time.Clock()
        self.start_time = None
        self.audio_path = audio_path
        
        # Initialize blink state
        self.blink_state = BlinkState()
        
        # Load all images
        self.body_image = self.load_image("/Users/nervous/Documents/GitHub/toon-in/assets/bear/body.png")
        self.viseme_images = self.load_viseme_images()
        self.blink_images = self.load_blink_images()
        
        # Load animation data
        self.animation_data = self.load_animation_data()
        self.current_viseme = "neutral.png"
        
        # Audio setup
        if audio_path and os.path.exists(audio_path):
            self.audio = pygame.mixer.Sound(audio_path)
            self.audio_length = self.audio.get_length()
        else:
            self.audio = None
            self.audio_length = 0

    def load_image(self, path: str) -> pygame.Surface:
        """Load and scale a single image"""
        try:
            image = pygame.image.load(path).convert_alpha()
            scale_factor = min(
                self.window_size[0] / image.get_width(),
                self.window_size[1] / image.get_height()
            )
            
            if scale_factor != 1:
                new_size = (
                    int(image.get_width() * scale_factor),
                    int(image.get_height() * scale_factor)
                )
                image = pygame.transform.smoothscale(image, new_size)
            return image
        except pygame.error as e:
            print(f"Error loading image {path}: {e}")
            return self.create_placeholder_image(os.path.basename(path))

    def load_animation_data(self) -> List[dict]:
        """Load and parse the viseme timing data from JSON"""
        try:
            with open('/Users/nervous/Documents/GitHub/toon-in/data/viseme_data.json', 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"Error loading animation data: {e}")
            return []

    def load_viseme_images(self) -> Dict[str, pygame.Surface]:
        """Load all viseme images"""
        visemes = {}
        viseme_path = "/Users/nervous/Documents/GitHub/toon-in/assets/bear/visemes"
        
        viseme_files = [
            "aei.png", "bmp.png", "cdgknstxyz.png", "ee.png", 
            "fv.png", "l.png", "o.png", "qw.png", "r.png", 
            "s.png", "shch.png", "th.png", "uw.png", "neutral.png"
        ]
        
        for filename in viseme_files:
            full_path = os.path.join(viseme_path, filename)
            visemes[filename] = self.load_image(full_path)
            
        return visemes

    def load_blink_images(self) -> Dict[str, pygame.Surface]:
        """Load all blink images"""
        blinks = {}
        blink_path = "/Users/nervous/Documents/GitHub/toon-in/assets/bear/blink"
        
        blink_files = ["open.png", "half.png", "closed.png"]
        
        for filename in blink_files:
            full_path = os.path.join(blink_path, filename)
            blinks[filename] = self.load_image(full_path)
            
        return blinks

    def create_placeholder_image(self, filename: str) -> pygame.Surface:
        """Create a placeholder image for missing images"""
        placeholder = pygame.Surface((200, 200), pygame.SRCALPHA)
        pygame.draw.rect(placeholder, (255, 0, 0, 128), placeholder.get_rect(), 2)
        
        font = pygame.font.Font(None, 36)
        text = font.render(filename, True, (255, 0, 0))
        text_rect = text.get_rect(center=placeholder.get_rect().center)
        placeholder.blit(text, text_rect)
        
        return placeholder

    def draw_frame(self, viseme_filename: str, blink_filename: str, surface=None):
        """Draw all layers of the character"""
        if surface is None:
            surface = self.screen
            
        # Clear screen with transparency
        surface.fill((0, 0, 0, 0))
        
        # Draw body (base layer)
        if self.body_image:
            image_rect = self.body_image.get_rect(center=(
                self.window_size[0] // 2,
                self.window_size[1] // 2
            ))
            surface.blit(self.body_image, image_rect)
        
        # Draw viseme (middle layer)
        if viseme_filename in self.viseme_images:
            image_rect = self.viseme_images[viseme_filename].get_rect(center=(
                self.window_size[0] // 2,
                self.window_size[1] // 2
            ))
            surface.blit(self.viseme_images[viseme_filename], image_rect)
        
        # Draw blink (top layer)
        if blink_filename in self.blink_images:
            image_rect = self.blink_images[blink_filename].get_rect(center=(
                self.window_size[0] // 2,
                self.window_size[1] // 2
            ))
            surface.blit(self.blink_images[blink_filename], image_rect)
        
        if surface == self.screen:
            pygame.display.flip()

    def get_current_viseme(self, current_time: float) -> str:
        """Determine which viseme should be shown at the current time"""
        for frame in self.animation_data:
            if frame["start_time"] <= current_time <= frame["end_time"]:
                return frame["mouth_shape"]
        return "neutral.png"

    def preview_animation(self):
        """Run the animation with audio preview"""
        running = True
        self.start_time = time.time()
        paused = False
        
        if self.audio:
            self.audio.play()
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
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
                self.draw_frame(viseme, blink)

            self.clock.tick(60)

        if self.audio:
            self.audio.stop()
        pygame.quit()

    def export_video(self, output_path: str = "/Users/nervous/Documents/GitHub/toon-in/output/output.mp4", fps: int = 60):
        """Export the animation as an MP4 video"""
        print("Starting video export...")
        
        # Calculate duration
        duration = self.audio_length if self.audio_length > 0 else max(
            frame["end_time"] for frame in self.animation_data
        )
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, self.window_size)
        
        # Create temporary surface for rendering
        temp_screen = pygame.Surface(self.window_size, pygame.SRCALPHA)
        
        # Generate frames
        frame_count = int(duration * fps)
        for i in range(frame_count):
            current_time = i / fps
            
            # Draw frame on temporary surface
            viseme = self.get_current_viseme(current_time)
            blink = self.blink_state.update(current_time)
            self.draw_frame(viseme, blink, temp_screen)
            
            # Convert Pygame surface to OpenCV format
            frame_data = pygame.surfarray.array3d(temp_screen)
            # Convert from RGB to BGR
            frame_data = cv2.cvtColor(frame_data, cv2.COLOR_RGB2BGR)
            # Transpose the array to match OpenCV's format
            frame_data = np.transpose(frame_data, (1, 0, 2))
            
            # Write frame
            out.write(frame_data)
            
            if i % fps == 0:
                print(f"Processed {i/fps:.1f}s of {duration:.1f}s")
        
        # Release video writer
        out.release()
        print(f"Video exported to {output_path}")
        
        # Add audio using ffmpeg if available
        if self.audio_path and os.path.exists(self.audio_path):
            print("Adding audio...")
            temp_video = output_path + ".temp.mp4"
            os.rename(output_path, temp_video)
            os.system(f'ffmpeg -i {temp_video} -i {self.audio_path} -c:v copy -c:a aac {output_path}')
            os.remove(temp_video)
            print("Audio added successfully")

def main():
    # Set your window size and audio path
    window_size = (1920, 1080)
    audio_path = "/Users/nervous/Documents/GitHub/toon-in/data/audio/audio.wav"  # Replace with your audio file path
    
    # Create animation instance
    animation = MouthAnimation(window_size=window_size, audio_path=audio_path)
    
    # Choose whether to preview or export
    # animation.preview_animation()  # For preview
    animation.export_video("/Users/nervous/Documents/GitHub/toon-in/output/output.mp4", fps=60)  # For export

if __name__ == "__main__":
    main()