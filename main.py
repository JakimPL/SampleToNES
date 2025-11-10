from browser.gui import GUI
from constants.general import SAMPLE_TO_NES_VERSION
from utils.logger import logger

if __name__ == "__main__":
    logger.info(f"SampleToNES v{SAMPLE_TO_NES_VERSION}")
    app = GUI()
    try:
        app.run()
    except KeyboardInterrupt:
        exit()
