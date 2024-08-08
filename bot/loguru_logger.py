import logging

from loguru import logger


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 6
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def configure_logging(logging_level: int, access_log_path: str) -> None:
    logging.basicConfig(handlers=[InterceptHandler()], level=logging_level)
    logger.add(
        access_log_path,
        serialize=True,
        level=logging_level,
        enqueue=True,
        backtrace=True,
        diagnose=True,
        encoding="UTF-8",
        rotation="256 MB",
        retention="7 days",
        compression="zip",
    )
