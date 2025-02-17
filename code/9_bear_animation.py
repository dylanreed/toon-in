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

class Movement:
    def __init__(self):
        self.bob_amplitude = .5
        self.sway_amplitude = .5
        self.bob_frequency = 1
        self.sway_frequency = .75
        self.micro_movement_scale = 0.5
        self.zoom_duration = 10.0
        self.zoom_start_scale = 1.0
        self.zoom_end_scale = 1.0
        self.random_offset = random.uniform(0, 2 * np.pi)
        self.noise_offset_x = random.uniform(0, 1000)
        self.noise_offset_y = random.uniform(0, 1000)
        self.noise_speed = 0.5

    def get_offset(self, current_time: float) -> Tuple[float, float, float]:
        bob = np.sin(current_time * self.bob_frequency * 2 * np.pi + self.random_offset) * self.bob_amplitude
        sway = np.sin(current_time * self.sway_frequency * 2 * np.pi + self.random_offset) * self.sway_amplitude
        
        noise_x = (np.sin(current_time * self.noise_speed + self.noise_offset_x) * 
                  self.micro_movement_scale)
        noise_y = (np.sin(current_time * self.noise_speed + self.noise_offset_y) * 
                  self.micro_movement_scale)
        
        zoom_progress = min(current_time / self.zoom_duration, 1.0)
        current_scale = self.zoom_start_scale + (self.zoom_end_scale - self.zoom_start_scale) * zoom_progress
        
        return sway + noise_x, bob + noise_y, current_scale
class MouthAnimation:

    def __init__(self, window_size: Tuple[int, int] = (400, 400), 
                 character_scale: float = 1.0,
                 character_position: Tuple[int, int] = None,
                 flip_vertical: bool = False,
                 audio_path: str = None, 
                 background_path: str = None,
                 pose_data_path: str = None,
                 emotions_data_path: str = None):
        pygame.init()
        pygame.mixer.init()
        self.window_size = window_size
        self.character_scale = character_scale
        self.character_position = character_position or (window_size[0] // 2, window_size[1] // 2)
        self.flip_vertical = flip_vertical
        self.screen = pygame.display.set_mode(window_size, pygame.SRCALPHA)
        pygame.display.set_caption("Character Animation")
        
        self.clock = pygame.time.Clock()
        self.start_time = None
        self.audio_path = audio_path
        
        self.blink_state = BlinkState()
        self.movement = Movement()
        
        # Load all images
        self.body_image = self.load_image("/Users/nervous/Documents/GitHub/toon-in/assets/bear/body.png")
        self.viseme_images = self.load_viseme_images()
        self.blink_images = self.load_blink_images()
        self.brow_images = self.load_brow_images()
        self.emotion_images = self.load_emotion_images()
        
        # Load background image
        self.background_image = None
        if background_path:
            self.background_image = pygame.image.load(background_path).convert()
            self.background_image = pygame.transform.scale(self.background_image, self.window_size)
        
        self.animation_data = self.load_animation_data()
        self.pose_data = self.load_pose_data(pose_data_path) if pose_data_path else []
        self.emotion_data = self.load_emotion_data(emotions_data_path) if emotions_data_path else []
        self.current_viseme = "neutral.png"
        self.current_brow = "neutral.png"
        self.current_emotion = "neutral.png"
        
        if audio_path and os.path.exists(audio_path):
            self.audio = pygame.mixer.Sound(audio_path)
            self.audio_length = self.audio.get_length()
        else:
            self.audio = None
            self.audio_length = 0

    def load_image(self, path: str) -> pygame.Surface:
        try:
            image = pygame.image.load(path).convert_alpha()
            return image
        except pygame.error as e:
            print(f"Error loading image {path}: {e}")
            return self.create_placeholder_image(os.path.basename(path))

    def create_placeholder_image(self, filename: str) -> pygame.Surface:
        placeholder = pygame.Surface((200, 200), pygame.SRCALPHA)
        pygame.draw.rect(placeholder, (255, 0, 0, 128), placeholder.get_rect(), 2)
        
        font = pygame.font.Font(None, 36)
        text = font.render(filename, True, (255, 0, 0))
        text_rect = text.get_rect(center=placeholder.get_rect().center)
        placeholder.blit(text, text_rect)
        
        return placeholder

    def load_viseme_images(self) -> Dict[str, pygame.Surface]:
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
        blinks = {}
        blink_path = "/Users/nervous/Documents/GitHub/toon-in/assets/bear/blink"
        
        blink_files = ["open.png", "half.png", "closed.png"]
        
        for filename in blink_files:
            full_path = os.path.join(blink_path, filename)
            blinks[filename] = self.load_image(full_path)
            
        return blinks

    def load_animation_data(self) -> List[dict]:
        try:
            with open('/Users/nervous/Documents/GitHub/toon-in/data/viseme_data.json', 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"Error loading animation data: {e}")
            return []

    def load_brow_images(self) -> Dict[str, pygame.Surface]:
        brows = {}
        brow_path = "/Users/nervous/Documents/GitHub/toon-in/assets/bear/brows"
        
        brow_files = ["angry.png", "neutral.png", "quirked.png", "worried.png"]
        
        for filename in brow_files:
            full_path = os.path.join(brow_path, filename)
            brows[filename] = self.load_image(full_path)
            
        return brows

    def load_pose_data(self, pose_data_path: str) -> List[dict]:
        try:
            with open(pose_data_path, 'r') as f:
                data = json.load(f)
            # Filter only brow poses
            brow_data = [pose for pose in data if pose["pose_folder"] == "brows"]
            return brow_data
        except Exception as e:
            print(f"Error loading pose data: {e}")
            return []

    def get_current_brow(self, current_time: float) -> str:
        # Default to neutral if no pose is active
        current_brow = "neutral.png"
        
        for pose in self.pose_data:
            if pose["pose_start_time"] <= current_time <= pose["pose_end_time"]:
                # Extract just the filename from the pose_image path
                current_brow = os.path.basename(pose["pose_image"])
                break
                
        return current_brow

    def load_emotion_images(self) -> Dict[str, pygame.Surface]:
        emotions = {}
        emotion_path = "/Users/nervous/Documents/GitHub/toon-in/assets/bear/emotions"
        
        emotion_files = [
            "neutral.png", "cringe.png", "frown.png", "mockery.png", 
            "sad.png", "smile_2.png", "smile.png"
        ]
        
        for filename in emotion_files:
            full_path = os.path.join(emotion_path, filename)
            emotions[filename] = self.load_image(full_path)
            
        return emotions

    def get_current_emotion(self, current_time: float) -> str:
        # Default to neutral if no emotion is active
        current_emotion = "neutral.png"
        
        for pose in self.pose_data:
            if pose["pose_folder"] == "emotions" and pose["pose_start_time"] <= current_time <= pose["pose_end_time"]:
                current_emotion = os.path.basename(pose["pose_image"])
                break
                
        return current_emotion

    def draw_frame(self, viseme_filename: str, blink_filename: str, current_time: float, surface=None):
        if surface is None:
            surface = self.screen
            
        surface.fill((0, 0, 0, 0))
        
        # Draw background (if exists)
        if self.background_image:
            surface.blit(self.background_image, (0, 0))
        
        # Get movement offsets
        offset_x, offset_y, movement_scale = self.movement.get_offset(current_time)
        
        # Apply both character scale and movement scale
        total_scale = self.character_scale * movement_scale
        
        if self.body_image:
            scaled_size = (
                int(self.body_image.get_width() * total_scale),
                int(self.body_image.get_height() * total_scale)
            )
            scaled_image = pygame.transform.smoothscale(self.body_image, scaled_size)
            if self.flip_vertical:
                scaled_image = pygame.transform.flip(scaled_image, True, False)
            
            image_rect = scaled_image.get_rect(center=(
                self.character_position[0] + offset_x,
                self.character_position[1] + offset_y
            ))
            surface.blit(scaled_image, image_rect)
        
        # Draw current brow
        current_brow = self.get_current_brow(current_time)
        if current_brow in self.brow_images:
            scaled_size = (
                int(self.brow_images[current_brow].get_width() * total_scale),
                int(self.brow_images[current_brow].get_height() * total_scale)
            )
            scaled_image = pygame.transform.smoothscale(self.brow_images[current_brow], scaled_size)
            if self.flip_vertical:
                scaled_image = pygame.transform.flip(scaled_image, True, False)
            
            image_rect = scaled_image.get_rect(center=(
                self.character_position[0] + offset_x,
                self.character_position[1] + offset_y
            ))
            surface.blit(scaled_image, image_rect)
        
        # Draw mouth (emotion by default, override with viseme when speaking)
        current_emotion = self.get_current_emotion(current_time)
        
        if viseme_filename and viseme_filename in self.viseme_images:
            print(f"Drawing viseme: {viseme_filename}")
            # Use viseme when speaking
            scaled_size = (
                int(self.viseme_images[viseme_filename].get_width() * total_scale),
                int(self.viseme_images[viseme_filename].get_height() * total_scale)
            )
            scaled_image = pygame.transform.smoothscale(self.viseme_images[viseme_filename], scaled_size)
            if self.flip_vertical:
                scaled_image = pygame.transform.flip(scaled_image, True, False)
            
            image_rect = scaled_image.get_rect(center=(
                self.character_position[0] + offset_x,
                self.character_position[1] + offset_y
            ))
            surface.blit(scaled_image, image_rect)
        else:
            # Use emotion if no viseme
            print(f"Drawing emotion: {current_emotion}")
            scaled_size = (
                int(self.emotion_images[current_emotion].get_width() * total_scale),
                int(self.emotion_images[current_emotion].get_height() * total_scale)
            )
            scaled_image = pygame.transform.smoothscale(self.emotion_images[current_emotion], scaled_size)
            if self.flip_vertical:
                scaled_image = pygame.transform.flip(scaled_image, True, False)
            
            image_rect = scaled_image.get_rect(center=(
                self.character_position[0] + offset_x,
                self.character_position[1] + offset_y
            ))
            surface.blit(scaled_image, image_rect)
        
        # Draw blink overlay last
        if blink_filename in self.blink_images:
            scaled_size = (
                int(self.blink_images[blink_filename].get_width() * total_scale),
                int(self.blink_images[blink_filename].get_height() * total_scale)
            )
            scaled_image = pygame.transform.smoothscale(self.blink_images[blink_filename], scaled_size)
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
        print(f"Current time: {current_time}")
        
        for frame in self.animation_data:
            if frame["start_time"] <= current_time <= frame["end_time"]:
                print(f"Found viseme: {frame['mouth_shape']} at time {current_time}")
                return frame["mouth_shape"]
                
        print(f"No viseme found at time {current_time}, using emotion")
        return None

    def preview_animation(self):
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
                self.draw_frame(viseme, blink, current_time)

            self.clock.tick(60)

        if self.audio:
            self.audio.stop()
        pygame.quit()

    def export_video(self, output_path: str = "output", fps: int = 60):
        print("Starting video export...")
        
        duration = self.audio_length if self.audio_length > 0 else max(
            frame["end_time"] for frame in self.animation_data
        )
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, self.window_size)
        
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
        
        if self.audio_path and os.path.exists(self.audio_path):
            print("Adding audio...")
            temp_video = output_path + "temp.mp4"
            os.rename(output_path, temp_video)
            os.system(f'ffmpeg -i {temp_video} -i {self.audio_path} -c:v copy -c:a aac {output_path}')
            os.remove(temp_video)
            print("Audio added successfully")
        if surface is None:
            surface = self.screen
            
        surface.fill((0, 0, 0, 0))
        
        # Draw background (if exists)
        if self.background_image:
            surface.blit(self.background_image, (0, 0))
        
        # Get movement offsets
        offset_x, offset_y, movement_scale = self.movement.get_offset(current_time)
        
        # Apply both character scale and movement scale
        total_scale = self.character_scale * movement_scale
        
        if self.body_image:
            scaled_size = (
                int(self.body_image.get_width() * total_scale),
                int(self.body_image.get_height() * total_scale)
            )
            scaled_image = pygame.transform.smoothscale(self.body_image, scaled_size)
            if self.flip_vertical:
                scaled_image = pygame.transform.flip(scaled_image, False, True)
            
            image_rect = scaled_image.get_rect(center=(
                self.character_position[0] + offset_x,
                self.character_position[1] + offset_y
            ))
            surface.blit(scaled_image, image_rect)
        
        # Draw current brow
        current_brow = self.get_current_brow(current_time)
        if current_brow in self.brow_images:
            scaled_size = (
                int(self.brow_images[current_brow].get_width() * total_scale),
                int(self.brow_images[current_brow].get_height() * total_scale)
            )
            scaled_image = pygame.transform.smoothscale(self.brow_images[current_brow], scaled_size)
            if self.flip_vertical:
                scaled_image = pygame.transform.flip(scaled_image, False, True)
            
            image_rect = scaled_image.get_rect(center=(
                self.character_position[0] + offset_x,
                self.character_position[1] + offset_y
            ))
            surface.blit(scaled_image, image_rect)
        
        if viseme_filename in self.viseme_images:
            scaled_size = (
                int(self.viseme_images[viseme_filename].get_width() * total_scale),
                int(self.viseme_images[viseme_filename].get_height() * total_scale)
            )
            scaled_image = pygame.transform.smoothscale(self.viseme_images[viseme_filename], scaled_size)
            if self.flip_vertical:
                scaled_image = pygame.transform.flip(scaled_image, False, True)
            
            image_rect = scaled_image.get_rect(center=(
                self.character_position[0] + offset_x,
                self.character_position[1] + offset_y
            ))
            surface.blit(scaled_image, image_rect)
        
        if blink_filename in self.blink_images:
            scaled_size = (
                int(self.blink_images[blink_filename].get_width() * total_scale),
                int(self.blink_images[blink_filename].get_height() * total_scale)
            )
            scaled_image = pygame.transform.smoothscale(self.blink_images[blink_filename], scaled_size)
            if self.flip_vertical:
                scaled_image = pygame.transform.flip(scaled_image, False, True)
            
            image_rect = scaled_image.get_rect(center=(
                self.character_position[0] + offset_x,
                self.character_position[1] + offset_y
            ))
            surface.blit(scaled_image, image_rect)
        
        if surface == self.screen:
            pygame.display.flip()
        
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
                self.draw_frame(viseme, blink, current_time)

            self.clock.tick(60)

        if self.audio:
            self.audio.stop()
        pygame.quit()

    def export_video(self, output_path: str = "output", fps: int = 60):
        print("Starting video export...")
        
        duration = self.audio_length if self.audio_length > 0 else max(
            frame["end_time"] for frame in self.animation_data
        )
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, self.window_size)
        
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
        
        if self.audio_path and os.path.exists(self.audio_path):
            print("Adding audio...")
            temp_video = output_path + "temp.mp4"
            os.rename(output_path, temp_video)
            os.system(f'ffmpeg -i {temp_video} -i {self.audio_path} -c:v copy -c:a aac {output_path}')
            os.remove(temp_video)
            print("Audio added successfully")

def main():
    # Set your window size and paths
    window_size = (1920, 1080)
    audio_path = "/Users/nervous/Documents/GitHub/toon-in/data/audio/audio.wav"
    background_path = "/Users/nervous/Documents/GitHub/toon-in/assets/background/bear_background.png"
    pose_data_path = "/Users/nervous/Documents/GitHub/toon-in/data/pose_data.json"
    
    # Create animation instance with custom character scale and position
    animation = MouthAnimation(
        window_size=window_size,
        character_scale=1,  # Adjust this to change character size
        character_position=(1200, 800),  # Adjust x,y coordinates
        flip_vertical=True,  # Set to True to flip the animation vertically
        audio_path=audio_path,
        background_path=background_path,
        pose_data_path=pose_data_path
    )
    
    # Choose whether to preview or export
    #animation.preview_animation()
    animation.export_video("/Users/nervous/Documents/GitHub/toon-in/output/bear/output.mp4", fps=60)

if __name__ == "__main__":
    main()