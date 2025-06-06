#!/usr/bin/env python3
"""
Maestro Backend - Simplified Batch Audio Plugin & App Installer
Automatically moves files to their correct locations based on file type.
"""

import os
import sys
import datetime
from pathlib import Path

# CRITICAL: Create log file FIRST before any other imports that might fail
def create_robust_log_file():
    """Create log file with multiple fallback strategies."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Try multiple log locations in order of preference
    possible_log_locations = [
        Path.home() / 'Maestro_Logs' / f'maestro_install_{timestamp}.log',
        Path.home() / f'maestro_install_{timestamp}.log',
        Path('/tmp') / f'maestro_install_{timestamp}.log',
        Path.cwd() / f'maestro_install_{timestamp}.log'
    ]
    
    for log_path in possible_log_locations:
        try:
            # Ensure directory exists
            log_path.parent.mkdir(exist_ok=True, parents=True)
            
            # Test write access
            with open(log_path, 'a') as f:
                f.write(f"# Maestro Log File Created: {datetime.datetime.now()}\n")
                f.write(f"# Backend startup initiated at: {datetime.datetime.now()}\n")
                f.write(f"# Python executable: {sys.executable}\n")
                f.write(f"# Working directory: {os.getcwd()}\n")
                f.write(f"# Log file location: {log_path}\n")
                f.flush()
            
            print(f"✅ Log file created: {log_path}")
            return log_path
            
        except Exception as e:
            print(f"❌ Failed to create log at {log_path}: {e}")
            continue
    
    # If all else fails, use stdout
    print("⚠️ WARNING: Could not create any log file, using stdout only")
    return None

# Create log file immediately
log_file = create_robust_log_file()

def robust_log(message, level="INFO"):
    """Write to log file with fallback to stdout."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    log_message = f"{timestamp} - {level} - {message}\n"
    
    # Always print to stdout
    print(f"[{level}] {message}")
    
    # Try to write to log file
    if log_file:
        try:
            with open(log_file, 'a') as f:
                f.write(log_message)
                f.flush()
        except Exception as e:
            print(f"⚠️ Failed to write to log file: {e}")

# Log startup
robust_log("🎼 MAESTRO BACKEND STARTUP INITIATED")
robust_log(f"🐍 Python Version: {sys.version}")
robust_log(f"📍 Working Directory: {os.getcwd()}")
robust_log(f"👤 User: {os.getenv('USER', 'unknown')}")

# Now try to import other modules with error handling
try:
    robust_log("📦 Importing required modules...")
    import shutil
    import subprocess
    import tempfile
    import time
    import zipfile
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    import logging
    robust_log("✅ All modules imported successfully")
except ImportError as e:
    robust_log(f"❌ CRITICAL: Failed to import required modules: {e}", "ERROR")
    sys.exit(1)
except Exception as e:
    robust_log(f"❌ CRITICAL: Unexpected error during imports: {e}", "ERROR")
    sys.exit(1)

# Setup proper logging now that modules are loaded
if log_file:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
else:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

logger = logging.getLogger(__name__)

# Enhanced startup logging
logger.info("="*80)
logger.info("🎼 MAESTRO AUDIO PLUGIN INSTALLER - BACKEND STARTED")
logger.info("="*80)
logger.info(f"⏰ Startup Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"📁 Log File: {log_file}")
logger.info(f"📂 Log Directory: {log_file.parent if log_file else 'No log file'}")
logger.info(f"🐍 Python Version: {sys.version}")
logger.info(f"📍 Working Directory: {os.getcwd()}")
logger.info(f"👤 User: {os.getenv('USER', 'unknown')}")

# System information
try:
    macos_version = subprocess.run(['sw_vers', '-productVersion'], capture_output=True, text=True).stdout.strip()
    logger.info(f"🍎 macOS Version: {macos_version}")
    
    # Check disk space
    import shutil
    total, used, free = shutil.disk_usage(Path.home())
    free_gb = free // (1024**3)
    total_gb = total // (1024**3)
    logger.info(f"💾 Disk Space: {free_gb} GB free of {total_gb} GB total")
    
    # Check user groups
    import grp
    groups = [g.gr_name for g in grp.getgrall() if os.getenv('USER', '') in g.gr_mem]
    if 'admin' in groups:
        logger.info(f"🔑 User Groups: {', '.join(groups)} (Admin privileges available)")
    else:
        logger.info(f"🔑 User Groups: {', '.join(groups)} (No admin privileges)")
        
except Exception as e:
    logger.warning(f"⚠️  Could not gather system information: {e}")

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
os.environ['FLASK_ENV'] = 'production'
os.environ['NO_COLOR'] = '1'

# Configure Flask logging to reduce noise
import logging
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)

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
        filename_lower = filename.lower()
        
        if filename_lower.endswith('.component'):
            return 'component'
        elif filename_lower.endswith('.vst'):
            return 'vst'
        elif filename_lower.endswith('.vst3'):
            return 'vst3'
        elif filename_lower.endswith('.aax'):
            return 'aax'
        elif filename_lower.endswith('.app'):
            return 'app'
        elif filename_lower.endswith('.pkg'):
            return 'pkg'
        else:
            return 'unknown'

    def ensure_directory_exists(self, path, use_sudo=False):
        """Ensure target directory exists, create if necessary."""
        try:
            if not path.exists():
                if use_sudo:
                    subprocess.run(['sudo', 'mkdir', '-p', str(path)], check=True)
                    subprocess.run(['sudo', 'chmod', '755', str(path)], check=True)
                else:
                    path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False

    def move_file(self, source_path, dest_path, use_sudo=False):
        """Move file to destination, handling permissions appropriately."""
        try:
            logger.info(f"Moving {source_path} to {dest_path} (sudo: {use_sudo})")
            
            if use_sudo:
                # Use sudo to copy the file
                subprocess.run(['sudo', 'cp', '-R', str(source_path), str(dest_path)], check=True, capture_output=True)
                
                # Set proper permissions for the installed file
                subprocess.run(['sudo', 'chmod', '-R', '755', str(dest_path)], check=True, capture_output=True)
                
                # For user-owned directories, fix ownership
                if '/Library' in str(dest_path) and not str(dest_path).startswith('/Library'):
                    current_user = os.getenv('USER')
                    if current_user:
                        subprocess.run(['sudo', 'chown', '-R', f'{current_user}:staff', str(dest_path)], 
                                     check=True, capture_output=True)
            else:
                if source_path.is_dir():
                    shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(source_path, dest_path)
            
            logger.info(f"Successfully moved {source_path.name} to {dest_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to move {source_path} to {dest_path}: {e}")
            return False

    def codesign_file(self, file_path):
        """Codesign the installed file for macOS compatibility."""
        try:
            subprocess.run([
                'codesign', '--force', '--sign', '-', '--deep', str(file_path)
            ], check=True, capture_output=True)
            logger.info(f"Successfully codesigned: {file_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"Codesign failed for {file_path}: {e}")
            return False

    def extract_pkg(self, pkg_path, extract_dir):
        """Extract PKG file and find audio plugins/apps."""
        try:
            logger.info(f"Extracting PKG file: {pkg_path}")
            
            # Create extraction directory
            extract_path = Path(extract_dir) / "extracted"
            extract_path.mkdir(exist_ok=True)
            
            # Extract the PKG using pkgutil
            logger.info("Expanding PKG package...")
            result = subprocess.run([
                'pkgutil', '--expand', str(pkg_path), str(extract_path)
            ], capture_output=True, text=True, check=True)
            
            logger.info(f"PKG expanded successfully to {extract_path}")
            
            # Find payload files and extract them
            found_files = []
            payload_files = list(extract_path.rglob("Payload"))
            
            if not payload_files:
                # Try alternative payload file names
                payload_files = list(extract_path.rglob("payload")) + list(extract_path.rglob("Archive.pax.gz"))
            
            logger.info(f"Found {len(payload_files)} payload files")
            
            for i, payload_file in enumerate(payload_files):
                if payload_file.is_file():
                    payload_extract = extract_path / f"payload_{i}"
                    payload_extract.mkdir(exist_ok=True)
                    
                    logger.info(f"Extracting payload: {payload_file}")
                    
                    # Try multiple extraction methods
                    extraction_successful = False
                    
                    # Method 1: Direct cpio
                    try:
                        with open(payload_file, 'rb') as f:
                            subprocess.run([
                                'cpio', '-idm'
                            ], input=f.read(), cwd=payload_extract, check=True, capture_output=True)
                        extraction_successful = True
                        logger.info("Extracted using direct cpio")
                    except subprocess.CalledProcessError:
                        pass
                    
                    # Method 2: Gunzip + cpio
                    if not extraction_successful:
                        try:
                            subprocess.run([
                                'sh', '-c', f'cd "{payload_extract}" && gunzip -c "{payload_file}" | cpio -idm'
                            ], check=True, capture_output=True, text=True)
                            extraction_successful = True
                            logger.info("Extracted using gunzip + cpio")
                        except subprocess.CalledProcessError:
                            pass
                    
                    # Method 3: Try as tar.gz
                    if not extraction_successful:
                        try:
                            subprocess.run([
                                'tar', '-xzf', str(payload_file), '-C', str(payload_extract)
                            ], check=True, capture_output=True)
                            extraction_successful = True
                            logger.info("Extracted using tar")
                        except subprocess.CalledProcessError:
                            pass
                    
                    if extraction_successful:
                        # Look for audio plugins and apps recursively
                        for item in payload_extract.rglob("*"):
                            if item.is_file() or item.is_dir():
                                item_name_lower = item.name.lower()
                                if any(item_name_lower.endswith(ext) for ext in ['.component', '.vst', '.vst3', '.aax', '.app']):
                                    found_files.append(item)
                                    logger.info(f"Found: {item.name} ({item})")
                    else:
                        logger.warning(f"Failed to extract payload: {payload_file}")
            
            logger.info(f"Total files found: {len(found_files)}")
            return found_files
            
        except Exception as e:
            logger.error(f"Failed to extract PKG {pkg_path}: {e}")
            return []

    def install_file(self, file_path, install_type='user', password=None):
        """Install a single file to the appropriate location."""
        try:
            file_path = Path(file_path)
            file_type = self.get_file_type(file_path.name)
            
            if file_type == 'unknown':
                return {
                    'success': False,
                    'filename': file_path.name,
                    'error': 'Unsupported file type'
                }
            
            # Handle PKG files specially
            if file_type == 'pkg':
                return self.install_pkg(file_path, install_type, password)
            
            # Get destination path
            if file_type not in self.install_paths[install_type]:
                return {
                    'success': False,
                    'filename': file_path.name,
                    'error': f'No installation path defined for {file_type}'
                }
            
            dest_dir = self.install_paths[install_type][file_type]
            dest_path = dest_dir / file_path.name
            
            # Check if file already exists
            if dest_path.exists():
                return {
                    'success': False,
                    'filename': file_path.name,
                    'error': f'File already exists at {dest_path}'
                }
            
            # Ensure destination directory exists
            use_sudo = install_type == 'system'
            if not self.ensure_directory_exists(dest_dir, use_sudo):
                return {
                    'success': False,
                    'filename': file_path.name,
                    'error': f'Failed to create destination directory {dest_dir}'
                }
            
            # Move the file
            if not self.move_file(file_path, dest_path, use_sudo):
                return {
                    'success': False,
                    'filename': file_path.name,
                    'error': f'Failed to move file to {dest_path}'
                }
            
            # Codesign the installed file
            self.codesign_file(dest_path)
            
            return {
                'success': True,
                'filename': file_path.name,
                'installed_path': str(dest_path),
                'file_type': file_type
            }
            
        except Exception as e:
            logger.error(f"Installation error for {file_path}: {e}")
            return {
                'success': False,
                'filename': file_path.name if file_path else 'unknown',
                'error': str(e)
            }

    def install_pkg(self, pkg_path, install_type='user', password=None):
        """Install PKG file using macOS installer command (like InstallPKG tool)."""
        try:
            logger.info("="*80)
            logger.info(f"Starting PKG installation: {pkg_path}")
            logger.info(f"Original filename: {pkg_path.name}")
            logger.info(f"Install type: {install_type}")
            logger.info(f"Password provided: {'Yes' if password else 'No'}")
            logger.info(f"PKG file size: {pkg_path.stat().st_size} bytes")
            logger.info(f"PKG file exists: {pkg_path.exists()}")
            logger.info(f"PKG file readable: {os.access(pkg_path, os.R_OK)}")
            
            # Check for special characters in filename that might cause issues
            problematic_chars = ['@', '#', '$', '%', '^', '&', '*', '(', ')', '[', ']', '{', '}', '|', '\\', ':', ';', '"', "'", '<', '>', ',', '?', '/', '`', '~']
            has_spaces = ' ' in pkg_path.name
            has_problematic = any(char in pkg_path.name for char in problematic_chars)
            
            if has_spaces or has_problematic:
                logger.warning(f"PKG filename contains spaces or special characters: {pkg_path.name}")
                logger.info("This might cause issues with macOS installer. Attempting installation...")
                
                # Create a sanitized copy if needed
                sanitized_name = pkg_path.name.replace(' ', '_')
                for char in problematic_chars:
                    sanitized_name = sanitized_name.replace(char, '_')
                
                if sanitized_name != pkg_path.name:
                    logger.info(f"Creating sanitized copy: {sanitized_name}")
                    sanitized_path = pkg_path.parent / sanitized_name
                    try:
                        shutil.copy2(pkg_path, sanitized_path)
                        logger.info(f"Sanitized copy created: {sanitized_path}")
                        # Use the sanitized copy for installation
                        pkg_path = sanitized_path
                    except Exception as copy_error:
                        logger.warning(f"Could not create sanitized copy: {copy_error}, using original")
            else:
                logger.info("PKG filename looks clean, no sanitization needed")
            
            # Check if PKG is valid
            logger.info("Checking PKG validity...")
            pkg_check = subprocess.run(['pkgutil', '--check-signature', str(pkg_path)], 
                                     capture_output=True, text=True)
            logger.info(f"PKG signature check return code: {pkg_check.returncode}")
            logger.info(f"PKG signature stdout: {pkg_check.stdout}")
            logger.info(f"PKG signature stderr: {pkg_check.stderr}")
            
            # Get PKG info
            logger.info("Getting PKG information...")
            pkg_info = subprocess.run(['installer', '-pkg', str(pkg_path), '-target', '/', '-showChoicesXML'], 
                                    capture_output=True, text=True)
            logger.info(f"PKG info return code: {pkg_info.returncode}")
            logger.info(f"PKG info stdout: {pkg_info.stdout[:1000]}...")  # Truncate long output
            if pkg_info.stderr:
                logger.warning(f"PKG info stderr: {pkg_info.stderr}")
            
            # Determine target - PKGs typically install to their intended locations
            target = '/'  # Root target lets the PKG decide where to install
            logger.info(f"Using target: {target}")
            
            # Build installer command
            if install_type == 'system' or password:
                cmd = ['sudo', 'installer', '-pkg', str(pkg_path), '-target', target, '-verbose']
                logger.info("Using sudo installer for system installation")
            else:
                cmd = ['installer', '-pkg', str(pkg_path), '-target', target, '-verbose']
                logger.info("Attempting user installation")
            
            logger.info(f"Installer command: {' '.join(cmd)}")
            
            # Check system requirements
            logger.info("Checking system state...")
            logger.info(f"Available disk space: {shutil.disk_usage('/')[2] / (1024**3):.2f} GB")
            logger.info(f"Current user groups: {subprocess.run(['groups'], capture_output=True, text=True).stdout.strip()}")
            
            # Execute the installer command
            start_time = time.time()
            logger.info("Starting installer execution...")
            
            if password and 'sudo' in cmd:
                # For sudo commands with password, use echo to pipe password
                password_cmd = f'echo "***" | sudo -S installer -pkg "{pkg_path}" -target {target} -verbose'
                logger.info(f"Password command (masked): {password_cmd}")
                
                # Actually run with real password
                real_password_cmd = f'echo "{password}" | sudo -S installer -pkg "{pkg_path}" -target {target} -verbose'
                result = subprocess.run(['bash', '-c', real_password_cmd], 
                                      capture_output=True, text=True, timeout=300)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            execution_time = time.time() - start_time
            logger.info(f"Installer execution completed in {execution_time:.2f} seconds")
            logger.info(f"Installer return code: {result.returncode}")
            logger.info("="*50 + " INSTALLER STDOUT " + "="*50)
            logger.info(result.stdout)
            logger.info("="*50 + " END STDOUT " + "="*50)
            
            if result.stderr:
                logger.error("="*50 + " INSTALLER STDERR " + "="*50)
                logger.error(result.stderr)
                logger.error("="*50 + " END STDERR " + "="*50)
            
            # Check installer logs
            logger.info("Checking installer logs...")
            try:
                installer_log = subprocess.run(['log', 'show', '--last', '2m', '--predicate', 'subsystem == "com.apple.installer"'], 
                                             capture_output=True, text=True, timeout=30)
                if installer_log.stdout:
                    logger.info("Recent installer log entries:")
                    logger.info(installer_log.stdout[-2000:])  # Last 2000 chars
            except Exception as log_error:
                logger.warning(f"Could not fetch installer logs: {log_error}")
            
            if result.returncode == 0:
                logger.info("Installation appears successful, scanning for installed items...")
                # Try to determine what was installed by checking common plugin locations
                installed_items = self.scan_for_newly_installed_items(pkg_path.name)
                logger.info(f"Found {len(installed_items)} newly installed items")
                
                return {
                    'success': True,
                    'filename': pkg_path.name,
                    'installed_count': len(installed_items) if installed_items else 1,
                    'message': 'PKG installed successfully using macOS installer',
                    'details': installed_items,
                    'installer_output': result.stdout,
                    'log_file': str(log_file),
                    'execution_time': execution_time
                }
            else:
                error_msg = result.stderr or result.stdout or 'Installation failed'
                logger.error(f"Installation failed with error: {error_msg}")
                
                return {
                    'success': False,
                    'filename': pkg_path.name,
                    'error': f'Installer failed (code {result.returncode}): {error_msg}',
                    'installer_output': result.stdout,
                    'installer_stderr': result.stderr,
                    'log_file': str(log_file),
                    'execution_time': execution_time
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"PKG installation timed out for {pkg_path}")
            return {
                'success': False,
                'filename': pkg_path.name,
                'error': 'Installation timed out (took longer than 5 minutes)',
                'log_file': str(log_file)
            }
        except Exception as e:
            logger.error(f"PKG installation exception for {pkg_path}: {e}", exc_info=True)
            return {
                'success': False,
                'filename': pkg_path.name,
                'error': f'Installation exception: {str(e)}',
                'log_file': str(log_file)
            }

    def scan_for_newly_installed_items(self, pkg_name):
        """Scan common plugin locations to see what might have been installed."""
        try:
            installed_items = []
            
            # Common plugin installation directories
            search_paths = [
                Path('/Library/Audio/Plug-Ins/Components'),
                Path('/Library/Audio/Plug-Ins/VST'),
                Path('/Library/Audio/Plug-Ins/VST3'),
                Path('/Library/Application Support/Avid/Audio/Plug-Ins'),
                Path('/Applications'),
                Path.home() / 'Library/Audio/Plug-Ins/Components',
                Path.home() / 'Library/Audio/Plug-Ins/VST',
                Path.home() / 'Library/Audio/Plug-Ins/VST3',
                Path.home() / 'Library/Application Support/Avid/Audio/Plug-Ins',
                Path.home() / 'Applications'
            ]
            
            # Look for recently modified items (within last 2 minutes)
            cutoff_time = time.time() - 120  # 2 minutes ago
            
            for search_path in search_paths:
                if search_path.exists():
                    try:
                        for item in search_path.iterdir():
                            if item.stat().st_mtime > cutoff_time:
                                file_type = self.get_file_type(item.name)
                                if file_type != 'unknown':
                                    installed_items.append({
                                        'filename': item.name,
                                        'path': str(item),
                                        'file_type': file_type,
                                        'success': True
                                    })
                    except (PermissionError, OSError):
                        continue
            
            return installed_items
            
        except Exception as e:
            logger.warning(f"Could not scan for installed items: {e}")
            return []

    def cleanup(self):
        """Clean up temporary files."""
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass

# Global installer instance
installer = MaestroInstaller()

# Make log file globally accessible
current_log_file = log_file

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'message': 'Maestro Backend is running'
    })

@app.route('/api/install', methods=['POST'])
def install_file():
    """Install a single file endpoint."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        install_type = request.form.get('install_type', 'user')
        password = request.form.get('password', '')
        
        # Save uploaded file temporarily
        temp_file_path = Path(installer.temp_dir) / file.filename
        file.save(temp_file_path)
        
        # Install the file
        result = installer.install_file(temp_file_path, install_type, password)
        
        # Clean up temp file
        try:
            temp_file_path.unlink()
        except:
            pass
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Install endpoint error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/batch-install', methods=['POST'])
def batch_install():
    """Batch install multiple files."""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        install_type = request.form.get('install_type', 'user')
        password = request.form.get('password', '')
        
        results = []
        
        for file in files:
            if file.filename == '':
                continue
                
            # Save uploaded file temporarily
            temp_file_path = Path(installer.temp_dir) / file.filename
            file.save(temp_file_path)
            
            # Install the file
            result = installer.install_file(temp_file_path, install_type, password)
            results.append(result)
            
            # Clean up temp file
            try:
                temp_file_path.unlink()
            except:
                pass
        
        return jsonify({
            'success': True,
            'results': results,
            'total_files': len(results),
            'successful': sum(1 for r in results if r['success']),
            'failed': sum(1 for r in results if not r['success'])
        })
        
    except Exception as e:
        logger.error(f"Batch install endpoint error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/install-paths', methods=['GET'])
def get_install_paths():
    """Get available installation paths."""
    return jsonify({
        'user_paths': {k: str(v) for k, v in installer.install_paths['user'].items()},
        'system_paths': {k: str(v) for k, v in installer.install_paths['system'].items()}
    })

@app.route('/api/log-info', methods=['GET'])
def get_log_info():
    """Get current log file information."""
    return jsonify({
        'log_file': str(current_log_file) if current_log_file else 'No log file',
        'log_dir': str(current_log_file.parent) if current_log_file else 'No log directory',
        'log_exists': current_log_file.exists() if current_log_file else False,
        'log_size': current_log_file.stat().st_size if current_log_file and current_log_file.exists() else 0
    })

@app.route('/api/log-content', methods=['GET'])
def get_log_content():
    """Get the content of the current log file."""
    try:
        if current_log_file.exists():
            with open(current_log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return "No log file found. Install some files to generate logs.", 404
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return f"Error reading log file: {str(e)}", 500

@app.route('/api/debug', methods=['GET'])
def debug_info():
    """Debug endpoint to check backend status."""
    return jsonify({
        'status': 'Backend is running successfully',
        'log_file': str(current_log_file) if current_log_file else 'No log file',
        'log_exists': current_log_file.exists() if current_log_file else False,
        'timestamp': datetime.datetime.now().isoformat(),
        'message': 'If you can see this, the backend is working correctly'
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

def find_free_port():
    """Find a free port for the Flask server."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

if __name__ == '__main__':
    try:
        # Find a free port
        port = find_free_port()
        
        # Print the port so the Swift app can discover it
        print(f"MAESTRO_BACKEND_PORT={port}")
        sys.stdout.flush()
        
        # Start the Flask server with custom logging
        logger.info(f"🚀 Starting Maestro Backend on port {port}")
        logger.info(f"🌐 Server URL: http://127.0.0.1:{port}")
        logger.info("📡 Backend is ready to accept requests")
        
        # Suppress Flask's default startup messages and use our logging
        import logging
        log = logging.getLogger('werkzeug')
        log.disabled = True
        
        app.run(host='127.0.0.1', port=port, debug=False, threaded=True, use_reloader=False)
        
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down Maestro Backend")
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        sys.exit(1)
    finally:
        logger.info("🧹 Cleaning up temporary files")
        installer.cleanup() 