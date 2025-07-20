import os
import shutil
import sys
from datetime import datetime
from PIL import Image # For EXIF data
from PIL.ExifTags import TAGS # For decoding EXIF tags

def get_exif_date(image_path):
    """
    Extracts the 'Date Taken' (DateTimeOriginal) from an image's EXIF data.
    """
    try:
        with Image.open(image_path) as img:
            exif_data = img._getexif()
            if exif_data:
                for tag, value in exif_data.items():
                    tag_name = TAGS.get(tag, tag)
                    if tag_name == 'DateTimeOriginal':
                        # EXIF date format is "YYYY:MM:DD HH:MM:SS"
                        return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
    except Exception as e:
        # print(f"  Warning: Could not read EXIF for {os.path.basename(image_path)}: {e}")
        pass # Ignore errors, fallback to file system date
    return None

def get_file_date(filepath):
    """
    Determines the best available date for a file (EXIF, then creation, then modification).
    """
    # Attempt to get EXIF date for image files
    if filepath.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff', '.heic')):
        exif_date = get_exif_date(filepath)
        if exif_date:
            return exif_date

    # Fallback to creation time for all files if EXIF fails or not an image
    try:
        # On Windows, os.path.getctime returns creation time
        # On Unix, it returns last metadata change time (often creation time on Linux)
        return datetime.fromtimestamp(os.path.getctime(filepath))
    except Exception as e:
        # Fallback to modification time
        # print(f"  Warning: Could not get creation time for {os.path.basename(filepath)}: {e}")
        return datetime.fromtimestamp(os.path.getmtime(filepath))

def organize_files(source_path, destination_path, what_if=False):
    """
    Organizes photos and videos from source_path to destination_path by date.
    """
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff', '.heic')
    video_extensions = ('.mp4', '.mov', '.avi', '.wmv', '.mkv', '.flv', '.webm')
    accepted_extensions = image_extensions + video_extensions

    month_names = [
        "01", "02", "03", "04", "05", "06",
        "07", "08", "09", "10", "11", "12"
    ]

    processed_count = 0
    skipped_count = 0
    error_count = 0

    print("\n--- Photo and Video Organizer Script (Python) ---")
    print(f"Source Path: {source_path}")
    print(f"Destination Path: {destination_path}")

    if what_if:
        print("\n*** RUNNING IN WHAT-IF MODE (NO CHANGES WILL BE MADE) ***\n")
    else:
        confirm = input("\nThis script will MOVE files. Are you sure you want to proceed? (yes/no): ").lower()
        if confirm != 'yes':
            print("Operation cancelled.")
            sys.exit(0)

    # Ensure destination path exists
    os.makedirs(destination_path, exist_ok=True)

    print("\nStarting file organization...")

    normalized_source_path = os.path.normpath(source_path)

    for root, _, files in os.walk(source_path):
        for filename in files:
            file_extension = os.path.splitext(filename)[1].lower()
            if file_extension not in accepted_extensions:
                skipped_count += 1
                continue # Skip non-photo/video files

            original_filepath = os.path.join(root, filename)

            try:
                determined_date = get_file_date(original_filepath)

                if not determined_date:
                    print(f"  Warning: Could not determine date for {filename}. Skipping.")
                    error_count += 1
                    continue
                
                relative_folder_path = os.path.relpath(root, normalized_source_path)

                if relative_folder_path == '.':
                    folder_name_parts = []
                else:
                    folder_name_parts = relative_folder_path.split(os.sep)
                cleaned_folder_names = []
                for part in folder_name_parts:
                    cleaned_part = part.replace(' ', '_').replace('.', '_').replace('-', '_')
                    cleaned_part = ''.join(c for c in cleaned_part if c.isalnum() or c == '_') # Keep only alphanumeric and underscore
                    if cleaned_part: # Ensure part is not empty after cleaning
                        cleaned_folder_names.append(cleaned_part)

                # Join them with underscores for the filename prefix
                folder_name_prefix = ""
                if cleaned_folder_names:
                    folder_name_prefix = "_" + "_".join(cleaned_folder_names) # e.g., "_Family_Birthday"


                year = determined_date.strftime("%Y")
                month_num = determined_date.month # 1-12
                month_name = month_names[month_num - 1] # 0-indexed array
                formatted_date_for_file = determined_date.strftime("%Y_%m_%d")

                year_folder_path = os.path.join(destination_path, year)
                month_folder_path = os.path.join(year_folder_path, f"{year}_{month_name}")

                # Prepare new filename with original basename
                base_name = os.path.splitext(filename)[0]
                new_filename_base = f"{formatted_date_for_file}{folder_name_prefix}_{base_name}"
                new_filename = f"{new_filename_base}{file_extension}"

                destination_file_path = os.path.join(month_folder_path, new_filename)

                # Handle duplicates
                counter = 1
                while os.path.exists(destination_file_path):
                    new_filename = f"{new_filename_base}_{counter}{file_extension}"
                    destination_file_path = os.path.join(month_folder_path, new_filename)
                    counter += 1

                print(f"\nProcessing: {filename}")
                print(f"  Detected Date: {determined_date.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  Moving to: {destination_file_path}")

                if not what_if:
                    os.makedirs(year_folder_path, exist_ok=True)
                    os.makedirs(month_folder_path, exist_ok=True)
                    shutil.move(original_filepath, destination_file_path)
                    processed_count += 1
                    print(f"  SUCCESS: Moved and renamed '{filename}' to '{new_filename}'")
                else:
                    print(f"  WHAT-IF: Would move and rename '{filename}' to '{destination_file_path}'")

            except Exception as e:
                print(f"  ERROR processing {filename}: {e}")
                error_count += 1

    print("\n--- Script Finished ---")
    print(f"Files Processed: {processed_count}")
    print(f"Files Skipped (non-photo/video): {skipped_count}")
    if error_count > 0:
        print(f"Files Skipped due to Errors: {error_count}")
    print(f"Total Files Examined: {processed_count + skipped_count + error_count}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Organize photos and videos by date.")
    parser.add_argument("-s", "--source", help="The source directory to scan for photos and videos.")
    parser.add_argument("-d", "--destination", help="The destination directory where organized files will be moved.")
    parser.add_argument("-w", "--what-if", action="store_true", help="Perform a dry run without making changes.")
    args = parser.parse_args()

    source_path = args.source
    destination_path = args.destination
    what_if = args.what_if

    if not source_path:
        while True:
            source_path = input("Enter the SOURCE directory (e.g., C:\\Unsorted_Photos): ")
            if os.path.isdir(source_path):
                break
            else:
                print("Source directory not found. Please try again.")

    if not destination_path:
        while True:
            destination_path = input("Enter the DESTINATION directory (e.g., D:\\Organized_Photos): ")
            if os.path.exists(destination_path) and not os.path.isdir(destination_path):
                print("Destination path exists but is not a directory. Please provide a valid directory.")
            elif os.path.isdir(destination_path):
                break
            else:
                # Ask to create if it doesn't exist
                create_confirm = input(f"Destination directory '{destination_path}' does not exist. Create it? (yes/no): ").lower()
                if create_confirm == 'yes':
                    break
                else:
                    print("Please provide an existing or valid new destination directory.")
                    destination_path = None # Reset to re-prompt


    organize_files(source_path, destination_path, what_if)