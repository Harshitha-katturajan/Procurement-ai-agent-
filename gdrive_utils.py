from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import datetime
import os

def init_drive():
    """Authenticate and return GoogleDrive instance."""
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()  # Opens browser for first-time authentication
    drive = GoogleDrive(gauth)
    return drive

def upload_file_to_drive(file_path, drive, folder_id=None):
    """Upload file to Google Drive, optionally inside a folder."""
    file_name = os.path.basename(file_path)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    final_name = f"{timestamp}_{file_name}"

    file_metadata = {'title': final_name}
    if folder_id:
        file_metadata['parents'] = [{'id': folder_id}]

    f = drive.CreateFile(file_metadata)
    f.SetContentFile(file_path)
    f.Upload()
    print(f"✅ Uploaded to Google Drive: {final_name} (ID: {f['id']})")
    return f['id']
