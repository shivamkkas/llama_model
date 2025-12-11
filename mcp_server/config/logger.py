
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from config import Config

def setup_logging():
    config = Config()
    log_file = config.log.LOG_FILE
    file_level = getattr(logging, config.log.LOG_FILE_LEVEL, logging.INFO)
    logger_level = getattr(logging, config.log.LOG_LEVEL, logging.DEBUG)
    enable_console = config.log.LOG_CONSOLE_ENABLED
    rotation = config.log.ROTATION

    log_dir = os.path.dirname(log_file)
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

    rotation_dict = vars(rotation)

    file_handler = TimedRotatingFileHandler(
        log_file,
        when=rotation_dict.get("when"),
        interval=rotation_dict.get("interval", 1),
        backupCount=rotation_dict.get("backupCount", 7)
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logger_level)
    root_logger.addHandler(file_handler)

    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logger_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Optional: Configure SQLAlchemy or other libraries
    for name in ['sqlalchemy.engine', 'sqlalchemy.orm']:
        sa_logger = logging.getLogger(name)
        sa_logger.setLevel(logging.INFO)
        sa_logger.propagate = False
        sa_logger.addHandler(file_handler)
