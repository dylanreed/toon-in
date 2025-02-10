import pygame
import json
import os
import shutil
from pathlib import Path
import cv2
import numpy as np
import cairosvg
from PIL import Image
from io import BytesIO
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import functools
import contextlib


# Cache for viseme images and interpolated frames
VISEME_CACHE = {}
BACKGROUND_CACHE = {}
INTERPOLATION_CACHE = {}

class SmoothAnimator:
    def __init__(self, resolution=(1920, 1080), fps=60):
        self.resolution = resolution
        self.fps = fps
        self.prev_frame = None
        self.motion_blur_factor = 0.2
        self.setup_pygame()
        
    def setup_pygame(self):
        """Initialize pygame with optimal settings for smooth rendering."""
        os.environ['SDL_VIDEODRIVER'] = 'opengl'
        pygame.init()
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)
        
    def interpolate_frames(self, frame1, frame2, factor):
        """Interpolate between two frames."""
        if frame1 is None or frame2 is None:
            return frame1 or frame2
            
        arr1 = pygame.surfarray.array3d(frame1)
        arr2 = pygame.surfarray.array3d(frame2)
        blended = (arr1 * (1 - factor) + arr2 * factor).astype('uint8')
        return pygame.surfarray.make_surface(blended)

    def apply_motion_blur(self, current_frame):
        """Apply motion blur effect."""
        if self.prev_frame is None:
            self.prev_frame = current_frame
            return current_frame
            
        blurred = self.interpolate_frames(self.prev_frame, current_frame, self.motion_blur_factor)
        self.prev_frame = current_frame
        return blurred

def generate_smooth_background(frame_num, frame_size, fps):
    """Generate a single background frame with smooth animations."""
    svg_template = """
    <svg width="100%" height="100%" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <filter id="blur" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="1" />
            </filter>
        </defs>
        <rect width="100%" height="100%" fill="#f1f1f1" />
        <g filter="url(#blur)">
            <path fill="#bf0a30" fill-opacity="0.5">
                <animate attributeName="d" dur="8s" repeatCount="indefinite" 
                    values="M-100 -100L200 -100L200 50L-100 50Z;
                           M-100 -90L200 -90L200 55L-100 55Z;
                           M-100 -100L200 -100L200 50L-100 50Z" />
            </path>
            <path fill="#ffffff" fill-opacity="0.4">
                <animate attributeName="d" dur="12s" repeatCount="indefinite"
                    values="M-100 -100L200 -100L200 60L-100 60Z;
                           M-100 -95L200 -95L200 65L-100 65Z;
                           M-100 -100L200 -100L200 60L-100 60Z" />
            </path>
            <path fill="#002868" fill-opacity="0.2">
                <animate attributeName="d" dur="15s" repeatCount="indefinite"
                    values="M-100 -100L200 -100L200 40L-100 40Z;
                           M-100 -85L200 -85L200 45L-100 45Z;
                           M-100 -100L200 -100L200 40L-100 40Z" />
            </path>
        </g>
    </svg>
    """
    
    # Add smooth wave movement
    time = frame_num / fps
    wave1 = np.sin(time * 0.5) * 5
    wave2 = np.sin(time * 0.3) * 7
    wave3 = np.sin(time * 0.2) * 10
    
    svg_content = svg_template.format(wave1=wave1, wave2=wave2, wave3=wave3)
    png_bytes = cairosvg.svg2png(bytestring=svg_content.encode(), 
                                output_width=frame_size[0], 
                                output_height=frame_size[1])
    return png_bytes

def interpolate_visemes(viseme_data, viseme_images, fps):
    """Create smooth transitions between viseme frames."""
    interpolated = []
    transition_frames = 3
    
    for i in range(len(viseme_data) - 1):
        current = viseme_data[i]
        next_viseme = viseme_data[i + 1]
        
        # Add current viseme
        interpolated.append(current)
        
        # Calculate transition frames
        if next_viseme['start_time'] - current['end_time'] > 1/fps * transition_frames:
            current_img = viseme_images[current['mouth_shape']]
            next_img = viseme_images[next_viseme['mouth_shape']]
            
            for j in range(1, transition_frames):
                factor = j / transition_frames
                transition_time = current['end_time'] + (next_viseme['start_time'] - current['end_time']) * factor
                
                # Create transition frame
                key = f"{current['mouth_shape']}_{next_viseme['mouth_shape']}_{j}"
                if key not in INTERPOLATION_CACHE:
                    INTERPOLATION_CACHE[key] = create_transition_frame(current_img, next_img, factor)
                
                interpolated.append({
                    'mouth_shape': key,
                    'start_time': transition_time,
                    'end_time': transition_time + 1/fps
                })
    
    interpolated.append(viseme_data[-1])
    return interpolated

def create_transition_frame(img1, img2, factor):
    """Create a transition frame between two images."""
    arr1 = pygame.surfarray.array3d(img1)
    arr2 = pygame.surfarray.array3d(img2)
    blended = (arr1 * (1 - factor) + arr2 * factor).astype('uint8')
    return pygame.surfarray.make_surface(blended)

def render_frame_smooth(animator, frame_data, current_time):
    """Render a single frame with smooth transitions."""
    screen = pygame.Surface(animator.resolution)
    
    # Render background
    bg_frame = BACKGROUND_CACHE.get(frame_data['frame_number'])
    if bg_frame:
        screen.blit(bg_frame, (0, 0))
    
    # Render character with interpolated visemes
    mouth_shape = frame_data['mouth_shape']
    if mouth_shape in INTERPOLATION_CACHE:
        viseme = INTERPOLATION_CACHE[mouth_shape]
    else:
        viseme = VISEME_CACHE[mouth_shape]
    
    # Apply motion blur
    screen = animator.apply_motion_blur(screen)
    
    return screen

def main():
    # Initialize smooth animator
    animator = SmoothAnimator(resolution=(1920, 1080), fps=60)
    
    # Your existing main function code here, but use the smooth animator
    # for rendering frames
    pass

if __name__ == "__main__":
    main()

def render_animation_smooth(viseme_data, subtitle_data, background_frames_dir, output_video, 
                         fps, resolution, temp_dir, head_image_path, blink_half_path, 
                         blink_closed_path, viseme_directory, audio_file, max_workers=None):
    """Render animation with smooth transitions and improved performance."""
    pygame.init()
    animator = SmoothAnimator(resolution=resolution, fps=fps)
    
    # Initialize font with better quality
    font = pygame.font.Font(None, 72)
    font.set_bold(True)
    
    # Load and cache images with antialiasing
    head_image = pygame.image.load(head_image_path).convert_alpha()
    blink_half = pygame.image.load(blink_half_path).convert_alpha()
    blink_closed = pygame.image.load(blink_closed_path).convert_alpha()
    
    # Load visemes with smoothing
    viseme_images = {}
    for filename in os.listdir(viseme_directory):
        if filename.endswith(".png"):
            image_path = os.path.join(viseme_directory, filename)
            img = pygame.image.load(image_path).convert_alpha()
            viseme_images[filename] = img
    
    # Create interpolated viseme data
    smooth_viseme_data = interpolate_visemes(viseme_data, viseme_images, fps)
    
    # Calculate total frames
    total_duration = viseme_data[-1]["end_time"]
    total_frames = int(total_duration * fps)
    
    # Generate blink timings with smoother transitions
    blinks = generate_smooth_blinks(total_duration)
    
    with temporary_directory(temp_dir) as temp_frames_dir:
        # Prepare frame data
        frame_data = []
        frame_time = 1 / fps
        
        for frame_number in range(total_frames):
            current_time = frame_number * frame_time
            
            # Find current viseme
            current_viseme = next(
                (v for v in smooth_viseme_data 
                 if v["start_time"] <= current_time < v["end_time"]),
                smooth_viseme_data[-1]
            )
            
            frame_data.append({
                'frame_number': frame_number,
                'time': current_time,
                'mouth_shape': current_viseme['mouth_shape'],
                'blinks': [b for b in blinks if b[0] <= current_time < b[1]]
            })
        
        # Render frames in parallel with progress tracking
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for fd in frame_data:
                futures.append(
                    executor.submit(render_frame_smooth, animator, fd, fd['time'])
                )
            
            # Process rendered frames
            for frame_number, future in enumerate(tqdm(as_completed(futures), 
                                                    total=total_frames, 
                                                    desc="Rendering frames")):
                screen = future.result()
                frame_path = temp_frames_dir / f"frame_{frame_number:04d}.png"
                pygame.image.save(screen, str(frame_path))
        
        # Combine frames into video with improved quality
        output_path = Path(output_video)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use higher quality FFmpeg settings
        temp_video = output_path.with_name('temp_output.mp4')
        os.system(f'ffmpeg -y -framerate {fps} -i {temp_frames_dir}/frame_%04d.png '
                 f'-c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p '
                 f'-vf "scale={resolution[0]}:-2:flags=lanczos" {temp_video}')
        
        # Add audio with high quality
        final_output = output_path.with_name('final_output.mp4')
        os.system(f'ffmpeg -y -i {temp_video} -i {audio_file} '
                 f'-c:v copy -c:a aac -b:a 192k -shortest {final_output}')
        
        # Cleanup
        if temp_video.exists():
            temp_video.unlink()

def generate_smooth_blinks(total_duration):
    """Generate natural-looking blink timings with smooth transitions."""
    blinks = []
    current_time = 0.0
    
    # Constants for more natural blinking
    MIN_BLINK_INTERVAL = 2.0
    MAX_BLINK_INTERVAL = 6.0
    BLINK_DURATION = 0.15
    
    while current_time < total_duration:
        # Random interval until next blink
        interval = np.random.uniform(MIN_BLINK_INTERVAL, MAX_BLINK_INTERVAL)
        current_time += interval
        
        # Add smooth blink transition
        if current_time + BLINK_DURATION <= total_duration:
            blinks.append((
                current_time,  # Start time
                current_time + BLINK_DURATION  # End time
            ))
    
    return blinks