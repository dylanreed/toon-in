from tqdm import tqdm
import pygame
import json
import os
import subprocess
import random
import shutil
import threading

# Constants
SCALE_FACTOR = 0.75  # Scale images down for faster processing

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

def render_animation_to_video(viseme_data, output_video, fps, resolution, temp_dir, head_image_path, blink_image_path, pose_data, background_path, eye_image, pupil_image):
    """Render animation frames and encode them into a video, dynamically switching viseme and pose folders."""
    pygame.init()
    pygame.display.set_mode((1, 1))  # Small dummy display to enable image processing

    # Set up display (off-screen rendering)
    screen = pygame.Surface(resolution)

    # Load & optimize images
    bg_image = pygame.image.load(background_path).convert_alpha()
    bg_image = pygame.transform.scale(bg_image, (int(resolution[0] * SCALE_FACTOR), int(resolution[1] * SCALE_FACTOR)))

    eye_image = pygame.image.load(eye_image).convert_alpha()
    pupil_image = pygame.image.load(pupil_image).convert_alpha()

    if os.path.exists(head_image_path):
        head_image = pygame.image.load(head_image_path).convert_alpha()
    else:
        raise FileNotFoundError(f"Head image not found: {head_image_path}")

    if os.path.exists(blink_image_path):
        blink_image = pygame.image.load(blink_image_path).convert_alpha()
    else:
        raise FileNotFoundError(f"Blink image not found: {blink_image_path}")

    # Preload pose images
    preloaded_poses = {}
    for entry in pose_data:
        pose_image_path = f"/Users/nervous/Documents/GitHub/toon-in/assets/{entry['pose_image']}"
        if os.path.exists(pose_image_path) and entry["pose_image"] not in preloaded_poses:
            preloaded_poses[entry["pose_image"]] = pygame.image.load(pose_image_path).convert_alpha()

    # Preload viseme images
    preloaded_visemes = {}

    # Ensure neutral viseme is always preloaded
    for pose_version in ["pose_1", "pose_2"]:
        neutral_path = f"/Users/nervous/Documents/GitHub/toon-in/assets/{pose_version}/visemes_{pose_version[-1]}/neutral.png"
        
        if os.path.exists(neutral_path):
            print(f"✅ Found neutral viseme at: {neutral_path}")  # Debug print
            preloaded_visemes["neutral"] = pygame.image.load(neutral_path).convert_alpha()
        else:
            print(f"⚠️ Warning: Neutral viseme missing at {neutral_path}")

    # Load all other visemes
    for entry in viseme_data:
        mouth_shape = entry["mouth_shape"]
        for pose_version in ["pose_1", "pose_2"]:
            viseme_path = f"/Users/nervous/Documents/GitHub/toon-in/assets/{pose_version}/visemes_{pose_version[-1]}/{mouth_shape}"
            if os.path.exists(viseme_path) and mouth_shape not in preloaded_visemes:
                print(f"Loading viseme: {mouth_shape} from {viseme_path}")  # Debug print
                preloaded_visemes[mouth_shape] = pygame.image.load(viseme_path).convert_alpha()

    # Debug: Print out loaded visemes
    print(f"Loaded visemes: {list(preloaded_visemes.keys())}")

    # Ensure fallback to neutral if missing
    if "neutral" not in preloaded_visemes:
        raise FileNotFoundError("🚨 CRITICAL ERROR: 'neutral.png' viseme not found in any folder!")

    # Ensure temp directory exists
    os.makedirs(temp_dir, exist_ok=True)

    # Generate random blink timings
    total_duration = viseme_data[-1]["end_time"]
    current_time = 0.0
    blinks = []
    while current_time < total_duration:
        blink_start = current_time + random.uniform(1, 7)
        blink_end = blink_start + 0.2
        if blink_end > total_duration:
            break
        blinks.append((blink_start, blink_end))
        current_time = blink_start

    # Prepare for frame generation
    total_frames = int(total_duration * fps)
    frame_time = 1 / fps
    current_time = 0.0
    last_active_pose_folder = "pose_1"
    last_active_pose = "pose_1/att1.png"
    frame_surfaces = []  # Store frames in memory

    print(f"Rendering {total_frames} frames...")
    for frame_number in tqdm(range(total_frames), desc="Rendering Frames"):
        screen.blit(bg_image, (0, 0))

        head_x = resolution[0] // 2 - head_image.get_width() // 2
        head_y = resolution[1] // 2 - head_image.get_height() // 2 + resolution[1] // 4
        screen.blit(head_image, (head_x, head_y))

        screen.blit(eye_image, (375, 1450))
        screen.blit(pupil_image, (425, 1500))

        # Persist last active pose until a new one appears
        for entry in pose_data:
            if entry["pose_start_time"] <= current_time < entry["pose_end_time"]:
                if entry["pose_image"] != last_active_pose:
                    last_active_pose = entry["pose_image"]
                    last_active_pose_folder = entry["pose_folder"]
                break

        pose_img = preloaded_poses.get(last_active_pose, head_image)
        screen.blit(pose_img, (head_x, head_y))

        # Load viseme images from the correct folder
        viseme_directory = f"/Users/nervous/Documents/GitHub/toon-in/assets/{last_active_pose_folder}/visemes_{last_active_pose_folder[-1]}"
        displayed_viseme = "neutral"

        for entry in viseme_data:
            if entry["start_time"] <= current_time < entry["end_time"]:
                displayed_viseme = entry["mouth_shape"]
                break

        mouth_image = preloaded_visemes.get(displayed_viseme, preloaded_visemes["neutral"])
        mouth_x = head_x + head_image.get_width() // 2.035 - mouth_image.get_width() // 2
        mouth_y = head_y + head_image.get_height() // 2.55 - mouth_image.get_height() // 2
        screen.blit(mouth_image, (mouth_x, mouth_y))

        if any(blink_start <= current_time < blink_end for blink_start, blink_end in blinks):
            screen.blit(blink_image, (375, 1450))

        frame_surfaces.append(screen.copy())  # Store frame in memory
        current_time += frame_time

    print("Saving frames in bulk...")
    for i, surface in enumerate(frame_surfaces):
        pygame.image.save(surface, os.path.join(temp_dir, f"frame_{i:04d}.png"))

    print("Starting video encoding...")
    encoding_thread = threading.Thread(target=encode_video, args=(fps, temp_dir, output_video))
    encoding_thread.start()
    encoding_thread.join()  # Ensure encoding finishes before audio is added

    final_output = "/Users/nervous/Documents/GitHub/toon-in/output/with_audio.mp4"
    combine_audio_with_video(output_video, audio_file, final_output)

def encode_video(fps, temp_dir, output_video):
    ffmpeg_command = [
        "ffmpeg", "-y", "-framerate", str(fps), "-i", f"{temp_dir}/frame_%04d.png",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", output_video
    ]
    subprocess.run(ffmpeg_command, check=True)
    print(f"Video saved to {output_video}")

def combine_audio_with_video(video_file, audio_file, output_file):
    print("Merging audio with video...")
    ffmpeg_command = [
        "ffmpeg", "-y", "-i", video_file, "-i", audio_file, 
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", output_file
    ]
    subprocess.run(ffmpeg_command, check=True)
    print(f"Final video with audio saved to {output_file}")

if __name__ == "__main__":
    viseme_file = "/Users/nervous/Documents/GitHub/toon-in/data/viseme_data.json"
    audio_file = "/Users/nervous/Documents/GitHub/toon-in/data/audio/audio_1.wav"
    temp_dir = "/Users/nervous/Documents/GitHub/toon-in/data/tmp_frames/"
    output_video = "/Users/nervous/Documents/GitHub/toon-in/data/without_audio.mp4"
    head_image_path = "/Users/nervous/Documents/GitHub/toon-in/assets/body/body.png"
    blink_image_path = "/Users/nervous/Documents/GitHub/toon-in/assets/pose_1/left_eye_1/pupil.png"
    pose_data_path = "/Users/nervous/Documents/GitHub/toon-in/data/pose_data.json"
    background_path = "/Users/nervous/Documents/GitHub/toon-in/assets/background/background.png"
    eye_image = "/Users/nervous/Documents/GitHub/toon-in/assets/pose_1/left_eye_1/pupil.png"
    pupil_image = "/Users/nervous/Documents/GitHub/toon-in/assets/pose_1/left_eye_1/pupil.png"
    fps = 30
    resolution = (1320, 2868)

    # Load data
    viseme_data = load_viseme_data(viseme_file)
    pose_data = load_pose_data(pose_data_path)

    # Run animation rendering
    render_animation_to_video(viseme_data, output_video, fps, resolution, temp_dir, head_image_path, blink_image_path, pose_data, background_path, eye_image, pupil_image)
