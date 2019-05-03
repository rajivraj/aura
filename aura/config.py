# coding=utf-8
import os
import sys
import resource
import logging
import configparser
from pathlib import Path
from logging.handlers import RotatingFileHandler


try:
    import simplejson as json
except ImportError:
    import json


CFG = configparser.ConfigParser(default_section='default')
SEMANTIC_RULES = None
LOG_FMT = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOG_STREAM = logging.StreamHandler()
LOG_ERR = RotatingFileHandler("aura_errors.log", maxBytes=1024**2, backupCount=5)
LOG_ERR.setLevel(logging.ERROR)

logger = logging.getLogger('aura')


if os.environ.get('AURA_DEBUG_LEAKS'):
    import gc
    gc.set_debug(gc.DEBUG_LEAK)



def configure_logger(level):
    logger.setLevel(level)
    LOG_STREAM.setLevel(level)
    LOG_STREAM.setFormatter(LOG_FMT)
    logger.addHandler(LOG_STREAM)
    logger.addHandler(LOG_ERR)

def get_logger(name):
    _log = logging.getLogger(name)
    _log.addHandler(LOG_ERR)
    _log.addHandler(LOG_STREAM)
    return _log


def load_config():
    global SEMANTIC_RULES, CFG
    pth = Path(os.environ.get('AURA_CFG', 'config.ini'))
    if pth.is_dir():
        pth /= "config.ini"

    if not pth.is_file():
        logger.fatal(f"Invalid configuration path: {pth}")
        sys.exit(1)

    CFG.read(pth)

    json_sig_pth = (pth.parent / CFG.get('aura', 'semantic-rules', fallback='signatures.json')).absolute()

    if not json_sig_pth.is_file:
        logger.fatal(f"Invalid path to the signatures file: {json_sig_pth}")
        sys.exit(1)

    # this environment variable is needed by python AST parser to pick up location of signatures
    if not os.environ.get('AURA_SIGNATURES'):
        os.putenv('AURA_SIGNATURES', os.fspath(json_sig_pth))

    SEMANTIC_RULES = json.loads(json_sig_pth.read_text())

    if 'LOG' in os.environ:
        log_level = logging.getLevelName(os.getenv('LOG'))
    else:
        log_level = logging.getLevelName(CFG.get('aura', 'log-level', fallback='warning').upper())

    logging.basicConfig(
        format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level = log_level
    )
    logger.setLevel(log_level)


    if CFG['aura'].get('rlimit-memory'):
        rss = int(CFG['aura']['rlimit-memory'])
        resource.setrlimit(resource.RLIMIT_RSS, (rss, rss))

    if CFG['aura'].get('rlimit-fsize'):
        fsize = int(CFG['aura']['rlimit-fsize'])
        resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))


load_config()