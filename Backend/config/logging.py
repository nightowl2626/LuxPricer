"""
Logging configuration module.
Sets up logging based on application settings.
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from config.settings import settings

def setup_logging():
    """
    Configure logging for the application based on settings.
    Creates console and file handlers if configured.
    """
    # Get logging configuration from settings
    log_level = getattr(logging, settings.logging.level.upper())
    log_format = settings.logging.format
    log_file = settings.logging.file
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Clear existing handlers to avoid duplication
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatters
    formatter = logging.Formatter(log_format)
    
    # Always add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if configured
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Create rotating file handler (max 10MB per file, keep 5 backups)
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Return the configured logger
    return logger

# Create a function to get a named logger
def get_logger(name):
    """
    Get a named logger configured with application settings.
    
    Args:
        name (str): Name of the logger (usually __name__)
        
    Returns:
        Logger: Configured logger instance
    """
    return logging.getLogger(name) 