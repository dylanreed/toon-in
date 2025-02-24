import sys
import os
import json
import time
import random
import numpy as np
import cv2
from enum import Enum
from typing import Dict, Tuple, List
import pygame

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
            
        #if self.is_blinking:
        #    blink_time = current_time - self.blink_start
        #    if blink_time < self.blink_duration * 0.2:
        #        self.current_frame = "half"
        #    elif blink_time < self.blink_duration * 0.4:
        #        self.current_frame = "closed"
        #    elif blink_time < self.blink_duration * 0.6:
        #        self.current_frame = "closed"
        #    elif blink_time < self.blink_duration * 0.8:
        #        self.current_frame = "half"
        #    elif blink_time < self.blink_duration:
        #        self.current_frame = "open"
        #    else:
        #        self.is_blinking = False
        #        self.current_frame = "open"
        #        self.next_blink = current_time + random.uniform(2, 6)
                
        return f"{self.current_frame}.png"

class Movement:
    def __init__(self):
        # Movement parameters
        self.bob_amplitude = 2.0  # Vertical movement in pixels
        self.sway_amplitude = 1.5  # Horizontal movement in pixels
        self.bob_frequency = 2.0  # Cycles per second for bobbing
        self.sway_frequency = 1.5  # Cycles per second for swaying
        self.micro_movement_scale = 0.5  # Scale for random micro-movements
        
        # Zoom parameters
        self.zoom_duration = 10.0  # Duration of zoom in seconds
        self.zoom_start_scale = 1.0  # Starting scale
        self.zoom_end_scale = 1.2  # Ending scale
        
        # Add some randomness to the movement
        self.random_offset = random.uniform(0, 2 * np.pi)
        
        # Smooth random movement
        self.noise_offset_x = random.uniform(0, 1000)
        self.noise_offset_y = random.uniform(0, 1000)
        self.noise_speed = 0.5

    def get_offset(self, current_time: float) -> Tuple[float, float, float]:
        # Main bobbing and swaying motion
        bob = np.sin(current_time * self.bob_frequency * 2 * np.pi + self.random_offset) * self.bob_amplitude
        sway = np.sin(current_time * self.sway_frequency * 2 * np.pi + self.random_offset) * self.sway_amplitude
        
        # Add smooth random micro-movements using noise
        noise_x = (np.sin(current_time * self.noise_speed + self.noise_offset_x) * 
                  self.micro_movement_scale)
        noise_y = (np.sin(current_time * self.noise_speed + self.noise_offset_y) * 
                  self.micro_movement_scale)
        
        # Calculate zoom scale
        zoom_progress = min(current_time / self.zoom_duration, 1.0)
        current_scale = self.zoom_start_scale + (self.zoom_end_scale - self.zoom_start_scale) * zoom_progress
        
        return sway + noise_x, bob + noise_y, current_scale

class MouthAnimation:
    def __init__(self, window_size: Tuple[int, int] = (400, 400), position: Tuple[int, int] = None, audio_path: str = None):
        pygame.init()
        pygame.mixer.init()
        self.window_size = window_size
        # If position is not specified, center in window
        self.position = position or (window_size[0] // 2, window_size[1] // 2)
        self.screen = pygame.display.set_mode(window_size, pygame.SRCALPHA)
        pygame.display.set_caption("Character Animation")
        
        self.clock = pygame.time.Clock()
        self.start_time = None
        self.audio_path = audio_path
        
        # Initialize blink state and movement
        #self.blink_state = BlinkState()
        self.movement = Movement()
        
        # Load all images
        self.body_image = self.load_image("/Users/nervous/Documents/GitHub/toon-in/assets/joke-a-tron/body.png")
        self.viseme_images = self.load_viseme_images()
        #self.blink_images = self.load_blink_images()
        
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

    def set_position(self, x: int, y: int):
        """Update the position of the animation"""
        self.position = (x, y)

    def get_position(self) -> Tuple[int, int]:
        """Get the current position of the animation"""
        return self.position

    def move_by(self, dx: int, dy: int):
        """Move the animation relative to its current position"""
        self.position = (self.position[0] + 1000, self.position[1] + dy)

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
        viseme_path = "/Users/nervous/Documents/GitHub/toon-in/assets/joke-a-tron/visemes"
        
        viseme_files = [
            "aei.png", "bmp.png", "cdgknstxyz.png", "ee.png", 
            "fv.png", "l.png", "o.png", "qw.png", "r.png", 
            "s.png", "shch.png", "th.png", "uw.png", "neutral.png"
        ]
        
        for filename in viseme_files:
            full_path = os.path.join(viseme_path, filename)
            visemes[filename] = self.load_image(full_path)
            
        return visemes

    #def load_blink_images(self) -> Dict[str, pygame.Surface]:
    #    """Load all blink images"""
    #    blinks = {}
    #    blink_path = "/Users/nervous/Documents/GitHub/toon-in/assets/bear/blink"
        
    #    blink_files = ["open.png", "half.png", "closed.png"]
        
    #    for filename in blink_files:
    #        full_path = os.path.join(blink_path, filename)
    #        blinks[filename] = self.load_image(full_path)
            
    #    return blinks

    def create_placeholder_image(self, filename: str) -> pygame.Surface:
        """Create a placeholder image for missing images"""
        placeholder = pygame.Surface((200, 200), pygame.SRCALPHA)
        pygame.draw.rect(placeholder, (255, 0, 0, 128), placeholder.get_rect(), 2)
        
        font = pygame.font.Font(None, 36)
        text = font.render(filename, True, (255, 0, 0))
        text_rect = text.get_rect(center=placeholder.get_rect().center)
        placeholder.blit(text, text_rect)
        
        return placeholder

    def draw_frame(self, viseme_filename: str, current_time: float, surface=None):
        """Draw all layers of the character"""
        if surface is None:
            surface = self.screen
            
        # Clear screen with transparency
        surface.fill((0, 0, 0, 0))
        
        # Get current movement offset and scale
        offset_x, offset_y, scale = self.movement.get_offset(current_time)
        
        # Draw body (base layer)
        if self.body_image:
            # Scale the image
            scaled_size = (
                int(self.body_image.get_width() * scale),
                int(self.body_image.get_height() * scale)
            )
            scaled_image = pygame.transform.smoothscale(self.body_image, scaled_size)
            
            image_rect = scaled_image.get_rect(center=(
                self.window_size[0] // 2 + offset_x,
                self.window_size[1] // 2 + offset_y
            ))
            surface.blit(scaled_image, image_rect)
        
        # Draw viseme (middle layer)
        if viseme_filename in self.viseme_images:
            # Scale the viseme image
            scaled_size = (
                int(self.viseme_images[viseme_filename].get_width() * scale),
                int(self.viseme_images[viseme_filename].get_height() * scale)
            )
            scaled_image = pygame.transform.smoothscale(self.viseme_images[viseme_filename], scaled_size)
            
            image_rect = scaled_image.get_rect(center=(
                self.window_size[0] // 2 + offset_x,
                self.window_size[1] // 2 + offset_y
            ))
            surface.blit(scaled_image, image_rect)
        
        # Draw blink (top layer)
        #if blink_filename in self.blink_images:
        #    # Scale the blink image
        #    scaled_size = (
        #        int(self.blink_images[blink_filename].get_width() * scale),
        #        int(self.blink_images[blink_filename].get_height() * scale)
        #    )
        #    scaled_image = pygame.transform.smoothscale(self.blink_images[blink_filename], scaled_size)
            
            image_rect = scaled_image.get_rect(center=(
                self.window_size[0] // 2 + offset_x,
                self.window_size[1] // 2 + offset_y
            ))
            surface.blit(scaled_image, image_rect)
        
        if surface == self.screen:
            pygame.display.flip()

    def get_current_viseme(self, current_time: float) -> str:
        """Determine which viseme should be shown at the current time"""
        # Print for debugging
        print(f"Current time: {current_time}")
        
        for frame in self.animation_data:
            if frame["start_time"] <= current_time <= frame["end_time"]:
                print(f"Found viseme: {frame['viseme']} at time {current_time}")
                return frame["viseme"]
                
        print(f"No viseme found at time {current_time}, using neutral")
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
                        #self.blink_state = BlinkState()
                        if self.audio:
                            self.audio.stop()
                            self.audio.play()

            if not paused:
                current_time = pygame.time.get_ticks() / 1000.0  # Convert to seconds
                if self.audio and current_time > self.audio_length:
                    running = False
                    break
                
                viseme = self.get_current_viseme(current_time)
                #blink = self.blink_state.update(current_time)
                self.draw_frame(viseme, blink, current_time)

            self.clock.tick(60)

        if self.audio:
            self.audio.stop()
        pygame.quit()

    def export_video(self, output_path: str = "output.mp4", fps: int = 60):
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
            #blink = self.blink_state.update(current_time)
            self.draw_frame(viseme, current_time, temp_screen)
            
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
    window_size = (800, 600)
    audio_path = "/Users/nervous/Documents/GitHub/toon-in/data/audio/audio.wav"  # Replace with your audio file path
    
    # Create animation instance
    animation = MouthAnimation(window_size=window_size, audio_path=audio_path)
    
    # Choose whether to preview or export
    # animation.preview_animation()  # For preview
    animation.export_video("/Users/nervous/Documents/GitHub/toon-in/output/joke-a-tron/output.mp4", fps=60)  # For export

if __name__ == "__main__":
    main()