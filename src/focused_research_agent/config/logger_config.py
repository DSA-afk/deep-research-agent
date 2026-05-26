from logging.handlers import RotatingFileHandler
import logging
from pathlib import Path


def setup_logging():
    """配置并返回应用程序的根记录器。

    记录器将错误级别日志写入到循环文件中
    项目的日志目录。如果已经配置了日志记录，
    现有记录器原封不动地返回。

    返回：
        logging.Logger：配置的根记录器。"""
    LOG_PATH = (
        Path(__file__).parent.parent.parent.parent
        / "logs"
        / "focused_research_agent.log"
    )
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    py_logger = logging.getLogger()
    py_logger.setLevel(logging.ERROR)

    if py_logger.handlers:
        return py_logger
    else:
        log_handler = RotatingFileHandler(
            filename=LOG_PATH, mode="a", maxBytes=1048576, backupCount=10
        )
        log_formatter = logging.Formatter(
            "%(name)s %(asctime)s %(levelname)s %(message)s"
        )
        log_handler.setFormatter(log_formatter)
        py_logger.addHandler(log_handler)

    return py_logger
