from sampletones.application.gui import GUI
from sampletones.constants import SAMPLE_TO_NES_NAME, SAMPLE_TO_NES_VERSION
from sampletones.utils import logger


def main():
    logger.info(f"{SAMPLE_TO_NES_NAME} v{SAMPLE_TO_NES_VERSION}")
    application = GUI()
    try:
        application.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
