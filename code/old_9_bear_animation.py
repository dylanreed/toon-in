from tqdm import tqdm
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

# Cache for viseme images
VISEME_CACHE = {}
BACKGROUND_CACHE = {}

@contextlib.contextmanager
def temporary_directory(dir_path):
    """Context manager for creating and cleaning up temporary directories."""
    path = Path(dir_path)
    try:
        path.mkdir(parents=True, exist_ok=True)
        yield path
    finally:
        if path.exists():
            shutil.rmtree(path)
            print(f"Cleaned up temporary directory: {path}")

def load_json(file_path):
    """Load JSON file with error handling."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_background_frame(frame_num, frame_size, fps):
    """Generate a single background frame with mesh flow animation."""
    width, height = frame_size
    
    # Use sine waves for smoother transitions
    time = frame_num / fps
    
    # Smoother oscillations using sine waves
    rotation1 = 10 * np.sin(2 * np.pi * time / 5)  # 5s cycle
    rotation2 = 30 * np.sin(2 * np.pi * time / 12.5)  # 12.5s cycle
    rotation3 = -40 * np.sin(2 * np.pi * time / 30)  # 30s cycle
    
    svg_template = f'''
    <svg width="{width}" height="{height}" viewBox="0 0 100 100" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="100%" height="100%" fill="#FFFFFF"/>
        <path fill="#FFFF00" fill-opacity="0.7" d="M-100 -100L200 -100L200 50L-100 50Z" transform="rotate({rotation1}, 50, 0)"/>
        <path fill="#00FFFF" fill-opacity="0.7" d="M-100 -100L200 -100L200 50L-100 50Z" transform="rotate({rotation2}, 50, 0)"/>
        <path fill="#FF00FF" fill-opacity="0.2" d="M-100 -100L200 -100L200 20L-100 20Z" transform="rotate({rotation3}, 50, 0)"/>
    </svg>
    '''
    
    png_bytes = cairosvg.svg2png(
        bytestring=svg_template.encode(),
        output_width=frame_size[0],
        output_height=frame_size[1]
    )
    return png_bytes

def generate_background_frames_parallel(output_path, frame_size, fps, duration, max_workers=None):
    """Generate background frames in parallel."""
    if max_workers is None:
        max_workers = mp.cpu_count()

    # Calculate total number of frames needed for the full duration
    num_frames = int(fps * duration)
    
    temp_frames_dir = Path(output_path).parent / "background_frames"
    
    with temporary_directory(temp_frames_dir) as temp_dir:
        print(f"Generating {num_frames} background frames using {max_workers} workers...")
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Generate each frame with its unique frame number
            gen_frame = functools.partial(generate_background_frame, frame_size=frame_size, fps=fps)
            futures = {executor.submit(gen_frame, frame_num): frame_num 
                      for frame_num in range(num_frames)}  # Generate all frames
            
            # Process results with progress bar
            for future in tqdm(as_completed(futures), total=num_frames, desc="Generating backgrounds"):
                frame_num = futures[future]
                png_bytes = future.result()
                
                frame_path = temp_dir / f"frame_{frame_num:04d}.png"
                Image.open(BytesIO(png_bytes)).save(frame_path)
                # Store in cache for later use
                with BytesIO(png_bytes) as bio:
                    BACKGROUND_CACHE[frame_num] = pygame.image.load(bio)

        return temp_dir

def load_viseme_images(viseme_directory):
    """Load and cache viseme images."""
    viseme_images = {}
    for filename in os.listdir(viseme_directory):
        if filename.endswith(".png"):
            image_path = os.path.join(viseme_directory, filename)
            viseme_images[filename] = pygame.image.load(image_path)
    return viseme_images

def interpolate_frames(frame1, frame2, factor):
    """Interpolate between two frames for smooth transitions."""
    if frame1 is None or frame2 is None:
        return frame1 or frame2
        
    # Create copies of the surfaces to avoid modifying originals
    frame1_copy = frame1.copy()
    frame2_copy = frame2.copy()
    
    try:
        # Lock surfaces for pixel manipulation
        arr1 = pygame.surfarray.pixels3d(frame1_copy)
        arr2 = pygame.surfarray.pixels3d(frame2_copy)
        
        # Blend frames
        blended = (arr1 * (1 - factor) + arr2 * factor).astype(np.uint8)
        
        # Create new surface for the result
        result_surface = pygame.Surface(frame1.get_size(), pygame.SRCALPHA)
        pygame.surfarray.blit_array(result_surface, blended)
        
        return result_surface
        
    finally:
        # Ensure we delete array references to unlock surfaces
        del arr1
        del arr2

def create_smooth_visemes(viseme_images):
    """Create interpolated viseme frames for smoother transitions."""
    smooth_visemes = {}
    transition_steps = 4  # Number of intermediate frames
    
    # Create copies of viseme images to avoid modifying originals
    viseme_copies = {k: v.copy() for k, v in viseme_images.items()}
    
    # Get list of all viseme names
    viseme_names = list(viseme_copies.keys())
    
    # Create transitions between each pair of visemes
    for i, v1 in enumerate(viseme_names):
        for j, v2 in enumerate(viseme_names):
            if i != j:
                for step in range(transition_steps):
                    factor = step / transition_steps
                    transition_key = f"{v1}_{v2}_{step}"
                    smooth_visemes[transition_key] = interpolate_frames(
                        viseme_copies[v1],
                        viseme_copies[v2],
                        factor
                    )
    
    return smooth_visemes

def render_frame(frame_number, current_time, viseme_data, subtitle_data, resolution, 
                head_image, blink_half, blink_closed, viseme_images, blinks, fps, font):
    """Render a single frame with transparent background."""
    # Create a surface with alpha channel
    screen = pygame.Surface(resolution, pygame.SRCALPHA)
    
    # Character positioning with subtle movement
    base_x = resolution[0] // 2 - head_image.get_width() // 2
    base_y = resolution[1] // 2 - head_image.get_height() // 2 + resolution[1] // 4
    
    # Add subtle floating movement
    offset_x = np.sin(current_time * 2) * 2
    offset_y = np.cos(current_time * 1.5) * 2
    head_x = int(base_x + offset_x)
    head_y = int(base_y + offset_y)
    
    # Draw character
    screen.blit(head_image, (head_x, head_y))
    
    # Find current viseme
    current_viseme = next(
        (entry for entry in viseme_data 
         if entry["start_time"] <= current_time < entry["end_time"]),
        {"mouth_shape": "aei.png"}  # Default to neutral mouth shape
    )
    viseme_to_render = current_viseme["mouth_shape"]
    
    # Draw the mouth shape
    if viseme_to_render in viseme_images:
        screen.blit(viseme_images[viseme_to_render], (head_x, head_y))
    
    # Handle blinking
    for blink_start, half, closed, half_back in blinks:
        if blink_start <= current_time < half:
            screen.blit(blink_half, (head_x, head_y))
        elif half <= current_time < closed:
            screen.blit(blink_closed, (head_x, head_y))
        elif closed <= current_time < half_back:
            screen.blit(blink_half, (head_x, head_y))
    
    return screen, current_viseme["mouth_shape"]

def render_animation_parallel(viseme_data, subtitle_data, output_video, fps, resolution, 
                            temp_dir, head_image_path, blink_half_path, blink_closed_path, 
                            viseme_directory, emotions_directory, audio_file, max_workers=None):
    """Render animation frames in parallel."""
    pygame.init()
    
    # Load images
    head_image = pygame.image.load(head_image_path).convert_alpha()
    blink_half = pygame.image.load(blink_half_path).convert_alpha()
    blink_closed = pygame.image.load(blink_closed_path).convert_alpha()
    viseme_images = load_viseme_images(viseme_directory)
    
    total_duration = viseme_data[-1]["end_time"]
    total_frames = int(total_duration * fps)
    blinks = generate_blink_timings(total_duration)
    frame_time = 1 / fps
    
    with temporary_directory(temp_dir) as temp_frames_dir:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for frame_number in range(total_frames):
                current_time = frame_number * frame_time
                futures.append(
                    executor.submit(render_frame,
                                  frame_number,
                                  current_time,
                                  viseme_data,
                                  subtitle_data,
                                  resolution,
                                  head_image,
                                  blink_half,
                                  blink_closed,
                                  viseme_images,
                                  blinks,
                                  fps,
                                  None)  # Font not needed anymore
                )
            
            for frame_number, future in enumerate(tqdm(as_completed(futures), 
                                                     total=total_frames, 
                                                     desc="Rendering frames")):
                screen, current_viseme = future.result()
                frame_path = Path(temp_frames_dir) / f"frame_{frame_number:04d}.png"
                pygame.image.save(screen, str(frame_path))
        
        # Create video with transparency
        temp_video = str(Path(output_video).with_name('bear_temp.mov'))
        final_output = str(Path(output_video).with_name('bear_final.mov'))
        
        # Create video with alpha channel
        os.system(f'ffmpeg -y -framerate {fps} -i {temp_frames_dir}/frame_%04d.png '
                 f'-c:v qtrle -pix_fmt argb '
                 f'{temp_video}')
        
        # Add audio
        os.system(f'ffmpeg -y -i {temp_video} -i {audio_file} '
                 f'-c:v copy -c:a aac -b:a 320k '
                 f'-shortest {final_output}')
        
        if os.path.exists(temp_video):
            os.remove(temp_video)
        
        print(f"Animation rendered to {final_output}")

def generate_blink_timings(total_duration):
    """Generate random blink timings with slower, more natural blinks."""
    current_time = 0.0
    blinks = []
    
    # Constants for blink timing (in seconds)
    HALF_BLINK_DURATION = 0.2    # Time to half-close eyes
    FULL_BLINK_DURATION = 0.2     # Time eyes stay closed
    REOPEN_DURATION = 0.2        # Time to reopen eyes
    MIN_BLINK_INTERVAL = 2.0      # Minimum time between blinks
    MAX_BLINK_INTERVAL = 10.0      # Maximum time between blinks
    
    while current_time < total_duration:
        # Random interval until next blink
        blink_start = current_time + np.random.uniform(MIN_BLINK_INTERVAL, MAX_BLINK_INTERVAL)
        
        # Calculate the timing sequence for this blink
        half_close = blink_start + HALF_BLINK_DURATION
        full_close = half_close + FULL_BLINK_DURATION
        reopen = full_close + REOPEN_DURATION
        
        blinks.append((blink_start, half_close, full_close, reopen))
        current_time = blink_start
    
    return blinks

if __name__ == "__main__":
    # File paths setup
    base_dir = Path("/Users/nervous/Documents/GitHub/toon-in")
    data_dir = base_dir / "data"
    
    # Data files
    viseme_file = data_dir / "viseme_data.json"
    audio_file = data_dir / "audio/audio.wav"
    
    # Asset files
    head_image_path = base_dir / "assets/bear/body.png"
    blink_half_path = base_dir / "assets/bear/blink/half.png"
    blink_closed_path = base_dir / "assets/bear/blink/closed.png"
    viseme_directory = base_dir / "assets/bear/visemes"
    emotions_directory = base_dir / "assets/bear/emotions"
    
    # Output and temporary directories
    output_video = base_dir / "output/clip.mp4"
    temp_dir = data_dir / "tmp_frames"
    temp_bg_dir = data_dir / "tmp_bg"
    
if __name__ == "__main__":
    # Animation settings
    fps = 120  # Increased for smoother animation
    playback_speed = 1.0
    output_fps = int(fps * playback_speed)
    resolution = (1920, 1080)
    max_workers = mp.cpu_count()
    
    try:
        # Load data
        viseme_data = load_json(viseme_file)        

        # Initialize smooth visemes
        viseme_images = load_viseme_images(viseme_directory)
        smooth_visemes = create_smooth_visemes(viseme_images)
        
        # Generate background frames with cleanup
        with temporary_directory(temp_bg_dir) as bg_frames_dir:
            background_frames_dir = generate_background_frames_parallel(
                str(base_dir / "assets/background/generated_background.png"),
                resolution,
                fps,
                viseme_data[-1]["end_time"],
                max_workers
            )
            
# Render animation
            render_animation_parallel(
                viseme_data,
                background_frames_dir,
                str(output_video),
                fps,
                resolution,
                str(temp_dir),
                str(head_image_path),
                str(blink_half_path),
                str(blink_closed_path),
                str(viseme_directory),
                str(emotions_directory),
                str(audio_file),
                max_workers
            )
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise