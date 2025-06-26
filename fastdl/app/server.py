import os
import re
import mimetypes
import sqlite3
import bz2
import hashlib
from pathlib import Path
from typing import Optional, Dict, Tuple
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import uvicorn
import threading
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
import signal
import sys

app = FastAPI(title="FastDL", description="FastDL server for CS:Source and CS 1.6")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=False,
	allow_methods=["GET"],
	allow_headers=[
		"Accept",
		"Accept-Encoding",
		"User-Agent"
	],
	expose_headers=[
		"Content-Length",
		"Content-Type",
		"ETag",
		"Cache-Control",
		"Last-Modified",
		"Content-Range"
	],
	max_age=3600
)

# ALLOWED_FILENAME_CHARS = re.compile(r'^[a-zA-Z0-9._\-()[\]{}!@#$%^&+=~` /]+$')
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

CSS_PATH = os.getenv("CSS_PATH", "/css")
CS16_PATH = os.getenv("CS16_PATH", "/cs16")

HOST = os.getenv("FASTDL_HOST", "0.0.0.0")
PORT = int(os.getenv("FASTDL_PORT", "3939"))

ENABLE_COMPRESSION = os.getenv("ENABLE_COMPRESSION", "false").lower() == "true"
ENABLE_WATCHER = os.getenv("ENABLE_WATCHER", "false").lower() == "true"
ENABLE_SERVER = os.getenv("ENABLE_SERVER", "true").lower() == "true"

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "104857600"))  # 100MB
BZ2_PATH = "/bz2"
DB_PATH = "/data/bz2_paths.db"

compression_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="bz2_worker")
db_lock = threading.Lock()

ALLOWED_EXTENSIONS = {
	".bsp", # Map files
	".bz2", # Compressed files for CS:Source
	".nav", # Navigation mesh files
	".mdl", # Model files
	".phy", # Physics files
	".vtx", # Vertex files
	".vvd", # Valve Vertex Data
	".dx80.vtx", ".dx90.vtx", # DirectX vertex files
	".sw.vtx", # Software vertex files
	".vmt", # Valve Material Type
	".vtf", # Valve Texture Format
	".wav", # Sound files
	".mp3", # Sound files
	".pcf", # Particle files
	".spr", # Sprite files
	".wad", # Texture wad files (CS 1.6)
	".tga", # Texture files
	".jpg", ".jpeg", ".png", ".gif" # Image files
}

ALLOWED_PATHS_CSS = {
	"maps",
	"materials",
	"models",
	"particles",
	"sound",
	"resource",
	"media"
}

ALLOWED_PATHS_CS16 = {
	"maps",
	"models",
	"sprites",
	"sound",
	"gfx",
	"overviews",
	"resource",
	"media"
}

def debug(msg: str):
	if DEBUG:
		print(f"DEBUG: {str}")

def init_db():
	os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
	os.makedirs(BZ2_PATH, exist_ok=True)
	
	with sqlite3.connect(DB_PATH) as conn:
		conn.execute("""
			CREATE TABLE IF NOT EXISTS bz2_paths (
				original_path TEXT PRIMARY KEY,
				bz2_path TEXT NOT NULL,
				file_hash TEXT NOT NULL,
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				file_size INTEGER
			)
		""")
		conn.execute("CREATE INDEX IF NOT EXISTS idx_file_hash ON bz2_paths(file_hash)")
		conn.commit()

def get_file_hash(file_path: Path) -> str:
	hash_sha256 = hashlib.sha256()
	try:
		with open(file_path, "rb") as f:
			while chunk := f.read(8192):
				hash_sha256.update(chunk)
		return hash_sha256.hexdigest()
	except OSError as e:
		debug("Error hashing file {file_path}: {e}")
		raise

def compress_file(original_path: Path) -> Optional[Path]:
	try:
		if not original_path.exists() or not original_path.is_file():
			return None
		
		if not check_file_size(original_path):
			debug("File too large to compress: {original_path}")
			return None
		
		rel_path = original_path.relative_to(CSS_PATH)
		bz2_rel_path = rel_path.with_suffix(rel_path.suffix + ".bz2")
		bz2_abs_path = Path(BZ2_PATH) / bz2_rel_path
		
		os.makedirs(bz2_abs_path.parent, exist_ok=True)
		
		with open(original_path, 'rb') as f_in, bz2.BZ2File(bz2_abs_path, 'wb') as f_out:
			while chunk := f_in.read(8192):
				f_out.write(chunk)
		
		return bz2_abs_path
	except Exception as e:
		debug("Error compressing {original_path}: {e}")
		return None

def update_bz2_mapping(original_path: Path):
	def _compress_task():
		try:
			if not should_compress_file(original_path):
				return
			
			file_hash = get_file_hash(original_path)
			file_size = original_path.stat().st_size
			original_abs = str(original_path.resolve())
			debug("Compressing file: {original_abs}")
			
			with db_lock:
				with sqlite3.connect(DB_PATH) as conn:
					cursor = conn.cursor()
					
					cursor.execute("SELECT bz2_path, file_hash FROM bz2_paths WHERE original_path = ?", (original_abs,))
					result = cursor.fetchone()
					
					if result:
						existing_bz2_path, existing_hash = result
						if existing_hash == file_hash and Path(existing_bz2_path).exists():
							debug("File already compressed and up to date: {original_abs}")
							return
						else:
							bz2_path_obj = Path(existing_bz2_path)
							if bz2_path_obj.exists():
								bz2_path_obj.unlink()
					
					bz2_path = compress_file(original_path)
					if bz2_path:
						debug("Compressed to: {bz2_path}")
						cursor.execute("""
							INSERT OR REPLACE INTO bz2_paths (original_path, bz2_path, file_hash, file_size)
							VALUES (?, ?, ?, ?)
						""", (original_abs, str(bz2_path), file_hash, file_size))
						conn.commit()
					else:
						debug("Failed to compress: {original_abs}")
		except Exception as e:
			debug("Error in compress task: {e}")
	
	compression_executor.submit(_compress_task)

def should_compress_file(file_path: Path) -> bool:
	try:
		if not file_path.is_file() or file_path.suffix == '.bz2':
			return False
		
		rel_path = file_path.relative_to(CSS_PATH)
		path_parts = rel_path.parts
		
		if not path_parts or path_parts[0].lower() not in ALLOWED_PATHS_CSS:
			return False
		
		# Check for compound extensions like .dx80.vtx
		if len(file_path.suffixes) > 1:
			compound_ext = "".join(file_path.suffixes).lower()
			if compound_ext in ALLOWED_EXTENSIONS:
				return True
		
		# Check single extension
		return file_path.suffix.lower() in ALLOWED_EXTENSIONS
	except (ValueError, OSError):
		return False

def get_bz2_path(original_path: str) -> Optional[str]:
	try:
		with db_lock:
			with sqlite3.connect(DB_PATH) as conn:
				cursor = conn.cursor()
				cursor.execute("SELECT bz2_path FROM bz2_paths WHERE original_path = ?", (original_path,))
				result = cursor.fetchone()
				
				if result and Path(result[0]).exists():
					return result[0]
				return None
	except Exception as e:
		debug("Error getting bz2 path: {e}")
		return None

def remove_bz2_mapping(original_path: str):
	def _remove_task():
		try:
			with db_lock:
				with sqlite3.connect(DB_PATH) as conn:
					cursor = conn.cursor()
					cursor.execute("SELECT bz2_path FROM bz2_paths WHERE original_path = ?", (original_path,))
					result = cursor.fetchone()
					
					if result:
						bz2_path = Path(result[0])
						if bz2_path.exists():
							bz2_path.unlink()
						cursor.execute("DELETE FROM bz2_paths WHERE original_path = ?", (original_path,))
					
					conn.commit()
		except Exception as e:
			debug("Error removing bz2 mapping: {e}")
	
	compression_executor.submit(_remove_task)

class CSSFileHandler(FileSystemEventHandler):
	def on_created(self, event):
		if not event.is_directory:
			update_bz2_mapping(Path(event.src_path))
	
	def on_modified(self, event):
		if not event.is_directory:
			update_bz2_mapping(Path(event.src_path))
	
	def on_deleted(self, event):
		if not event.is_directory:
			remove_bz2_mapping(str(Path(event.src_path).resolve()))

def start_file_watcher():
	if not os.path.exists(CSS_PATH):
		return None
	
	event_handler = CSSFileHandler()
	observer = Observer()
	observer.schedule(event_handler, CSS_PATH, recursive=True)
	observer.start()
	return observer

def initial_compression():
	def _initial_task():
		css_path = Path(CSS_PATH)
		if not css_path.exists():
			return
		
		for file_path in css_path.rglob("*"):
			if file_path.is_file() and should_compress_file(file_path):
				update_bz2_mapping(file_path)
	
	compression_executor.submit(_initial_task)

def http404():
	raise HTTPException(status_code=404, detail="Not Found")

def http400():
	raise HTTPException(status_code=400, detail="Bad Request")

def sanitize_path(path: str) -> str:
	if not path or not isinstance(path, str):
		raise ValueError("Invalid path")

	# Check for null bytes
	if "\x00" in path:
		raise ValueError("Null byte in path")

	# Dumbass regex pattern, might not work
	# if not ALLOWED_FILENAME_CHARS.match(path):
	#	raise ValueError("Invalid characters in path")
	
	# Check for dangerous patterns
	dangerous_patterns = ["../", "..\\", "..", "~", "$"]
	for pattern in dangerous_patterns:
		if pattern in path:
			raise ValueError("Dangerous path pattern")
	
	return path.strip()

def is_path_allowed(path: str, game_type: str) -> bool:
	try:
		sanitized_path = sanitize_path(path)
		path_parts = Path(sanitized_path).parts
		
		if not path_parts:
			return False
		
		first_dir = path_parts[0].lower()
		if game_type == "css":
			return first_dir in ALLOWED_PATHS_CSS
		elif game_type == "cs16":
			return first_dir in ALLOWED_PATHS_CS16
		
		return False
	except (ValueError, OSError):
		return False

def is_extension_allowed(filename: str, check_original_for_bz2: bool = False) -> bool:
	try:
		sanitized_filename = sanitize_path(filename)
		file_path = Path(sanitized_filename)
		
		if check_original_for_bz2 and sanitized_filename.endswith('.bz2'):
			original_filename = sanitized_filename[:-4]
			file_path = Path(original_filename)

		if len(file_path.suffixes) > 1:
			compound_ext = "".join(file_path.suffixes).lower()
			if compound_ext in ALLOWED_EXTENSIONS:
				return True

		return file_path.suffix.lower() in ALLOWED_EXTENSIONS
	except (ValueError, OSError):
		return False

def get_safe_path(base_path: str, requested_path: str) -> Optional[Path]:
	try:
		sanitized_path = sanitize_path(requested_path)
		base = Path(base_path).resolve()  # Remove strict=True
		target = (base / sanitized_path).resolve()
		
		try:
			target.relative_to(base)
		except ValueError:
			debug("Path traversal attempt: {target} not within {base}")
			return None
		
		if target.exists() and target.is_file() and not target.is_symlink():
			if not check_file_size(target):
				debug("File too large: {target}")
				return None
			return target
		
		debug("File does not exist or is not a regular file: {target}")
		return None
	except (ValueError, OSError, RuntimeError) as e:
		debug("get_safe_path error: {e}")
		return None

def check_file_size(file_path: Path) -> bool:
	try:
		return file_path.stat().st_size <= MAX_FILE_SIZE
	except OSError:
		return False

@app.get("/", response_class=PlainTextResponse)
async def root():
	return "FastDL Server for Counter-Strike:Source and Counter-Strike:1.6"

@app.get("/css/{path:path}")
async def serve_css_file(path: str, request: Request):
	try:
		sanitized_path = sanitize_path(path)

		if sanitized_path.endswith('.bz2'):
			original_path_str = sanitized_path[:-4]
			
			if not is_path_allowed(original_path_str, "css") or not is_extension_allowed(sanitized_path, check_original_for_bz2=True):
				debug("Path not allowed or extension not allowed: {original_path_str}")
				http404()

			original_path = Path(CSS_PATH) / original_path_str
			original_abs = str(original_path.resolve())
			
			debug("Looking for bz2 path for original: {original_abs}")
			
			bz2_path = get_bz2_path(original_abs)
			debug("get_bz2_path returned: {bz2_path}")
			
			if not bz2_path:
				debug("No bz2_path found in database for: {original_abs}")
				http404()
				
			bz2_file_path = Path(bz2_path)
			if not bz2_file_path.exists():
				debug("bz2 file does not exist at: {bz2_path}")
				http404()

			if not check_file_size(bz2_file_path):
				debug("BZ2 file too large: {bz2_path}")
				http404()
			
			debug("Serving bz2 file: {bz2_path}")
			return FileResponse(
				path=bz2_path,
				media_type="application/x-bzip2",
				filename=Path(original_path_str).name + ".bz2"
			)
		else:
			if not is_path_allowed(sanitized_path, "css") or not is_extension_allowed(sanitized_path):
				debug("Path not allowed or extension not allowed: {sanitized_path}")
				http404()
			
			file_path = get_safe_path(CSS_PATH, sanitized_path)
			if not file_path:
				debug("get_safe_path returned None for: {sanitized_path}")
				http404()
			
			original_abs = str(file_path.resolve())
			bz2_path = get_bz2_path(original_abs)
			
			if bz2_path and Path(bz2_path).exists():
				debug("Redirecting to compressed version: /css/{sanitized_path}.bz2")
				return RedirectResponse(url=f"/css/{sanitized_path}.bz2", status_code=302)

			content_type = mimetypes.guess_type(str(file_path))[0]
			if not content_type:
				content_type = "application/octet-stream"
			
			debug("Serving original file: {file_path}")
			return FileResponse(
				path=str(file_path),
				media_type=content_type,
				filename=file_path.name
			)
	except ValueError as e:
		debug("ValueError: {e}")
		http400()
	except HTTPException:
		raise  # Re-raise HTTP exceptions as-is
	except Exception as e:
		debug("Exception: {e}")
		http404()

def debug_database():
	try:
		with db_lock:
			conn = sqlite3.connect(DB_PATH)
			cursor = conn.cursor()
			cursor.execute("SELECT original_path, bz2_path FROM bz2_paths LIMIT 10")
			results = cursor.fetchall()
			conn.close()
			
			print("DEBUG: Database contents (first 10 entries):")
			for original, bz2 in results:
				print(f"  Original: {original}")
				print(f"  BZ2: {bz2}")
				print(f"  BZ2 exists: {Path(bz2).exists()}")
				print("---")
	except Exception as e:
		debug("Error reading database: {e}")

@app.get("/cs16/{path:path}")
async def serve_cs16_file(path: str, request: Request):
	try:
		sanitized_path = sanitize_path(path)
		
		if not is_path_allowed(sanitized_path, "cs16") or not is_extension_allowed(sanitized_path):
			http404()
		
		file_path = get_safe_path(CS16_PATH, sanitized_path)
		if not file_path:
			http404()
		
		content_type = mimetypes.guess_type(str(file_path))[0]
		if not content_type:
			content_type = "application/octet-stream"
		
		return FileResponse(
			path=str(file_path),
			media_type=content_type,
			filename=file_path.name
		)
	except ValueError:
		http400()
	except HTTPException:
		raise  # Re-raise HTTP exceptions as-is
	except Exception:
		http404()

@app.get("/health", response_class=PlainTextResponse)
async def health_check():
	css_exists = "OK" if os.path.exists(CSS_PATH) else "FAIL"
	cs16_exists = "OK" if os.path.exists(CS16_PATH) else "FAIL"
	bz2_exists = "OK" if os.path.exists(BZ2_PATH) else "FAIL"
	db_exists = "OK" if os.path.exists(DB_PATH) else "FAIL"
	return f"""FastDL Server Health Check
/css: {css_exists}
/cs16: {cs16_exists}
/bz2: {bz2_exists}
database: {db_exists}"""

def signal_handler(signum, frame):
	print("\nShutting down gracefully...")
	compression_executor.shutdown(wait=True)
	sys.exit(0)

if __name__ == "__main__":
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	
	print(f"Starting FastDL Server...")
	print(f"CSS Path: {CSS_PATH}")
	print(f"CS 1.6 Path: {CS16_PATH}")
	print(f"BZ2 Path: {BZ2_PATH}")
	print(f"Database Path: {DB_PATH}")
	print(f"Compression enabled: {ENABLE_COMPRESSION}")
	print(f"File watcher enabled: {ENABLE_WATCHER}")
	print(f"Server enabled: {ENABLE_SERVER}")
	print(f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
	
	os.makedirs(CSS_PATH, exist_ok=True)
	os.makedirs(CS16_PATH, exist_ok=True)
	
	init_db()
	
	observer = None
	if ENABLE_COMPRESSION:
		print("Starting initial compression...")
		initial_compression()
		import time
		time.sleep(2)
		debug_database()

		if ENABLE_WATCHER:
			print("Starting file watcher...")
			observer = start_file_watcher()
	
	if ENABLE_SERVER:
		try:
			print(f"Server is running on http://{HOST}:{PORT}")
			uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
		finally:
			if observer:
				observer.stop()
				observer.join()
			compression_executor.shutdown(wait=True)
	else:
		print("Server disabled, running compression/watcher only...")
		try:
			while True:
				time.sleep(1)
		except KeyboardInterrupt:
			print("Shutting down...")
		finally:
			if observer:
				observer.stop()
				observer.join()
			compression_executor.shutdown(wait=True)
