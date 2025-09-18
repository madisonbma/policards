import logging
import os


logfile_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gen_cards.log')
my_logger = logging.getLogger(__name__)
my_logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(logfile_path)
console_handler = logging.StreamHandler()

file_handler.setLevel(logging.DEBUG)
console_handler.setLevel(logging.WARNING)

formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

my_logger.addHandler(file_handler)
my_logger.addHandler(console_handler)
