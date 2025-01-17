#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#

import argparse
import gzip
import os
import sys
import warnings

from rdkit import Chem

from meeko import PDBQTMolecule
from meeko import RDKitMolCreate


def cmd_lineparser():
    parser = argparse.ArgumentParser(description='Export docking results to SDF format')
    parser.add_argument(dest='docking_results_filename', nargs = "+",
                        action='store', help='Docking output file, either a PDBQT \
                        file from Vina or a DLG file from AD-GPU.')
    parser.add_argument('-o', '--output_filename', dest='output_filename',
                        action='store', help='Output molecule filename. If not specified, suffix _docked is \
                        added to the filename based on the input molecule file, and using the same \
                        molecule file format')
    parser.add_argument('-s', '--suffix', dest='suffix_name', default='_docked',
                        action='store', help='Add suffix to output filename if -o/--output_filename \
                        not specified. WARNING: If specified as empty string (\'\'), this will overwrite \
                        the original molecule input file (default: _docked).')
    parser.add_argument('-c', '--only_cluster_leads', action='store_true',
                        help='Keep top pose from each AutoDock-GPU cluster, sorted by \
                        predicted free energy of cluster lead.')
    parser.add_argument('-', '--',  dest='redirect_stdout', action='store_true',
                        help='do not write file, redirect output to STDOUT. Arguments -o/--output_filename \
                        is ignored.')
    return parser.parse_args()

args = cmd_lineparser()

docking_results_filenames = args.docking_results_filename
output_filename = args.output_filename
suffix_name = args.suffix_name
only_cluster_leads = args.only_cluster_leads
redirect_stdout = args.redirect_stdout

if output_filename is not None and len(docking_results_filenames) > 1:
    print("Option -o/--output_filename incompatible with multiple input files", file=sys.stderr)
    sys.exit()
 
for filename in docking_results_filenames:
    is_dlg = filename.endswith('.dlg') or filename.endswith(".dlg.gz")
    if filename.endswith(".gz"):
        with gzip.open(filename) as f:
            string = f.read().decode()
    else:
        with open(filename) as f:
            string = f.read()
    pdbqt_mol = PDBQTMolecule(string, is_dlg=is_dlg, skip_typing=True)

    output_string, failures = RDKitMolCreate.write_sd_string(
            pdbqt_mol, only_cluster_leads=only_cluster_leads)
    output_format = 'sdf'
    for i in failures:
        warnings.warn("molecule %d not converted to RDKit/SD File" % i)
    if len(failures) == len(pdbqt_mol._atom_annotations["mol_index"]):
        msg = "\nCould not convert to RDKit. Maybe meeko was not used for preparing\n"
        msg += "the input PDBQT for docking, and the SMILES string is missing?\n"
        msg += "Except for standard protein sidechains, all ligands and flexible residues\n"
        msg += "require a REMARK SMILES line in the PDBQT, which is added automatically by meeko."
        raise RuntimeError(msg)
    if not redirect_stdout:
        if output_filename is None:
            fn = '%s%s.%s' % (os.path.splitext(filename)[0], suffix_name, output_format)
        else:
            fn = output_filename
        print(output_string, file=open(fn, 'w'), end="")
    else:
        print(output_string)
