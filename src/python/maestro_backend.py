#!/usr/bin/env python3
"""
Maestro Backend - Simplified Batch Audio Plugin & App Installer
Automatically moves files to their correct locations based on file type.
"""

import os
import sys
import datetime
from pathlib import Path
import logging
import logging.handlers
import socket
import time
import json
import shutil
import subprocess
import tempfile
import zipfile
from flask import Flask, request, jsonify
from flask_cors import CORS

# Define constants for logging and communication
LOG_DIR = Path.home() / 'Library/Logs/MaestroInstaller'
LOG_FILE_PATH = LOG_DIR / 'Maestro_Install.log'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s'
BACKEND_PORT = 52000  # Fixed port
LOCK_FILE = Path.home() / 'Library/Application Support/Maestro' / 'backend.lock'

INSTALLPKG_URL = "https://raw.githubusercontent.com/henri/installpkg/refs/heads/master/install_components/installpkg"
INSTALLPKG_PATH = Path("/usr/local/bin/installpkg")

def acquire_lock():
    """Try to acquire the backend lock file."""
    try:
        # Ensure directory exists
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Try to create lock file
        with open(LOCK_FILE, 'x') as f:
            json.dump({
                'pid': os.getpid(),
                'port': BACKEND_PORT,
                'start_time': datetime.datetime.now().isoformat()
            }, f)
        return True
    except FileExistsError:
        # Lock file exists, check if process is still running
        try:
            with open(LOCK_FILE, 'r') as f:
                lock_data = json.load(f)
                pid = lock_data.get('pid')
                
                # Check if process is still running
                try:
                    os.kill(pid, 0)  # This will raise an error if process doesn't exist
                    return False  # Process is still running
                except (OSError, ProcessLookupError):
                    # Process is not running, we can take the lock
                    os.remove(LOCK_FILE)
                    return acquire_lock()
        except (json.JSONDecodeError, IOError):
            # Lock file is corrupted, remove it
            os.remove(LOCK_FILE)
            return acquire_lock()
    except Exception as e:
        logger.error(f"Error acquiring lock: {e}")
        return False

def release_lock():
    """Release the backend lock file."""
    try:
        if LOCK_FILE.exists():
            os.remove(LOCK_FILE)
    except Exception as e:
        logger.error(f"Error releasing lock: {e}")

# Configure logging
def setup_logging():
    """Configures the logging module."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Create a file handler
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE_PATH, maxBytes=5*1024*1024, backupCount=2
        )
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

        # Create a stream handler (for console output)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))

        # Get the root logger and add handlers
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG) # Set to DEBUG to capture all levels
        root_logger.addHandler(file_handler)
        root_logger.addHandler(stream_handler)

        # Configure Flask's and Werkzeug's loggers
        flask_logger = logging.getLogger('flask.app')
        werkzeug_logger = logging.getLogger('werkzeug')

        for logger_instance in [flask_logger, werkzeug_logger]:
            logger_instance.setLevel(logging.DEBUG) # Or your preferred level
            logger_instance.handlers = [] # Remove existing handlers
            logger_instance.addHandler(file_handler) # Add our file handler
            logger_instance.addHandler(stream_handler) # Optionally add stream handler
            logger_instance.propagate = False # Prevent duplicate logging to root

        # Initial log messages
        logging.info("Logging configured successfully.")
        logging.info(f"Log file: {LOG_FILE_PATH}")

    except Exception as e:
        # Fallback to basic stdout logging if setup fails
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.error(f"Error setting up logging: {e}. Falling back to basic stdout logging.")

setup_logging() # Call the setup function immediately

# Get a logger for this module
logger = logging.getLogger(__name__)

# Log startup
logger.info("🎼 MAESTRO BACKEND STARTUP INITIATED")
logger.info(f"🐍 Python Version: {sys.version}")
logger.info(f"📍 Working Directory: {os.getcwd()}")
logger.info(f"👤 User: {os.getenv('USER', 'unknown')}")

# Now try to import other modules with error handling
try:
    logger.info("📦 Importing required modules...")
    import shutil
    import subprocess
    import tempfile
    import time
    import zipfile
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    logger.info("✅ All modules imported successfully")
except ImportError as e:
    logger.critical(f"❌ CRITICAL: Failed to import required modules: {e}")
    sys.exit(1)
except Exception as e:
    logger.critical(f"❌ CRITICAL: Unexpected error during imports: {e}")
    sys.exit(1)

# Enhanced startup logging
logger.info("="*80)
logger.info("🎼 MAESTRO AUDIO PLUGIN INSTALLER - BACKEND STARTED")
logger.info("="*80)
logger.info(f"⏰ Startup Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"📁 Log File: {LOG_FILE_PATH}")
logger.info(f"📂 Log Directory: {LOG_DIR}")
logger.info(f"🐍 Python Version: {sys.version}")
logger.info(f"📍 Working Directory: {os.getcwd()}")
logger.info(f"👤 User: {os.getenv('USER', 'unknown')}")

# System information
try:
    macos_version = subprocess.run(['sw_vers', '-productVersion'], capture_output=True, text=True, check=False).stdout.strip()
    logger.info(f"🍎 macOS Version: {macos_version}")

    total, used, free = shutil.disk_usage(Path.home())
    free_gb = free // (1024**3)
    total_gb = total // (1024**3)
    logger.info(f"💾 Disk Space: {free_gb} GB free of {total_gb} GB total")

    # Check user groups (import grp here as it's specific to this block)
    import grp
    groups = [g.gr_name for g in grp.getgrall() if os.getenv('USER', '') in g.gr_mem]
    if 'admin' in groups:
        logger.info(f"🔑 User Groups: {', '.join(groups)} (Admin privileges available)")
    else:
        logger.info(f"🔑 User Groups: {', '.join(groups)} (No admin privileges)")

except Exception as e:
    logger.warning(f"⚠️ Could not gather system information: {e}")

# Check installation paths
logger.info("📦 Installation Paths Check:")
paths_to_check = [
    ("/Library/Audio/Plug-Ins/Components", "System Components"),
    ("/Library/Audio/Plug-Ins/VST", "System VST"),
    ("/Library/Audio/Plug-Ins/VST3", "System VST3"),
    (str(Path.home() / "Library/Audio/Plug-Ins/Components"), "User Components"),
    (str(Path.home() / "Library/Audio/Plug-Ins/VST"), "User VST"),
    (str(Path.home() / "Library/Audio/Plug-Ins/VST3"), "User VST3"),
]

for path, name in paths_to_check:
    if Path(path).exists():
        logger.info(f"   ✅ {name}: {path}")
    else:
        logger.info(f"   ❌ {name}: {path} (will be created if needed)")

logger.info("-"*80)
logger.info("🚀 Backend initialization complete - Ready for plugin installations!")
logger.info("-"*80)

app = Flask(__name__)
CORS(app)

# Disable Flask colored output to prevent ANSI codes in logs
# os.environ['FLASK_ENV'] = 'production' # This is already handled by how Flask is run
# os.environ['NO_COLOR'] = '1' # This might not be necessary with direct logger control

# Werkzeug logger is configured in setup_logging()

class MaestroInstaller:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="maestro_")
        
        # Installation paths for different file types
        self.install_paths = {
            'user': {
                'component': Path.home() / 'Library/Audio/Plug-Ins/Components',
                'vst': Path.home() / 'Library/Audio/Plug-Ins/VST',
                'vst3': Path.home() / 'Library/Audio/Plug-Ins/VST3',
                'aax': Path.home() / 'Library/Application Support/Avid/Audio/Plug-Ins',
                'app': Path.home() / 'Applications'
            },
            'system': {
                'component': Path('/Library/Audio/Plug-Ins/Components'),
                'vst': Path('/Library/Audio/Plug-Ins/VST'),
                'vst3': Path('/Library/Audio/Plug-Ins/VST3'),
                'aax': Path('/Library/Application Support/Avid/Audio/Plug-Ins'),
                'app': Path('/Applications')
            }
        }
        self.installpkg_ready = False # Track if installpkg is ready to use

    def ensure_installpkg(self, password):
        """Ensures the 'installpkg' command is available, downloading it if necessary."""
        if self.installpkg_ready:
            return True
        if INSTALLPKG_PATH.exists() and os.access(INSTALLPKG_PATH, os.X_OK):
            logger.info(f"✅ Found trusted installer at {INSTALLPKG_PATH}")
            self.installpkg_ready = True
            return True

        logger.warning(f"'{INSTALLPKG_PATH}' not found. Attempting to download and install...")
        try:
            # Download to a temporary location
            with tempfile.NamedTemporaryFile(delete=False, mode='wb') as tmp_file:
                download_proc = subprocess.run(['curl', '-L', '-o', tmp_file.name, INSTALLPKG_URL], check=True)
                tmp_path = Path(tmp_file.name)
            
            logger.info(f"Downloaded 'installpkg' to {tmp_path}")

            # Make executable
            tmp_path.chmod(0o755)

            # Use sudo to move it into place and set ownership
            move_command = [
                'sudo', '-S', 'mv', str(tmp_path), str(INSTALLPKG_PATH)
            ]
            chown_command = [
                'sudo', '-S', 'chown', 'root:wheel', str(INSTALLPKG_PATH)
            ]

            logger.info(f"Running command: {' '.join(move_command)}")
            move_proc = subprocess.run(move_command, input=f"{password}\n".encode(), capture_output=True, text=True, check=True)
            logger.info("Successfully moved 'installpkg' to /usr/local/bin")
            
            logger.info(f"Running command: {' '.join(chown_command)}")
            chown_proc = subprocess.run(chown_command, input=f"{password}\n".encode(), capture_output=True, text=True, check=True)
            logger.info("Successfully set ownership for 'installpkg'")

            self.installpkg_ready = True
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to set up 'installpkg': {e.stderr}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"❌ An unexpected error occurred during 'installpkg' setup: {e}", exc_info=True)
            return False

    def get_file_type(self, original_filename):
        """
        Intelligently determine file type based on its extension.
        This function assumes the filename is the final, correct name (post-unzip).
        """
        logger.debug(f"Determining file type for filename: {original_filename}")
        filename = original_filename.lower()

        # This function NO LONGER handles '.zip' stripping.
        # That logic is now exclusively in the 'install_file' method.

        if filename.endswith('.component'):
            return 'component'
        elif filename.endswith('.vst'):
            return 'vst'
        elif filename.endswith('.vst3'):
            return 'vst3'
        elif filename.endswith('.aax'):
            return 'aax'
        elif filename.endswith('.app'):
            return 'app'
        elif filename.endswith('.pkg'):
            return 'pkg'
        else:
            logger.warning(f"Unknown file type for: {original_filename}")
            return 'unknown'

    def ensure_directory_exists(self, path, use_sudo=False, password=None):
        """Ensure target directory exists, create if necessary."""
        logger.info(f"Ensuring directory exists: {path} (sudo: {use_sudo})")
        try:
            if not path.exists():
                logger.info(f"Directory not found, creating: {path}")
                if use_sudo:
                    logger.debug(f"Using sudo to create directory: {path}")
                    # Use a password with mkdir if provided
                    mkdir_cmd = ['sudo', '-S', 'mkdir', '-p', str(path)]
                    mkdir_proc = subprocess.run(mkdir_cmd, input=f"{password}\n".encode(), check=True, capture_output=True)
                    logger.debug(f"mkdir stdout: {mkdir_proc.stdout.decode()}, stderr: {mkdir_proc.stderr.decode()}")
                    
                    chmod_cmd = ['sudo', '-S', 'chmod', '775', str(path)] # More permissive for group writes
                    chmod_proc = subprocess.run(chmod_cmd, input=f"{password}\n".encode(), check=True, capture_output=True)
                    logger.debug(f"chmod stdout: {chmod_proc.stdout.decode()}, stderr: {chmod_proc.stderr.decode()}")
                else:
                    path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Successfully created directory: {path}")
            else:
                logger.debug(f"Directory already exists: {path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create directory {path} with sudo: {e.stderr.decode() if e.stderr else e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}", exc_info=True)
            return False

    def move_file(self, source_path, dest_path, use_sudo=False, password=None):
        """Move file to destination, handling permissions appropriately."""
        logger.info(f"Moving {source_path} to {dest_path} (sudo: {use_sudo})")
        try:
            if use_sudo:
                logger.debug(f"Using sudo to move {source_path} to {dest_path}")
                cmd = ['sudo', '-S', 'cp', '-R', str(source_path), str(dest_path)]
                proc = subprocess.run(cmd, input=f"{password}\n".encode(), check=True, capture_output=True)
                logger.debug(f"Sudo cp output: {proc.stdout.decode()} {proc.stderr.decode()}")
            else:
                logger.debug(f"Using standard shutil to move {source_path} to {dest_path}")
                shutil.move(str(source_path), str(dest_path))
            
            logger.info(f"Successfully moved file to {dest_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to move file with sudo: {e.stderr.decode() if e.stderr else e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Failed to move file: {e}", exc_info=True)
            return False

    def finalize_installation(self, target_path, use_sudo=False, password=None):
        """Set permissions and codesign the installed file."""
        logger.info(f"Finalizing installation for {target_path}")
        try:
            if use_sudo:
                # Set permissions: rwxr-xr-x for directories, rw-r--r-- for files
                perm_cmd = ['sudo', '-S', 'chmod', '-R', '755', str(target_path)]
                logger.debug(f"Running command: {' '.join(perm_cmd)}")
                perm_proc = subprocess.run(perm_cmd, input=f"{password}\n".encode(), check=True, capture_output=True)
                logger.debug(f"Permissions set: {perm_proc.stdout.decode()} {perm_proc.stderr.decode()}")

                # Set ownership
                chown_cmd = ['sudo', '-S', 'chown', '-R', 'root:wheel', str(target_path)]
                logger.debug(f"Running command: {' '.join(chown_cmd)}")
                chown_proc = subprocess.run(chown_cmd, input=f"{password}\n".encode(), check=True, capture_output=True)
                logger.debug(f"Ownership set: {chown_proc.stdout.decode()} {chown_proc.stderr.decode()}")

            # Ad-hoc codesign everything (plugins, apps, etc.)
            sign_cmd = ['sudo', '-S', 'codesign', '--force', '--deep', '--sign', '-', str(target_path)]
            logger.debug(f"Running command: {' '.join(sign_cmd)}")
            sign_proc = subprocess.run(sign_cmd, input=f"{password}\n".encode(), check=True, capture_output=True)
            logger.info(f"Successfully codesigned {target_path}")
            logger.debug(f"Codesign output: {sign_proc.stdout.decode()} {sign_proc.stderr.decode()}")
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Finalization step failed for {target_path}: {e.stderr.decode() if e.stderr else e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error during finalization: {e}", exc_info=True)
            return False

    def extract_pkg(self, pkg_path, extract_dir):
        """Extract a .pkg file to a temporary directory."""
        logger.info(f"Extracting {pkg_path} to {extract_dir}")
        try:
            # Create a temporary directory for extraction
            temp_extract_dir = Path(tempfile.mkdtemp(prefix="maestro_pkg_"))
            logger.debug(f"Created temporary extraction directory: {temp_extract_dir}")
            
            # Use pkgutil to expand the package
            expand_result = subprocess.run(['pkgutil', '--expand', str(pkg_path), str(temp_extract_dir)],
                                         check=True, capture_output=True)
            logger.debug(f"pkgutil expand output: {expand_result.stdout.decode()} {expand_result.stderr.decode()}")
            
            # Find the payload file
            payload_files = list(temp_extract_dir.rglob('Payload'))
            if not payload_files:
                logger.error(f"No Payload file found in {pkg_path}")
                return False
            
            # Extract the payload
            for payload_file in payload_files:
                logger.info(f"Found Payload file: {payload_file}")
                # Use cpio to extract the payload
                cpio_result = subprocess.run(['cpio', '-idm', '-D', str(extract_dir)],
                                           input=payload_file.read_bytes(),
                                           check=True, capture_output=True)
                logger.debug(f"cpio extract output: {cpio_result.stdout.decode()} {cpio_result.stderr.decode()}")
            
            # Clean up temporary directory
            shutil.rmtree(temp_extract_dir)
            logger.info(f"Successfully extracted {pkg_path} to {extract_dir}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract {pkg_path}: {e.stderr.decode() if e.stderr else e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error during package extraction: {e}", exc_info=True)
            return False

    def install_file(self, file_path, install_type='user', password=None, install_options=None):
        """
        Main installation router.
        `install_options` is a dict of booleans for each file type.
        """
        try:
            p_file_path = Path(file_path)
            original_filename = p_file_path.name
            
            # Unzip if it's a zipped bundle from drag-drop
            unzipped_filename_for_log = ""
            if any(original_filename.lower().endswith(suffix) for suffix in ['.component.zip', '.vst.zip', '.vst3.zip', '.app.zip']):
                logger.info(f"{original_filename} appears to be a zipped bundle, attempting to decompress.")
                try:
                    with zipfile.ZipFile(p_file_path, 'r') as zip_ref:
                        # Extract to a subdirectory within the temp dir
                        unzip_dir = p_file_path.parent / "unzipped"
                        unzip_dir.mkdir()
                        zip_ref.extractall(unzip_dir)
                        
                        # Find the actual plugin/app inside, ignoring macOS junk
                        significant_items = [
                            item for item in unzip_dir.iterdir()
                            if not item.name.startswith('__') and not item.name.startswith('.')
                        ]

                        if not significant_items:
                            raise Exception("Zipped file was empty or contained only hidden/system files.")
                        
                        # Assume the first significant item is the one we want
                        p_file_path = significant_items[0]
                        original_filename = p_file_path.name
                        unzipped_filename_for_log = original_filename # for logging
                        logger.info(f"Successfully unzipped. New file to install is {original_filename}")
                except Exception as zip_e:
                    logger.error(f"Failed to unzip {original_filename}: {zip_e}", exc_info=True)
                    # If unzipping fails, we can't proceed with this file.
                    return {'success': False, 'error': f"Failed to unzip {original_filename}: {zip_e}"}

            file_type = self.get_file_type(original_filename)
            log_filename = unzipped_filename_for_log or original_filename
            
            # Respect the user's choices from the frontend
            if install_options and not install_options.get(file_type, True):
                msg = f"Skipping {log_filename} (type: {file_type}) as per user settings."
                logger.info(msg)
                return {'success': True, 'message': msg, 'skipped': True}

            if file_type == 'pkg':
                return self.install_pkg_with_trusted_tool(p_file_path, password)
            
            if file_type == 'unknown':
                msg = f"Skipping {log_filename} (type unsupported)."
                logger.warning(msg)
                return {'success': False, 'error': msg, 'skipped': True}

            # Get the appropriate installation path
            install_path = self.install_paths[install_type][file_type]
            logger.info(f"Installation path for {log_filename}: {install_path}")
            
            # Ensure the target directory exists
            if not self.ensure_directory_exists(install_path, use_sudo=(install_type == 'system'), password=password):
                error_msg = f"Failed to create installation directory: {install_path}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # Move the file to the target location
            target_path = install_path / original_filename
            if not self.move_file(p_file_path, target_path, use_sudo=(install_type == 'system'), password=password):
                error_msg = f"Failed to move file to {target_path}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # Finalize (permissions, codesign)
            if not self.finalize_installation(target_path, use_sudo=(install_type == 'system'), password=password):
                logger.warning(f"Failed to finalize installation for {target_path}, but the file was moved.")
                # We can decide if this should be a hard failure or not. For now, let's call it a success.
            
            logger.info(f"Successfully installed {original_filename} to {target_path}")
            return {
                'success': True,
                'file': str(p_file_path),
                'type': file_type,
                'location': str(target_path)
            }
            
        except Exception as e:
            logger.error(f"Error installing {file_path}: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def install_pkg_with_trusted_tool(self, pkg_path, password):
        """Install a .pkg file using the trusted 'installpkg' command."""
        logger.info(f"Installing package {pkg_path} with trusted 'installpkg' tool.")
        try:
            # First, ensure installpkg is ready
            if not self.ensure_installpkg(password):
                return {'success': False, 'error': "Failed to set up the required 'installpkg' tool."}

            command = [
                'sudo', '-S',
                str(INSTALLPKG_PATH),
                str(pkg_path)
            ]
            
            logger.info(f"Running trusted installer command: {' '.join(command)}")
            
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, 'SUDO_ASKPASS': ''} # Ensure it uses stdin
            )
            
            stdout, stderr = process.communicate(input=f"{password}\n")

            if process.returncode != 0:
                error_message = f"installpkg failed with exit code {process.returncode}.\n"
                error_message += f"Stderr: {stderr.strip()}"
                logger.error(error_message)
                return {'success': False, 'error': stderr.strip()}
            
            success_message = f"Successfully installed {Path(pkg_path).name} with 'installpkg'."
            logger.info(success_message)
            logger.debug(f"installpkg stdout: {stdout}")
            return {'success': True, 'message': success_message}

        except FileNotFoundError:
            logger.error("❌ 'sudo' command not found. This is highly unusual.")
            return {'success': False, 'error': "'sudo' command not found."}
        except Exception as e:
            logger.error(f"❌ Unexpected error during package installation: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def scan_for_newly_installed_items(self, pkg_name):
        """Scan for newly installed items after package installation."""
        logger.info(f"Scanning for newly installed items from {pkg_name}")
        try:
            # Get list of installed items
            installed_items = []
            
            # Check common installation locations
            locations = [
                Path('/Library/Audio/Plug-Ins/Components'),
                Path('/Library/Audio/Plug-Ins/VST'),
                Path('/Library/Audio/Plug-Ins/VST3'),
                Path.home() / 'Library/Audio/Plug-Ins/Components',
                Path.home() / 'Library/Audio/Plug-Ins/VST',
                Path.home() / 'Library/Audio/Plug-Ins/VST3',
                Path('/Applications'),
                Path.home() / 'Applications'
            ]
            
            for location in locations:
                if location.exists():
                    for item in location.glob('**/*'):
                        if item.is_file() and pkg_name.lower() in item.name.lower():
                            installed_items.append(str(item))
            
            logger.info(f"Found {len(installed_items)} installed items")
            return installed_items
            
        except Exception as e:
            logger.error(f"Error scanning for installed items: {e}", exc_info=True)
            return []

    def cleanup(self):
        """Clean up temporary files."""
        logger.info("Cleaning up temporary files")
        try:
            if self.temp_dir and Path(self.temp_dir).exists():
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {e}", exc_info=True)

# Create installer instance
installer = MaestroInstaller()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    logger.info("Health check request received")
    return jsonify({
        'status': 'ok',
        'message': 'Maestro Backend is running'
    })

@app.route('/api/install', methods=['POST'])
def install_file_route(): # Renamed to avoid conflict with installer.install_file
    """Install a single file endpoint."""
    logger.info(f"Received request for /api/install from {request.remote_addr}")
    try:
        if 'file' not in request.files:
            logger.warning("No file provided in /api/install request.")
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.warning("No file selected in /api/install request.")
            return jsonify({'error': 'No file selected'}), 400
        
        install_type = request.form.get('install_type', 'user')
        password = request.form.get('password', '') # Avoid logging password directly
        logger.info(f"File: {file.filename}, Install Type: {install_type}, Password Provided: {'yes' if password else 'no'}")
        
        temp_file_path = Path(installer.temp_dir) / file.filename
        logger.debug(f"Saving uploaded file temporarily to: {temp_file_path}")
        file.save(temp_file_path)
        
        result = installer.install_file(temp_file_path, install_type, password)
        logger.info(f"Installation result for {file.filename}: {result.get('success', False)}")
        
        try:
            logger.debug(f"Cleaning up temporary file: {temp_file_path}")
            temp_file_path.unlink()
        except Exception as e_unlink:
            logger.warning(f"Could not delete temporary file {temp_file_path}: {e_unlink}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in /api/install endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/batch-install', methods=['POST'])
def batch_install_route(): # Renamed for clarity
    start_time = time.time()
    try:
        logger.info(f"Received request for /api/batch-install from {request.remote_addr}")
        files = request.files.getlist('files')
        install_type = request.form.get('install_type', 'user')
        password = request.form.get('password', '')
        
        # Get the per-file-type installation options
        install_options_json = request.form.get('install_options', '{}')
        install_options = json.loads(install_options_json)

        logger.info(f"Number of files: {len(files)}, Install Type: {install_type}, Password Provided: {'yes' if password else 'no'}")
        logger.debug(f"Installation Options: {install_options}")

        if not files:
            return jsonify({'success': False, 'error': 'No files uploaded'}), 400

        results = []
        successful_installs = 0
        failed_installs = 0

        try:
            for i, file in enumerate(files, 1):
                logger.info(f"Processing file {i}/{len(files)}: {file.filename}")
                
                # Use a secure temporary directory for this file
                batch_tmp_dir = Path(installer.temp_dir) / f"file_{i}"
                batch_tmp_dir.mkdir()
                
                # IMPORTANT: Use the original filename provided by the browser
                original_filename = file.filename
                tmp_path = batch_tmp_dir / original_filename
                
                logger.debug(f"Saving temporary file for batch: {tmp_path}")
                file.save(str(tmp_path))

                result = installer.install_file(tmp_path, install_type, password, install_options)
                
                result['file'] = original_filename # Ensure original filename is in the result
                results.append(result)
                
                if result.get('success'):
                    successful_installs += 1
                else:
                    failed_installs += 1
                logger.info(f"Result for {original_filename} in batch: {'Success' if result.get('success') else 'Failure'}")
                logger.debug(f"Cleaning up temporary directory from batch: {batch_tmp_dir}")
                shutil.rmtree(batch_tmp_dir)

        finally:
            installer.cleanup()
        
        total_time = time.time() - start_time
        logger.info(f"Batch install summary: {successful_installs} successful, {failed_installs} failed out of {len(files)}.")
        logger.info(f"Total processing time: {total_time:.2f} seconds.")
        
        return jsonify({
            'success': True,
            'results': results,
            'total_files': len(results),
            'successful_installs': successful_installs,
            'failed_installs': failed_installs
        })
        
    except Exception as e:
        logger.error(f"Error in /api/batch-install endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/install-paths', methods=['GET'])
def get_install_paths():
    """Get available installation paths."""
    logger.info("Request for /api/install-paths")
    paths = {
        'user_paths': {k: str(v) for k, v in installer.install_paths['user'].items()},
        'system_paths': {k: str(v) for k, v in installer.install_paths['system'].items()}
    }
    logger.debug(f"Returning install paths: {paths}")
    return jsonify(paths)

@app.route('/api/log-info', methods=['GET'])
def get_log_info():
    """Get current log file information."""
    logger.info("Request for /api/log-info")
    log_exists = LOG_FILE_PATH.exists()
    log_size = LOG_FILE_PATH.stat().st_size if log_exists else 0
    info = {
        'log_file': str(LOG_FILE_PATH),
        'log_dir': str(LOG_DIR),
        'log_exists': log_exists,
        'log_size_bytes': log_size,
        'log_size_human': f"{log_size / 1024:.2f} KB" if log_exists else "N/A"
    }
    logger.debug(f"Returning log info: {info}")
    return jsonify(info)

@app.route('/api/log-content', methods=['GET'])
def get_log_content():
    """Get the content of the current log file."""
    logger.info("Request for /api/log-content")
    try:
        if LOG_FILE_PATH.exists():
            logger.debug(f"Reading log file content from {LOG_FILE_PATH}")
            with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
            # Consider adding a limit to how much content is returned if logs can be very large
            # content = content[-10000:] # e.g., last 10000 characters
            logger.info(f"Returning log content, length: {len(content)} chars.")
            return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            logger.warning("Log file not found for /api/log-content.")
            return "No log file found. Install some files to generate logs.", 404
    except Exception as e:
        logger.error(f"Error reading log file {LOG_FILE_PATH}: {e}", exc_info=True)
        return f"Error reading log file: {str(e)}", 500

@app.route('/api/debug', methods=['GET'])
def debug_info():
    """Debug endpoint to check backend status."""
    logger.info("Request for /api/debug")
    debug_data = {
        'status': 'Backend is running successfully',
        'log_file': str(LOG_FILE_PATH),
        'log_exists': LOG_FILE_PATH.exists(),
        'timestamp': datetime.datetime.now().isoformat(),
        'message': 'If you can see this, the backend is working correctly'
    }
    logger.debug(f"Returning debug info: {debug_data}")
    return jsonify(debug_data)

@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 Not Found: {request.path} (Error: {error})")
    return jsonify({'error': 'Endpoint not found', 'details': str(error)}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 Internal Server Error: {request.path} (Error: {error})", exc_info=True)
    return jsonify({'error': 'Internal server error', 'details': str(error)}), 500

if __name__ == '__main__':
    try:
        # Try to acquire the lock
        if not acquire_lock():
            logger.error("Another backend instance is already running")
            sys.exit(1)
        
        logger.info(f"🚀 Starting Maestro Backend on port {BACKEND_PORT}")
        logger.info(f"🌐 Server URL: http://127.0.0.1:{BACKEND_PORT}")
        
        # Disable the reloader to prevent crashes when run from the app bundle
        # and ensure logs are properly captured.
        logger.info("📡 Backend is ready to accept requests. Werkzeug logs are now handled by our logger.")
        app.run(host='0.0.0.0', port=BACKEND_PORT, debug=False, use_reloader=False)

    except Exception as e:
        logger.critical(f"❌ Failed to start server: {e}", exc_info=True)
    finally:
        logger.info("🧹 Cleaning up temporary files before exit.")
        installer.cleanup()
        release_lock()
        logger.info("👋 Maestro Backend shutdown complete.")