# utils/logger.py

import logging
import os

def setup_logger(name, log_file, level=logging.INFO):
    """
    Set up a logger with the specified name and log file.
    
    Parameters:
    - name: Name of the logger.
    - log_file: File path to store logs.
    - level: Logging level.
    
    Returns:
    - Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create log directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Avoid adding multiple handlers to the logger
    if not logger.handlers:
        # Create file handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(level)

        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(level)

        # Create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        # Add handlers to the logger
        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger
