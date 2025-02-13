import numpy as np
import cairosvg
from pathlib import Path
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
from PIL import Image
from io import BytesIO  # Add this import
import shutil
import os
import functools
import contextlib

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

def generate_background_frame(frame_num, frame_size, fps):
    """Generate a single background frame with mesh flow animation."""
    width, height = frame_size
    
    # Use smooth interpolation with higher precision
    time = frame_num / fps
    
    # Smoother oscillations using cubic easing
    def smooth_oscillation(t, period, amplitude):
        phase = (t % period) / period
        # Smooth cubic easing
        return amplitude * (4 * (phase - 0.5) ** 3 + 0.5)
    
    rotation1 = smooth_oscillation(time, 5, 10)    # 5s cycle, ±10 degrees
    rotation2 = smooth_oscillation(time, 12.5, 30) # 12.5s cycle, ±30 degrees
    rotation3 = smooth_oscillation(time, 30, 40)   # 30s cycle, ±40 degrees
    
    svg_template = f'''
    <svg width="{width}" height="{height}" viewBox="0 0 100 100" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <filter id="blur" x="-5%" y="-5%" width="110%" height="110%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="0.5"/>
            </filter>
        </defs>
        <rect width="100%" height="100%" fill="#FFFFFF"/>
        <g filter="url(#blur)">
            <path fill="#FFFF00" fill-opacity="0.7" d="M-100 -100L200 -100L200 50L-100 50Z" transform="rotate({rotation1}, 50, 0)"/>
            <path fill="#00FFFF" fill-opacity="0.7" d="M-100 -100L200 -100L200 50L-100 50Z" transform="rotate({rotation2}, 50, 0)"/>
            <path fill="#FF00FF" fill-opacity="0.2" d="M-100 -100L200 -100L200 20L-100 20Z" transform="rotate({rotation3}, 50, 0)"/>
        </g>
    </svg>
    '''
    
    png_bytes = cairosvg.svg2png(
        bytestring=svg_template.encode(),
        output_width=frame_size[0],
        output_height=frame_size[1]
    )
    return png_bytes

def generate_background_video(output_path, duration, fps=60, resolution=(800, 600), max_workers=None):
    """Generate a video of the background animation."""
    if max_workers is None:
        max_workers = mp.cpu_count()

    # Calculate total number of frames
    num_frames = int(fps * duration)
    
    # Create temporary directory for frames
    temp_dir = Path(output_path).parent / "temp_background_frames"
    
    with temporary_directory(temp_dir) as temp_frames_dir:
        print(f"Generating {num_frames} background frames using {max_workers} workers...")
        
        # Generate frames in parallel
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            gen_frame = functools.partial(generate_background_frame, frame_size=resolution, fps=fps)
            futures = {executor.submit(gen_frame, frame_num): frame_num 
                      for frame_num in range(num_frames)}
            
            # Process results with progress bar
            for future in tqdm(as_completed(futures), total=num_frames, desc="Generating frames"):
                frame_num = futures[future]
                png_bytes = future.result()
                
                frame_path = temp_frames_dir / f"frame_{frame_num:04d}.png"
                Image.open(BytesIO(png_bytes)).save(frame_path)

        # Create video from frames
        print("Creating video from frames...")
        os.system(f'ffmpeg -y -framerate {fps} -i {temp_frames_dir}/frame_%04d.png '
                 f'-c:v libx264 -preset slow -crf 17 '
                 f'-profile:v high -tune animation '
                 f'-movflags +faststart '
                 f'-pix_fmt yuv420p '
                 f'-vf "scale={resolution[0]}:-2:flags=lanczos" '
                 f'{output_path}')
        
        print(f"Background video saved to: {output_path}")

if __name__ == "__main__":
    # Settings
    output_video = "background.mp4"  # Output video path
    duration = 6 # Duration in seconds
    fps = 60  # Frames per second
    resolution = (800, 600)  # Video resolution
    
    # Generate the background video
    generate_background_video(output_video, duration, fps, resolution)