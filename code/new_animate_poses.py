from tqdm import tqdm
import pygame
import json
import os
import subprocess
import random
import shutil

def load_viseme_data(viseme_file):
    """Load viseme data from a JSON file."""
    with open(viseme_file, "r", encoding="utf-8") as f:
        return json.load(f)

def load_pose_data(pose_data_path):
    """Load pose data from a JSON file and validate its structure."""
    with open(pose_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("pose_data should be a list of dictionaries")

        for entry in data:
            if not isinstance(entry, dict):
                raise ValueError(f"Invalid pose data entry: {entry}")
            required_keys = ["pose_folder", "pose_image", "pose_start_time", "pose_end_time"]
            for key in required_keys:
                if key not in entry:
                    raise ValueError(f"Missing key '{key}' in pose data entry: {entry}")

        return data

def render_animation_to_video(viseme_data, output_video, fps, resolution, temp_dir, head_image_path, blink_images, background_path, eye_image, pupil_image, pose_data, viseme_image):
    """Render animation frames and encode them into a video, dynamically switching viseme and pose folders."""
    pygame.init()

    # Set up display (off-screen rendering)
    screen = pygame.Surface(resolution)

    # Load Background Image
    if os.path.exists(background_path):
        bg_image = pygame.image.load(background_path)
        bg_image = pygame.transform.scale(bg_image, resolution)
    else:
        raise FileNotFoundError(f"Background image not found: {background_path}")
    # Load body image
    body_image_path = "/Users/nervous/Documents/GitHub/toon-in/assets/body/body.png"
    if os.path.exists(body_image_path):
        body_image = pygame.image.load(body_image_path)
    else:
        raise FileNotFoundError(f"Body image not found: {body_image_path}")

    # Load head image
    if os.path.exists(head_image_path):
        head_image = pygame.image.load(head_image_path)
    else:
        raise FileNotFoundError(f"Head image not found: {head_image_path}")

    # Load blink images
    blink_frames = {}
    for blink_state, path in blink_images.items():
        if os.path.exists(path):
            blink_frames[blink_state] = pygame.image.load(path)
        else:
            raise FileNotFoundError(f"Blink image not found: {path}")

    # Ensure temp directory exists
    os.makedirs(temp_dir, exist_ok=True)

    # Generate random blink timings (between 2-10 seconds)
    total_duration = viseme_data[-1]["end_time"]
    current_time = 0.0
    blinks = []
    while current_time < total_duration:
        blink_start = current_time + random.uniform(2, 10)
        blink_end = blink_start + 0.1  # half blink
        full_blink_end = blink_start + 0.2  # full close
        reopen_half = blink_start + 0.3  # reopen to half
        reopen_full = blink_start + 0.4  # fully open
        
        if reopen_full > total_duration:
            break
        
        blinks.append((blink_start, blink_end, full_blink_end, reopen_half, reopen_full))
        current_time = blink_start

    # Load Visemes
    viseme_images = {}
    viseme_directory = os.path.dirname(viseme_image)
    for entry in viseme_data:
        mouth_shape = entry["mouth_shape"]
        # Ensure .png is correctly formatted
        if not mouth_shape.endswith(".png"):
            mouth_shape += ".png"

        image_path = os.path.join(viseme_directory, mouth_shape)
        if os.path.exists(image_path):
            viseme_images[mouth_shape] = pygame.image.load(image_path)
        else:
            print(f"Warning: Viseme image not found: {image_path}")
    
    neutral_path = os.path.join(viseme_directory, "neutral.png")
    if os.path.exists(neutral_path):
        viseme_images["neutral"] = pygame.image.load(neutral_path)
    else:
        raise FileNotFoundError(f"Critical Error: Neutral viseme image not found at {neutral_path}")


    # Render frames
    total_frames = int(total_duration * fps)
    frame_time = 1 / fps
    current_time = 0.0

    print(f"Rendering {total_frames} frames...")
    for frame_number in tqdm(range(total_frames), desc="Rendering Frames"):
        screen.blit(bg_image, (0, 0))

        # Add body before rendering the head
        body_x = resolution[0] // 2 - body_image.get_width() // 2
        body_y = resolution[1] // 2.4 - body_image.get_height() // 2 + resolution[1] // 3
        screen.blit(body_image, (body_x, body_y))
        # Adjust positions
        head_x = resolution[0] // 2 - head_image.get_width() // 2
        head_y = resolution[1] // 2 - head_image.get_height() // 2 + resolution[1] // 4
        screen.blit(head_image, (head_x, head_y))

        # Determine which viseme to show
        displayed_viseme = "neutral"
        for entry in viseme_data:
            if entry["start_time"] <= current_time < entry["end_time"]:
                displayed_viseme = entry["mouth_shape"]
                break  # Exit once a match is found

        # Ensure the neutral viseme is always displayed when no viseme matches
        if displayed_viseme not in viseme_images:
            displayed_viseme = "neutral"

        # Render the Viseme
        if displayed_viseme in viseme_images:
            viseme_image = viseme_images[displayed_viseme]
            screen.blit(viseme_image, (head_x, head_y))
        else:
            print(f"Warning: Viseme image for {displayed_viseme} not found")

        # Determine blink state and render accordingly
        is_blinking = False
        for blink_start, blink_end, full_blink_end, reopen_half, reopen_full in blinks:
            if blink_start <= current_time < blink_end:
                screen.blit(blink_frames["half"], (head_x, head_y))
                is_blinking = True
            elif blink_end <= current_time < full_blink_end:
                screen.blit(blink_frames["close"], (head_x, head_y))
                is_blinking = True
            elif full_blink_end <= current_time < reopen_half:
                screen.blit(blink_frames["half"], (head_x, head_y))
                is_blinking = True

        if not is_blinking:
            # Render Eyes only if not blinking
            if os.path.exists(eye_image) and os.path.exists(pupil_image):
                eye_image_surface = pygame.image.load(eye_image)
                pupil_image_surface = pygame.image.load(pupil_image)
                screen.blit(eye_image_surface, (head_x, head_y))
                screen.blit(pupil_image_surface, (head_x, head_y))
            else:
                raise FileNotFoundError("Eye or pupil image not found.")

        # Save the frame as an image
        frame_path = os.path.join(temp_dir, f"frame_{frame_number:04d}.png")
        pygame.image.save(screen, frame_path)

        # Increment time
        current_time += frame_time

    # Encode frames to video
    ffmpeg_command = [
        "ffmpeg", "-y", "-framerate", str(fps), "-i", f"{temp_dir}/frame_%04d.png",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", output_video
    ]
    subprocess.run(ffmpeg_command, check=True)
    print(f"Video saved to {output_video}")

        # Merge audio into final output
    final_output = "/Users/nervous/Documents/GitHub/toon-in/output/with_audio.mp4"
    combine_audio_with_video(output_video, audio_file, final_output)

def combine_audio_with_video(video_file, audio_file, output_file):
    """Combine the rendered video and audio into a single file."""
    print("Merging audio with video...")
    ffmpeg_command = [
        "ffmpeg", "-y", "-i", video_file, "-i", audio_file, 
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", output_file
    ]
    subprocess.run(ffmpeg_command, check=True)
    print(f"Final video with audio saved to {output_file}")

    # Clean up temporary frames
    try:
        shutil.rmtree(temp_dir)
        print(f"Temporary frames in {temp_dir} deleted.")
    except Exception as e:
        print(f"Error deleting temporary frames: {e}")

if __name__ == "__main__":
    viseme_file = "/Users/nervous/Documents/GitHub/toon-in/data/viseme_data.json"
    pose_data_path = "/Users/nervous/Documents/GitHub/toon-in/data/pose_data.json"
    temp_dir = "/Users/nervous/Documents/GitHub/toon-in/data/tmp_frames/"
    output_video = "/Users/nervous/Documents/GitHub/toon-in/data/without_audio.mp4"
    head_image_path = "/Users/nervous/Documents/GitHub/toon-in/assets/pose_1/att_1.png"
    background_path = "/Users/nervous/Documents/GitHub/toon-in/assets/background/background.png"
    eye_image = "/Users/nervous/Documents/GitHub/toon-in/assets/pose_1/eye/eye_1.png"
    pupil_image = "/Users/nervous/Documents/GitHub/toon-in/assets/pose_1/eye/eye_1.png"
    audio_file = "/Users/nervous/Documents/GitHub/toon-in/data/audio/audio_1.wav"
    viseme_image = "/Users/nervous/Documents/GitHub/toon-in/assets/pose_1/visemes_1/"
    fps = 30
    resolution = (660, 1434)

    blink_images = {
        "half": "/Users/nervous/Documents/GitHub/toon-in/assets/pose_1/eye/half_1.png",
        "close": "/Users/nervous/Documents/GitHub/toon-in/assets/pose_1/eye/close_1.png"
    }

    viseme_data = load_viseme_data(viseme_file)
    pose_data = load_pose_data(pose_data_path)

    render_animation_to_video(viseme_data, output_video, fps, resolution, temp_dir, head_image_path, blink_images, background_path, eye_image, pupil_image, pose_data, viseme_image)
