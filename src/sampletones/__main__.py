from sampletones.application.gui import GUI
from sampletones.constants.application import SAMPLETONES_NAME, SAMPLETONES_VERSION
from sampletones.utils import logger


def main():
    logger.info(f"{SAMPLETONES_NAME} v{SAMPLETONES_VERSION}")
    application = GUI()
    try:
        application.run()
    except KeyboardInterrupt:
        logger.info("Application terminated")
    else:
        logger.info("Application closed")


if __name__ == "__main__":
    main()
