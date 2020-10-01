import os
import logging

import numpy as np
from scipy.signal import find_peaks

from hplc_analyze import chemstation

PEAK_HEIGHT = 200
PEAK_PROXIMITY = 100  # entire chromatogram is around 4000 points
REAGENTS_FOLDER = "/mnt/scapa4/group/Hessam Mehr/Data/Discovery/data/reagents/"
REAGENTS = [
    REAGENTS_FOLDER + i
    for i in os.listdir(REAGENTS_FOLDER)
    if "HPLC" in i and "BLANK" not in i
]
HPLC_FILENAME = "DAD1A.npz"


def get_reagent_file(n):
    for i in REAGENTS:
        if i.split("_")[1] == n:
            return i


def load_hplc(experiment_dir: str, channel: str = "A"):
    logger = logging.getLogger("experiment-manager")
    filename = os.path.join(experiment_dir, f"DAD1{channel}")
    npz_file = filename + ".npz"
    if os.path.exists(npz_file):
        # already processed
        data = np.load(npz_file)
        return data["times"], data["values"]
    else:
        logger.debug(f"Not found {npz_file}")
        ch_file = filename + ".ch"
        data = chemstation.CHFile(ch_file)
        np.savez_compressed(npz_file, times=data.times, values=data.values)
        return np.array(data.times), np.array(data.values)


def forge_blank_name(filename):
    parts = filename.split("_")
    parts.insert(2, "BLANK")
    return "_".join(parts)


def hplc_process(filename):
    """
    function to compare hplc of the mixture with its blank and the reagents
    :param filename: full path of the hplc folder (ex:'Z:\\group\\Hessam Mehr\\Data\\Discovery\\data\\0_17-7_HPLC'
    :return: 0 if no new peaks are observed, 1 if new peaks are found
    """
    logger = logging.getLogger("experiment-manager")
    reagents_n = filename.split("_")[1].split("-")
    old_peaks = []
    for r in reagents_n:
        r_file = get_reagent_file(r)
        r_time, r_val = load_hplc(r_file)
        r_peaks, _ = find_peaks(r_val, height=PEAK_HEIGHT, distance=20)
        old_peaks.extend(r_peaks)
    b_time, b_val = load_hplc(forge_blank_name(filename))
    b_peaks, _ = find_peaks(b_val, height=PEAK_HEIGHT, distance=20)
    old_peaks.extend(b_peaks)

    time, val = load_hplc(filename)
    peaks, _ = find_peaks(val, height=PEAK_HEIGHT, distance=20)

    new_peaks = []
    logger.info(f"peaks {peaks}")
    logger.info(f"old_peaks {old_peaks}")
    for p in peaks:
        for o in old_peaks:
            if o - PEAK_PROXIMITY < p < o + PEAK_PROXIMITY:
                old_peaks.remove(o)
                break
        else:
            new_peaks.append(p)
    logger.info(f"old_peaks {new_peaks}")
    if new_peaks:
        return False
    else:
        return True


if __name__ == "__main__":
    print(hplc_process("Z:\\group\\Hessam Mehr\\Data\\Discovery\\data\\0_17-7_HPLC"))
