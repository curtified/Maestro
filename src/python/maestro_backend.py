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

# Define constants for logging
LOG_DIR = Path.home() / 'Library/Logs/MaestroInstaller'
LOG_FILE_PATH = LOG_DIR / 'Maestro_Install.log'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s'

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

    def get_file_type(self, filename):
        """Determine file type from extension."""
        logger.debug(f"Determining file type for: {filename}")
        filename_lower = filename.lower()

        if filename_lower.endswith('.component'):
            logger.debug("File type: component")
            return 'component'
        elif filename_lower.endswith('.vst'):
            logger.debug("File type: vst")
            return 'vst'
        elif filename_lower.endswith('.vst3'):
            logger.debug("File type: vst3")
            return 'vst3'
        elif filename_lower.endswith('.aax'):
            logger.debug("File type: aax")
            return 'aax'
        elif filename_lower.endswith('.app'):
            logger.debug("File type: app")
            return 'app'
        elif filename_lower.endswith('.pkg'):
            logger.debug("File type: pkg")
            return 'pkg'
        else:
            logger.warning(f"Unknown file type for: {filename}")
            return 'unknown'

    def ensure_directory_exists(self, path, use_sudo=False):
        """Ensure target directory exists, create if necessary."""
        logger.info(f"Ensuring directory exists: {path} (sudo: {use_sudo})")
        try:
            if not path.exists():
                logger.info(f"Directory not found, creating: {path}")
                if use_sudo:
                    logger.debug(f"Using sudo to create directory: {path}")
                    subprocess.run(['sudo', 'mkdir', '-p', str(path)], check=True, capture_output=True)
                    subprocess.run(['sudo', 'chmod', '755', str(path)], check=True, capture_output=True)
                    logger.info(f"Successfully created directory with sudo: {path}")
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

    def move_file(self, source_path, dest_path, use_sudo=False):
        """Move file to destination, handling permissions appropriately."""
        logger.info(f"Moving {source_path} to {dest_path} (sudo: {use_sudo})")
        try:
            if use_sudo:
                logger.debug(f"Using sudo to move {source_path} to {dest_path}")
                # Use sudo to copy the file
                copy_result = subprocess.run(['sudo', 'cp', '-R', str(source_path), str(dest_path)], check=True, capture_output=True)
                logger.debug(f"Sudo cp output: {copy_result.stdout.decode()} {copy_result.stderr.decode()}")

                # Set proper permissions for the installed file
                chmod_result = subprocess.run(['sudo', 'chmod', '-R', '755', str(dest_path)], check=True, capture_output=True)
                logger.debug(f"Sudo chmod output: {chmod_result.stdout.decode()} {chmod_result.stderr.decode()}")
                
                # For user-owned directories, fix ownership (this logic seems specific and might need review)
                # It's generally better to install to system locations with sudo, user locations without.
                if str(dest_path).startswith(str(Path.home())) and '/Library' not in str(dest_path): # Simplified condition
                    current_user = os.getenv('USER')
                    if current_user:
                        logger.info(f"Attempting to chown {dest_path} to {current_user}:staff")
                        chown_result = subprocess.run(['sudo', 'chown', '-R', f'{current_user}:staff', str(dest_path)],
                                     check=True, capture_output=True)
                        logger.debug(f"Sudo chown output: {chown_result.stdout.decode()} {chown_result.stderr.decode()}")
            else:
                logger.debug(f"Using standard shutil to move {source_path} to {dest_path}")
                if source_path.is_dir():
                    shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(source_path, dest_path)
            
            logger.info(f"Successfully moved {source_path.name} to {dest_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to move {source_path} to {dest_path} using sudo: {e.stderr.decode() if e.stderr else e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Failed to move {source_path} to {dest_path}: {e}", exc_info=True)
            return False

    def codesign_file(self, file_path):
        """Codesign the installed file for macOS compatibility."""
        logger.info(f"Attempting to codesign: {file_path}")
        try:
            result = subprocess.run([
                'codesign', '--force', '--sign', '-', '--deep', str(file_path)
            ], check=True, capture_output=True, text=True)
            logger.info(f"Successfully codesigned: {file_path}. Output: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"Codesign failed for {file_path}: {e.stderr}")
            return False
        except FileNotFoundError:
            logger.warning("codesign command not found. Skipping codesigning.")
            return False

    def extract_pkg(self, pkg_path, extract_dir):
        """Extract PKG file and find audio plugins/apps."""
        logger.info(f"Extracting PKG file: {pkg_path} into {extract_dir}")
        try:
            extract_path = Path(extract_dir) / "extracted"
            extract_path.mkdir(exist_ok=True)
            logger.debug(f"Extraction path: {extract_path}")

            logger.info(f"Expanding PKG package: {pkg_path} using pkgutil...")
            result = subprocess.run([
                'pkgutil', '--expand', str(pkg_path), str(extract_path)
            ], capture_output=True, text=True, check=True)
            logger.info(f"PKG expanded successfully to {extract_path}. Output: {result.stdout}")

            found_files = []
            payload_files = list(extract_path.rglob("Payload"))
            if not payload_files:
                logger.info("No 'Payload' file found, trying 'payload' or 'Archive.pax.gz'")
                payload_files = list(extract_path.rglob("payload")) + list(extract_path.rglob("Archive.pax.gz"))
            
            logger.info(f"Found {len(payload_files)} payload file(s): {payload_files}")

            for i, payload_file in enumerate(payload_files):
                if payload_file.is_file():
                    payload_extract_dir = extract_path / f"payload_contents_{i}"
                    payload_extract_dir.mkdir(exist_ok=True)
                    logger.info(f"Extracting payload: {payload_file} to {payload_extract_dir}")

                    extraction_successful = False
                    methods_tried = []

                    # Method 1: Direct cpio
                    try:
                        logger.debug(f"Attempting extraction method 1: direct cpio for {payload_file}")
                        with open(payload_file, 'rb') as f_in:
                            # Use subprocess.run with Popen for piping if needed, or direct input
                            # For cpio, it expects input from stdin
                            cpio_proc = subprocess.run(
                                ['cpio', '-idm'],
                                input=f_in.read(),
                                cwd=payload_extract_dir,
                                check=True,
                                capture_output=True, text=True
                            )
                        extraction_successful = True
                        logger.info(f"Extracted {payload_file} using direct cpio. Output: {cpio_proc.stdout[:200]}")
                        methods_tried.append("direct cpio: success")
                    except subprocess.CalledProcessError as e:
                        logger.warning(f"Direct cpio failed for {payload_file}: {e.stderr}")
                        methods_tried.append(f"direct cpio: failed ({e.returncode})")
                    except Exception as e:
                        logger.warning(f"Direct cpio failed with other error for {payload_file}: {e}")
                        methods_tried.append(f"direct cpio: failed (exception)")


                    # Method 2: Gunzip + cpio
                    if not extraction_successful:
                        try:
                            logger.debug(f"Attempting extraction method 2: gunzip + cpio for {payload_file}")
                            # This command is safer to run via shell=True if paths are complex, but ensure paths are safe.
                            # Using a list of args is generally safer.
                            # cmd_str = f'gunzip -c "{payload_file}" | cpio -idm' # Original command
                            # Consider creating the pipeline more robustly if needed
                            gunzip_proc = subprocess.Popen(['gunzip', '-c', str(payload_file)], stdout=subprocess.PIPE)
                            cpio_proc = subprocess.Popen(['cpio', '-idm'], stdin=gunzip_proc.stdout, cwd=payload_extract_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            gunzip_proc.stdout.close() # Allow gunzip_proc to receive a SIGPIPE if cpio_proc exits.
                            cpio_stdout, cpio_stderr = cpio_proc.communicate()

                            if cpio_proc.returncode == 0:
                                extraction_successful = True
                                logger.info(f"Extracted {payload_file} using gunzip + cpio. Output: {cpio_stdout.decode()[:200]}")
                                methods_tried.append("gunzip + cpio: success")
                            else:
                                logger.warning(f"gunzip + cpio failed for {payload_file}. CPIO stderr: {cpio_stderr.decode()}")
                                methods_tried.append(f"gunzip + cpio: failed (cpio ret {cpio_proc.returncode})")
                        except Exception as e: # Broad exception for Popen setup or communication
                            logger.warning(f"gunzip + cpio failed with other error for {payload_file}: {e}")
                            methods_tried.append(f"gunzip + cpio: failed (exception)")
                    
                    # Method 3: Try as tar.gz
                    if not extraction_successful:
                        try:
                            logger.debug(f"Attempting extraction method 3: tar -xzf for {payload_file}")
                            tar_proc = subprocess.run([
                                'tar', '-xzf', str(payload_file), '-C', str(payload_extract_dir)
                            ], check=True, capture_output=True, text=True)
                            extraction_successful = True
                            logger.info(f"Extracted {payload_file} using tar. Output: {tar_proc.stdout[:200]}")
                            methods_tried.append("tar: success")
                        except subprocess.CalledProcessError as e:
                            logger.warning(f"Tar extraction failed for {payload_file}: {e.stderr}")
                            methods_tried.append(f"tar: failed ({e.returncode})")
                        except Exception as e:
                            logger.warning(f"Tar extraction failed with other error for {payload_file}: {e}")
                            methods_tried.append(f"tar: failed (exception)")

                    logger.debug(f"Extraction attempts for {payload_file}: {'; '.join(methods_tried)}")

                    if extraction_successful:
                        logger.info(f"Scanning for audio files in {payload_extract_dir}")
                        for item in payload_extract_dir.rglob("*"):
                            # Check if item is a directory or a file of interest
                            if item.is_file() or item.is_dir(): # Ensure it's a file/dir before checking extension
                                item_name_lower = item.name.lower()
                                if any(item_name_lower.endswith(ext) for ext in ['.component', '.vst', '.vst3', '.aax', '.app']):
                                    found_files.append(item)
                                    logger.info(f"Found relevant file/bundle: {item.name} at {item}")
                    else:
                        logger.warning(f"Failed to extract payload: {payload_file} after trying all methods.")
            
            logger.info(f"Total relevant files/bundles found after PKG extraction: {len(found_files)}")
            return found_files
            
        except subprocess.CalledProcessError as e:
            logger.error(f"PKG extraction command failed for {pkg_path}: {e.stderr}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Failed to extract PKG {pkg_path}: {e}", exc_info=True)
            return []

    def install_file(self, file_path, install_type='user', password=None):
        """Install a single file to the appropriate location."""
        logger.info(f"Attempting to install file: {file_path}, type: {install_type}, password provided: {'yes' if password else 'no'}")
        try:
            file_path = Path(file_path)
            file_type = self.get_file_type(file_path.name)
            logger.debug(f"File: {file_path.name}, Detected type: {file_type}")

            if file_type == 'unknown':
                logger.error(f"Unsupported file type for: {file_path.name}")
                return {
                    'success': False,
                    'filename': file_path.name,
                    'error': 'Unsupported file type'
                }
            
            if file_type == 'pkg':
                logger.info(f"Handing off PKG installation for: {file_path.name}")
                return self.install_pkg(file_path, install_type, password)
            
            if file_type not in self.install_paths[install_type]:
                logger.error(f"No installation path defined for file type '{file_type}' with install_type '{install_type}'")
                return {
                    'success': False,
                    'filename': file_path.name,
                    'error': f'No installation path defined for {file_type} under {install_type} scope'
                }
            
            dest_dir = self.install_paths[install_type][file_type]
            dest_path = dest_dir / file_path.name
            logger.info(f"Destination directory: {dest_dir}, Destination path: {dest_path}")

            if dest_path.exists():
                logger.warning(f"File already exists at destination: {dest_path}")
                return {
                    'success': False,
                    'filename': file_path.name,
                    'error': f'File already exists at {dest_path}'
                }
            
            use_sudo = install_type == 'system'
            logger.debug(f"Requires sudo for directory creation/move: {use_sudo}")
            if not self.ensure_directory_exists(dest_dir, use_sudo):
                # Error already logged by ensure_directory_exists
                return {
                    'success': False,
                    'filename': file_path.name,
                    'error': f'Failed to create destination directory {dest_dir}'
                }
            
            if not self.move_file(file_path, dest_path, use_sudo):
                # Error already logged by move_file
                return {
                    'success': False,
                    'filename': file_path.name,
                    'error': f'Failed to move file to {dest_path}'
                }
            
            self.codesign_file(dest_path) # Logged within codesign_file
            
            logger.info(f"Successfully installed {file_path.name} to {dest_path}")
            return {
                'success': True,
                'filename': file_path.name,
                'installed_path': str(dest_path),
                'file_type': file_type
            }
            
        except Exception as e:
            logger.error(f"Generic installation error for {file_path.name if file_path else 'unknown file'}: {e}", exc_info=True)
            return {
                'success': False,
                'filename': file_path.name if file_path else 'unknown',
                'error': str(e)
            }

    def install_pkg(self, pkg_path, install_type='user', password=None):
        """Install PKG file using macOS installer command."""
        original_pkg_path_name = pkg_path.name
        logger.info("="*80)
        logger.info(f"Starting PKG installation for: {pkg_path}, original name: {original_pkg_path_name}")
        logger.info(f"Install type: {install_type}, Password provided: {'Yes' if password else 'No'}")
        logger.debug(f"PKG file size: {pkg_path.stat().st_size} bytes, Exists: {pkg_path.exists()}, Readable: {os.access(pkg_path, os.R_OK)}")

        problematic_chars = ['@', '#', '$', '%', '^', '&', '*', '(', ')', '[', ']', '{', '}', '|', '\\', ':', ';', '"', "'", '<', '>', ',', '?', '/', '`', '~']
        if ' ' in pkg_path.name or any(char in pkg_path.name for char in problematic_chars):
            logger.warning(f"PKG filename '{pkg_path.name}' contains spaces or special characters. Sanitizing for installer.")
            sanitized_name = pkg_path.name.replace(' ', '_')
            for char in problematic_chars:
                sanitized_name = sanitized_name.replace(char, '_')

            if sanitized_name != pkg_path.name:
                new_pkg_path = pkg_path.parent / sanitized_name
                try:
                    shutil.copy2(pkg_path, new_pkg_path)
                    logger.info(f"Created sanitized PKG copy: {new_pkg_path}")
                    pkg_path = new_pkg_path # Use the sanitized path for installation
                except Exception as copy_error:
                    logger.warning(f"Could not create sanitized PKG copy '{new_pkg_path}': {copy_error}. Using original path '{pkg_path}'.")
        else:
            logger.info("PKG filename is clean, no sanitization needed.")

        try:
            logger.info(f"Checking PKG signature for: {pkg_path}")
            pkg_check_cmd = ['pkgutil', '--check-signature', str(pkg_path)]
            pkg_check_result = subprocess.run(pkg_check_cmd, capture_output=True, text=True, check=False)
            logger.debug(f"PKG signature check cmd: {' '.join(pkg_check_cmd)}")
            logger.info(f"PKG signature check return code: {pkg_check_result.returncode}")
            if pkg_check_result.stdout: logger.info(f"PKG signature stdout: {pkg_check_result.stdout.strip()}")
            if pkg_check_result.stderr: logger.warning(f"PKG signature stderr: {pkg_check_result.stderr.strip()}")

            logger.info(f"Getting PKG info for: {pkg_path}")
            pkg_info_cmd = ['installer', '-pkg', str(pkg_path), '-target', '/', '-showChoicesXML']
            pkg_info_result = subprocess.run(pkg_info_cmd, capture_output=True, text=True, check=False)
            logger.debug(f"PKG info cmd: {' '.join(pkg_info_cmd)}")
            logger.info(f"PKG info return code: {pkg_info_result.returncode}")
            if pkg_info_result.stdout: logger.info(f"PKG info stdout (truncated): {pkg_info_result.stdout[:1000].strip()}...")
            if pkg_info_result.stderr: logger.warning(f"PKG info stderr: {pkg_info_result.stderr.strip()}")

            target = '/'
            logger.info(f"Installer target: {target}")

            base_cmd = ['installer', '-pkg', str(pkg_path), '-target', target, '-verboseR'] # Changed to -verboseR
            run_with_sudo = install_type == 'system' or bool(password)

            if run_with_sudo:
                cmd = ['sudo'] + base_cmd
                logger.info("Using sudo for installer command.")
            else:
                cmd = base_cmd
                logger.info("Attempting user-level installation (no sudo in command).")

            logger.info(f"Full installer command: {' '.join(cmd if not password else ['echo \"***\" | sudo -S'] + base_cmd)}")
            
            logger.info("Checking system state before installation...")
            logger.info(f"Available disk space on /: {shutil.disk_usage('/')[2] / (1024**3):.2f} GB")
            try:
                groups_output = subprocess.run(['groups'], capture_output=True, text=True, check=False).stdout.strip()
                logger.info(f"Current user groups: {groups_output}")
            except Exception as e_groups:
                logger.warning(f"Could not get user groups: {e_groups}")

            start_time = time.time()
            logger.info("Starting installer execution...")

            install_process_result = None
            if password and run_with_sudo:
                # Ensure 'sudo -S' is used correctly with the password
                # The command must be structured so `sudo -S` receives the password on stdin
                # and then executes the `installer` command.
                # Example: echo "password" | sudo -S installer ...
                # Note: The `cmd` list already includes `sudo` if `run_with_sudo` is true.
                # We need to adjust `cmd` if password is provided to use `sudo -S`.

                # Remove 'sudo' from cmd if already present, as we'll add 'sudo -S'
                if cmd[0] == 'sudo':
                    installer_part_of_cmd = cmd[1:]
                else: # Should not happen if password and run_with_sudo logic is correct
                    installer_part_of_cmd = cmd

                # Construct the shell command string for piping password
                # Ensure pkg_path is quoted if it contains spaces, though we sanitized it
                shell_cmd_str = f'echo "{password}" | sudo -S {" ".join(installer_part_of_cmd)}'
                logger.info(f"Password command (masked password): echo \"***\" | sudo -S {' '.join(installer_part_of_cmd)}")
                
                install_process_result = subprocess.run(
                    shell_cmd_str,
                    shell=True, # shell=True is needed for the pipe
                    capture_output=True, text=True, timeout=300 # 5 minutes timeout
                )
            else:
                install_process_result = subprocess.run(
                    cmd,
                    capture_output=True, text=True, timeout=300 # 5 minutes timeout
                )
            
            execution_time = time.time() - start_time
            logger.info(f"Installer execution completed in {execution_time:.2f} seconds.")
            logger.info(f"Installer return code: {install_process_result.returncode}")

            # Log full stdout and stderr, then truncate for return payload
            full_stdout = install_process_result.stdout
            full_stderr = install_process_result.stderr

            log_limit = 4000 # Increased limit for internal logging
            if full_stdout:
                logger.info("="*25 + " INSTALLER STDOUT (full) " + "="*25)
                logger.info(full_stdout)
                logger.info("="*25 + " END INSTALLER STDOUT (full) " + "="*25)
            else:
                logger.info("Installer STDOUT was empty.")
            
            if full_stderr:
                logger.error("="*25 + " INSTALLER STDERR (full) " + "="*25)
                logger.error(full_stderr)
                logger.error("="*25 + " END INSTALLER STDERR (full) " + "="*25)
            else:
                logger.info("Installer STDERR was empty (which is good).")

            # Check macOS installer logs - this remains a good diagnostic step
            logger.info("Checking macOS system logs for installer activity (last 2 mins)...")
            try:
                log_cmd = ['log', 'show', '--last', '2m', '--predicate', 'processImagePath contains "installer" or eventMessage contains "install" or senderImagePath contains "installd"']
                installer_log_result = subprocess.run(log_cmd, capture_output=True, text=True, timeout=30, check=False)
                if installer_log_result.stdout:
                    logger.info(f"Recent macOS system log entries related to installer (last {log_limit} chars):")
                    logger.info(installer_log_result.stdout[-log_limit:])
                else:
                    logger.info("No relevant entries found in macOS system logs for installer.")
                if installer_log_result.stderr:
                    logger.warning(f"Error fetching macOS system logs for installer: {installer_log_result.stderr.strip()}")
            except subprocess.TimeoutExpired:
                logger.warning("Timeout fetching macOS system logs for installer.")
            except Exception as log_error:
                logger.warning(f"Could not fetch macOS system logs for installer: {log_error}", exc_info=True)
            
            # Prepare truncated output for the return dictionary
            truncated_stdout = full_stdout[-2000:] if full_stdout else ""
            truncated_stderr = full_stderr[-2000:] if full_stderr else ""

            if install_process_result.returncode == 0:
                logger.info(f"PKG installation for '{original_pkg_path_name}' appears successful (return code 0). Scanning for newly installed items.")
                installed_items = self.scan_for_newly_installed_items(original_pkg_path_name)
                logger.info(f"Found {len(installed_items)} newly installed items related to '{original_pkg_path_name}'.")
                
                return {
                    'success': True,
                    'filename': original_pkg_path_name,
                    'installed_count': len(installed_items) if installed_items else 1,
                    'message': 'PKG installed successfully using macOS installer.',
                    'details': installed_items,
                    'installer_output': truncated_stdout, # Return truncated output
                    'installer_stderr': truncated_stderr, # Return truncated stderr
                    'log_file': str(LOG_FILE_PATH),
                    'execution_time': execution_time,
                    'return_code': install_process_result.returncode
                }
            else:
                # Construct a more detailed error message
                error_detail = f"Installer command failed with return code {install_process_result.returncode}."
                if full_stderr:
                    error_detail += f" Stderr: {full_stderr.strip()[:1000]}" # Add first 1000 chars of stderr
                elif full_stdout: # If stderr is empty, stdout might contain error info from some installers
                    error_detail += f" Stdout: {full_stdout.strip()[:1000]}"
                else:
                    error_detail += " No specific error message found in stdout/stderr."

                logger.error(f"PKG installation failed for '{original_pkg_path_name}'. {error_detail}")
                
                return {
                    'success': False,
                    'filename': original_pkg_path_name,
                    'error': error_detail,
                    'installer_output': truncated_stdout,
                    'installer_stderr': truncated_stderr,
                    'log_file': str(LOG_FILE_PATH),
                    'execution_time': execution_time,
                    'return_code': install_process_result.returncode
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"PKG installation timed out for {original_pkg_path_name} (>{300}s).", exc_info=True)
            return {
                'success': False,
                'filename': original_pkg_path_name,
                'error': 'Installation timed out (took longer than 5 minutes).',
                'log_file': str(LOG_FILE_PATH)
            }
        except Exception as e:
            logger.error(f"PKG installation exception for {original_pkg_path_name}: {e}", exc_info=True)
            return {
                'success': False,
                'filename': original_pkg_path_name,
                'error': f'Installation exception: {str(e)}',
                'log_file': str(LOG_FILE_PATH)
            }
        finally:
            # Clean up sanitized PKG if it was created
            if 'new_pkg_path' in locals() and new_pkg_path.exists() and new_pkg_path != pkg_path : # Check if new_pkg_path was defined and used
                 try:
                     logger.info(f"Cleaning up sanitized PKG copy: {new_pkg_path}")
                     new_pkg_path.unlink()
                 except Exception as e_clean:
                     logger.warning(f"Could not clean up sanitized PKG {new_pkg_path}: {e_clean}")


    def scan_for_newly_installed_items(self, pkg_name):
        """Scan common plugin locations to see what might have been installed."""
        logger.info(f"Scanning for newly installed items possibly related to PKG: {pkg_name}")
        installed_items = []
        search_paths = [
            Path('/Library/Audio/Plug-Ins/Components'), Path('/Library/Audio/Plug-Ins/VST'),
            Path('/Library/Audio/Plug-Ins/VST3'), Path('/Library/Application Support/Avid/Audio/Plug-Ins'),
            Path('/Applications'),
            Path.home() / 'Library/Audio/Plug-Ins/Components', Path.home() / 'Library/Audio/Plug-Ins/VST',
            Path.home() / 'Library/Audio/Plug-Ins/VST3',
            Path.home() / 'Library/Application Support/Avid/Audio/Plug-Ins',
            Path.home() / 'Applications'
        ]

        cutoff_time = time.time() - 120  # 2 minutes ago
        logger.debug(f"Scanning for items modified after: {datetime.datetime.fromtimestamp(cutoff_time).strftime('%Y-%m-%d %H:%M:%S')}")

        for search_path in search_paths:
            if search_path.exists():
                logger.debug(f"Scanning directory: {search_path}")
                try:
                    for item in search_path.iterdir():
                        try:
                            item_stat = item.stat()
                            if item_stat.st_mtime > cutoff_time or item_stat.st_ctime > cutoff_time: # Check modification or creation time
                                file_type = self.get_file_type(item.name)
                                # Heuristic: check if item name is related to pkg_name (optional, can be noisy)
                                # if file_type != 'unknown' and (pkg_name.lower() in item.name.lower() or item.name.lower() in pkg_name.lower()):
                                if file_type != 'unknown': # Simpler check: any recent plugin/app
                                    logger.info(f"Found potentially new/updated item: {item.name} in {search_path} (type: {file_type})")
                                    installed_items.append({
                                        'filename': item.name,
                                        'path': str(item),
                                        'file_type': file_type,
                                        'modified_time': datetime.datetime.fromtimestamp(item_stat.st_mtime).isoformat(),
                                        'created_time': datetime.datetime.fromtimestamp(item_stat.st_ctime).isoformat(),
                                        'success': True # Assuming if found, it's a success for this context
                                    })
                        except (PermissionError, OSError) as e_iter_item:
                            logger.warning(f"Could not stat item {item} in {search_path}: {e_iter_item}")
                            continue # Skip this item
                except (PermissionError, OSError) as e_iter_dir:
                    logger.warning(f"Could not iterate directory {search_path}: {e_iter_dir}")
                    continue # Skip this directory
            else:
                logger.debug(f"Search path does not exist, skipping: {search_path}")

        logger.info(f"Scan complete. Found {len(installed_items)} potentially new/updated items.")
        return installed_items

    def cleanup(self):
        """Clean up temporary files."""
        logger.info(f"Cleaning up temporary directory: {self.temp_dir}")
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logger.info(f"Successfully removed temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary directory {self.temp_dir}: {e}", exc_info=True)
            pass # ignore_errors=True handles this, but logging is good.

# Global installer instance
installer = MaestroInstaller()

# Make log file globally accessible (already defined as LOG_FILE_PATH)
# current_log_file = LOG_FILE_PATH # This is a Path object

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    logger.info("Health check endpoint called.")
    return jsonify({
        'status': 'healthy',
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
    """Batch install multiple files."""
    logger.info(f"Received request for /api/batch-install from {request.remote_addr}")
    try:
        if 'files' not in request.files:
            logger.warning("No files provided in /api/batch-install request.")
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        install_type = request.form.get('install_type', 'user')
        password = request.form.get('password', '') # Avoid logging password
        logger.info(f"Number of files: {len(files)}, Install Type: {install_type}, Password Provided: {'yes' if password else 'no'}")

        results = []
        
        for i, file in enumerate(files):
            if file.filename == '':
                logger.debug(f"Skipping empty filename in batch (file #{i+1}).")
                continue

            logger.info(f"Processing file {i+1}/{len(files)}: {file.filename}")
            temp_file_path = Path(installer.temp_dir) / file.filename
            logger.debug(f"Saving temporary file for batch: {temp_file_path}")
            file.save(temp_file_path)
            
            result = installer.install_file(temp_file_path, install_type, password)
            results.append(result)
            logger.info(f"Result for {file.filename} in batch: {result.get('success', False)}")
            
            try:
                logger.debug(f"Cleaning up temporary file from batch: {temp_file_path}")
                temp_file_path.unlink()
            except Exception as e_unlink_batch:
                logger.warning(f"Could not delete temporary file {temp_file_path} from batch: {e_unlink_batch}")
        
        summary = {
            'success': True, # Overall request success
            'results': results,
            'total_files': len(results),
            'successful_installs': sum(1 for r in results if r.get('success')),
            'failed_installs': sum(1 for r in results if not r.get('success'))
        }
        logger.info(f"Batch install summary: {summary['successful_installs']} successful, {summary['failed_installs']} failed out of {summary['total_files']}.")
        return jsonify(summary)
        
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

def find_free_port():
    """Find a free port for the Flask server."""
    logger.debug("Attempting to find a free port.")
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0)) # Bind to address 0.0.0.0, port 0 (OS assigns free port)
        s.listen(1)
        port = s.getsockname()[1]
    logger.info(f"Found free port: {port}")
    return port

if __name__ == '__main__':
    try:
        port = find_free_port()
        
        # This print is for the Swift app to capture the port.
        # It should ideally not go into the log file if stream_handler uses stdout.
        # Consider a separate mechanism or specific logger for this if it's an issue.
        print(f"MAESTRO_BACKEND_PORT={port}")
        sys.stdout.flush() # Ensure it's printed immediately
        
        logger.info(f"🚀 Starting Maestro Backend on port {port}")
        logger.info(f"🌐 Server URL: http://127.0.0.1:{port}")
        logger.info("📡 Backend is ready to accept requests. Werkzeug logs are now handled by our logger.")
        
        # Flask's 'debug=True' enables its own reloader and debugger, which can interfere
        # with production logging and behavior. Ensure it's False for this setup.
        # Werkzeug logger is already configured by setup_logging().
        app.run(host='127.0.0.1', port=port, debug=False, threaded=True, use_reloader=False)
        
    except KeyboardInterrupt:
        logger.info("🛑 Maestro Backend shutting down due to KeyboardInterrupt.")
    except Exception as e:
        logger.critical(f"❌ Failed to start server: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("🧹 Cleaning up temporary files before exit.")
        installer.cleanup()
        logging.info("👋 Maestro Backend shutdown complete.")