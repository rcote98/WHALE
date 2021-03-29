from WHALE.structures import Geometry
import WHALE.parsers as p

from shutil import copyfile
import numpy as np
import os, csv

ORCA_EXEC = os.getenv("ORCA_EXEC", default = None) 

def log(log_file, message):

    with open(log_file, "a+") as f:
        # Move read cursor to the start of file.
        f.seek(0)
        # If file is not empty then append '\n'
        data = f.read(100)
        if len(data) > 0 :
            f.write("\n")
        # Append text at the end of file
        f.write(message)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#                         simple jobs                           #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

def create_input(fname, geom, settings, run_type="sp", inc_ghost=True):

    if run_type == "sp" or run_type == "energy":
        comment = "# Single point ORCA input file."
        mode    = "SP"
    elif run_type == "opt":
        comment = "# Geometry ORCA input file."
        mode    = "OPT NUMFREQ"
    else:
        print("Please, choose a compliant run type.")
        exit

    method      = settings["method"]
    basis       = settings["basis"] 

    try:
        addons  = settings["addons"]
    except:
        addons  = ""

    try:
        charge  = settings["charge"]
    except:
        charge  = 0

    try:
        spin    = settings["spin"]
    except:
        spin    = 1

    try:       
        nproc   = settings["nproc"]
    except:
        nproc   =   1

    try:
        solvent = settings["solvent"]
    except:
        solvent = None

    with open(fname, "w") as f:

        tsv = csv.writer(f, delimiter="\t")
        
        tsv.writerow([comment])
        tsv.writerow(["!", method, addons, basis])
        tsv.writerow(["!", mode])
        tsv.writerow([" "])

        if solvent != None:
            tsv.writerow(["%CPCM"])
            tsv.writerow(["    ", "SMD", "True"])
            f.write(f"    SMD    True")
            f.write(f'    SMDSolvent    "{solvent}"\n')
            tsv.writerow(["END"])
            tsv.writerow([" "])

        tsv.writerow(["%PAL NPROCS", nproc, "END"])
        tsv.writerow([" "])
        tsv.writerow(["* xyz ", charge, spin])

        for i in range(geom.nats):
            if (i in geom.ghost) and inc_ghost:
                line = [geom.species[i] + ":"] + ["{:10.8F}".format(d) for d in geom.positions[i,:]]
                tsv.writerow(line)
            if (i not in geom.ghost):
                line = [geom.species[i]] + ["{:10.8F}".format(d) for d in geom.positions[i,:]]
                tsv.writerow(line)

        tsv.writerow(["*"])

def single_point_run(folder, geom, settings, inc_ghost=True):

    original_dir = os.getcwd()
    working_dir = os.path.abspath(folder)

    try:
        os.makedirs(working_dir)
    except:
        pass

    os.chdir(working_dir)
    create_input("ORCA_run.inp", geom, settings, inc_ghost=inc_ghost) 
    os.system(ORCA_EXEC + " " + "ORCA_run.inp > ORCA_output.txt")
    os.chdir(original_dir)

    return True

def geometry_run(folder, geom, settings):

    original_dir = os.getcwd()
    working_dir = os.path.abspath(folder)

    try:
        os.makedirs(working_dir)
    except:
        pass

    os.chdir(working_dir)
    create_input("ORCA_run.inp", geom, settings, run_type="opt") 
    os.system(ORCA_EXEC + " " + "ORCA_run.inp > ORCA_output.txt")
    
    #converged   = p.check_geometry_coverged("ORCA_output.txt")
    #minimum     = p.check_real_frequencies("ORCA_output.txt")

    os.chdir(original_dir)

    return True, True

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#                       more complex jobs                       #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

def optimize_geometry(folder, geom, settings):

    # add prints and shit
    original_dir = os.getcwd()
    base_dir = os.path.abspath(folder)
    log_file = os.path.join(base_dir, "run.log")
    
    try:
        os.makedirs(folder)
    except:
        pass

    os.chdir(base_dir)
    rn = 0

    def perturb_geometry(folder, scaling=0.5):

        g = Geometry()
        g.read_xyz(os.path.join(folder, "ORCA_run.xyz"))
        frecs   = p.parse_frequencies(os.path.join(folder, "ORCA_output.txt"))
        n_modes = p.parse_normal_modes(os.path.join(folder, "ORCA_output.txt"))
        im_mode = np.argmax(frecs < 0)
        g.positions = g.positions + scaling*n_modes[im_mode]
        return g, im_mode

    # optimize the geometry
    run = f"run{rn}"
    run_dir = os.path.join(base_dir, run)
    log(log_file, run + ": starting run")
    c, m = geometry_run(run_dir, geom, settings)
    geom.read_xyz(os.path.join(run_dir, "ORCA_run.xyz"))

    while not c:

        run += 1
        run = f"run{rn}"
        log(log_file, run + ": attempting to reach convergence")
        c, m = geometry_run(run, geom, settings)
        geom.read_xyz(os.path.join(base_dir, run, "ORCA_run.xyz"))

    while not m:

        geom, im = perturb_geometry(os.path.join(base_dir, run))

        run +=1
        run = f"run{rn}"
        log(log_file, run + f": correcting imaginary mode {im}")
        c, m = geometry_run(run, geom, settings)
        geom.read_xyz(os.path.join(base_dir, run, "ORCA_run.xyz"))

    geom.write_xyz(os.path.join(base_dir, "ORCA_run.xyz"))
    final = os.path.abspath(run)

    copyfile(os.path.join(final, "ORCA_output.txt"), 
    os.path.join(base_dir, "ORCA_output.txt"))

    os.chdir(original_dir)

def bsse_correction(folder, geom, settings, monomers):

    # add prints and shit
    original_dir = os.getcwd()
    base_dir = os.path.abspath(folder)

    try:
        os.makedirs(folder)
    except:
        pass

    os.chdir(base_dir)
    all_atoms = set(range(geom.nats))

    for m in monomers:

        mon_setts = settings.copy()
        mon_setts["charge"] = m[2]
        mon_setts["solvent"] = None
        geom.ghost = all_atoms - set(m[1])

        # full basis
        run_dir = os.path.join(base_dir, m[0] + "-f_basis")
        single_point_run(run_dir, geom, mon_setts)  

        # reduced basis
        run_dir = os.path.join(base_dir, m[0] + "-r_basis")
        geom.ghost = all_atoms - set(m[1])
        single_point_run(run_dir, geom, mon_setts, inc_ghost=False)  

    os.chdir(original_dir)

    return True