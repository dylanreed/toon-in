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
    """Generate a single background frame."""
    svg_template = """
    <svg width="100%" height="100%" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <rect width="100%" height="100%" fill="#f1f1f1" />
        <path fill="#bf0a30" fill-opacity="0.7" d="M-100 -100L200 -100L200 {y1}L-100 {y1}Z" transform="rotate({r1}, 50, 0)"/>
        <path fill="#ffffff" fill-opacity="0.7" d="M-100 -100L200 -100L200 {y2}L-100 {y2}Z" transform="rotate({r2}, 50, 0)"/>
        <path fill="#002868" fill-opacity="0.2" d="M-100 -100L200 -100L200 {y3}L-100 {y3}Z" transform="rotate({r3}, 50, 0)"/>
    </svg>
    """
    
    # Smooth out the animation by reducing frequency and amplitude
    r1 = -5 + 10 * np.sin(frame_num * 2 * np.pi / (fps * 1))
    r2 = -15 + 30 * np.sin(frame_num * 2 * np.pi / (fps * 15))
    r3 = 20 - 40 * np.sin(frame_num * 2 * np.pi / (fps * 20))
    
    # Smoother wave movements
    y1 = 50 + 5 * np.sin(frame_num * 0.05)
    y2 = 50 + 7 * np.sin(frame_num * 0.04)
    y3 = 20 + 10 * np.sin(frame_num * 0.03)
    
    svg_content = svg_template.format(y1=y1, y2=y2, y3=y3, r1=r1, r2=r2, r3=r3)
    png_bytes = cairosvg.svg2png(bytestring=svg_content.encode(), output_width=frame_size[0], output_height=frame_size[1])
    return png_bytes

def generate_background_frames_parallel(output_path, frame_size, fps, duration, max_workers=None):
    """Generate background frames in parallel."""
    if max_workers is None:
        max_workers = mp.cpu_count()

    num_frames = int(fps * duration)
    temp_frames_dir = Path(output_path).parent / "background_frames"
    
    with temporary_directory(temp_frames_dir) as temp_dir:
        print(f"Generating {num_frames} background frames using {max_workers} workers...")
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            gen_frame = functools.partial(generate_background_frame, frame_size=frame_size, fps=fps)
            futures = {executor.submit(gen_frame, frame_num): frame_num 
                      for frame_num in range(num_frames)}
            
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

def render_frame(frame_number, current_time, viseme_data, subtitle_data, background_frames_dir, 
                resolution, head_image, blink_half, blink_closed, viseme_images, blinks, fps, font):
    """Render a single frame."""
    screen = pygame.Surface(resolution)
    
    # Use cached background if available, otherwise load
    if frame_number in BACKGROUND_CACHE:
        bg_image = BACKGROUND_CACHE[frame_number]
    else:
        bg_frame_path = Path(background_frames_dir) / f"frame_{frame_number % len(os.listdir(background_frames_dir)):04d}.png"
        bg_image = pygame.image.load(str(bg_frame_path))
        BACKGROUND_CACHE[frame_number] = bg_image

    screen.blit(bg_image, (0, 0))
    
    # Character positioning
    head_x = resolution[0] // 2 - head_image.get_width() // 2
    head_y = resolution[1] // 2 - head_image.get_height() // 2 + resolution[1] // 4
    
    # Draw character
    screen.blit(head_image, (head_x, head_y))
    
    # Find current viseme
    viseme_to_render = next(
        (entry["mouth_shape"] for entry in viseme_data 
         if entry["start_time"] <= current_time < entry["end_time"]),
        "sad.png"
    )
    
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
    
    # Render subtitles
    subtitle_text = ""
    for subtitle in subtitle_data:
        if subtitle["start_time"] <= current_time < subtitle["end_time"]:
            subtitle_text = subtitle["word"].strip()
            break
    
    if subtitle_text:
        # Render with outline for better visibility
        text_color = (255, 255, 255)  # White text
        outline_color = (0, 0, 0)     # Black outline
        outline_width = 2
        
        text_surface = font.render(subtitle_text, True, text_color)
        text_rect = text_surface.get_rect(center=(resolution[0] // 2, resolution[1] - 200))
        
        # Draw outline
        for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
            outline_surface = font.render(subtitle_text, True, outline_color)
            outline_rect = outline_surface.get_rect(center=(text_rect.centerx + dx * outline_width, 
                                                          text_rect.centery + dy * outline_width))
            screen.blit(outline_surface, outline_rect)
        
        # Draw main text
        screen.blit(text_surface, text_rect)
    
    return screen

def render_animation_parallel(viseme_data, subtitle_data, background_frames_dir, output_video, 
                            fps, resolution, temp_dir, head_image_path, blink_half_path, 
                            blink_closed_path, viseme_directory, emotions_directory, audio_file,
                            max_workers=None):
    """Render animation frames in parallel with automatic cleanup."""
    pygame.init()
    
    # Initialize font
    font = pygame.font.Font(None, 72)  # Adjusted font size for better visibility
    
    # Load and cache images
    head_image = pygame.image.load(head_image_path)
    blink_half = pygame.image.load(blink_half_path)
    blink_closed = pygame.image.load(blink_closed_path)
    viseme_images = load_viseme_images(viseme_directory)
    
    total_duration = viseme_data[-1]["end_time"]
    total_frames = int(total_duration * fps)
    blinks = generate_blink_timings(total_duration)
    frame_time = 1 / fps
    
    with temporary_directory(temp_dir) as temp_frames_dir:
        render_partial = functools.partial(
            render_frame,
            viseme_data=viseme_data,
            subtitle_data=subtitle_data,
            background_frames_dir=background_frames_dir,
            resolution=resolution,
            head_image=head_image,
            blink_half=blink_half,
            blink_closed=blink_closed,
            viseme_images=viseme_images,
            blinks=blinks,
            fps=fps,
            font=font
        )
        
        print(f"Rendering {total_frames} frames using {max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for frame_number in range(total_frames):
                current_time = frame_number * frame_time
                futures.append(
                    executor.submit(render_partial, frame_number, current_time)
                )
            
            for frame_number, future in enumerate(tqdm(as_completed(futures), total=total_frames, desc="Rendering frames")):
                screen = future.result()
                frame_path = temp_frames_dir / f"frame_{frame_number:04d}.png"
                pygame.image.save(screen, str(frame_path))
        
        # Create output directory if it doesn't exist
        output_path = Path(output_video)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Combine frames into video with higher bitrate for better quality
        temp_video = output_path.with_name('temp_output.mp4')
        os.system(f'ffmpeg -y -framerate {fps} -i {temp_frames_dir}/frame_%04d.png '
                 f'-c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p {temp_video}')
        
        # Add audio and create final output
        final_output = output_path.with_name('final_output.mp4')
        os.system(f'ffmpeg -y -i {temp_video} -i {audio_file} -c:v copy -c:a aac '
                 f'-b:a 192k -shortest {final_output}')
        
        # Clean up temporary video file
        if temp_video.exists():
            temp_video.unlink()
            print(f"Cleaned up temporary video: {temp_video}")
        
        print(f"Animation rendered to {final_output}")

def generate_blink_timings(total_duration):
    """Generate random blink timings."""
    current_time = 0.0
    blinks = []
    while current_time < total_duration:
        blink_start = current_time + np.random.uniform(2, 7)
        blinks.append((blink_start, blink_start + 0.1, blink_start + 0.2, blink_start + 0.3))
        current_time = blink_start
    return blinks

if __name__ == "__main__":
    # File paths setup
    base_dir = Path("/Users/nervous/Documents/GitHub/toon-in")
    data_dir = base_dir / "data"
    
    # Data files
    viseme_file = data_dir / "viseme_data.json"
    subtitle_file = data_dir / "word_data.json"
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
    
# Animation settings
    fps = 30  # Original FPS
    playback_speed = 0.25  # Playback speed (1.0 is normal, 0.5 is half speed, etc.)
    output_fps = int(fps * playback_speed)  # Adjusted FPS for output
    resolution = (1920, 1080)
    max_workers = mp.cpu_count()
    
    try:
        # Load data
        subtitle_data = load_json(subtitle_file)
        viseme_data = load_json(viseme_file)
        
        # Generate background frames with cleanup
        with temporary_directory(base_dir / "assets/background/temp_bg") as bg_frames_dir:
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
                subtitle_data,
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