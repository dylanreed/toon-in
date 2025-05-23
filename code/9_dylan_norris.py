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

# Constants
FPS = 60
DEFAULT_WINDOW_SIZE = (1080, 1350)
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
        self.body_image = self.load_image(self.base_dir / "assets/dylan/body.png")
        
        # Load visemes - updated with specific viseme set
        self.viseme_images = {}
        viseme_path = self.base_dir / "assets/dylan/visemes"
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
        blink_path = self.base_dir / "assets/dylan/blink"
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

    def _blend_surfaces(self, surface1: pygame.Surface, surface2: pygame.Surface, 
                       blend_factor: float) -> pygame.Surface:
        """
        Blend two surfaces based on the blend factor (0.0 to 1.0)
        """
        # Create a copy of both surfaces to preserve originals
        surf1 = surface1.copy()
        surf2 = surface2.copy()
        
        # Set the alpha for each surface based on blend factor
        surf1.set_alpha(int(255 * (1 - blend_factor)))
        surf2.set_alpha(int(255 * blend_factor))
        
        # Create a new surface for the blend
        blended = pygame.Surface(surface1.get_size(), pygame.SRCALPHA)
        
        # Blit both surfaces onto the new one
        blended.blit(surf1, (0, 0))
        blended.blit(surf2, (0, 0))
        
        return blended

    def _get_morphed_viseme(self, current_viseme: str, current_time: float) -> Tuple[pygame.Surface, float]:
        """
        Get the morphed viseme surface based on transition between previous and current viseme
        Returns the morphed surface and its scale factor
        """
        if current_viseme != self.previous_viseme:
            transition_time = current_time - self.previous_viseme_time
            if transition_time < self.morph_duration:
                # Calculate blend factor (0 to 1)
                blend_factor = transition_time / self.morph_duration
                
                # Get the two viseme surfaces
                prev_surface = self.viseme_images[self.previous_viseme]
                curr_surface = self.viseme_images[current_viseme]
                
                # Create the morphed surface
                morphed_surface = self._blend_surfaces(prev_surface, curr_surface, blend_factor)
                return morphed_surface, blend_factor
            else:
                # Update previous viseme info
                self.previous_viseme = current_viseme
                self.previous_viseme_time = current_time
        
        # If no morphing needed, return current viseme
        return self.viseme_images[current_viseme], 1.0

    def draw_frame(self, viseme_filename: str, blink_filename: str, current_time: float, surface=None):
        """Draw a single frame of animation with morphing between visemes"""
        surface = surface or self.screen
        surface.fill((0, 0, 0, 0))
        
        if self.background_image:
            surface.blit(self.background_image, (0, 0))
        
        offset_x, offset_y, movement_scale = self.movement.get_offset(current_time)
        total_scale = self.character_scale * movement_scale
        
        # Draw body
        if self.body_image:
            scaled_body = self._scale_and_flip_image(self.body_image, total_scale)
            self._blit_centered(surface, scaled_body, offset_x, offset_y)
        
        # Get morphed viseme
        if viseme_filename in self.viseme_images:
            morphed_viseme, _ = self._get_morphed_viseme(viseme_filename, current_time)
            scaled_viseme = self._scale_and_flip_image(morphed_viseme, total_scale)
            self._blit_centered(surface, scaled_viseme, offset_x, offset_y)
        
        # Draw blink overlay
        if blink_filename in self.blink_images:
            scaled_blink = self._scale_and_flip_image(self.blink_images[blink_filename], total_scale)
            self._blit_centered(surface, scaled_blink, offset_x, offset_y)
        
        if surface == self.screen:
            pygame.display.flip()

    def _scale_and_flip_image(self, image: pygame.Surface, scale: float) -> pygame.Surface:
        """Scale and flip an image if needed"""
        scaled_size = (int(image.get_width() * scale), int(image.get_height() * scale))
        scaled_image = pygame.transform.smoothscale(image, scaled_size)
        
        if self.flip_vertical:
            scaled_image = pygame.transform.flip(scaled_image, True, False)
        
        return scaled_image

    def _blit_centered(self, surface: pygame.Surface, image: pygame.Surface, 
                      offset_x: float, offset_y: float):
        """Blit an image centered at the character position with offsets"""
        image_rect = image.get_rect(center=(
            self.character_position[0] + offset_x,
            self.character_position[1] + offset_y
        ))
        surface.blit(image, image_rect)

    def get_current_viseme(self, current_time: float) -> str:
        """Get the current viseme based on time, with smoother transitions"""
        current_viseme = "neutral.png"
        
        for frame in self.animation_data:
            if frame["start_time"] <= current_time <= frame["end_time"]:
                current_viseme = frame["viseme"]
                break
        
        return current_viseme

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
                # Create thread-local animation state
                thread_local.blink_state = BlinkState()
                thread_local.movement = Movement()
                thread_local.surface = pygame.Surface(self.window_size, pygame.SRCALPHA)
                thread_local.previous_viseme = "neutral.png"
                thread_local.previous_viseme_time = 0
                
                # Initialize states for consistency
                if start_idx > 0:
                    for i in range(0, start_idx, max(1, fps // 10)):
                        simulated_time = i / fps
                        thread_local.blink_state.update(simulated_time)
                        thread_local.movement.get_offset(simulated_time)
                
                processed_frames = 0
                for i in range(start_idx, end_idx):
                    current_time = i / fps
                    
                    # Get animation elements
                    viseme = self.get_current_viseme(current_time)
                    blink = thread_local.blink_state.update(current_time)
                    
                    # Clear surface
                    thread_local.surface.fill((0, 0, 0, 0))
                    
                    # Draw background if exists
                    if self.background_image:
                        thread_local.surface.blit(self.background_image, (0, 0))
                    
                    # Get movement offset
                    offset_x, offset_y, movement_scale = thread_local.movement.get_offset(current_time)
                    total_scale = self.character_scale * movement_scale
                    
                    # Draw body
                    if self.body_image:
                        scaled_body = self._scale_and_flip_image(self.body_image, total_scale)
                        self._blit_centered(thread_local.surface, scaled_body, offset_x, offset_y)
                    
                    # Handle viseme morphing in thread-local context
                    if viseme in self.viseme_images:
                        # Simplified morphing for threaded rendering
                        if viseme != thread_local.previous_viseme:
                            transition_time = current_time - thread_local.previous_viseme_time
                            if transition_time < self.morph_duration:
                                # Calculate blend factor
                                blend_factor = transition_time / self.morph_duration
                                
                                # Get surfaces
                                prev_surf = self.viseme_images[thread_local.previous_viseme]
                                curr_surf = self.viseme_images[viseme]
                                
                                # Create morphed surface
                                morphed = self._blend_surfaces(prev_surf, curr_surf, blend_factor)
                                scaled_viseme = self._scale_and_flip_image(morphed, total_scale)
                            else:
                                thread_local.previous_viseme = viseme
                                thread_local.previous_viseme_time = current_time
                                scaled_viseme = self._scale_and_flip_image(self.viseme_images[viseme], total_scale)
                        else:
                            scaled_viseme = self._scale_and_flip_image(self.viseme_images[viseme], total_scale)
                            
                        self._blit_centered(thread_local.surface, scaled_viseme, offset_x, offset_y)
                    
                    # Draw blink overlay
                    if blink in self.blink_images:
                        scaled_blink = self._scale_and_flip_image(self.blink_images[blink], total_scale)
                        self._blit_centered(thread_local.surface, scaled_blink, offset_x, offset_y)
                    
                    # Convert and save frame
                    frame_data = pygame.surfarray.array3d(thread_local.surface)
                    frame_data = cv2.cvtColor(frame_data, cv2.COLOR_RGB2BGR)
                    frame_data = np.transpose(frame_data, (1, 0, 2))
                    
                    # Save frame to disk with padded index for sorting
                    frame_path = temp_dir / f"frame_{i:010d}.png"
                    cv2.imwrite(str(frame_path), frame_data)
                    
                    processed_frames += 1
                    
                    # Progress reporting - show more frequent updates
                    if processed_frames % (fps // 2) == 0:
                        percent_done = ((i - start_idx + 1) / (end_idx - start_idx)) * 100
                        print(f"Thread {thread_id}: {percent_done:.1f}% complete - " +
                              f"frame {i}/{end_idx-1} ({i/fps:.1f}s/{duration:.1f}s)")
                
                return processed_frames
            
            # Process chunks in parallel
            print(f"Starting parallel processing with {num_threads} threads...")
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = {
                    executor.submit(process_chunk, start, end, i): i 
                    for i, (start, end) in enumerate(chunks)
                }
                
                # Wait for all to complete and get total frames
                total_processed = 0
                for future in as_completed(futures):
                    thread_id = futures[future]
                    try:
                        frames_processed = future.result()
                        total_processed += frames_processed
                        print(f"Thread {thread_id} completed, processed {frames_processed} frames")
                    except Exception as e:
                        print(f"Thread {thread_id} failed with error: {e}")
                
                print(f"Processed {total_processed} frames across {num_threads} threads")
            
            # Write frames to video in correct order
            print("Creating video from processed frames...")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(output_path), fourcc, fps, self.window_size)
            
            # Get all frame files and sort them
            frame_files = sorted(temp_dir.glob("frame_*.png"))
            
            # Progress tracking for frame writing
            total_frames = len(frame_files)
            for i, frame_file in enumerate(frame_files):
                frame_data = cv2.imread(str(frame_file))
                if frame_data is not None:
                    out.write(frame_data)
                else:
                    print(f"Warning: Failed to read frame {frame_file}")
                
                # Show progress for writing frames
                if i % (total_frames // 10) == 0:
                    print(f"Writing frames to video: {i}/{total_frames} ({i/total_frames*100:.1f}%)")
            
            out.release()
            print(f"Video exported to {output_path}")
            
            # Add audio if available
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
    parser = argparse.ArgumentParser(description='Generate animation for dylan dylan')
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
    window_size = (1080, 1350)
    
    # Create animation instance with custom character scale and position
    animation = MouthAnimation(
        window_size=window_size,
        character_scale=0.2,
        character_position=(540, 1000),
        flip_vertical=False,
        audio_path=args.audio_path,
        background_path=args.background_path,
    )
    
    # Use the threaded export if requested, otherwise use normal export
    if args.threaded:
        animation.export_video_threaded(
            args.output_path, 
            fps=60,
            num_threads=args.num_threads
        )
    else:
        animation.export_video(args.output_path, fps=60)

if __name__ == "__main__":
    main()