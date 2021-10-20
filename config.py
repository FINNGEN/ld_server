import logging

tempdir = '/mnt/ld/ld_temp'

panels = {
    'sisu3': {
        'position_mapping': '/mnt/ld/sisu3/sisu3_twk_mapping.txt.gz',
        'file_template': '/mnt/ld/sisu3/pre_phased_[CHROMOSOME].twk',
        'X_in_filename': '23'
    },
    'sisu4': {
        'position_mapping': '/mnt/ld/sisu4/sisu4_twk_mapping.txt.gz',
        'file_template': '/mnt/ld/sisu4/chr[CHROMOSOME]_phased_SNPID.twk',
        'X_in_filename': '23'
    }
}

window = {
    'min': 100000,
    'max': 5000000
}

log_level = logging.INFO
num_decimals = 4
