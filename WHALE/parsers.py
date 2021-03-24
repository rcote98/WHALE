
import pandas as pd
import numpy as np
import re

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text 

def generate_lines_that_match(string, fp):
    for line in fp:
        if re.search(string, line):
            yield line

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

def check_geometry_coverged(fname):

    with open(fname, "r") as f:
        pattern = "THE OPTIMIZATION HAS CONVERGED"
        for _ in generate_lines_that_match(pattern, f):
            return True
    return False

def check_real_frequencies(fname):

    vibrations = False
    with open(fname, "r") as f:
        pattern = "VIBRATIONAL FREQUENCIES"
        for _ in generate_lines_that_match(pattern, f):
            vibrations = True

    if vibrations == False:
        return None

    with open(fname, "r") as f:
        pattern = "***imaginary mode***"
        for _ in generate_lines_that_match(pattern, f):
            return False
    
    return True

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #    

# energies

def parse_scf_energy(fname):

    with open(fname, "r") as f:
        string = "Total Energy       :"
        for l in generate_lines_that_match(string, f):
            last_energy = l

    return float(last_energy.split()[3])

def parse_dispersion_correction(fname):

    with open(fname, "r") as f:
        string = "Dispersion correction    "
        for l in generate_lines_that_match(string, f):
            last_energy = l

    try:
        return float(last_energy.split()[2])
    except:
        return None

def parse_solvent_correction(fname):

    with open(fname, "r") as f:
        string = "Charge-correction       :"
        for l in generate_lines_that_match(string, f):
            last_charge = l

    with open(fname, "r") as f:
        string = "Free-energy"
        for l in generate_lines_that_match(string, f):
            last_free = l
            
    try:
        return float(last_charge.split()[2]), float(last_free.split()[3])
    except:
        return None

# frequencies

def parse_frequencies(fname):

    frequencies  = []
    with open(fname, "r") as f:
    
        found = False
        while not found:
            line = f.readline()
            string = "VIBRATIONAL FREQUENCIES"
            if re.search(string, line):
                found = True

        for _ in range(4):
            f.readline()
        
        while True:
            line = f.readline()
            
            if line.strip() == "":
                break
                
            frequencies.append(float(line.split()[1]))

    return np.array(frequencies)

def parse_normal_modes(fname):

    normal_modes = {}
    with open(fname, "r") as f:
    
        found = False
        while not found:
            line = f.readline()
            string = "NORMAL MODES"
            if re.search(string, line):
                found = True

        for _ in range(6):
            f.readline()
        
        while True:

            line = f.readline()
            line = line.split()

            if line == []:
                break

            if (len(line) == 3) or (len(line) == 6):
                last = [int(mode) for mode in line]
                for mode in last:
                    normal_modes[mode] = []

            if (len(line) == 4) or (len(line) == 7):
                coord = [float(c) for c in line[1:]]
                for i, c in enumerate(coord):
                    normal_modes[last[i]].append(c)

    nats = len(normal_modes.keys())

    for k in normal_modes.keys():
        normal_modes[k] = np.array(normal_modes[k]).reshape(int(nats/3),3)

    return normal_modes

# masses

def parse_masses(fname):
    pass

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #