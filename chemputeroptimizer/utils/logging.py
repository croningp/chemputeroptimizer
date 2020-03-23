import logging


def get_logger(level=logging.DEBUG):

    logger = logging.getLogger('optimizer')
    logger.setLevel(logging.DEBUG)

    ff = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(ff)

    fh = logging.FileHandler('optimizer.log', mode='a')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(ff)

    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger
