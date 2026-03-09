# Standard library imports
import os
import sys
import re
import time
import hashlib
import threading
import tempfile
import shutil
import warnings
import xml.etree.ElementTree as ET
import json
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple, Optional, Literal
from urllib.parse import parse_qs, urljoin, urlparse, urlunsplit, urlencode
from urllib.robotparser import RobotFileParser
from dataclasses import dataclass, asdict, field
import concurrent.futures
from zoneinfo import ZoneInfo

# Third-party imports
import numpy as np
import pandas as pd
import requests
import yt_dlp
import duckdb
import pytz
import html2text
import ollama
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from IPython.display import display
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from sentence_transformers import SentenceTransformer

# Optional imports with fallback
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    print("Warning: whisper not installed. Install with: pip install openai-whisper")
    WHISPER_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    print("Warning: librosa not installed. Install with: pip install librosa")
    LIBROSA_AVAILABLE = False

# Silence warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)