import logging

position_mapping = '/mnt/ld/sisu3/sisu3_twk_mapping.txt.gz'
tempdir = '/mnt/ld/ld_temp'

panels = {
    'sisu3': {
        'file_template': '/mnt/ld/sisu3/pre_phased_[CHROMOSOME].twk',
        'X_in_filename': '23'
    }
}

window = {
    'min': 100000,
    'max': 5000000
}

log_level = logging.INFO
num_decimals = 4
