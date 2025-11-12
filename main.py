from application.gui import GUI
from constants import SAMPLE_TO_NES_NAME, SAMPLE_TO_NES_VERSION
from utils.logger import logger


def run():
    logger.info(f"{SAMPLE_TO_NES_NAME} v{SAMPLE_TO_NES_VERSION}")
    application = GUI()
    try:
        application.run()
    except KeyboardInterrupt:
        exit()


if __name__ == "__main__":
    run()
