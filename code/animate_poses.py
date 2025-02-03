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

def render_animation_to_video(viseme_data, output_video, fps, resolution, temp_dir, head_image_path, blink_image_path, pose_data, background_path, eye_image, pupil_image):
    """Render animation frames and encode them into a video, dynamically switching viseme and pose folders."""
    pygame.init()

    # Set up display (off-screen rendering)
    screen = pygame.Surface(resolution)

    # Load Background Image
    bg_image = pygame.image.load(background_path)
    bg_image = pygame.transform.scale(bg_image, resolution)

    # Load Eye Image
    eye_image = pygame.image.load(eye_image)

    # Load Pupil Image
    pupil_image = pygame.image.load(pupil_image)

    # Load head image
    if os.path.exists(head_image_path):
        head_image = pygame.image.load(head_image_path)
    else:
        raise FileNotFoundError(f"Head image not found: {head_image_path}")

    # Load blink image
    if os.path.exists(blink_image_path):
        blink_image = pygame.image.load(blink_image_path)
    else:
        raise FileNotFoundError(f"Blink image not found: {blink_image_path}")

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

    # Render frames
    total_frames = int(total_duration * fps)
    frame_time = 1 / fps
    current_time = 0.0
    last_active_pose_folder = "pose_1"  # Default to pose_1

    print(f"Rendering {total_frames} frames...")
    for frame_number in tqdm(range(total_frames), desc="Rendering Frames"):
        screen.blit(bg_image, (0, 0))

        # Adjust positions
        head_x = resolution[0] // 2 - head_image.get_width() // 2
        head_y = resolution[1] // 2 - head_image.get_height() // 2 + resolution[1] // 4
        screen.blit(head_image, (head_x, head_y))

        # Render Eyes
        eye_image_x = 375
        eye_image_y = 1450
        screen.blit(eye_image, (eye_image_x, eye_image_y))

        # Render Pupil
        screen.blit(pupil_image, (eye_image_x+50, eye_image_y+50))

        # Keep track of last active pose image
        last_active_pose = "pose_1/att_1.png"  # Default pose

        # Keep track of last active pose
        if current_time == 0.0:
            last_active_pose = "pose_1/att_1.png"  # Default pose at start
            last_active_pose_folder = "pose_1"

        # Track the last pose and ensure it stays visible
        # Keep track of the last active pose and folder
        if "last_active_pose" not in locals():
            last_active_pose = "pose_1/att_1.png"  # Default pose
            last_active_pose_folder = "pose_1"

        pose_changed = False  # Flag to track pose changes

        for entry in pose_data:
            pose_start = entry["pose_start_time"]
            pose_end = entry["pose_end_time"]
            pose_image = entry["pose_image"]
            pose_folder = entry["pose_folder"]

            if pose_start <= current_time < pose_end:
                if pose_image != last_active_pose:  # Only update if a new pose appears
                    last_active_pose = pose_image
                    last_active_pose_folder = pose_folder
                    pose_changed = True  # Flag the change
                break

        # Load pose image only if it changed, otherwise keep the previous one
        pose_image_path = f"/Users/nervous/Documents/GitHub/toon-in/assets/{last_active_pose}"
        if os.path.exists(pose_image_path):
            pose_img = pygame.image.load(pose_image_path)
            screen.blit(pose_img, (head_x, head_y))
        else:
            print(f"Warning: Pose image not found: {pose_image_path}")


        # Load visemes from the correct pose folder
        viseme_directory = f"/Users/nervous/Documents/GitHub/toon-in/assets/{last_active_pose_folder}/visemes_{last_active_pose_folder[-1]}"
        viseme_images = {}

        for entry in viseme_data:
            mouth_shape = entry["mouth_shape"]
            if mouth_shape not in viseme_images:
                image_path = os.path.join(viseme_directory, mouth_shape)
                if os.path.exists(image_path):
                    viseme_images[mouth_shape] = pygame.image.load(image_path)

        # Ensure the neutral viseme is loaded
        neutral_viseme_path = os.path.join(viseme_directory, "neutral.png")
        if os.path.exists(neutral_viseme_path):
            viseme_images["neutral"] = pygame.image.load(neutral_viseme_path)
        else:
            raise FileNotFoundError(f"Neutral viseme ('neutral.png') not found in {viseme_directory}.")

        # Determine which viseme to show
        displayed_viseme = "neutral"
        for entry in viseme_data:
            viseme_start = entry["start_time"]
            viseme_end = entry["end_time"]
            mouth_shape = entry["mouth_shape"]

            if viseme_start <= current_time < viseme_end:
                displayed_viseme = mouth_shape
                break

        # Display the selected viseme
        if displayed_viseme in viseme_images:
            mouth_image = viseme_images[displayed_viseme]
            mouth_x = head_x + head_image.get_width() // 2 - mouth_image.get_width() // 2
            mouth_y = head_y + head_image.get_height() // 2 - mouth_image.get_height() // 2
            screen.blit(mouth_image, (mouth_x, mouth_y))

        # Check if the current frame is during a blink
        is_blinking = any(blink_start <= current_time < blink_end for blink_start, blink_end in blinks)
        if is_blinking:          
            screen.blit(blink_image, (eye_image_x, eye_image_y))

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

    viseme_data = load_viseme_data(viseme_file)
    pose_data = load_pose_data(pose_data_path)

render_animation_to_video(viseme_data, output_video, fps, resolution, temp_dir, head_image_path, blink_image_path, pose_data, background_path, eye_image, pupil_image)
