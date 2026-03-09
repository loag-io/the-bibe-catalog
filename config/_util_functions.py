# Initialize project environment
import sys; sys.path.insert(0, next((str(p) for p in __import__('pathlib').Path.cwd().parents if (p/'config').exists()), '.'))

from config.settings import *

# Import common libraries
from config._common_libraries import *

class ClockHandler:
    """Timer for tracking workflow duration in CDT"""
    
    def __init__(self):
        self.cdt = ZoneInfo('America/Chicago')
        self.start_dt = None
        self.end_dt = None
    
    def start(self):
        """Mark start time"""
        self.start_dt = datetime.now(self.cdt)
    
    def end(self):
        """Mark end time"""
        self.end_dt = datetime.now(self.cdt)
    
    def get_elapsed_time(self):
        """Get elapsed time as formatted string"""
        if not self.start_dt or not self.end_dt:
            return None
        
        elapsed = self.end_dt - self.start_dt
        seconds = int(elapsed.total_seconds())
        
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def get_start_time(self, format_str="%Y-%m-%d %I:%M:%S %p"):
        """Get formatted start time"""
        if not self.start_dt:
            return None
        return self.start_dt.strftime(format_str)
    
    def get_end_time(self, format_str="%Y-%m-%d %I:%M:%S %p"):
        """Get formatted end time"""
        if not self.end_dt:
            return None
        return self.end_dt.strftime(format_str)
    
    def get_start_timestamp(self):
        """Get start time as timestamp for hashing"""
        if not self.start_dt:
            return None
        return self.start_dt.isoformat()


class NotificationsHandler:
    """Handler for sending Discord workflow notifications"""
    
    def __init__(self, webhook_url: str, username: str = "notification-bot"):
        self.webhook_url = webhook_url
        self.username = username
    
    @staticmethod
    def generate_job_id(job_name: str, length: int = 16) -> str:
        """
        Generate a consistent Job ID from job name using SHA256 hash.
        Same job name always produces the same Job ID.
        
        Args:
            job_name: Name of the job
            length: Length of the ID (default 16)
            
        Returns:
            Fixed-length hexadecimal hash string
        """
        hash_obj = hashlib.sha256(job_name.encode())
        return hash_obj.hexdigest()[:length]
    
    @staticmethod
    def generate_run_id(start_timestamp: str, length: int = 16) -> str:
        """
        Generate a unique Run ID from start timestamp using SHA256 hash.
        Each run gets a unique Run ID based on its start time.
        
        Args:
            start_timestamp: ISO format timestamp
            length: Length of the ID (default 16)
            
        Returns:
            Fixed-length hexadecimal hash string
        """
        hash_obj = hashlib.sha256(start_timestamp.encode())
        return hash_obj.hexdigest()[:length]
    
    def send_discord_message(
        self,
        message: str,
        timeout: int = 10,
        retry_count: int = 3
    ):
        """
        Send a formatted message to Discord via webhook.
        
        Args:
            message: Pre-formatted message content
            timeout: Request timeout in seconds
            retry_count: Number of retry attempts
        """
        
        # Input validation
        if not message or not self.webhook_url:
            print("  → Message and webhook_url are required")
            return
        
        if not self.webhook_url.startswith("https://discord.com/api/webhooks/"):
            print("  → nvalid Discord webhook URL")
            return
        
        # Discord has 2000 char limit for content
        max_length = 1950
        if len(message) > max_length:
            message = message[:max_length] + "\n... (truncated)"
            print(f"  → Message truncated to {max_length} characters")
        
        data = {
            "content": message,
            "username": self.username
        }
        
        # Retry logic with exponential backoff
        for attempt in range(retry_count):
            try:
                response = requests.post(
                    self.webhook_url,
                    json=data,
                    timeout=timeout,
                    headers={"Content-Type": "application/json"}
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = response.json().get("retry_after", 1)
                    print(f"  → Rate limited. Retry after {retry_after}s")
                    time.sleep(retry_after)
                    continue
                
                # Success check
                if response.status_code == 204:
                    print("  → Discord notification sent successfully")
                    return
                
                # Log other status codes
                print(f"  → Discord webhook returned {response.status_code}: {response.text}")
                
            except requests.exceptions.Timeout:
                print(f"  → Discord webhook timeout (attempt {attempt + 1}/{retry_count})")
            except requests.exceptions.ConnectionError:
                print(f"> Connection error to Discord (attempt {attempt + 1}/{retry_count})")
            except Exception as e:
                print(f"  → Unexpected error sending Discord message: {e}")
                
            # Exponential backoff before retry
            if attempt < retry_count - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
    
    def format_workflow_notification(
        self,
        workflow_name: str,
        status: str,
        job_name: str,
        start_timestamp: str,
        environment: Optional[str] = None,
        debug: Optional[bool] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        duration: Optional[str] = None,
        custom_message: Optional[str] = None,
        additional_details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format a workflow notification message in the specified style.
        
        Args:
            workflow_name: Name of the workflow
            status: Status (SUCCESS, FAILED, WARNING, RUNNING, etc.)
            job_name: Job name for generating Job ID
            start_timestamp: Start timestamp for generating Run ID
            environment: Environment name (dev, staging, prod, etc.)
            debug: Whether debug mode is enabled
            start_time: Workflow start timestamp (formatted)
            end_time: Workflow end timestamp (formatted)
            duration: Human-readable duration
            custom_message: Custom summary message
            additional_details: Any extra key-value pairs to include
            
        Returns:
            Formatted message string
        """
        
        # Generate IDs (both 16 characters)
        job_id = self.generate_job_id(job_name)
        run_id = self.generate_run_id(start_timestamp)
        
        # Status emoji and label mapping
        status_map = {
            "SUCCESS": "✅ **[SUCCESS]**",
            "FAILED": "❌ **[FAILED]**",
            "WARNING": "⚠️ **[WARNING]**",
            "RUNNING": "🔄 **[RUNNING]**",
            "STARTED": "▶️ **[STARTED]**",
            "CANCELLED": "🚫 **[CANCELLED]**",
            "TIMEOUT": "⏱️ **[TIMEOUT]**"
        }
        
        status_upper = status.upper()
        status_header = status_map.get(status_upper, f"ℹ️ **[{status_upper}]**")
        
        # Build message sections
        lines = [
            f"{status_header} - {workflow_name}"
        ]
        
        # Run Details section (always include Job ID and Run ID)
        lines.append("\n**Run Details:**")
        lines.append(f"Job ID: {job_id}")
        lines.append(f"Run ID: {run_id}")
        if environment is not None:
            lines.append(f"Environment: {environment}")
        if debug is not None:
            lines.append(f"Debug: {debug}")
        
        # Run Metrics section
        if any([start_time, end_time, duration]):
            lines.append("\n**Run Metrics:**")
            if start_time:
                lines.append(f"Start Time: {start_time}")
            if end_time:
                lines.append(f"End Time: {end_time}")
            if duration:
                lines.append(f"Duration: {duration}")
        
        # Additional details
        if additional_details:
            lines.append("\n**Additional Details:**")
            for key, value in additional_details.items():
                lines.append(f"{key}: {value}")
        
        # Custom message
        if custom_message:
            lines.append(f"\n**Message:**\n{custom_message}\n")
        
        return "\n".join(lines)
    
    def send_workflow_notification(
        self,
        workflow_name: str,
        job_name: str,
        status: str,
        timer: ClockHandler,
        environment: Optional[str] = None,
        debug: Optional[bool] = None,
        custom_message: Optional[str] = None,
        additional_details: Optional[Dict[str, Any]] = None
    ):
        """
        Convenience function to format and send workflow notification.
        
        Args:
            workflow_name: Name of the workflow
            job_name: Job name for generating Job ID
            status: Status (SUCCESS, FAILED, WARNING, etc.)
            timer: ClockHandler instance with timing data
            environment: Environment name
            debug: Debug mode flag
            custom_message: Custom summary message
            additional_details: Any extra key-value pairs to include
        """
        message = self.format_workflow_notification(
            workflow_name=workflow_name,
            status=status,
            job_name=job_name,
            start_timestamp=timer.get_start_timestamp(),
            environment=environment,
            debug=debug,
            start_time=timer.get_start_time(),
            end_time=timer.get_end_time(),
            duration=timer.get_elapsed_time(),
            custom_message=custom_message,
            additional_details=additional_details
        )
        
        self.send_discord_message(message=message)